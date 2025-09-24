# Automated Issue Processing Agent

A GitHub Copilot-based agent that automatically processes issues labeled with `site-monitor` by selecting appropriate workflows from `docs/workflow/deliverables/**` and generating structured research documents.

## Target Audience

- **Primary**: Development team members who need automated research and analysis on specific topics
- **Secondary**: Project maintainers who want to streamline issue resolution workflows
- **Use Case**: Converting GitHub issues into structured research documents without manual intervention

## Desired Features

### Workflow Management
- [ ] Scan deliverables for available workflow definitions
  - [ ] Parse workflow files to extract naming conventions and structure requirements
  - [ ] Build index of available workflows with their trigger labels
  - [ ] Cache workflow definitions for performance
- [ ] Match issues to workflows based on labels
  - [ ] Primary trigger: `site-monitor` label
  - [ ] Secondary matching via additional labels
  - [ ] No default workflow - pause if no clear match

### Issue Processing
- [ ] Monitor GitHub issues for `site-monitor` label
  - [ ] Integrate with existing `site_monitor.py` flow
  - [ ] Support both GitHub Actions and local execution
  - [ ] Queue management using issue assignment
- [ ] Execute selected workflow
  - [ ] Load workflow-specific folder/file naming conventions
  - [ ] Apply workflow context to processing
  - [ ] Generate deliverables per workflow specification

### Agent Behavior
- [ ] Self-assignment mechanism
  - [ ] Assign issue to agent when processing begins
  - [ ] Remove assignment when awaiting clarification
  - [ ] Re-assign when clarification received
- [ ] Clarification handling
  - [ ] Detect ambiguous workflow matches
  - [ ] Comment on issue requesting clarification
  - [ ] Pause branch work until response received

### Output Generation
- [ ] Create structured documents per workflow specs
  - [ ] Use folder structure from selected `deliverables/**` template
  - [ ] Apply naming conventions from workflow definition
  - [ ] Generate in study directory
- [ ] Git integration
  - [ ] Create feature branch per issue
  - [ ] Commit generated documents
  - [ ] Natural versioning through git history

### Integration Points
- [ ] Extend existing monitoring infrastructure
  - [ ] Add new command to main.py for agent processing
  - [ ] Reuse `GitHubIssueCreator` for issue updates
  - [ ] Leverage `config_manager.py` for agent configuration
- [ ] Error handling
  - [ ] Pause on unclear workflow selection
  - [ ] Log processing attempts
  - [ ] Graceful degradation to manual processing

## Design Requests

### Configuration
- [ ] Extend config.yaml with agent settings
  - [ ] Workflow directory path
  - [ ] Agent GitHub username for assignment
  - [ ] Processing timeout values
- [ ] Workflow definition format in `deliverables/`
  - [ ] YAML front matter with metadata
  - [ ] Clear folder/file naming patterns
  - [ ] Required vs optional deliverables

### Implementation Architecture
- [ ] New module: `src/issue_processor.py`
  - [ ] Class `IssueProcessor` with workflow matching logic
  - [ ] Integration with `SiteMonitorIssueCreator`
  - [ ] State management for paused issues
- [ ] Extend main.py with new command
  - [ ] `process-issues` subcommand
  - [ ] Options for dry-run and specific issue targeting
  - [ ] Progress reporting

## Implementation Approach

````python
"""Issue processing agent for automated workflow execution"""

import os
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import yaml

from .github_issue_creator import GitHubIssueCreator
from .config_manager import ConfigManager


class WorkflowMatcher:
    """Matches issues to appropriate workflows based on labels"""
    
    def __init__(self, workflow_dir: str = "docs/workflow/deliverables"):
        self.workflow_dir = Path(workflow_dir)
        self._workflow_cache: Dict[str, Dict] = {}
        self._load_workflows()
    
    def _load_workflows(self) -> None:
        """Load and cache all workflow definitions"""
        if not self.workflow_dir.exists():
            raise ValueError(f"Workflow directory not found: {self.workflow_dir}")
        
        for workflow_file in self.workflow_dir.rglob("*.yaml"):
            with open(workflow_file, 'r') as f:
                workflow_data = yaml.safe_load(f)
                if workflow_data and 'trigger_labels' in workflow_data:
                    self._workflow_cache[str(workflow_file)] = workflow_data
    
    def find_matching_workflow(self, labels: List[str]) -> Optional[Tuple[str, Dict]]:
        """Find workflow matching the given labels"""
        if 'site-monitor' not in labels:
            return None
        
        matches = []
        for workflow_path, workflow_data in self._workflow_cache.items():
            trigger_labels = workflow_data.get('trigger_labels', [])
            if any(label in labels for label in trigger_labels):
                matches.append((workflow_path, workflow_data))
        
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - need clarification
            return None
        else:
            # No matches beyond site-monitor
            return None


class IssueProcessor:
    """Processes GitHub issues using matched workflows"""
    
    def __init__(self, github_token: str, repo_name: str, config_path: str = "config.yaml"):
        self.github = GitHubIssueCreator(github_token, repo_name)
        self.config = ConfigManager.load_config(config_path)
        self.workflow_matcher = WorkflowMatcher()
        self.agent_username = self.config.get('agent_username', 'github-actions[bot]')
    
    def process_issue(self, issue_number: int) -> Dict:
        """Process a single issue"""
        issue = self.github.get_issue(issue_number)
        
        # Check if already assigned to agent
        if issue.assignee and issue.assignee.login == self.agent_username:
            return {'status': 'already_processing', 'issue': issue_number}
        
        # Find matching workflow
        labels = [label.name for label in issue.labels]
        workflow_match = self.workflow_matcher.find_matching_workflow(labels)
        
        if workflow_match is None:
            # Need clarification
            self._request_clarification(issue)
            return {'status': 'needs_clarification', 'issue': issue_number}
        
        # Assign to agent and process
        issue.add_to_assignees(self.agent_username)
        
        try:
            workflow_path, workflow_data = workflow_match
            result = self._execute_workflow(issue, workflow_data)
            return {'status': 'completed', 'issue': issue_number, 'result': result}
        except Exception as e:
            issue.remove_from_assignees(self.agent_username)
            return {'status': 'error', 'issue': issue_number, 'error': str(e)}
    
    def _request_clarification(self, issue) -> None:
        """Request clarification on workflow selection"""
        comment = (
            "🤖 **Workflow Selection Required**\n\n"
            "Multiple workflows could apply to this issue, or no specific workflow was found.\n"
            "Please add additional labels to clarify which workflow should be used.\n\n"
            "Available workflows can be found in `docs/workflow/deliverables/`"
        )
        issue.create_comment(comment)
    
    def _execute_workflow(self, issue, workflow_data: Dict) -> Dict:
        """Execute the matched workflow"""
        # Extract naming conventions
        folder_structure = workflow_data.get('folder_structure', 'study/{issue_number}')
        file_pattern = workflow_data.get('file_pattern', '{deliverable_name}.md')
        
        # Create output directory
        output_dir = Path(folder_structure.format(issue_number=issue.number))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process deliverables
        deliverables = workflow_data.get('deliverables', [])
        created_files = []
        
        for deliverable in deliverables:
            file_name = file_pattern.format(
                deliverable_name=deliverable['name'],
                issue_number=issue.number
            )
            file_path = output_dir / file_name
            
            # Generate content based on issue and deliverable spec
            content = self._generate_deliverable_content(issue, deliverable)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            created_files.append(str(file_path))
        
        return {
            'workflow': workflow_data.get('name', 'Unknown'),
            'created_files': created_files
        }
    
    def _generate_deliverable_content(self, issue, deliverable_spec: Dict) -> str:
        """Generate content for a specific deliverable"""
        # This would integrate with Copilot API to generate content
        # For now, return a template
        return f"""# {deliverable_spec['name']}

Generated from issue #{issue.number}: {issue.title}

## Overview
{deliverable_spec.get('description', 'No description provided')}

## Content
[Content would be generated here based on workflow specifications]

---
*Generated automatically by issue processor*
"""
````

````python
# ...existing code...
    
    # Add new process-issues command
    process_parser = subparsers.add_parser('process-issues', help='Process issues with workflows')
    process_parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    process_parser.add_argument('--issue', type=int, help='Process specific issue number')
    process_parser.add_argument('--dry-run', action='store_true', help='Show what would be processed')
    
# ...existing code...

        elif args.command == 'process-issues':
            # Issue processing
            from src.issue_processor import IssueProcessor
            
            if not os.path.exists(args.config):
                print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
                sys.exit(1)
            
            processor = IssueProcessor(github_token, repo_name, args.config)
            
            if args.issue:
                # Process specific issue
                result = processor.process_issue(args.issue)
                print(f"Processing result: {result['status']}")
            else:
                # Process all site-monitor labeled issues
                # This would need implementation to find and process all relevant issues
                print("Batch processing not yet implemented")
````

## Other Notes

- The agent integrates seamlessly with existing `site_monitor.py` infrastructure
- Workflow definitions in deliverables should include YAML front matter specifying trigger labels and output structure
- Git commits provide natural versioning for regenerated content
- The pause-and-clarify approach prevents incorrect workflow selection
- Can be triggered via GitHub Actions or local development