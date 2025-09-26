"""
Git operations manager for automated deliverable versioning.

This module provides git operations for the issue processing system, enabling
automatic branch creation and commit management for generated deliverables.
It integrates with the existing issue processor to provide version control
for research documents and deliverables.

The GitManager class handles:
- Feature branch creation per issue
- Automatic commit of generated deliverables
- Branch naming conventions and cleanup
- Git repository state validation
- Integration with GitHub workflows

This maintains a clean git history where each issue's deliverables are
contained in separate feature branches, allowing for easy tracking and
review of generated content.
"""

import os
import subprocess
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import tempfile
import shlex
from urllib.parse import urlparse


@dataclass
class BranchInfo:
    """Information about a git branch."""
    name: str
    created_at: datetime
    issue_number: int
    base_branch: str
    commit_count: int = 0
    last_commit_hash: Optional[str] = None


@dataclass
class CommitInfo:
    """Information about a git commit."""
    hash: str
    message: str
    author: str
    timestamp: datetime
    files_changed: List[str]


class GitOperationError(Exception):
    """Raised when git operations fail."""
    pass


class GitManager:
    """
    Manages git operations for issue processing and deliverable generation.
    
    This class provides high-level git operations specifically designed for
    the issue processing workflow, including automatic branch management
    and commit generation for deliverables.
    """
    
    def __init__(self, 
                 repo_path: Optional[str] = None,
                 base_branch: str = "main",
                 branch_prefix: str = "issue",
                 auto_cleanup: bool = True):
        """
        Initialize the git manager.
        
        Args:
            repo_path: Path to git repository (defaults to current directory)
            base_branch: Base branch for creating feature branches
            branch_prefix: Prefix for issue-related branches
            auto_cleanup: Whether to automatically cleanup merged branches
        """
        self.logger = logging.getLogger(__name__)
        
        # Set repository path
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        if not self._is_git_repository():
            raise GitOperationError(f"Not a git repository: {self.repo_path}")
        
        # Determine actual base branch - use provided branch if it exists, otherwise detect
        available_branches = self._get_available_branches()
        if base_branch in available_branches:
            self.base_branch = base_branch
        else:
            detected_branch = self._get_default_branch()
            self.base_branch = detected_branch if detected_branch else base_branch
        self.branch_prefix = branch_prefix
        self.auto_cleanup = auto_cleanup
        
        # Validate git configuration
        self._validate_git_config()
        
        # Cache for branch information
        self._branch_cache: Dict[str, BranchInfo] = {}
    
    def _is_git_repository(self) -> bool:
        """Check if the current directory is a git repository."""
        git_dir = self.repo_path / '.git'
        return git_dir.exists()
    
    def _get_default_branch(self) -> Optional[str]:
        """Get the default branch name (main, master, etc)."""
        try:
            # Try to get current branch first
            current = self._run_git_command(['branch', '--show-current']).strip()
            if current:
                return current
            
            # Try to get all branches and pick main/master
            branches = self._get_available_branches()
            
            # Prefer main, then master, then first available
            for preferred in ['main', 'master']:
                if preferred in branches:
                    return preferred
            
            # Return first branch if available
            return branches[0] if branches else None
            
        except GitOperationError:
            return None
    
    def _get_available_branches(self) -> List[str]:
        """Get list of available local branches."""
        try:
            branches_output = self._run_git_command(['branch', '--list'])
            branches = [b.strip().lstrip('* ') for b in branches_output.split('\n') if b.strip()]
            return branches
        except GitOperationError:
            return []
    
    def _validate_git_config(self) -> None:
        """Validate that git is properly configured."""
        try:
            # Check if user.name and user.email are configured
            self._run_git_command(['config', 'user.name'])
            self._run_git_command(['config', 'user.email'])
        except GitOperationError:
            self.logger.warning("Git user configuration not found. Some operations may fail.")
        
        # Check if we're in a clean state for operations
        try:
            status = self._run_git_command(['status', '--porcelain'])
            if status.strip():
                self.logger.warning("Repository has uncommitted changes. This may affect operations.")
        except GitOperationError:
            pass  # Continue anyway
    
    def _run_git_command(self, command: List[str], check_return_code: bool = True) -> str:
        """
        Run a git command and return the output.
        
        Args:
            command: Git command arguments
            check_return_code: Whether to raise exception on non-zero return code
            
        Returns:
            Command output
            
        Raises:
            GitOperationError: If command fails and check_return_code is True
        """
        full_command = ['git'] + command
        
        try:
            result = subprocess.run(
                full_command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if check_return_code and result.returncode != 0:
                error_msg = f"Git command failed: {' '.join(full_command)}\nError: {result.stderr}"
                self.logger.error(error_msg)
                raise GitOperationError(error_msg)
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            error_msg = f"Git command timed out: {' '.join(full_command)}"
            self.logger.error(error_msg)
            raise GitOperationError(error_msg)
        except subprocess.SubprocessError as e:
            error_msg = f"Git command error: {' '.join(full_command)}\nError: {str(e)}"
            self.logger.error(error_msg)
            raise GitOperationError(error_msg)
    
    def create_issue_branch(self, issue_number: int, title: str = "") -> BranchInfo:
        """
        Create a new feature branch for an issue.
        
        Args:
            issue_number: GitHub issue number
            title: Optional issue title for branch naming
            
        Returns:
            BranchInfo object with branch details
            
        Raises:
            GitOperationError: If branch creation fails
        """
        # Generate branch name
        title_slug = self._slugify(title) if title else ""
        branch_name = f"{self.branch_prefix}-{issue_number}"
        if title_slug:
            branch_name += f"-{title_slug}"
        
        # Limit branch name length
        if len(branch_name) > 60:
            branch_name = f"{self.branch_prefix}-{issue_number}-{title_slug[:30]}"
        
        self.logger.info(f"Creating branch '{branch_name}' for issue #{issue_number}")
        
        try:
            # Ensure we're on the base branch and it's up to date
            self._checkout_base_branch()
            self._pull_latest_changes()
            
            # Check if branch already exists
            if self._branch_exists(branch_name):
                self.logger.warning(f"Branch '{branch_name}' already exists")
                return self._get_branch_info(branch_name)
            
            # Create new branch
            self._run_git_command(['checkout', '-b', branch_name])
            
            # Create branch info
            branch_info = BranchInfo(
                name=branch_name,
                created_at=datetime.now(),
                issue_number=issue_number,
                base_branch=self.base_branch
            )
            
            self._branch_cache[branch_name] = branch_info
            self.logger.info(f"Successfully created branch '{branch_name}'")
            
            return branch_info
            
        except GitOperationError as e:
            self.logger.error(f"Failed to create branch for issue #{issue_number}: {e}")
            raise
    
    def commit_deliverables(self, 
                          file_paths: List[str], 
                          issue_number: int,
                          workflow_name: str,
                          commit_message: Optional[str] = None) -> CommitInfo:
        """
        Commit generated deliverable files.
        
        Args:
            file_paths: List of file paths to commit
            issue_number: GitHub issue number
            workflow_name: Name of the workflow that generated the files
            commit_message: Optional custom commit message
            
        Returns:
            CommitInfo object with commit details
            
        Raises:
            GitOperationError: If commit fails
        """
        if not file_paths:
            raise GitOperationError("No files to commit")
        
        # Validate that files exist
        missing_files = []
        for file_path in file_paths:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            raise GitOperationError(f"Files not found: {missing_files}")
        
        self.logger.info(f"Committing {len(file_paths)} deliverable files for issue #{issue_number}")
        
        try:
            # Add files to staging
            for file_path in file_paths:
                self._run_git_command(['add', file_path])
            
            # Generate commit message
            if not commit_message:
                file_summary = self._generate_file_summary(file_paths)
                commit_message = (
                    f"Add {workflow_name} deliverables for issue #{issue_number}\n\n"
                    f"Generated files:\n{file_summary}\n\n"
                    f"Workflow: {workflow_name}\n"
                    f"Issue: #{issue_number}"
                )
            
            # Commit changes
            self._run_git_command(['commit', '-m', commit_message])
            
            # Get commit information
            commit_hash = self._run_git_command(['rev-parse', 'HEAD']).strip()
            commit_details = self._get_commit_details(commit_hash)
            
            self.logger.info(f"Successfully committed deliverables: {commit_hash[:8]}")
            
            return commit_details
            
        except GitOperationError as e:
            self.logger.error(f"Failed to commit deliverables for issue #{issue_number}: {e}")
            raise
    
    def push_branch(self, branch_name: str, set_upstream: bool = True) -> bool:
        """
        Push a branch to the remote repository.
        
        Args:
            branch_name: Name of the branch to push
            set_upstream: Whether to set the upstream branch
            
        Returns:
            True if push succeeded, False otherwise
        """
        try:
            self.logger.info(f"Pushing branch '{branch_name}' to remote")
            
            # Ensure we're on the correct branch
            current_branch = self._get_current_branch()
            if current_branch != branch_name:
                self._run_git_command(['checkout', branch_name])
            
            # Push the branch
            if set_upstream:
                self._run_git_command(['push', '-u', 'origin', branch_name])
            else:
                self._run_git_command(['push', 'origin', branch_name])
            
            self.logger.info(f"Successfully pushed branch '{branch_name}'")
            return True
            
        except GitOperationError as e:
            self.logger.error(f"Failed to push branch '{branch_name}': {e}")
            return False
    
    def cleanup_merged_branches(self, dry_run: bool = False) -> List[str]:
        """
        Clean up branches that have been merged.
        
        Args:
            dry_run: If True, only return branches that would be deleted
            
        Returns:
            List of branches that were (or would be) deleted
        """
        try:
            # Get merged branches
            merged_output = self._run_git_command(['branch', '--merged', self.base_branch])
            merged_branches = [
                branch.strip().lstrip('* ') 
                for branch in merged_output.split('\n') 
                if branch.strip() and not branch.strip().startswith('*')
            ]
            
            # Filter for issue branches
            issue_branches = [
                branch for branch in merged_branches 
                if branch.startswith(self.branch_prefix) and branch != self.base_branch
            ]
            
            if dry_run:
                self.logger.info(f"Would delete {len(issue_branches)} merged branches")
                return issue_branches
            
            # Delete merged issue branches
            deleted_branches = []
            for branch in issue_branches:
                try:
                    self._run_git_command(['branch', '-d', branch])
                    deleted_branches.append(branch)
                    self.logger.info(f"Deleted merged branch: {branch}")
                    
                    # Remove from cache
                    if branch in self._branch_cache:
                        del self._branch_cache[branch]
                        
                except GitOperationError as e:
                    self.logger.warning(f"Failed to delete branch '{branch}': {e}")
            
            return deleted_branches
            
        except GitOperationError as e:
            self.logger.error(f"Failed to cleanup merged branches: {e}")
            return []
    
    def get_branch_status(self, branch_name: str) -> Dict[str, Any]:
        """
        Get status information for a branch.
        
        Args:
            branch_name: Name of the branch
            
        Returns:
            Dictionary with branch status information
        """
        try:
            # Check if branch exists
            if not self._branch_exists(branch_name):
                return {'exists': False}
            
            # Get branch info
            branch_info = self._get_branch_info(branch_name)
            
            # Get commit count
            commit_count = self._get_commit_count(branch_name)
            
            # Check if branch has been pushed
            remote_exists = self._remote_branch_exists(branch_name)
            
            # Check if branch is ahead/behind remote
            ahead_behind = self._get_ahead_behind_count(branch_name) if remote_exists else None
            
            return {
                'exists': True,
                'branch_info': branch_info,
                'commit_count': commit_count,
                'remote_exists': remote_exists,
                'ahead_behind': ahead_behind,
                'is_merged': self._is_branch_merged(branch_name)
            }
            
        except GitOperationError as e:
            self.logger.error(f"Failed to get branch status for '{branch_name}': {e}")
            return {'exists': False, 'error': str(e)}
    
    def _checkout_base_branch(self) -> None:
        """Checkout the base branch."""
        current_branch = self._get_current_branch()
        if current_branch != self.base_branch:
            self._run_git_command(['checkout', self.base_branch])
    
    def _pull_latest_changes(self) -> None:
        """Pull latest changes from remote."""
        try:
            self._run_git_command(['pull', 'origin', self.base_branch])
        except GitOperationError:
            # If pull fails, continue anyway (might be offline or no remote)
            self.logger.warning("Failed to pull latest changes")
    
    def _branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists locally."""
        try:
            output = self._run_git_command(['branch', '--list', branch_name])
            return branch_name in output
        except GitOperationError:
            return False
    
    def _remote_branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists on remote."""
        try:
            output = self._run_git_command(['branch', '-r', '--list', f"origin/{branch_name}"])
            return f"origin/{branch_name}" in output
        except GitOperationError:
            return False
    
    def _get_current_branch(self) -> str:
        """Get the name of the current branch."""
        return self._run_git_command(['branch', '--show-current']).strip()
    
    def _get_branch_info(self, branch_name: str) -> BranchInfo:
        """Get information about a branch."""
        if branch_name in self._branch_cache:
            return self._branch_cache[branch_name]
        
        # Extract issue number from branch name
        issue_number = 0
        if branch_name.startswith(self.branch_prefix):
            try:
                parts = branch_name.split('-')
                if len(parts) >= 2:
                    issue_number = int(parts[1])
            except (ValueError, IndexError):
                pass
        
        # Create basic branch info
        branch_info = BranchInfo(
            name=branch_name,
            created_at=datetime.now(),  # Approximate
            issue_number=issue_number,
            base_branch=self.base_branch
        )
        
        self._branch_cache[branch_name] = branch_info
        return branch_info
    
    def _get_commit_details(self, commit_hash: str) -> CommitInfo:
        """Get detailed information about a commit."""
        # Get commit information
        commit_info = self._run_git_command([
            'show', '--format=%H|%s|%an|%at', '--name-only', commit_hash
        ]).strip().split('\n')
        
        # Parse commit details
        header_parts = commit_info[0].split('|')
        commit_hash = header_parts[0]
        message = header_parts[1]
        author = header_parts[2]
        timestamp = datetime.fromtimestamp(int(header_parts[3]))
        
        # Get changed files (skip empty lines)
        files_changed = [line for line in commit_info[2:] if line.strip()]
        
        return CommitInfo(
            hash=commit_hash,
            message=message,
            author=author,
            timestamp=timestamp,
            files_changed=files_changed
        )
    
    def _get_commit_count(self, branch_name: str) -> int:
        """Get the number of commits in a branch."""
        try:
            output = self._run_git_command(['rev-list', '--count', branch_name])
            return int(output.strip())
        except (GitOperationError, ValueError):
            return 0
    
    def _get_ahead_behind_count(self, branch_name: str) -> Tuple[int, int]:
        """Get how many commits ahead/behind the branch is from remote."""
        try:
            output = self._run_git_command([
                'rev-list', '--left-right', '--count', 
                f'{branch_name}...origin/{branch_name}'
            ])
            ahead, behind = map(int, output.strip().split('\t'))
            return ahead, behind
        except (GitOperationError, ValueError):
            return 0, 0
    
    def _is_branch_merged(self, branch_name: str) -> bool:
        """Check if a branch has been merged into the base branch."""
        try:
            merged_output = self._run_git_command(['branch', '--merged', self.base_branch])
            return branch_name in merged_output
        except GitOperationError:
            return False
    
    def _generate_file_summary(self, file_paths: List[str]) -> str:
        """Generate a summary of files for commit messages."""
        if not file_paths:
            return "No files"
        
        # Group files by directory
        file_groups = {}
        for file_path in file_paths:
            path = Path(file_path)
            dir_name = str(path.parent) if path.parent != Path('.') else '.'
            if dir_name not in file_groups:
                file_groups[dir_name] = []
            file_groups[dir_name].append(path.name)
        
        # Generate summary
        summary_lines = []
        for dir_name, files in file_groups.items():
            if len(files) == 1:
                summary_lines.append(f"- {dir_name}/{files[0]}")
            else:
                summary_lines.append(f"- {dir_name}/ ({len(files)} files)")
        
        return '\n'.join(summary_lines)
    
    def _slugify(self, text: str) -> str:
        """Convert text to a URL-safe slug."""
        
        # Convert to lowercase and replace spaces with hyphens
        slug = text.lower().replace(' ', '-')
        
        # Remove special characters except hyphens and alphanumeric
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        # Limit length and ensure it doesn't end with hyphen
        slug = slug[:50].rstrip('-')
        
        return slug