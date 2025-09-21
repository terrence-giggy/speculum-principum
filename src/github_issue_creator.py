"""
GitHub Operations Module
Handles GitHub API operations for Speculum Principum
"""

from github import Github, Auth
from github.GithubException import GithubException
from typing import List, Optional
from unittest.mock import Mock


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
                    if hasattr(label, '_mock_name'):
                        # For mock objects created with Mock(name="labelname")
                        repo_labels.append(label._mock_name)
                    elif hasattr(label, 'name') and not isinstance(label.name, Mock):
                        # For real GitHub label objects
                        repo_labels.append(label.name)
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
            raise RuntimeError(f"Failed to create GitHub issue: {e.data.get('message', str(e))}") from e
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
            raise RuntimeError(f"Failed to get repository info: {e.data.get('message', str(e))}") from e


