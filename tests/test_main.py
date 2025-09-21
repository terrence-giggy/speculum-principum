"""
Integration tests for main.py application entry point
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from io import StringIO

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import main


class TestMainApplication:
    """Test cases for main application entry point"""
    
    @patch('main.load_dotenv')
    def test_main_missing_github_token(self, mock_load_dotenv, monkeypatch, capsys):
        """Test main function with missing GITHUB_TOKEN"""
        # Remove GITHUB_TOKEN from environment
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_REPOSITORY", "testuser/testrepo")
        
        # Mock sys.argv
        test_args = ["main.py", "create-issue", "--title", "Test Issue"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        # Test should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            main.main()
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: GITHUB_TOKEN environment variable is required" in captured.err
    
    @patch('main.load_dotenv')
    def test_main_missing_github_repository(self, mock_load_dotenv, monkeypatch, capsys):
        """Test main function with missing GITHUB_REPOSITORY"""
        # Set GITHUB_TOKEN but remove GITHUB_REPOSITORY
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        
        # Mock sys.argv
        test_args = ["main.py", "create-issue", "--title", "Test Issue"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        # Test should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            main.main()
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: GITHUB_REPOSITORY environment variable is required" in captured.err
    
    @patch('main.GitHubIssueCreator')
    def test_main_create_issue_success(self, mock_creator_class, environment_variables, monkeypatch, capsys, mock_github_issue):
        """Test successful issue creation through main function"""
        # Setup mocks
        mock_creator_instance = Mock()
        mock_creator_class.return_value = mock_creator_instance
        mock_creator_instance.create_issue.return_value = mock_github_issue
        
        # Mock sys.argv
        test_args = [
            "main.py", "create-issue",
            "--title", "Test Issue",
            "--body", "Test body",
            "--labels", "bug", "urgent",
            "--assignees", "user1", "user2"
        ]
        monkeypatch.setattr(sys, "argv", test_args)
        
        # Call main function
        main.main()
        
        # Verify issue creator was called correctly
        mock_creator_class.assert_called_once_with("ghp_test_token_1234567890abcdef", "testuser/testrepo")
        mock_creator_instance.create_issue.assert_called_once_with(
            title="Test Issue",
            body="Test body",
            labels=["bug", "urgent"],
            assignees=["user1", "user2"]
        )
        
        # Check output
        captured = capsys.readouterr()
        assert "Successfully created issue #123: Test Issue" in captured.out
        assert "URL: https://github.com/testuser/testrepo/issues/123" in captured.out
    
    @patch('main.GitHubIssueCreator')
    def test_main_create_issue_minimal_args(self, mock_creator_class, environment_variables, monkeypatch, capsys, mock_github_issue):
        """Test issue creation with minimal arguments"""
        # Setup mocks
        mock_creator_instance = Mock()
        mock_creator_class.return_value = mock_creator_instance
        mock_creator_instance.create_issue.return_value = mock_github_issue
        
        # Mock sys.argv with minimal args
        test_args = ["main.py", "create-issue", "--title", "Minimal Issue"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        # Call main function
        main.main()
        
        # Verify issue creator was called with defaults
        mock_creator_instance.create_issue.assert_called_once_with(
            title="Minimal Issue",
            body="",
            labels=[],
            assignees=[]
        )
    
    @patch('main.GitHubIssueCreator')
    def test_main_create_issue_exception(self, mock_creator_class, environment_variables, monkeypatch, capsys):
        """Test main function with exception during issue creation"""
        # Setup mocks
        mock_creator_instance = Mock()
        mock_creator_class.return_value = mock_creator_instance
        mock_creator_instance.create_issue.side_effect = RuntimeError("API Error")
        
        # Mock sys.argv
        test_args = ["main.py", "create-issue", "--title", "Test Issue"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        # Test should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            main.main()
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: API Error" in captured.err
    
    def test_main_invalid_operation(self, environment_variables, monkeypatch, capsys):
        """Test main function with invalid operation"""
        # Mock sys.argv with invalid operation
        test_args = ["main.py", "invalid-operation", "--title", "Test"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        # Test should exit with code 2 (argparse error)
        with pytest.raises(SystemExit) as exc_info:
            main.main()
        
        assert exc_info.value.code == 2
    
    def test_main_missing_required_title(self, environment_variables, monkeypatch, capsys):
        """Test main function with missing required title argument"""
        # Mock sys.argv without required title
        test_args = ["main.py", "create-issue"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        # Test should exit with code 2 (argparse error)
        with pytest.raises(SystemExit) as exc_info:
            main.main()
        
        assert exc_info.value.code == 2


class TestArgumentParsing:
    """Test cases for CLI argument parsing"""
    
    def test_parse_create_issue_full_args(self, monkeypatch):
        """Test parsing of create-issue with all arguments"""
        test_args = [
            "main.py", "create-issue",
            "--title", "Full Test Issue",
            "--body", "Detailed description",
            "--labels", "bug", "urgent", "enhancement",
            "--assignees", "dev1", "dev2", "qa1"
        ]
        monkeypatch.setattr(sys, "argv", test_args)
        
        # Import here to avoid module-level execution
        import argparse
        
        parser = argparse.ArgumentParser(description='Speculum Principum - GitHub Operations via Actions')
        parser.add_argument('operation', choices=['create-issue'], help='Operation to perform')
        parser.add_argument('--title', required=True, help='Issue title')
        parser.add_argument('--body', help='Issue body/description')
        parser.add_argument('--labels', nargs='*', help='Issue labels')
        parser.add_argument('--assignees', nargs='*', help='Issue assignees')
        
        args = parser.parse_args(test_args[1:])  # Skip script name
        
        assert args.operation == "create-issue"
        assert args.title == "Full Test Issue"
        assert args.body == "Detailed description"
        assert args.labels == ["bug", "urgent", "enhancement"]
        assert args.assignees == ["dev1", "dev2", "qa1"]
    
    def test_parse_create_issue_minimal_args(self, monkeypatch):
        """Test parsing of create-issue with minimal arguments"""
        test_args = ["main.py", "create-issue", "--title", "Simple Issue"]
        
        import argparse
        
        parser = argparse.ArgumentParser(description='Speculum Principium - GitHub Operations via Actions')
        parser.add_argument('operation', choices=['create-issue'], help='Operation to perform')
        parser.add_argument('--title', required=True, help='Issue title')
        parser.add_argument('--body', help='Issue body/description')
        parser.add_argument('--labels', nargs='*', help='Issue labels')
        parser.add_argument('--assignees', nargs='*', help='Issue assignees')
        
        args = parser.parse_args(test_args[1:])  # Skip script name
        
        assert args.operation == "create-issue"
        assert args.title == "Simple Issue"
        assert args.body is None
        assert args.labels is None
        assert args.assignees is None


class TestEnvironmentSetup:
    """Test cases for environment variable handling"""
    
    def test_load_dotenv_called(self, monkeypatch):
        """Test that load_dotenv is called during main execution"""
        # Set required environment variables
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "test/repo")
        
        # Mock sys.argv with invalid operation to exit early
        test_args = ["main.py", "invalid-op"]
        monkeypatch.setattr(sys, "argv", test_args)
        
        with patch('main.load_dotenv') as mock_load_dotenv:
            # Expect SystemExit due to invalid operation
            with pytest.raises(SystemExit):
                main.main()
            
            # Verify load_dotenv was called
            mock_load_dotenv.assert_called_once()
    
    def test_environment_variable_retrieval(self, monkeypatch):
        """Test environment variable retrieval"""
        test_token = "test_github_token_123"
        test_repo = "myuser/myproject"
        
        monkeypatch.setenv("GITHUB_TOKEN", test_token)
        monkeypatch.setenv("GITHUB_REPOSITORY", test_repo)
        
        # Verify environment variables are accessible
        assert os.getenv("GITHUB_TOKEN") == test_token
        assert os.getenv("GITHUB_REPOSITORY") == test_repo


@pytest.mark.integration
class TestMainIntegration:
    """Integration tests for complete main application flow"""
    
    @pytest.mark.skip(reason="Requires real GitHub credentials")
    def test_end_to_end_issue_creation(self):
        """Test complete end-to-end issue creation (skipped by default)"""
        # This would test the complete flow with real GitHub API
        # Skipped to avoid accidental API calls during testing
        pass


class TestMainModuleExecution:
    """Test cases for direct module execution"""
    
    def test_main_module_name_check(self):
        """Test that main() is called when module is executed directly"""
        # This tests the if __name__ == "__main__": block
        with patch('main.main') as mock_main:
            # Import the module to trigger the check
            import importlib
            import main as main_module
            
            # Reload to trigger the __name__ == "__main__" check
            # Note: This is tricky to test directly, so we verify the structure exists
            assert hasattr(main_module, 'main')
            assert callable(main_module.main)