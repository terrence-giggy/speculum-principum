"""
Workflow Orchestrator

This module handles the coordination and execution of workflows for issue processing,
including workflow discovery, execution management, and deliverable coordination.
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from pathlib import Path

from .workflow_matcher import WorkflowMatcher, WorkflowInfo, WorkflowLoadError
from .deliverable_generator import DeliverableGenerator, DeliverableSpec
from .git_manager import GitManager, GitOperationError
from .error_handler import ErrorHandler
from .issue_state_manager import IssueStateManager
from .logging_config import get_logger, log_exception


class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails."""
    pass


class WorkflowOrchestrator:
    """
    Orchestrates workflow discovery, execution, and deliverable generation.
    
    This class manages:
    - Finding appropriate workflows for issues
    - Executing workflow logic
    - Coordinating deliverable generation
    - Managing git operations for deliverables
    """
    
    def __init__(self, 
                 workflow_matcher: WorkflowMatcher,
                 deliverable_generator: DeliverableGenerator,
                 error_handler: ErrorHandler,
                 git_manager: Optional[GitManager] = None,
                 agent_username: str = 'github-actions[bot]'):
        """
        Initialize the workflow orchestrator.
        
        Args:
            workflow_matcher: Matcher for finding appropriate workflows
            deliverable_generator: Generator for creating deliverables
            error_handler: Error handler for managing failures
            git_manager: Optional git manager for version control operations
            agent_username: Username for agent operations
        """
        self.logger = get_logger(__name__)
        self.workflow_matcher = workflow_matcher
        self.deliverable_generator = deliverable_generator
        self.error_handler = error_handler
        self.git_manager = git_manager
        self.agent_username = agent_username

    def find_workflow_with_retry(self, issue_data: Any) -> Tuple[Optional[WorkflowInfo], Optional[str]]:
        """
        Find appropriate workflow for an issue with retry logic.
        
        Args:
            issue_data: Issue data to match against workflows
            
        Returns:
            Tuple of (workflow_info, error_message)
        """
        @self.error_handler.retry_on_exception(
            exceptions=(WorkflowLoadError,),
            max_retries=2
        )
        def _find_workflow():
            # Use the correct method name and pass labels
            matching_workflows = self.workflow_matcher.find_matching_workflows(issue_data.labels)
            if matching_workflows:
                # Return the best match (first one)
                return matching_workflows[0]
            return None
        
        try:
            workflow_info = _find_workflow()
            if workflow_info:
                self.logger.info(f"Found workflow: {workflow_info.name} for issue #{issue_data.number}")
                return workflow_info, None
            else:
                error_msg = f"No matching workflow found for issue #{issue_data.number}"
                self.logger.warning(error_msg)
                return None, error_msg
        except Exception as e:
            error_msg = f"Failed to find workflow for issue #{issue_data.number}: {e}"
            self.logger.error(error_msg)
            return None, error_msg

    def execute_workflow_with_recovery(self, issue_data: Any, workflow_info: WorkflowInfo) -> Dict[str, Any]:
        """
        Execute workflow with error recovery and fallback strategies.
        
        Args:
            issue_data: Issue data for processing
            workflow_info: Workflow to execute
            
        Returns:
            Execution result with deliverables and metadata
            
        Raises:
            WorkflowExecutionError: If execution fails
        """
        def primary_execution():
            return self._execute_workflow(issue_data, workflow_info)
        
        def fallback_execution():
            self.logger.info(f"Executing fallback workflow for issue #{issue_data.number}")
            return self._execute_basic_workflow(issue_data, workflow_info)
        
        try:
            result, used_fallback = self.error_handler.execute_with_fallback(
                primary_func=primary_execution,
                fallback_func=fallback_execution,
                issue_number=issue_data.number
            )
            
            if used_fallback:
                result['used_fallback'] = True
                result['execution_mode'] = 'fallback'
            else:
                result['execution_mode'] = 'primary'
                
            return result
            
        except Exception as e:
            error_msg = f"Workflow execution failed for issue #{issue_data.number}: {e}"
            log_exception(self.logger, error_msg, e)
            raise WorkflowExecutionError(error_msg) from e

    def _execute_workflow(self, issue_data: Any, workflow_info: WorkflowInfo) -> Dict[str, Any]:
        """
        Execute the main workflow logic.
        
        Args:
            issue_data: Issue data for processing
            workflow_info: Workflow information and specifications
            
        Returns:
            Execution result dictionary
        """
        self.logger.info(f"Executing workflow '{workflow_info.name}' for issue #{issue_data.number}")
        
        result = {
            'workflow_name': workflow_info.name,
            'workflow_description': workflow_info.description,
            'deliverables': [],
            'git_operations': [],
            'execution_time': None,
            'started_at': datetime.now().isoformat()
        }
        
        start_time = datetime.now()
        
        try:
            # Process deliverables from workflow
            deliverables_created = []
            
            for deliverable_spec in workflow_info.deliverables:
                self.logger.debug(f"Processing deliverable: {deliverable_spec.get('name', 'unnamed')}")
                
                # Generate deliverable content
                deliverable_result = self._generate_deliverable(
                    issue_data=issue_data,
                    deliverable_spec=deliverable_spec,
                    workflow_info=workflow_info
                )
                
                if deliverable_result:
                    deliverables_created.append(deliverable_result)
            
            result['deliverables'] = deliverables_created
            
            # Handle git operations if enabled
            if self.git_manager and deliverables_created:
                git_results = self._handle_git_operations(issue_data, deliverables_created, workflow_info.name)
                result['git_operations'] = git_results
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            result['execution_time'] = execution_time
            result['completed_at'] = datetime.now().isoformat()
            
            self.logger.info(f"Workflow execution completed for issue #{issue_data.number} "
                           f"in {execution_time:.2f}s with {len(deliverables_created)} deliverables")
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            result['execution_time'] = execution_time
            result['failed_at'] = datetime.now().isoformat()
            result['error'] = str(e)
            
            log_exception(self.logger, f"Workflow execution failed for issue #{issue_data.number}", e)
            raise

    def _execute_basic_workflow(self, issue_data: Any, workflow_info: WorkflowInfo) -> Dict[str, Any]:
        """
        Execute a basic fallback workflow with minimal deliverables.
        
        Args:
            issue_data: Issue data for processing
            workflow_info: Workflow information (used for context)
            
        Returns:
            Basic execution result
        """
        self.logger.info(f"Executing basic fallback workflow for issue #{issue_data.number}")
        
        result = {
            'workflow_name': f"{workflow_info.name}_fallback",
            'workflow_type': 'basic_fallback',
            'deliverables': [],
            'execution_mode': 'fallback',
            'started_at': datetime.now().isoformat()
        }
        
        start_time = datetime.now()
        
        try:
            # Create a basic deliverable
            basic_deliverable_spec = {
                'name': 'basic_analysis',
                'title': 'Basic Issue Analysis',
                'description': 'Basic analysis generated as fallback',
                'template': 'basic',
                'type': 'document',
                'format': 'markdown'
            }
            
            deliverable_result = self._generate_deliverable(
                issue_data=issue_data,
                deliverable_spec=basic_deliverable_spec,
                workflow_info=workflow_info
            )
            
            if deliverable_result:
                result['deliverables'] = [deliverable_result]
            
            execution_time = (datetime.now() - start_time).total_seconds()
            result['execution_time'] = execution_time
            result['completed_at'] = datetime.now().isoformat()
            
            self.logger.info(f"Basic workflow execution completed for issue #{issue_data.number}")
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            result['execution_time'] = execution_time
            result['failed_at'] = datetime.now().isoformat()
            result['error'] = str(e)
            
            log_exception(self.logger, f"Basic workflow execution failed for issue #{issue_data.number}", e)
            raise

    def _generate_deliverable(self, 
                            issue_data: Any,
                            deliverable_spec: Dict[str, Any],
                            workflow_info: WorkflowInfo) -> Optional[Dict[str, Any]]:
        """
        Generate a single deliverable from the specification.
        
        Args:
            issue_data: Issue data for context
            deliverable_spec: Specification for the deliverable to generate
            workflow_info: Workflow context information
            
        Returns:
            Deliverable result or None if generation failed
        """
        try:
            # Convert dict spec to DeliverableSpec if needed
            if isinstance(deliverable_spec, dict):
                spec = DeliverableSpec(
                    name=deliverable_spec.get('name', 'unnamed'),
                    title=deliverable_spec.get('title', 'Untitled Deliverable'),
                    description=deliverable_spec.get('description', 'No description'),
                    template=deliverable_spec.get('template', 'basic'),
                    required=deliverable_spec.get('required', True),
                    order=deliverable_spec.get('order', 1),
                    type=deliverable_spec.get('type', 'document'),
                    format=deliverable_spec.get('format', 'markdown'),
                    sections=deliverable_spec.get('sections', []),
                    metadata=deliverable_spec.get('metadata', {})
                )
            else:
                spec = deliverable_spec
            
            # Generate content using the deliverable generator
            content = self.deliverable_generator.generate_deliverable(
                issue_data=issue_data,
                deliverable_spec=spec,
                workflow_info=workflow_info
            )
            
            # Create filename
            filename = self._create_deliverable_filename(issue_data, spec)
            
            # Write to file
            file_path = self.deliverable_generator.output_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            deliverable_result = {
                'name': spec.name,
                'title': spec.title,
                'filename': filename,
                'file_path': str(file_path),
                'template': spec.template,
                'type': spec.type,
                'format': spec.format,
                'size_bytes': len(content.encode('utf-8')),
                'created_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Generated deliverable '{spec.name}' for issue #{issue_data.number}: {filename}")
            return deliverable_result
            
        except Exception as e:
            self.logger.error(f"Failed to generate deliverable '{deliverable_spec.get('name', 'unknown')}' "
                            f"for issue #{issue_data.number}: {e}")
            log_exception(self.logger, "Deliverable generation failed", e)
            return None

    def _create_deliverable_filename(self, issue_data: Any, spec: DeliverableSpec) -> str:
        """Create a filename for a deliverable."""
        # Create a safe slug from the issue title
        issue_slug = self._slugify(issue_data.title)
        
        # Limit slug length to avoid filesystem issues
        if len(issue_slug) > 50:
            issue_slug = issue_slug[:50]
        
        # Get file extension based on format
        extension = 'md' if spec.format == 'markdown' else spec.format
        
        return f"issue-{issue_data.number}-{spec.name}-{issue_slug}.{extension}"

    def _slugify(self, text: str) -> str:
        """Convert text to a URL-safe slug."""
        import re
        
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')

    def _handle_git_operations(self, issue_data: Any, deliverables: List[Dict[str, Any]], workflow_name: str) -> List[Dict[str, Any]]:
        """
        Handle git operations for deliverables.
        
        Args:
            issue_data: Issue data for context
            deliverables: List of generated deliverables
            
        Returns:
            List of git operation results
        """
        if not self.git_manager:
            return []
        
        git_results = []
        
        try:
            # Create branch for the issue
            branch_name = f"issue-{issue_data.number}"
            
            # Create branch using the git manager
            branch_info = self.git_manager.create_issue_branch(
                issue_number=issue_data.number,
                title=issue_data.title
            )
            git_results.append({
                'operation': 'create_branch',
                'branch_name': branch_info.name,
                'success': branch_info.name is not None,
                'timestamp': datetime.now().isoformat()
            })
            
            # Commit deliverables
            file_paths = [Path(d['file_path']) for d in deliverables]
            
            commit_message = f"Add deliverables for issue #{issue_data.number}: {issue_data.title}"
            
            commit_result = self.git_manager.commit_deliverables(
                file_paths=[str(p) for p in file_paths],
                issue_number=issue_data.number,
                workflow_name=workflow_name,
                commit_message=commit_message
            )
            
            git_results.append({
                'operation': 'commit',
                'files': [str(p) for p in file_paths],
                'commit_message': commit_message,
                'success': commit_result is not None,
                'commit_hash': commit_result.hash[:8] if commit_result and hasattr(commit_result, 'hash') else None,
                'timestamp': datetime.now().isoformat()
            })
            
            self.logger.info(f"Git operations completed for issue #{issue_data.number}")
            
        except GitOperationError as e:
            error_result = {
                'operation': 'git_error',
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
            git_results.append(error_result)
            self.logger.warning(f"Git operations failed for issue #{issue_data.number}: {e}")
        
        except Exception as e:
            error_result = {
                'operation': 'unexpected_error',
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
            git_results.append(error_result)
            log_exception(self.logger, f"Unexpected git error for issue #{issue_data.number}", e)
        
        return git_results

    def generate_clarification_message(self, issue_data: Any) -> str:
        """
        Generate a clarification message when no workflow can be found.
        
        Args:
            issue_data: Issue data to analyze
            
        Returns:
            Formatted clarification message
        """
        message_parts = [
            f"## Issue Processing Status\n",
            f"**Issue #{issue_data.number}:** {issue_data.title}\n",
            f"**Status:** Unable to determine appropriate workflow\n",
            f"**Agent:** {self.agent_username}\n",
            f"**Timestamp:** {datetime.now().isoformat()}\n\n",
            
            "### Analysis\n",
            f"- **Labels present:** {', '.join(issue_data.labels) if issue_data.labels else 'None'}\n",
            f"- **Issue processing available**\n\n",
            
            "### Next Steps\n",
            "To help me process this issue, please:\n",
            "1. Add appropriate workflow labels (e.g., `research`, `analysis`, `documentation`)\n",
            "2. Provide more specific requirements in the issue description\n",
            "3. Reference any related issues or context\n\n",
            
            "### Available Workflow Types\n"
        ]
        
        # Add available workflow information
        try:
            available_workflows = self.workflow_matcher.find_matching_workflows([])  # Get all workflows
            for workflow in available_workflows[:5]:  # Limit to first 5
                message_parts.append(f"- **{workflow.name}:** {workflow.description}\n")
            
            if len(available_workflows) > 5:
                message_parts.append(f"- *...and {len(available_workflows) - 5} more workflows*\n")
        except Exception as e:
            self.logger.warning(f"Could not retrieve available workflows: {e}")
            message_parts.append("- Unable to retrieve available workflows at this time\n")
        
        message_parts.append("\n*This message was generated automatically by the issue processing agent.*")
        
        return "".join(message_parts)