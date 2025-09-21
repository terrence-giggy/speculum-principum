"""
Unit tests for GitHub operations module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.github_issue_creator import GitHubIssueCreator
from tests.conftest import MockGitHubException


class TestGitHubIssueCreator:
    """Test cases for GitHubIssueCreator class"""
    
    def test_init(self, mock_github_token, mock_repository_name):
        """Test GitHubIssueCreator initialization"""
        with patch('src.github_issue_creator.Github') as mock_github_class, \
             patch('src.github_issue_creator.Auth') as mock_auth_class:
            mock_github_instance = Mock()
            mock_repo = Mock()
            mock_auth_token = Mock()
            mock_github_class.return_value = mock_github_instance
            mock_github_instance.get_repo.return_value = mock_repo
            mock_auth_class.Token.return_value = mock_auth_token
            
            creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
            
            mock_auth_class.Token.assert_called_once_with(mock_github_token)
            mock_github_class.assert_called_once_with(auth=mock_auth_token)
            mock_github_instance.get_repo.assert_called_once_with(mock_repository_name)
            assert creator.repository == mock_repository_name
            assert creator.repo == mock_repo
    
    @patch('src.github_issue_creator.Github')
    def test_create_issue_success(self, mock_github_class, mock_github_token, mock_repository_name, mock_issue_data, mock_github_issue):
        """Test successful issue creation"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.create_issue.return_value = mock_github_issue
        mock_repo.get_labels.return_value = [Mock(name="bug"), Mock(name="urgent")]
        
        # Create instance and test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        result = creator.create_issue(
            title=mock_issue_data["title"],
            body=mock_issue_data["body"],
            labels=mock_issue_data["labels"],
            assignees=mock_issue_data["assignees"]
        )
        
        # Assertions
        mock_repo.create_issue.assert_called_once_with(
            title=mock_issue_data["title"],
            body=mock_issue_data["body"],
            labels=mock_issue_data["labels"],
            assignees=mock_issue_data["assignees"]
        )
        assert result == mock_github_issue
    
    @patch('src.github_issue_creator.Github')
    def test_create_issue_minimal(self, mock_github_class, mock_github_token, mock_repository_name, mock_github_issue):
        """Test issue creation with minimal parameters"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.create_issue.return_value = mock_github_issue
        mock_repo.get_labels.return_value = []
        
        # Create instance and test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        result = creator.create_issue(title="Test Issue")
        
        # Assertions
        mock_repo.create_issue.assert_called_once_with(
            title="Test Issue",
            body="",
            labels=[],
            assignees=[]
        )
        assert result == mock_github_issue
    
    @patch('src.github_issue_creator.Github')
    def test_create_issue_invalid_labels(self, mock_github_class, mock_github_token, mock_repository_name, mock_github_issue, capsys):
        """Test issue creation with invalid labels"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.create_issue.return_value = mock_github_issue
        mock_repo.get_labels.return_value = [Mock(name="bug")]  # Only 'bug' exists
        
        # Create instance and test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        result = creator.create_issue(
            title="Test Issue",
            labels=["bug", "nonexistent-label"]
        )
        
        # Check warning was printed
        captured = capsys.readouterr()
        assert "Warning: Labels not found in repository: ['nonexistent-label']" in captured.out
        
        # Check only valid labels were used
        mock_repo.create_issue.assert_called_once_with(
            title="Test Issue",
            body="",
            labels=["bug"],
            assignees=[]
        )
        assert result == mock_github_issue
    
    @patch('src.github_issue_creator.Github')
    def test_create_issue_github_exception(self, mock_github_class, mock_github_token, mock_repository_name):
        """Test issue creation with GitHub API exception"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_labels.return_value = []
        
        # Configure exception
        github_exception = MockGitHubException("API rate limit exceeded")
        mock_repo.create_issue.side_effect = github_exception
        
        # Create instance and test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        
        with pytest.raises(RuntimeError, match="Failed to create GitHub issue: API rate limit exceeded"):
            creator.create_issue(title="Test Issue")
    
    @patch('src.github_issue_creator.Github')
    def test_create_issue_unexpected_exception(self, mock_github_class, mock_github_token, mock_repository_name):
        """Test issue creation with unexpected exception"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_labels.return_value = []
        mock_repo.create_issue.side_effect = ValueError("Unexpected error")
        
        # Create instance and test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        
        with pytest.raises(RuntimeError, match="Unexpected error creating issue: Unexpected error"):
            creator.create_issue(title="Test Issue")
    
    @patch('src.github_issue_creator.Github')
    def test_get_repository_info_success(self, mock_github_class, mock_github_token, mock_repository_name, sample_repo_info):
        """Test successful repository info retrieval"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        
        # Configure repo attributes
        mock_repo.name = sample_repo_info['name']
        mock_repo.full_name = sample_repo_info['full_name']
        mock_repo.description = sample_repo_info['description']
        mock_repo.html_url = sample_repo_info['url']
        mock_repo.open_issues_count = sample_repo_info['issues_count']
        
        # Create instance and test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        result = creator.get_repository_info()
        
        # Assertions
        assert result == sample_repo_info
    
    @patch('src.github_issue_creator.Github')
    def test_get_repository_info_exception(self, mock_github_class, mock_github_token, mock_repository_name):
        """Test repository info retrieval with exception"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        
        # Configure exception
        github_exception = MockGitHubException("Repository not found")
        # Use type() to set the property on the mock's class
        type(mock_repo).name = property(lambda self: (_ for _ in ()).throw(github_exception))
        
        # Create instance and test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        
        with pytest.raises(RuntimeError, match="Failed to get repository info: Repository not found"):
            creator.get_repository_info()


@pytest.mark.integration
class TestGitHubOperationsIntegration:
    """Integration tests for GitHub operations (requires real API calls)"""
    
    @pytest.mark.skip(reason="Requires real GitHub token and repository")
    def test_real_issue_creation(self):
        """Test real issue creation (skipped by default)"""
        # This test would require real credentials and a test repository
        # It's marked as skip by default to avoid accidental API calls
        pass