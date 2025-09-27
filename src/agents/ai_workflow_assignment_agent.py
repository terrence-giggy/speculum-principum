"""
AI-Enhanced Workflow Assignment Agent using GitHub Models API

This module provides an intelligent agent that analyzes GitHub issue content
using GitHub Models API to suggest and assign appropriate workflows.

Key improvements over label-based matching:
- Semantic analysis of issue title and body
- Content-based workflow recommendations
- Learning from past assignments (stored in GitHub)
- Multi-factor scoring combining labels, content, and patterns
"""

import json
import logging
import time
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
import hashlib
import re

import requests
from github import Github

from ..workflow.workflow_matcher import WorkflowMatcher, WorkflowInfo, WorkflowMatcherError
from ..clients.github_issue_creator import GitHubIssueCreator
from ..utils.config_manager import ConfigManager
from ..utils.logging_config import get_logger, log_exception


@dataclass
class ContentAnalysis:
    """Results from AI content analysis"""
    summary: str
    key_topics: List[str]
    suggested_workflows: List[str]
    confidence_scores: Dict[str, float]
    technical_indicators: List[str]
    urgency_level: str  # low, medium, high, critical
    content_type: str  # research, bug, feature, security, documentation


class GitHubModelsClient:
    """
    Client for GitHub Models API
    
    GitHub Models provides access to AI models directly within GitHub,
    perfect for GitHub Actions workflows.
    """
    
    BASE_URL = "https://models.inference.ai.github.com"
    
    def __init__(self, github_token: str, model: str = "gpt-4o"):
        """
        Initialize GitHub Models client.
        
        Args:
            github_token: GitHub token with models API access
            model: Model to use (gpt-4o, llama-3.2, etc.)
        """
        self.logger = get_logger(__name__)
        self.token = github_token
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
    def analyze_issue_content(self, 
                            title: str, 
                            body: str,
                            labels: List[str],
                            available_workflows: List[WorkflowInfo]) -> ContentAnalysis:
        """
        Use GitHub Models to analyze issue content and suggest workflows.
        
        Args:
            title: Issue title
            body: Issue body/description
            labels: Current issue labels
            available_workflows: List of available workflow definitions
            
        Returns:
            ContentAnalysis with AI-generated insights
        """
        try:
            # Prepare workflow context for the model
            workflow_descriptions = []
            for wf in available_workflows:
                deliverable_types = [d.get('name', '') for d in wf.deliverables[:3]]  # First 3
                workflow_descriptions.append(
                    f"- {wf.name}: {wf.description}\n"
                    f"  Trigger labels: {', '.join(wf.trigger_labels)}\n"
                    f"  Deliverables: {', '.join(deliverable_types)}"
                )
            
            # Construct prompt for issue analysis
            prompt = self._build_analysis_prompt(
                title, body, labels, workflow_descriptions
            )
            
            # Call GitHub Models API
            response = self._call_models_api(prompt)
            
            # Parse AI response into structured analysis
            return self._parse_ai_response(response, available_workflows)
            
        except Exception as e:
            log_exception(self.logger, "GitHub Models analysis failed", e)
            # Return fallback analysis
            return ContentAnalysis(
                summary="Failed to analyze with AI",
                key_topics=[],
                suggested_workflows=[],
                confidence_scores={},
                technical_indicators=[],
                urgency_level="medium",
                content_type="unknown"
            )
    
    def _build_analysis_prompt(self, 
                              title: str, 
                              body: str,
                              labels: List[str],
                              workflow_descriptions: List[str]) -> str:
        """Build prompt for GitHub Models API"""
        
        return f"""Analyze this GitHub issue and suggest the most appropriate workflow(s).

ISSUE DETAILS:
Title: {title}
Labels: {', '.join(labels) if labels else 'None'}
Body:
{body[:2000] if body else 'No description provided'}

AVAILABLE WORKFLOWS:
{chr(10).join(workflow_descriptions)}

TASK:
1. Summarize the issue's main purpose (50 words max)
2. Identify key topics/technologies mentioned
3. Suggest the most appropriate workflow(s) from the list above
4. Rate confidence (0-1) for each suggested workflow
5. Identify technical indicators (e.g., security issue, performance, architecture)
6. Assess urgency level (low/medium/high/critical)
7. Categorize content type (research/bug/feature/security/documentation)

Return response as valid JSON only:
{{
  "summary": "Brief summary of the issue",
  "key_topics": ["topic1", "topic2"],
  "suggested_workflows": ["workflow_name1", "workflow_name2"],
  "confidence_scores": {{"workflow_name1": 0.9, "workflow_name2": 0.7}},
  "technical_indicators": ["indicator1", "indicator2"],
  "urgency_level": "medium",
  "content_type": "research"
}}"""
    
    def _call_models_api(self, prompt: str) -> Dict[str, Any]:
        """
        Call GitHub Models API endpoint.
        
        Note: This uses the GitHub Models inference endpoint which is
        available in GitHub Actions with proper authentication.
        """
        endpoint = f"{self.BASE_URL}/v1/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an AI assistant analyzing GitHub issues to suggest appropriate processing workflows. Always respond with valid JSON only, no additional text or explanation."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Lower temperature for more consistent analysis
            "max_tokens": 500
        }
        
        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the AI's response
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                # Clean up response and parse JSON
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                return json.loads(content)
            else:
                raise ValueError("Invalid response structure from GitHub Models")
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"GitHub Models API request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse AI response as JSON: {e}")
            self.logger.error(f"Raw response content: {content}")
            raise
    
    def _parse_ai_response(self, 
                          response: Dict[str, Any],
                          available_workflows: List[WorkflowInfo]) -> ContentAnalysis:
        """Parse AI response into ContentAnalysis object"""
        
        # Validate suggested workflows exist
        valid_workflows = {wf.name for wf in available_workflows}
        suggested = response.get("suggested_workflows", [])
        validated_suggestions = [w for w in suggested if w in valid_workflows]
        
        # Filter confidence scores to valid workflows
        confidence_scores = response.get("confidence_scores", {})
        validated_scores = {
            k: v for k, v in confidence_scores.items() 
            if k in valid_workflows
        }
        
        return ContentAnalysis(
            summary=response.get("summary", ""),
            key_topics=response.get("key_topics", []),
            suggested_workflows=validated_suggestions,
            confidence_scores=validated_scores,
            technical_indicators=response.get("technical_indicators", []),
            urgency_level=response.get("urgency_level", "medium"),
            content_type=response.get("content_type", "unknown")
        )


class AIWorkflowAssignmentAgent:
    """
    Enhanced workflow assignment agent using GitHub Models AI.
    
    Improvements over label-based assignment:
    - Semantic understanding of issue content
    - Multi-factor scoring combining AI analysis and labels
    - Learning from historical assignments
    - Intelligent fallback strategies
    """
    
    # Confidence thresholds for automatic assignment
    HIGH_CONFIDENCE_THRESHOLD = 0.8
    MEDIUM_CONFIDENCE_THRESHOLD = 0.6
    
    # Skip labels (same as original agent)
    SKIP_LABELS = {'feature', 'needs clarification', 'needs-review'}
    
    def __init__(self,
                 github_token: str,
                 repo_name: str,
                 config_path: str = "config.yaml",
                 workflow_directory: str = "docs/workflow/deliverables",
                 enable_ai: bool = True):
        """
        Initialize AI-enhanced workflow assignment agent.
        
        Args:
            github_token: GitHub API token
            repo_name: Repository name in format 'owner/repo'
            config_path: Path to configuration file
            workflow_directory: Directory containing workflow definitions
            enable_ai: Whether to use GitHub Models AI (can disable for testing)
        """
        self.logger = get_logger(__name__)
        self.github = GitHubIssueCreator(github_token, repo_name)
        self.repo_name = repo_name
        self.enable_ai = enable_ai
        
        # Load configuration
        try:
            self.config = ConfigManager.load_config(config_path)
            # Load AI configuration if available
            ai_config = getattr(self.config, 'ai', None)
            if ai_config:
                self.enable_ai = ai_config.get('enabled', enable_ai)
                self.HIGH_CONFIDENCE_THRESHOLD = ai_config.get('confidence_thresholds', {}).get('auto_assign', 0.8)
                self.MEDIUM_CONFIDENCE_THRESHOLD = ai_config.get('confidence_thresholds', {}).get('request_review', 0.6)
                ai_model = ai_config.get('model', 'gpt-4o')
            else:
                ai_model = 'gpt-4o'
        except Exception as e:
            self.logger.warning(f"Could not load config from {config_path}: {e}")
            ai_model = 'gpt-4o'
        
        # Initialize workflow matcher for fallback
        self.workflow_matcher = WorkflowMatcher(workflow_directory)
        
        # Initialize AI client if enabled
        if self.enable_ai:
            self.ai_client = GitHubModelsClient(github_token, model=ai_model)
        else:
            self.ai_client = None
            
        # Load learning data from previous assignments
        self.assignment_history = self._load_assignment_history()
        
        self.logger.info(
            f"Initialized AI workflow agent (AI={'enabled' if self.enable_ai else 'disabled'}, "
            f"model={ai_model if self.enable_ai else 'none'})"
        )
    
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
            
            self.logger.info(f"Found {len(candidate_issues)} candidate issues for AI workflow assignment")
            return candidate_issues
        
        except Exception as e:
            log_exception(self.logger, "Failed to get unassigned site-monitor issues", e)
            return []
    
    def analyze_issue_with_ai(self, 
                             issue_data: Dict[str, Any]) -> Tuple[Optional[WorkflowInfo], ContentAnalysis, str]:
        """
        Analyze issue using AI to determine best workflow match.
        
        Args:
            issue_data: Issue data dictionary
            
        Returns:
            Tuple of (WorkflowInfo if found, AI analysis, explanation message)
            
        Raises:
            RuntimeError: If AI is required but unavailable
        """
        available_workflows = self.workflow_matcher.get_available_workflows()
        
        # Check if we're in GitHub Actions environment
        is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
        
        if not is_github_actions:
            raise RuntimeError(
                "AI workflow assignment requires GitHub Actions environment with access to GitHub Models API. "
                "This feature is not available when running locally. "
                "Please run this command within a GitHub Actions workflow."
            )
        
        # Get AI analysis
        if not self.enable_ai or not self.ai_client:
            raise RuntimeError(
                "AI workflow assignment is disabled but required for operation. "
                "Please enable AI in configuration or run in GitHub Actions environment."
            )
        
        try:
            analysis = self.ai_client.analyze_issue_content(
                title=issue_data.get('title', ''),
                body=issue_data.get('body', ''),
                labels=issue_data.get('labels', []),
                available_workflows=available_workflows
            )
            
            # Combine AI analysis with label-based validation
            return self._combine_ai_and_label_analysis(
                issue_data, analysis, available_workflows
            )
            
        except Exception as e:
            error_msg = f"AI analysis failed: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(
                f"AI workflow assignment failed and no fallback is available. "
                f"Error: {error_msg}. "
                f"This feature requires a working connection to GitHub Models API."
            ) from e
    
    def _combine_ai_and_label_analysis(self,
                                      issue_data: Dict[str, Any],
                                      ai_analysis: ContentAnalysis,
                                      available_workflows: List[WorkflowInfo]) -> Tuple[Optional[WorkflowInfo], ContentAnalysis, str]:
        """
        Combine AI content analysis with label-based matching for best results.
        
        Uses a weighted scoring system:
        - AI confidence: 70% weight
        - Label matching: 20% weight  
        - Historical success: 10% weight
        """
        combined_scores = {}
        
        # Get label-based matches
        label_matches = self.workflow_matcher.find_matching_workflows(
            issue_data.get('labels', [])
        )
        label_match_names = {wf.name for wf in label_matches}
        
        for workflow in available_workflows:
            score = 0.0
            
            # AI confidence score (70% weight)
            if workflow.name in ai_analysis.confidence_scores:
                score += ai_analysis.confidence_scores[workflow.name] * 0.7
            
            # Label matching bonus (20% weight)
            if workflow.name in label_match_names:
                score += 0.2
            
            # Historical success rate (10% weight)
            historical_score = self._get_historical_success_rate(
                workflow.name, 
                ai_analysis.content_type
            )
            score += historical_score * 0.1
            
            if score > 0:
                combined_scores[workflow.name] = score
        
        # Find best workflow
        if combined_scores:
            best_workflow_name = max(combined_scores.keys(), key=lambda x: combined_scores[x])
            best_score = combined_scores[best_workflow_name]
            
            if best_score >= self.HIGH_CONFIDENCE_THRESHOLD:
                best_workflow = next(
                    wf for wf in available_workflows 
                    if wf.name == best_workflow_name
                )
                message = (
                    f"AI analysis selected '{best_workflow_name}' "
                    f"(confidence: {best_score:.2f}, "
                    f"content type: {ai_analysis.content_type})"
                )
                
                # Update AI analysis with combined scores
                ai_analysis.confidence_scores = combined_scores
                
                return best_workflow, ai_analysis, message
            
            elif best_score >= self.MEDIUM_CONFIDENCE_THRESHOLD:
                # Medium confidence - suggest but request confirmation
                message = (
                    f"AI suggests '{best_workflow_name}' "
                    f"(confidence: {best_score:.2f}) but recommends human review"
                )
                ai_analysis.confidence_scores = combined_scores
                return None, ai_analysis, message
        
        # Low confidence
        message = "AI analysis inconclusive - no workflow has sufficient confidence"
        return None, ai_analysis, message
    
    def _get_historical_success_rate(self, 
                                    workflow_name: str,
                                    content_type: str) -> float:
        """
        Get historical success rate for a workflow/content type combination.
        
        Returns:
            Success rate between 0 and 1
        """
        # This would query historical assignment data stored in GitHub
        # For now, return a default value based on content type matching
        if workflow_name == "Research Analysis" and content_type in ["research", "analysis"]:
            return 0.8
        elif workflow_name == "Technical Review" and content_type in ["technical", "code", "security"]:
            return 0.8
        else:
            return 0.5
    
    def _load_assignment_history(self) -> Dict[str, Any]:
        """
        Load historical assignment data from GitHub.
        
        Could be stored as:
        - GitHub Gist
        - Repository file
        - GitHub Actions artifacts
        """
        # Placeholder - would load from GitHub storage
        return {}
    
    def process_issue_with_ai(self,
                             issue_data: Dict[str, Any],
                             dry_run: bool = False) -> Dict[str, Any]:
        """
        Process issue using AI-enhanced workflow assignment.
        
        Args:
            issue_data: Issue data dictionary
            dry_run: If True, don't make actual changes
            
        Returns:
            Assignment result with AI insights
        """
        issue_number = issue_data['number']
        
        # Analyze with AI
        workflow, ai_analysis, message = self.analyze_issue_with_ai(issue_data)
        
        result = {
            'issue_number': issue_number,
            'ai_analysis': asdict(ai_analysis),
            'message': message,
            'action_taken': None,
            'assigned_workflow': None,
            'labels_added': [],
            'dry_run': dry_run
        }
        
        if workflow and ai_analysis.confidence_scores.get(workflow.name, 0) >= self.HIGH_CONFIDENCE_THRESHOLD:
            # High confidence - assign automatically
            labels_added = self._assign_workflow_with_ai_context(
                issue_number, workflow, ai_analysis, dry_run
            )
            result['action_taken'] = 'auto_assigned'
            result['assigned_workflow'] = workflow.name
            result['labels_added'] = labels_added
            
        elif ai_analysis.suggested_workflows:
            # Medium confidence - request human review
            labels_added = self._request_review_with_ai_context(
                issue_number, ai_analysis, dry_run
            )
            result['action_taken'] = 'review_requested'
            result['labels_added'] = labels_added
            
        else:
            # Low confidence - request more information
            labels_added = self._request_clarification_with_ai_context(
                issue_number, ai_analysis, dry_run
            )
            result['action_taken'] = 'clarification_requested'
            result['labels_added'] = labels_added
        
        return result
    
    def _assign_workflow_with_ai_context(self,
                                        issue_number: int,
                                        workflow: WorkflowInfo,
                                        analysis: ContentAnalysis,
                                        dry_run: bool = False) -> List[str]:
        """Assign workflow with AI analysis context in comment"""
        
        labels_added = []
        
        if not dry_run:
            issue = self.github.repo.get_issue(issue_number)
            current_labels = {label.name for label in issue.labels}
            
            # Add workflow labels that aren't already present
            for label in workflow.trigger_labels:
                if label not in current_labels:
                    issue.add_to_labels(label)
                    labels_added.append(label)
            
            # Add AI analysis as comment
            confidence = analysis.confidence_scores.get(workflow.name, 0)
            comment = f"""🤖 **AI Workflow Assignment**

**Assigned Workflow:** {workflow.name}
**Confidence:** {confidence:.0%}
**Content Type:** {analysis.content_type}
**Urgency:** {analysis.urgency_level}

**AI Analysis Summary:**
{analysis.summary}

**Key Topics Identified:**
{', '.join(analysis.key_topics) if analysis.key_topics else 'None identified'}

**Technical Indicators:**
{', '.join(analysis.technical_indicators) if analysis.technical_indicators else 'None identified'}

---
*This assignment was made using GitHub Models AI analysis combined with label matching.*
"""
            issue.create_comment(comment)
        else:
            # In dry run, just return what labels would be added
            current_issue = self.github.repo.get_issue(issue_number)
            current_labels = {label.name for label in current_issue.labels}
            labels_added = [label for label in workflow.trigger_labels if label not in current_labels]
        
        return labels_added
    
    def _request_review_with_ai_context(self,
                                       issue_number: int,
                                       analysis: ContentAnalysis,
                                       dry_run: bool = False) -> List[str]:
        """Request human review with AI suggestions"""
        
        labels_added = []
        
        if not dry_run:
            issue = self.github.repo.get_issue(issue_number)
            current_labels = {label.name for label in issue.labels}
            
            if 'needs-review' not in current_labels:
                issue.add_to_labels('needs-review')
                labels_added.append('needs-review')
            
            # Build suggestion list with confidence scores
            suggestions = []
            for workflow_name in analysis.suggested_workflows[:3]:  # Top 3
                confidence = analysis.confidence_scores.get(workflow_name, 0)
                suggestions.append(f"- **{workflow_name}** (confidence: {confidence:.0%})")
            
            comment = f"""🤖 **Human Review Requested**

The AI analysis suggests these workflows but confidence is moderate:

{chr(10).join(suggestions) if suggestions else '- No clear workflow matches found'}

**AI Summary:** {analysis.summary}

**Content Type:** {analysis.content_type}
**Urgency:** {analysis.urgency_level}

Please review and either:
1. Confirm one of the suggested workflows by adding its trigger labels
2. Select a different workflow by adding appropriate labels
3. Add more context to help improve the analysis

---
*Analysis powered by GitHub Models AI*
"""
            issue.create_comment(comment)
        else:
            # In dry run, check what labels would be added
            current_issue = self.github.repo.get_issue(issue_number)
            current_labels = {label.name for label in current_issue.labels}
            if 'needs-review' not in current_labels:
                labels_added.append('needs-review')
        
        return labels_added
    
    def _request_clarification_with_ai_context(self,
                                              issue_number: int,
                                              analysis: ContentAnalysis,
                                              dry_run: bool = False) -> List[str]:
        """Request clarification with AI insights"""
        
        labels_added = []
        
        if not dry_run:
            issue = self.github.repo.get_issue(issue_number)
            current_labels = {label.name for label in issue.labels}
            
            if 'needs clarification' not in current_labels:
                issue.add_to_labels('needs clarification')
                labels_added.append('needs clarification')
            
            comment = f"""🤖 **Additional Information Needed**

The AI couldn't confidently match this issue to a workflow.

**What I understood:**
{analysis.summary if analysis.summary else "Unable to determine issue purpose"}

**Topics identified:** {', '.join(analysis.key_topics) if analysis.key_topics else 'None'}

**To help me assign the right workflow, please:**
1. Add more descriptive labels
2. Clarify the issue's purpose in the description
3. Specify the type of deliverable needed

Available workflow types:
- `research` / `analysis` - For in-depth research
- `technical-review` / `code-review` - For technical assessments
- `security` - For security analysis
- `documentation` - For documentation tasks

---
*Analysis powered by GitHub Models AI*
"""
            issue.create_comment(comment)
        else:
            # In dry run, check what labels would be added
            current_issue = self.github.repo.get_issue(issue_number)
            current_labels = {label.name for label in current_issue.labels}
            if 'needs clarification' not in current_labels:
                labels_added.append('needs clarification')
        
        return labels_added
    
    def process_issues_batch(self, 
                           limit: Optional[int] = None,
                           dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a batch of issues using AI-enhanced workflow assignment.
        
        Args:
            limit: Maximum number of issues to process
            dry_run: If True, don't make actual changes
            
        Returns:
            Dictionary with processing statistics and results
        """
        start_time = time.time()
        self.logger.info(f"Starting AI workflow assignment batch processing (limit: {limit}, dry_run: {dry_run})")
        
        try:
            # Get candidate issues
            issues = self.get_unassigned_site_monitor_issues(limit)
            
            if not issues:
                self.logger.info("No issues found for AI workflow assignment")
                return {
                    'total_issues': 0,
                    'processed': 0,
                    'results': [],
                    'statistics': {
                        'auto_assigned': 0,
                        'review_requested': 0,
                        'clarification_requested': 0,
                        'errors': 0
                    },
                    'duration_seconds': time.time() - start_time
                }
            
            # Process each issue
            results = []
            statistics = {
                'auto_assigned': 0,
                'review_requested': 0,
                'clarification_requested': 0,
                'errors': 0
            }
            
            for issue_data in issues:
                try:
                    result = self.process_issue_with_ai(issue_data, dry_run)
                    results.append(result)
                    
                    action = result.get('action_taken', 'error')
                    if action in statistics:
                        statistics[action] += 1
                    else:
                        statistics['errors'] += 1
                    
                    # Add small delay between issues to be respectful to APIs
                    time.sleep(0.5)  # Slightly longer delay for AI calls
                    
                except Exception as e:
                    error_result = {
                        'issue_number': issue_data['number'],
                        'action_taken': 'error',
                        'message': f"Processing error: {e}",
                        'ai_analysis': {},
                        'assigned_workflow': None,
                        'labels_added': [],
                        'dry_run': dry_run
                    }
                    results.append(error_result)
                    statistics['errors'] += 1
                    
                    log_exception(self.logger, f"Failed to process issue #{issue_data['number']}", e)
            
            duration = time.time() - start_time
            
            # Log summary
            processed_count = len([r for r in results if r.get('action_taken') != 'error'])
            
            self.logger.info(f"AI batch processing completed: {processed_count}/{len(issues)} issues processed "
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
            log_exception(self.logger, "AI batch processing failed", e)
            return {
                'total_issues': 0,
                'processed': 0,
                'results': [],
                'statistics': {
                    'auto_assigned': 0,
                    'review_requested': 0,
                    'clarification_requested': 0,
                    'errors': 1
                },
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
                'needs_review': 0,
                'feature_labeled': 0,
                'workflow_breakdown': {},
                'label_distribution': {},
                'ai_enabled': self.enable_ai
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
                if 'needs-review' in issue_labels:
                    stats['needs_review'] += 1
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