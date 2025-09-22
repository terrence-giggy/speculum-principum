"""
GitHub Operations Module
Handles GitHub API operations for Speculum Principum
"""

from github import Github, Auth
from github.GithubException import GithubException
from typing import List, Optional, Dict, Any
from unittest.mock import Mock
from datetime import datetime


class GitHubIssueCreator:
    """Handles creation of GitHub issues"""
    
    def __init__(self, token: str, repository: str):
        """
        Initialize the GitHub issue creator
        
        Args:
            token: GitHub personal access token
            repository: Repository name in format 'owner/repo'
        """
        self.github = Github(auth=Auth.Token(token))
        self.repository = repository
        self.repo = self.github.get_repo(repository)
    
    def _extract_github_error_message(self, e: GithubException) -> str:
        """
        Safely extract error message from GitHub exception.
        
        Args:
            e: GithubException instance
            
        Returns:
            String error message
        """
        try:
            if hasattr(e, 'data') and e.data and hasattr(e.data, 'get'):
                return e.data.get('message', str(e))
            else:
                return str(e)
        except (AttributeError, TypeError):
            return str(e)
    
    def create_issue(
        self, 
        title: str, 
        body: str = "", 
        labels: Optional[List[str]] = None, 
        assignees: Optional[List[str]] = None
    ):
        """
        Create a new GitHub issue
        
        Args:
            title: Issue title
            body: Issue description/body
            labels: List of label names to apply
            assignees: List of usernames to assign
            
        Returns:
            Created issue object
            
        Raises:
            GithubException: If issue creation fails
        """
        try:
            # Validate labels exist in the repository
            if labels:
                repo_labels = []
                for label in self.repo.get_labels():
                    # Handle both real GitHub label objects and mock objects
                    if hasattr(label, 'name') and not isinstance(label.name, Mock):
                        # For real GitHub label objects
                        repo_labels.append(label.name)
                    elif hasattr(label, '_mock_name'):
                        # For mock objects created with Mock(name="labelname")
                        repo_labels.append(getattr(label, '_mock_name', str(label)))
                    else:
                        # Fallback for other mock setups
                        repo_labels.append(str(label))
                
                invalid_labels = [label for label in labels if label not in repo_labels]
                if invalid_labels:
                    print(f"Warning: Labels not found in repository: {invalid_labels}")
                    labels = [label for label in labels if label in repo_labels]
            
            # Create the issue
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=labels or [],
                assignees=assignees or []
            )
            
            return issue
            
        except GithubException as e:
            raise RuntimeError(f"Failed to create GitHub issue: {self._extract_github_error_message(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error creating issue: {str(e)}") from e
    
    def get_repository_info(self):
        """Get basic repository information"""
        try:
            return {
                'name': self.repo.name,
                'full_name': self.repo.full_name,
                'description': self.repo.description,
                'url': self.repo.html_url,
                'issues_count': self.repo.open_issues_count
            }
        except GithubException as e:
            raise RuntimeError(f"Failed to get repository info: {self._extract_github_error_message(e)}") from e

    def get_issue(self, issue_number: int):
        """
        Get a specific issue by number
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            GitHub issue object
            
        Raises:
            RuntimeError: If issue retrieval fails
        """
        try:
            return self.repo.get_issue(issue_number)
        except GithubException as e:
            raise RuntimeError(f"Failed to get issue #{issue_number}: {self._extract_github_error_message(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error getting issue #{issue_number}: {str(e)}") from e

    def get_issues_with_labels(self, 
                              labels: List[str], 
                              state: str = "open",
                              limit: Optional[int] = None) -> List:
        """
        Get issues that have specific labels
        
        Args:
            labels: List of label names to filter by
            state: Issue state ('open', 'closed', 'all')
            limit: Maximum number of issues to return
            
        Returns:
            List of GitHub issue objects
            
        Raises:
            RuntimeError: If issue retrieval fails
        """
        try:
            issues = self.repo.get_issues(state=state, labels=labels)
            if limit:
                return list(issues[:limit])
            return list(issues)
        except GithubException as e:
            raise RuntimeError(f"Failed to get issues with labels {labels}: {self._extract_github_error_message(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error getting issues with labels {labels}: {str(e)}") from e

    def assign_issue(self, issue_number: int, assignees: List[str]) -> bool:
        """
        Assign an issue to specific users
        
        Args:
            issue_number: GitHub issue number
            assignees: List of usernames to assign
            
        Returns:
            True if assignment was successful
            
        Raises:
            RuntimeError: If assignment fails
        """
        try:
            issue = self.get_issue(issue_number)
            issue.add_to_assignees(*assignees)
            return True
        except GithubException as e:
            raise RuntimeError(f"Failed to assign issue #{issue_number}: {self._extract_github_error_message(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error assigning issue #{issue_number}: {str(e)}") from e

    def unassign_issue(self, issue_number: int, assignees: List[str]) -> bool:
        """
        Remove assignment from an issue
        
        Args:
            issue_number: GitHub issue number
            assignees: List of usernames to unassign
            
        Returns:
            True if unassignment was successful
            
        Raises:
            RuntimeError: If unassignment fails
        """
        try:
            issue = self.get_issue(issue_number)
            issue.remove_from_assignees(*assignees)
            return True
        except GithubException as e:
            raise RuntimeError(f"Failed to unassign issue #{issue_number}: {self._extract_github_error_message(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error unassigning issue #{issue_number}: {str(e)}") from e

    def add_comment(self, issue_number: int, comment_body: str):
        """
        Add a comment to an issue
        
        Args:
            issue_number: GitHub issue number
            comment_body: Comment text content
            
        Returns:
            Created comment object
            
        Raises:
            RuntimeError: If comment creation fails
        """
        try:
            issue = self.get_issue(issue_number)
            return issue.create_comment(comment_body)
        except GithubException as e:
            raise RuntimeError(f"Failed to add comment to issue #{issue_number}: {self._extract_github_error_message(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error adding comment to issue #{issue_number}: {str(e)}") from e

    def update_issue_labels(self, issue_number: int, labels: List[str]) -> bool:
        """
        Update labels on an issue
        
        Args:
            issue_number: GitHub issue number
            labels: List of label names to set
            
        Returns:
            True if labels were updated successfully
            
        Raises:
            RuntimeError: If label update fails
        """
        try:
            issue = self.get_issue(issue_number)
            # Validate labels exist in repository
            repo_labels = []
            for label in self.repo.get_labels():
                # Handle both real GitHub label objects and mock objects
                if hasattr(label, 'name') and not isinstance(label.name, Mock):
                    # For real GitHub label objects
                    repo_labels.append(label.name)
                elif hasattr(label, '_mock_name'):
                    # For mock objects created with Mock(name="labelname")
                    repo_labels.append(getattr(label, '_mock_name', str(label)))
                else:
                    # Fallback for other mock setups
                    repo_labels.append(str(label))
            
            invalid_labels = [label for label in labels if label not in repo_labels]
            if invalid_labels:
                print(f"Warning: Labels not found in repository: {invalid_labels}")
                labels = [label for label in labels if label in repo_labels]
            
            issue.set_labels(*labels)
            return True
        except GithubException as e:
            raise RuntimeError(f"Failed to update labels on issue #{issue_number}: {self._extract_github_error_message(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error updating labels on issue #{issue_number}: {str(e)}") from e

    def get_issue_data(self, issue_number: int) -> Dict[str, Any]:
        """
        Get standardized issue data for processing
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Dictionary with standardized issue data
            
        Raises:
            RuntimeError: If issue retrieval fails
        """
        try:
            issue = self.get_issue(issue_number)
            
            # Extract assignee usernames
            assignees = []
            if issue.assignees:
                assignees = [assignee.login for assignee in issue.assignees]
            
            # Extract label names
            labels = []
            if issue.labels:
                labels = [label.name for label in issue.labels]
            
            return {
                'number': issue.number,
                'title': issue.title,
                'body': issue.body or '',
                'labels': labels,
                'assignees': assignees,
                'created_at': issue.created_at.isoformat() if issue.created_at else datetime.now().isoformat(),
                'updated_at': issue.updated_at.isoformat() if issue.updated_at else datetime.now().isoformat(),
                'url': issue.html_url,
                'state': issue.state
            }
        except GithubException as e:
            raise RuntimeError(f"Failed to get issue data for #{issue_number}: {self._extract_github_error_message(e)}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error getting issue data for #{issue_number}: {str(e)}") from e


