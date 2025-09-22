"""
Tests for GitHub integration functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import json
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.github_issue_creator import GitHubIssueCreator
from src.issue_processor import GitHubIntegratedIssueProcessor, IssueData, ProcessingResult, IssueProcessingStatus
from tests.conftest import MockGitHubException


class TestExtendedGitHubIssueCreator:
    """Test cases for extended GitHubIssueCreator functionality"""
    
    @patch('src.github_issue_creator.Github')
    def test_get_issue_success(self, mock_github_class, mock_github_token, mock_repository_name):
        """Test successful issue retrieval"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.title = "Test Issue"
        
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue
        
        # Test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        result = creator.get_issue(123)
        
        # Assertions
        mock_repo.get_issue.assert_called_once_with(123)
        assert result == mock_issue
    
    @patch('src.github_issue_creator.Github')
    def test_get_issue_failure(self, mock_github_class, mock_github_token, mock_repository_name):
        """Test issue retrieval failure"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_issue.side_effect = MockGitHubException("Issue not found")
        
        # Test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        
        with pytest.raises(RuntimeError, match="Failed to get issue #123"):
            creator.get_issue(123)
    
    @patch('src.github_issue_creator.Github')
    def test_get_issues_with_labels(self, mock_github_class, mock_github_token, mock_repository_name):
        """Test getting issues with specific labels"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_issue1 = Mock()
        mock_issue1.number = 1
        mock_issue2 = Mock()
        mock_issue2.number = 2
        
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_issues.return_value = [mock_issue1, mock_issue2]
        
        # Test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        result = creator.get_issues_with_labels(["site-monitor", "bug"], state="open", limit=5)
        
        # Assertions
        mock_repo.get_issues.assert_called_once_with(state="open", labels=["site-monitor", "bug"])
        assert len(result) == 2
        assert result[0] == mock_issue1
        assert result[1] == mock_issue2
    
    @patch('src.github_issue_creator.Github')
    def test_assign_issue(self, mock_github_class, mock_github_token, mock_repository_name):
        """Test issue assignment"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue
        
        # Test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        result = creator.assign_issue(123, ["user1", "user2"])
        
        # Assertions
        mock_repo.get_issue.assert_called_once_with(123)
        mock_issue.add_to_assignees.assert_called_once_with("user1", "user2")
        assert result is True
    
    @patch('src.github_issue_creator.Github')
    def test_unassign_issue(self, mock_github_class, mock_github_token, mock_repository_name):
        """Test issue unassignment"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue
        
        # Test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        result = creator.unassign_issue(123, ["user1"])
        
        # Assertions
        mock_repo.get_issue.assert_called_once_with(123)
        mock_issue.remove_from_assignees.assert_called_once_with("user1")
        assert result is True
    
    @patch('src.github_issue_creator.Github')
    def test_add_comment(self, mock_github_class, mock_github_token, mock_repository_name):
        """Test adding comment to issue"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        mock_comment = Mock()
        
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue
        mock_issue.create_comment.return_value = mock_comment
        
        # Test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        result = creator.add_comment(123, "Test comment")
        
        # Assertions
        mock_repo.get_issue.assert_called_once_with(123)
        mock_issue.create_comment.assert_called_once_with("Test comment")
        assert result == mock_comment
    
    @patch('src.github_issue_creator.Github')
    def test_get_issue_data(self, mock_github_class, mock_github_token, mock_repository_name):
        """Test getting standardized issue data"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_repo = Mock()
        mock_issue = Mock()
        mock_assignee1 = Mock()
        mock_assignee1.login = "user1"
        mock_assignee2 = Mock()
        mock_assignee2.login = "user2"
        mock_label1 = Mock()
        mock_label1.name = "bug"
        mock_label2 = Mock()
        mock_label2.name = "site-monitor"
        
        mock_issue.number = 123
        mock_issue.title = "Test Issue"
        mock_issue.body = "Test body"
        mock_issue.assignees = [mock_assignee1, mock_assignee2]
        mock_issue.labels = [mock_label1, mock_label2]
        mock_issue.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_issue.updated_at = datetime(2023, 1, 2, 12, 0, 0)
        mock_issue.html_url = "https://github.com/owner/repo/issues/123"
        mock_issue.state = "open"
        
        mock_github_class.return_value = mock_github_instance
        mock_github_instance.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue
        
        # Test
        creator = GitHubIssueCreator(mock_github_token, mock_repository_name)
        result = creator.get_issue_data(123)
        
        # Assertions
        expected = {
            'number': 123,
            'title': "Test Issue",
            'body': "Test body",
            'labels': ["bug", "site-monitor"],
            'assignees': ["user1", "user2"],
            'created_at': "2023-01-01T12:00:00",
            'updated_at': "2023-01-02T12:00:00",
            'url': "https://github.com/owner/repo/issues/123",
            'state': "open"
        }
        assert result == expected


class TestGitHubIntegratedIssueProcessor:
    """Test cases for GitHubIntegratedIssueProcessor"""
    
    @pytest.fixture
    def mock_config_with_agent(self, tmp_path):
        """Create a mock config file with agent settings"""
        config_content = """
agent:
  username: "test-agent"
  workflow_directory: "docs/workflow/deliverables"
  output_directory: "study"
  processing:
    default_timeout_minutes: 5
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)
        return str(config_file)
    
    @patch('src.issue_processor.GitHubIssueCreator')
    @patch('src.issue_processor.WorkflowMatcher')
    @patch('src.issue_processor.ConfigManager')
    def test_init_success(self, mock_config_manager, mock_workflow_matcher, mock_github_creator, mock_config_with_agent):
        """Test successful initialization of GitHub integrated processor"""
        # Setup mocks
        mock_config = Mock()
        mock_config.agent = Mock()
        mock_config.agent.username = "test-agent"
        mock_config.agent.workflow_directory = "docs/workflow/deliverables"
        mock_config.agent.template_directory = "templates"
        mock_config.agent.template_directory = "templates"
        mock_config.agent.output_directory = "study"
        mock_config.agent.processing = Mock()
        mock_config.agent.processing.default_timeout_minutes = 5
        
        mock_config_manager.load_config.return_value = mock_config
        mock_workflow_matcher.return_value = Mock()
        mock_github_creator.return_value = Mock()
        
        # Test
        processor = GitHubIntegratedIssueProcessor(
            github_token="token123",
            repository="owner/repo",
            config_path=mock_config_with_agent
        )
        
        # Assertions
        mock_config_manager.load_config.assert_called_once_with(mock_config_with_agent)
        mock_github_creator.assert_called_once_with("token123", "owner/repo")
        assert processor.repository == "owner/repo"
        assert processor.agent_username == "test-agent"
    
    @patch('src.issue_processor.GitHubIssueCreator')
    @patch('src.issue_processor.WorkflowMatcher')
    @patch('src.issue_processor.ConfigManager')
    def test_process_github_issue_success(self, mock_config_manager, mock_workflow_matcher, mock_github_creator, mock_config_with_agent, tmp_path):
        """Test successful GitHub issue processing"""
        # Setup mocks
        mock_config = Mock()
        mock_config.agent = Mock()
        mock_config.agent.username = "test-agent"
        mock_config.agent.workflow_directory = "docs/workflow/deliverables"
        mock_config.agent.template_directory = "templates"
        mock_config.agent.output_directory = str(tmp_path)
        mock_config.agent.processing = Mock()
        mock_config.agent.processing.default_timeout_minutes = 5
        
        mock_config_manager.load_config.return_value = mock_config
        
        # Mock workflow matcher
        mock_workflow = Mock()
        mock_workflow.name = "test-workflow"
        mock_workflow.deliverables = []
        mock_workflow.output = {"folder_structure": "issue_{issue_number}", "file_pattern": "{deliverable_name}.md"}
        mock_workflow_matcher_instance = Mock()
        mock_workflow_matcher_instance.get_best_workflow_match.return_value = (mock_workflow, "Found match")
        mock_workflow_matcher.return_value = mock_workflow_matcher_instance
        
        # Mock GitHub creator
        mock_github_instance = Mock()
        mock_github_instance.get_issue_data.return_value = {
            'number': 123,
            'title': "Test Issue",
            'body': "Test body",
            'labels': ["site-monitor", "bug"],
            'assignees': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'url': "https://github.com/owner/repo/issues/123",
            'state': "open"
        }
        mock_github_creator.return_value = mock_github_instance
        
        # Test
        processor = GitHubIntegratedIssueProcessor(
            github_token="token123",
            repository="owner/repo",
            config_path=mock_config_with_agent
        )
        
        result = processor.process_github_issue(123)
        
        # Assertions
        mock_github_instance.get_issue_data.assert_called_once_with(123)
        mock_github_instance.assign_issue.assert_called_once_with(123, ["test-agent"])
        mock_github_instance.add_comment.assert_called_once()
        
        assert result.issue_number == 123
        assert result.status == IssueProcessingStatus.COMPLETED
        assert result.workflow_name == "test-workflow"
    
    @patch('src.issue_processor.GitHubIssueCreator')
    @patch('src.issue_processor.WorkflowMatcher')
    @patch('src.issue_processor.ConfigManager')
    def test_process_github_issue_needs_clarification(self, mock_config_manager, mock_workflow_matcher, mock_github_creator, mock_config_with_agent, tmp_path):
        """Test GitHub issue processing that needs clarification"""
        # Setup mocks
        mock_config = Mock()
        mock_config.agent = Mock()
        mock_config.agent.username = "test-agent"
        mock_config.agent.workflow_directory = "docs/workflow/deliverables"
        mock_config.agent.template_directory = "templates"
        mock_config.agent.output_directory = str(tmp_path)
        mock_config.agent.processing = Mock()
        mock_config.agent.processing.default_timeout_minutes = 5
        
        mock_config_manager.load_config.return_value = mock_config
        
        # Mock workflow matcher - no match found
        mock_workflow_matcher_instance = Mock()
        mock_workflow_matcher_instance.get_best_workflow_match.return_value = (None, "No match found")
        mock_workflow_matcher_instance.get_available_workflows.return_value = []
        mock_workflow_matcher.return_value = mock_workflow_matcher_instance
        
        # Mock GitHub creator
        mock_github_instance = Mock()
        mock_github_instance.get_issue_data.return_value = {
            'number': 123,
            'title': "Test Issue",
            'body': "Test body",
            'labels': ["site-monitor"],
            'assignees': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'url': "https://github.com/owner/repo/issues/123",
            'state': "open"
        }
        mock_github_creator.return_value = mock_github_instance
        
        # Test
        processor = GitHubIntegratedIssueProcessor(
            github_token="token123",
            repository="owner/repo",
            config_path=mock_config_with_agent
        )
        
        result = processor.process_github_issue(123)
        
        # Assertions
        mock_github_instance.get_issue_data.assert_called_once_with(123)
        mock_github_instance.assign_issue.assert_called_once_with(123, ["test-agent"])
        mock_github_instance.add_comment.assert_called_once()
        mock_github_instance.unassign_issue.assert_called_once_with(123, ["test-agent"])
        
        assert result.issue_number == 123
        assert result.status == IssueProcessingStatus.NEEDS_CLARIFICATION
        assert result.clarification_needed is not None
    
    @patch('src.issue_processor.GitHubIssueCreator')
    @patch('src.issue_processor.WorkflowMatcher')
    @patch('src.issue_processor.ConfigManager')
    def test_should_process_issue(self, mock_config_manager, mock_workflow_matcher, mock_github_creator, mock_config_with_agent):
        """Test issue processing criteria"""
        # Setup mocks
        mock_config = Mock()
        mock_config.agent = Mock()
        mock_config.agent.username = "test-agent"
        mock_config.agent.workflow_directory = "docs/workflow/deliverables"
        mock_config.agent.template_directory = "templates"
        mock_config.agent.output_directory = "study"
        mock_config.agent.processing = Mock()
        mock_config.agent.processing.default_timeout_minutes = 5
        
        mock_config_manager.load_config.return_value = mock_config
        mock_workflow_matcher.return_value = Mock()
        mock_github_creator.return_value = Mock()
        
        # Test
        processor = GitHubIntegratedIssueProcessor(
            github_token="token123",
            repository="owner/repo",
            config_path=mock_config_with_agent
        )
        
        # Test case 1: Valid issue
        issue_data = IssueData(
            number=123,
            title="Test",
            body="Body",
            labels=["site-monitor", "bug"],
            assignees=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="test-url"
        )
        assert processor._should_process_issue(issue_data) is True
        
        # Test case 2: No site-monitor label
        issue_data.labels = ["bug"]
        assert processor._should_process_issue(issue_data) is False
        
        # Test case 3: Already assigned to agent
        issue_data.labels = ["site-monitor"]
        issue_data.assignees = ["test-agent"]
        # Should return False if already processing
        processor._processing_state["123"] = {"status": "processing"}
        assert processor._should_process_issue(issue_data) is False
    
    @patch('src.issue_processor.GitHubIssueCreator')
    @patch('src.issue_processor.WorkflowMatcher')
    @patch('src.issue_processor.ConfigManager')
    def test_process_labeled_issues(self, mock_config_manager, mock_workflow_matcher, mock_github_creator, mock_config_with_agent):
        """Test processing multiple labeled issues"""
        # Setup mocks
        mock_config = Mock()
        mock_config.agent = Mock()
        mock_config.agent.username = "test-agent"
        mock_config.agent.workflow_directory = "docs/workflow/deliverables"
        mock_config.agent.template_directory = "templates"
        mock_config.agent.output_directory = "study"
        mock_config.agent.processing = Mock()
        mock_config.agent.processing.default_timeout_minutes = 5
        
        mock_config_manager.load_config.return_value = mock_config
        mock_workflow_matcher.return_value = Mock()
        
        # Mock GitHub creator
        mock_issue1 = Mock()
        mock_issue1.number = 1
        mock_issue2 = Mock()
        mock_issue2.number = 2
        
        mock_github_instance = Mock()
        mock_github_instance.get_issues_with_labels.return_value = [mock_issue1, mock_issue2]
        mock_github_creator.return_value = mock_github_instance
        
        # Test
        processor = GitHubIntegratedIssueProcessor(
            github_token="token123",
            repository="owner/repo",
            config_path=mock_config_with_agent
        )
        
        # Mock the process_github_issue method to avoid full processing
        processor.process_github_issue = Mock(side_effect=[
            ProcessingResult(1, IssueProcessingStatus.COMPLETED),
            ProcessingResult(2, IssueProcessingStatus.ERROR, error_message="Test error")
        ])
        
        results = processor.process_labeled_issues(["site-monitor"], limit=5)
        
        # Assertions
        mock_github_instance.get_issues_with_labels.assert_called_once_with(["site-monitor"], state="open", limit=5)
        assert len(results) == 2
        assert results[0].issue_number == 1
        assert results[0].status == IssueProcessingStatus.COMPLETED
        assert results[1].issue_number == 2
        assert results[1].status == IssueProcessingStatus.ERROR
    
    def test_generate_completion_comment(self):
        """Test completion comment generation"""
        from src.issue_processor import GitHubIntegratedIssueProcessor
        
        # Create a simple processor instance for testing the method
        # We can't easily mock the full initialization, so we'll test the method directly
        result = ProcessingResult(
            issue_number=123,
            status=IssueProcessingStatus.COMPLETED,
            workflow_name="test-workflow",
            created_files=["file1.md", "file2.md"],
            processing_time_seconds=45.6
        )
        
        # Mock a processor instance
        processor = Mock()
        processor._generate_completion_comment = GitHubIntegratedIssueProcessor._generate_completion_comment
        
        comment = processor._generate_completion_comment(processor, result)
        
        assert "✅ **Issue Processing Complete**" in comment
        assert "test-workflow" in comment
        assert "45.6s" in comment
        assert "file1.md" in comment
        assert "file2.md" in comment
    
    def test_generate_error_comment(self):
        """Test error comment generation"""
        from src.issue_processor import GitHubIntegratedIssueProcessor
        
        result = ProcessingResult(
            issue_number=123,
            status=IssueProcessingStatus.ERROR,
            error_message="Something went wrong"
        )
        
        # Mock a processor instance
        processor = Mock()
        processor._generate_error_comment = GitHubIntegratedIssueProcessor._generate_error_comment
        
        comment = processor._generate_error_comment(processor, result)
        
        assert "❌ **Issue Processing Failed**" in comment
        assert "Something went wrong" in comment
        assert "unassigned" in comment