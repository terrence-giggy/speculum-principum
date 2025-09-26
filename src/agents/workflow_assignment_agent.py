"""
Workflow Assignment Agent

This module provides an automated agent that reviews GitHub issues with the 'site-monitor' 
label and assigns appropriate workflows based on issue content and labels.

Key responsibilities:
- Monitor unassigned issues with 'site-monitor' label
- Match issues to workflows using WorkflowMatcher
- Assign workflows when there's high confidence (single match)
- Request clarification when no clear workflow match exists
- Skip issues labeled with 'feature' or 'needs clarification'
- Add appropriate status labels during processing

The agent operates independently and can be run as part of a scheduled process
or triggered manually via CLI commands.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from ..workflow.workflow_matcher import WorkflowMatcher, WorkflowInfo, WorkflowMatcherError
from ..clients.github_issue_creator import GitHubIssueCreator
from ..utils.config_manager import ConfigManager
from ..utils.logging_config import get_logger, log_exception


class AssignmentAction(Enum):
    """Possible actions the agent can take on an issue"""
    SKIP_FEATURE = "skip_feature"
    SKIP_NEEDS_CLARIFICATION = "skip_needs_clarification"
    SKIP_ALREADY_ASSIGNED = "skip_already_assigned"
    ASSIGN_WORKFLOW = "assign_workflow"
    REQUEST_CLARIFICATION = "request_clarification"
    ERROR = "error"


@dataclass
class AssignmentResult:
    """Result of workflow assignment attempt"""
    issue_number: int
    action: AssignmentAction
    workflow_name: Optional[str] = None
    message: str = ""
    labels_added: Optional[List[str]] = None
    labels_removed: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.labels_added is None:
            self.labels_added = []
        if self.labels_removed is None:
            self.labels_removed = []


class WorkflowAssignmentAgent:
    """
    Agent that reviews issues and assigns workflows based on labels and content.
    
    This agent implements the missing step in the processing pipeline:
    1. Site Monitor creates issues with 'site-monitor' label
    2. → WorkflowAssignmentAgent assigns appropriate workflows ← (THIS AGENT)
    3. Issue Processor processes issues according to assigned workflow
    """
    
    # Labels to skip processing
    SKIP_LABELS = {'feature', 'needs clarification'}
    
    # Status labels managed by this agent
    NEEDS_CLARIFICATION_LABEL = 'needs clarification'
    AGENT_PROCESSING_LABEL = 'agent-processing'
    
    def __init__(self, 
                 github_token: str, 
                 repo_name: str, 
                 config_path: str = "config.yaml",
                 workflow_directory: str = "docs/workflow/deliverables"):
        """
        Initialize the workflow assignment agent.
        
        Args:
            github_token: GitHub API token
            repo_name: Repository name in format 'owner/repo'
            config_path: Path to configuration file
            workflow_directory: Directory containing workflow definitions
        """
        self.logger = get_logger(__name__)
        self.github = GitHubIssueCreator(github_token, repo_name)
        self.repo_name = repo_name
        
        # Load configuration
        try:
            self.config = ConfigManager.load_config(config_path)
            self.agent_username = self.config.agent.username if self.config.agent else 'github-actions[bot]'
        except Exception as e:
            self.logger.warning(f"Could not load config from {config_path}: {e}")
            self.agent_username = 'github-actions[bot]'
        
        # Initialize workflow matcher
        try:
            self.workflow_matcher = WorkflowMatcher(workflow_directory)
            workflow_count = len(self.workflow_matcher.get_available_workflows())
            self.logger.info(f"Initialized agent with {workflow_count} available workflows")
        except Exception as e:
            self.logger.error(f"Failed to initialize workflow matcher: {e}")
            raise
    
    def get_unassigned_site_monitor_issues(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get unassigned issues with 'site-monitor' label that need workflow assignment.
        
        Args:
            limit: Maximum number of issues to return
            
        Returns:
            List of issue data dictionaries
        """
        try:
            # Get all open site-monitor issues
            issues = self.github.get_issues_with_labels(['site-monitor'], state='open')
            
            candidate_issues = []
            for issue in issues:
                issue_labels = {label.name for label in issue.labels}
                
                # Skip if already assigned
                if issue.assignee is not None:
                    continue
                
                # Skip if has exclusion labels
                if issue_labels.intersection(self.SKIP_LABELS):
                    continue
                
                # Convert to dictionary format
                issue_data = {
                    'number': issue.number,
                    'title': issue.title,
                    'body': issue.body or "",
                    'labels': list(issue_labels),
                    'assignee': None,
                    'created_at': issue.created_at.isoformat() if issue.created_at else None,
                    'updated_at': issue.updated_at.isoformat() if issue.updated_at else None,
                    'url': issue.html_url,
                    'user': issue.user.login if issue.user else None
                }
                
                candidate_issues.append(issue_data)
                
                # Apply limit
                if limit and len(candidate_issues) >= limit:
                    break
            
            self.logger.info(f"Found {len(candidate_issues)} candidate issues for workflow assignment")
            return candidate_issues
        
        except Exception as e:
            log_exception(self.logger, "Failed to get unassigned site-monitor issues", e)
            return []
    
    def analyze_issue_for_workflow(self, issue_data: Dict[str, Any]) -> Tuple[Optional[WorkflowInfo], str]:
        """
        Analyze an issue to determine the best workflow match.
        
        Args:
            issue_data: Issue data dictionary
            
        Returns:
            Tuple of (WorkflowInfo if found, explanation message)
        """
        try:
            issue_labels = issue_data.get('labels', [])
            
            # Use workflow matcher to find best match
            workflow, message = self.workflow_matcher.get_best_workflow_match(issue_labels)
            
            if workflow:
                self.logger.debug(f"Issue #{issue_data['number']}: {message}")
            else:
                self.logger.debug(f"Issue #{issue_data['number']}: No workflow match - {message}")
            
            return workflow, message
            
        except WorkflowMatcherError as e:
            error_msg = f"Workflow matching error: {e}"
            self.logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during workflow analysis: {e}"
            log_exception(self.logger, "Issue workflow analysis failed", e)
            return None, error_msg
    
    def assign_workflow_to_issue(self, 
                               issue_number: int, 
                               workflow: WorkflowInfo,
                               dry_run: bool = False) -> AssignmentResult:
        """
        Assign a specific workflow to an issue by adding workflow labels.
        
        Args:
            issue_number: GitHub issue number
            workflow: Workflow to assign
            dry_run: If True, don't make actual changes
            
        Returns:
            AssignmentResult with outcome details
        """
        try:
            # Determine labels to add (workflow trigger labels)
            labels_to_add = []
            current_issue = self.github.repo.get_issue(issue_number)
            current_labels = {label.name for label in current_issue.labels}
            
            # Add workflow trigger labels that aren't already present
            for trigger_label in workflow.trigger_labels:
                if trigger_label not in current_labels:
                    labels_to_add.append(trigger_label)
            
            if not labels_to_add:
                # Workflow labels already present
                message = f"Workflow '{workflow.name}' labels already present"
                self.logger.info(f"Issue #{issue_number}: {message}")
                return AssignmentResult(
                    issue_number=issue_number,
                    action=AssignmentAction.ASSIGN_WORKFLOW,
                    workflow_name=workflow.name,
                    message=message
                )
            
            if not dry_run:
                # Add the workflow trigger labels
                for label in labels_to_add:
                    current_issue.add_to_labels(label)
                
                # Add comment explaining the assignment
                comment_body = (
                    f"🤖 **Workflow Assignment**\n\n"
                    f"I've assigned the **{workflow.name}** workflow to this issue.\n\n"
                    f"**Added labels:** {', '.join(labels_to_add)}\n\n"
                    f"The issue will be processed according to this workflow's specifications. "
                    f"If this assignment is incorrect, please remove the workflow labels and add "
                    f"more specific labels to help with proper classification."
                )
                current_issue.create_comment(comment_body)
            
            message = f"Assigned workflow '{workflow.name}' (labels: {', '.join(labels_to_add)})"
            self.logger.info(f"Issue #{issue_number}: {message}")
            
            return AssignmentResult(
                issue_number=issue_number,
                action=AssignmentAction.ASSIGN_WORKFLOW,
                workflow_name=workflow.name,
                message=message,
                labels_added=labels_to_add
            )
            
        except Exception as e:
            error_msg = f"Failed to assign workflow '{workflow.name}': {e}"
            log_exception(self.logger, f"Workflow assignment failed for issue #{issue_number}", e)
            
            return AssignmentResult(
                issue_number=issue_number,
                action=AssignmentAction.ERROR,
                workflow_name=workflow.name,
                message=error_msg
            )
    
    def request_clarification_for_issue(self, 
                                      issue_number: int, 
                                      reason: str,
                                      suggestions: Optional[List[str]] = None,
                                      dry_run: bool = False) -> AssignmentResult:
        """
        Request clarification for an issue that couldn't be matched to a workflow.
        
        Args:
            issue_number: GitHub issue number
            reason: Reason why clarification is needed
            suggestions: List of suggested workflow labels
            dry_run: If True, don't make actual changes
            
        Returns:
            AssignmentResult with outcome details
        """
        try:
            if suggestions is None:
                suggestions = []
            
            current_issue = self.github.repo.get_issue(issue_number)
            current_labels = {label.name for label in current_issue.labels}
            
            labels_to_add = []
            
            # Add 'needs clarification' label if not already present
            if self.NEEDS_CLARIFICATION_LABEL not in current_labels:
                labels_to_add.append(self.NEEDS_CLARIFICATION_LABEL)
            
            if not dry_run:
                # Add labels
                for label in labels_to_add:
                    current_issue.add_to_labels(label)
                
                # Create clarification comment
                comment_parts = [
                    "🤖 **Workflow Clarification Needed**\n",
                    f"**Issue:** {reason}\n"
                ]
                
                if suggestions:
                    comment_parts.extend([
                        "\n**Suggested workflow labels:**\n",
                        "\n".join(f"- `{label}`" for label in suggestions),
                        "\n"
                    ])
                else:
                    # Get general suggestions
                    current_issue_labels = [label.name for label in current_issue.labels]
                    general_suggestions = self.workflow_matcher.get_workflow_suggestions(current_issue_labels)
                    if general_suggestions:
                        comment_parts.extend([
                            "\n**Available workflow labels:**\n",
                            "\n".join(f"- `{label}`" for label in general_suggestions[:10]),  # Limit to 10
                            "\n"
                        ])
                
                comment_parts.append(
                    "\nPlease add one or more workflow labels to help me determine how to process this issue. "
                    "Once you've added appropriate labels, I'll remove the 'needs clarification' label "
                    "and assign the correct workflow."
                )
                
                comment_body = "".join(comment_parts)
                current_issue.create_comment(comment_body)
            
            message = f"Requested clarification: {reason}"
            self.logger.info(f"Issue #{issue_number}: {message}")
            
            return AssignmentResult(
                issue_number=issue_number,
                action=AssignmentAction.REQUEST_CLARIFICATION,
                message=message,
                labels_added=labels_to_add
            )
            
        except Exception as e:
            error_msg = f"Failed to request clarification: {e}"
            log_exception(self.logger, f"Clarification request failed for issue #{issue_number}", e)
            
            return AssignmentResult(
                issue_number=issue_number,
                action=AssignmentAction.ERROR,
                message=error_msg
            )
    
    def process_issue_assignment(self, issue_data: Dict[str, Any], dry_run: bool = False) -> AssignmentResult:
        """
        Process a single issue for workflow assignment.
        
        Args:
            issue_data: Issue data dictionary
            dry_run: If True, don't make actual changes
            
        Returns:
            AssignmentResult with processing outcome
        """
        issue_number = issue_data['number']
        issue_labels = set(issue_data.get('labels', []))
        
        try:
            # Check for skip conditions
            if issue_labels.intersection(self.SKIP_LABELS):
                skip_label = next(iter(issue_labels.intersection(self.SKIP_LABELS)))
                if skip_label == 'feature':
                    action = AssignmentAction.SKIP_FEATURE
                else:
                    action = AssignmentAction.SKIP_NEEDS_CLARIFICATION
                
                message = f"Skipping issue with '{skip_label}' label"
                self.logger.debug(f"Issue #{issue_number}: {message}")
                
                return AssignmentResult(
                    issue_number=issue_number,
                    action=action,
                    message=message
                )
            
            # Analyze issue for workflow match
            workflow, analysis_message = self.analyze_issue_for_workflow(issue_data)
            
            if workflow:
                # High confidence match - assign workflow
                return self.assign_workflow_to_issue(issue_number, workflow, dry_run)
            else:
                # No clear match - request clarification
                suggestions = self.workflow_matcher.get_workflow_suggestions(list(issue_labels))
                return self.request_clarification_for_issue(
                    issue_number, 
                    analysis_message,
                    suggestions[:5],  # Limit to top 5 suggestions
                    dry_run
                )
                
        except Exception as e:
            error_msg = f"Unexpected error processing issue: {e}"
            log_exception(self.logger, f"Issue processing failed for issue #{issue_number}", e)
            
            return AssignmentResult(
                issue_number=issue_number,
                action=AssignmentAction.ERROR,
                message=error_msg
            )
    
    def process_issues_batch(self, 
                           limit: Optional[int] = None,
                           dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a batch of issues for workflow assignment.
        
        Args:
            limit: Maximum number of issues to process
            dry_run: If True, don't make actual changes
            
        Returns:
            Dictionary with processing statistics and results
        """
        start_time = time.time()
        self.logger.info(f"Starting workflow assignment batch processing (limit: {limit}, dry_run: {dry_run})")
        
        try:
            # Get candidate issues
            issues = self.get_unassigned_site_monitor_issues(limit)
            
            if not issues:
                self.logger.info("No issues found for workflow assignment")
                return {
                    'total_issues': 0,
                    'processed': 0,
                    'results': [],
                    'statistics': {action.value: 0 for action in AssignmentAction},
                    'duration_seconds': time.time() - start_time
                }
            
            # Process each issue
            results = []
            statistics = {action.value: 0 for action in AssignmentAction}
            
            for issue_data in issues:
                try:
                    result = self.process_issue_assignment(issue_data, dry_run)
                    results.append(result)
                    statistics[result.action.value] += 1
                    
                    # Add small delay between issues to be respectful to GitHub API
                    time.sleep(0.1)
                    
                except Exception as e:
                    error_result = AssignmentResult(
                        issue_number=issue_data['number'],
                        action=AssignmentAction.ERROR,
                        message=f"Processing error: {e}"
                    )
                    results.append(error_result)
                    statistics[AssignmentAction.ERROR.value] += 1
                    
                    log_exception(self.logger, f"Failed to process issue #{issue_data['number']}", e)
            
            duration = time.time() - start_time
            
            # Log summary
            processed_count = sum(count for action, count in statistics.items() 
                                if action not in [AssignmentAction.SKIP_FEATURE.value, 
                                                AssignmentAction.SKIP_NEEDS_CLARIFICATION.value])
            
            self.logger.info(f"Batch processing completed: {processed_count}/{len(issues)} issues processed "
                           f"in {duration:.1f}s")
            
            for action, count in statistics.items():
                if count > 0:
                    self.logger.info(f"  {action}: {count}")
            
            return {
                'total_issues': len(issues),
                'processed': processed_count,
                'results': results,
                'statistics': statistics,
                'duration_seconds': duration
            }
            
        except Exception as e:
            log_exception(self.logger, "Batch processing failed", e)
            return {
                'total_issues': 0,
                'processed': 0,
                'results': [],
                'statistics': {action.value: 0 for action in AssignmentAction},
                'duration_seconds': time.time() - start_time,
                'error': str(e)
            }
    
    def get_assignment_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about current workflow assignment state.
        
        Returns:
            Dictionary with assignment statistics
        """
        try:
            # Get all site-monitor issues
            all_issues = self.github.get_issues_with_labels(['site-monitor'], state='open')
            
            stats = {
                'total_site_monitor_issues': len(all_issues),
                'unassigned': 0,
                'assigned': 0,
                'needs_clarification': 0,
                'feature_labeled': 0,
                'workflow_breakdown': {},
                'label_distribution': {}
            }
            
            for issue in all_issues:
                issue_labels = {label.name for label in issue.labels}
                
                # Count by assignment status
                if issue.assignee:
                    stats['assigned'] += 1
                else:
                    stats['unassigned'] += 1
                
                # Count special labels
                if 'needs clarification' in issue_labels:
                    stats['needs_clarification'] += 1
                if 'feature' in issue_labels:
                    stats['feature_labeled'] += 1
                
                # Count workflow assignments
                workflows = self.workflow_matcher.get_available_workflows()
                for workflow in workflows:
                    workflow_labels = set(workflow.trigger_labels)
                    if workflow_labels.intersection(issue_labels):
                        if workflow.name not in stats['workflow_breakdown']:
                            stats['workflow_breakdown'][workflow.name] = 0
                        stats['workflow_breakdown'][workflow.name] += 1
                
                # Count label distribution
                for label_name in issue_labels:
                    if label_name not in stats['label_distribution']:
                        stats['label_distribution'][label_name] = 0
                    stats['label_distribution'][label_name] += 1
            
            return stats
            
        except Exception as e:
            log_exception(self.logger, "Failed to get assignment statistics", e)
            return {'error': str(e)}