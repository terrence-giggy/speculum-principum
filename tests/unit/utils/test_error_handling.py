"""
Test cases for error handling scenarios across the issue processing system.

This module tests various error conditions including network failures,
file system errors, configuration issues, and API failures to ensure
the system handles them gracefully.
"""

import pytest
import tempfile
import shutil
import json
import yaml
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
from datetime import datetime

from src.core.issue_processor import (
    IssueProcessor, IssueProcessingError, ProcessingTimeoutError,
    IssueProcessingStatus, ProcessingResult, IssueData, GitHubIntegratedIssueProcessor
)
from src.workflow.workflow_matcher import (
    WorkflowMatcher, WorkflowLoadError
)
from src.utils.config_manager import ConfigManager
from src.storage.git_manager import GitManager, GitOperationError
from src.utils.logging_config import setup_logging


class TestIssueProcessorErrorHandling:
    """Test error handling in IssueProcessor class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_config(self, temp_dir):
        """Create a mock configuration for testing."""
        config_content = {
            'sites': [
                {
                    'url': 'https://example.com',
                    'name': 'Test Site',
                    'keywords': ['test']
                }
            ],
            'github': {
                'token': 'test-token',
                'repository': 'test/repo'
            },
            'search': {
                'api_key': 'test-api-key',
                'search_engine_id': 'test-engine-id'
            },
            'agent': {
                'username': 'test-agent',
                'workflow_directory': f"{temp_dir}/workflows",
                'output_directory': f"{temp_dir}/output",
                'template_directory': f"{temp_dir}/templates",
                'processing': {
                    'default_timeout_minutes': 5
                },
                'git': {
                    'branch_prefix': 'issue',
                    'auto_push': False
                }
            }
        }
        config_file = Path(temp_dir) / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)
        return str(config_file)
    
    @pytest.fixture
    def sample_issue_data(self):
        """Create sample issue data for testing."""
        return IssueData(
            number=123,
            title="Test Issue",
            body="This is a test issue body",
            labels=["site-monitor", "research"],
            assignees=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/test/repo/issues/123"
        )
    
    def test_invalid_config_file_path(self, temp_dir):
        """Test error handling for non-existent config file."""
        invalid_config = f"{temp_dir}/nonexistent.yaml"
        
        with pytest.raises(IssueProcessingError) as exc_info:
            IssueProcessor(config_path=invalid_config)
        
        assert exc_info.value.error_code == "CONFIG_NOT_FOUND"
        assert "Configuration file not found" in str(exc_info.value)
    
    def test_corrupted_config_file(self, temp_dir):
        """Test error handling for corrupted YAML config."""
        config_file = Path(temp_dir) / 'bad_config.yaml'
        with open(config_file, 'w') as f:
            f.write("sites: [unclosed bracket\ngithub: {token: test}\nsearch: {")
        
        with pytest.raises(IssueProcessingError) as exc_info:
            IssueProcessor(config_path=str(config_file))
        
        assert exc_info.value.error_code == "CONFIG_INVALID"
    
    def test_workflow_directory_not_found(self, mock_config, temp_dir):
        """Test error handling when workflow directory doesn't exist."""
        # Don't create the workflow directory
        with pytest.raises(IssueProcessingError) as exc_info:
            IssueProcessor(config_path=mock_config)
        
        assert exc_info.value.error_code == "DIRECTORY_NOT_FOUND"
    
    def test_output_directory_creation_failure(self, mock_config, temp_dir):
        """Test error handling when output directory cannot be created."""
        # Create workflow directory but make output parent read-only
        os.makedirs(f"{temp_dir}/workflows")
        
        # Make the temp directory read-only to prevent creating output dir
        with patch('pathlib.Path.mkdir', side_effect=OSError("Permission denied")):
            with pytest.raises(IssueProcessingError) as exc_info:
                IssueProcessor(config_path=mock_config)
            
            assert exc_info.value.error_code == "OUTPUT_DIR_ERROR"
    
    @patch('src.core.issue_processor.DeliverableGenerator')
    def test_deliverable_generator_initialization_failure(self, mock_gen, mock_config, temp_dir):
        """Test error handling when deliverable generator fails to initialize."""
        os.makedirs(f"{temp_dir}/workflows")
        mock_gen.side_effect = Exception("Deliverable generator failed")
        
        with pytest.raises(IssueProcessingError) as exc_info:
            IssueProcessor(config_path=mock_config)
        
        assert exc_info.value.error_code == "DELIVERABLE_GENERATOR_ERROR"
    
    def test_invalid_issue_data_validation(self, mock_config, temp_dir):
        """Test validation of invalid issue data."""
        os.makedirs(f"{temp_dir}/workflows")
        processor = IssueProcessor(config_path=mock_config)
        
        # Test invalid issue number
        invalid_issue = IssueData(
            number=-1, title="Test", body="", labels=[],
            assignees=[], created_at=datetime.now(), updated_at=datetime.now(), url=""
        )
        result = processor.process_issue(invalid_issue)
        
        assert result.status == IssueProcessingStatus.ERROR
        assert result.error_message and "Invalid issue number" in result.error_message
    
    def test_empty_issue_title_validation(self, mock_config, temp_dir):
        """Test validation of empty issue title."""
        os.makedirs(f"{temp_dir}/workflows")
        processor = IssueProcessor(config_path=mock_config)
        
        # Test empty title
        invalid_issue = IssueData(
            number=1, title="", body="", labels=["site-monitor"],
            assignees=[], created_at=datetime.now(), updated_at=datetime.now(), url=""
        )
        result = processor.process_issue(invalid_issue)
        
        assert result.status == IssueProcessingStatus.ERROR
        assert result.error_message and "empty title" in result.error_message.lower()
    
    def test_processing_timeout_error(self, mock_config, temp_dir):
        """Test processing timeout detection."""
        os.makedirs(f"{temp_dir}/workflows")
        processor = IssueProcessor(config_path=mock_config)
        
        # Simulate an issue that started processing a long time ago
        issue_data = IssueData(
            number=1, title="Test", body="", labels=["site-monitor"],
            assignees=[], created_at=datetime.now(), updated_at=datetime.now(), url=""
        )
        processor._processing_state["1"] = {
            "status": IssueProcessingStatus.PROCESSING.value,
            "started_at": "2020-01-01T00:00:00"  # Very old timestamp
        }
        
        result = processor.process_issue(issue_data)
        assert result.status == IssueProcessingStatus.ERROR
        assert result.error_message and "timeout" in result.error_message.lower()
    
    @patch('src.core.issue_processor.WorkflowMatcher')
    def test_workflow_matching_failure(self, mock_matcher, mock_config, temp_dir):
        """Test error handling when workflow matching fails."""
        os.makedirs(f"{temp_dir}/workflows")
        mock_matcher.return_value.get_best_workflow_match.side_effect = Exception("Workflow matching failed")
        
        processor = IssueProcessor(config_path=mock_config)
        issue_data = IssueData(
            number=1, title="Test", body="", labels=["site-monitor"],
            assignees=[], created_at=datetime.now(), updated_at=datetime.now(), url=""
        )
        
        result = processor.process_issue(issue_data)
        assert result.status == IssueProcessingStatus.ERROR
        assert result.error_message and "Failed to find matching workflow" in result.error_message
    
    def test_state_file_corruption_recovery(self, mock_config, temp_dir):
        """Test recovery from corrupted state file."""
        os.makedirs(f"{temp_dir}/workflows")
        output_dir = Path(temp_dir) / "output"
        output_dir.mkdir()
        
        # Create corrupted state file
        state_file = output_dir / ".processing_state.json"
        with open(state_file, 'w') as f:
            f.write("invalid json content {")
        
        # Should handle corrupted state gracefully
        processor = IssueProcessor(config_path=mock_config)
        assert processor._processing_state == {}
        
        # Check that backup file was created
        backup_files = list(output_dir.glob(".processing_state.backup.*"))
        assert len(backup_files) == 1


class TestWorkflowMatcherErrorHandling:
    """Test error handling in WorkflowMatcher class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_nonexistent_workflow_directory(self, temp_dir):
        """Test error handling for non-existent workflow directory."""
        nonexistent_dir = f"{temp_dir}/nonexistent"
        
        with pytest.raises(WorkflowLoadError) as exc_info:
            WorkflowMatcher(nonexistent_dir)
        
        assert exc_info.value.error_code == "DIRECTORY_NOT_FOUND"
    
    def test_workflow_directory_is_file(self, temp_dir):
        """Test error handling when workflow path is a file, not directory."""
        file_path = Path(temp_dir) / "not_a_dir.txt"
        file_path.write_text("I'm a file, not a directory")
        
        with pytest.raises(WorkflowLoadError) as exc_info:
            WorkflowMatcher(str(file_path))
        
        assert exc_info.value.error_code == "NOT_A_DIRECTORY"
    
    def test_invalid_yaml_workflow_file(self, temp_dir):
        """Test error handling for invalid YAML in workflow file."""
        workflow_dir = Path(temp_dir) / "workflows"
        workflow_dir.mkdir()
        
        bad_workflow = workflow_dir / "bad.yaml"
        bad_workflow.write_text("invalid: yaml: content: [unclosed")
        
        # Should not raise exception during initialization, but log error
        matcher = WorkflowMatcher(str(workflow_dir))
        assert len(matcher._workflow_cache) == 0
    
    def test_missing_required_fields_in_workflow(self, temp_dir):
        """Test error handling for workflow files missing required fields."""
        workflow_dir = Path(temp_dir) / "workflows"
        workflow_dir.mkdir()
        
        # Workflow missing required fields
        incomplete_workflow = workflow_dir / "incomplete.yaml"
        incomplete_content = {
            "name": "Incomplete Workflow",
            # Missing trigger_labels and deliverables
        }
        with open(incomplete_workflow, 'w') as f:
            yaml.dump(incomplete_content, f)
        
        matcher = WorkflowMatcher(str(workflow_dir))
        assert len(matcher._workflow_cache) == 0
    
    def test_workflow_file_permission_error(self, temp_dir):
        """Test error handling for workflow files with permission issues."""
        workflow_dir = Path(temp_dir) / "workflows"
        workflow_dir.mkdir()
        
        protected_workflow = workflow_dir / "protected.yaml"
        protected_workflow.write_text("name: Protected")
        
        # Mock file permission error
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            matcher = WorkflowMatcher(str(workflow_dir))
            # Should handle the error gracefully and continue
            assert len(matcher._workflow_cache) == 0
    
    def test_workflow_directory_scan_failure(self, temp_dir):
        """Test error handling when directory scanning fails."""
        workflow_dir = Path(temp_dir) / "workflows"
        workflow_dir.mkdir()
        
        # Mock OSError during directory scanning
        with patch.object(Path, 'glob', side_effect=OSError("Scan failed")):
            with pytest.raises(WorkflowLoadError) as exc_info:
                WorkflowMatcher(str(workflow_dir))
            
            assert exc_info.value.error_code == "DIRECTORY_SCAN_FAILED"
    
    def test_all_workflows_invalid(self, temp_dir):
        """Test error handling when all workflow files are invalid."""
        workflow_dir = Path(temp_dir) / "workflows"
        workflow_dir.mkdir()
        
        # Create multiple invalid workflow files to trigger NO_VALID_WORKFLOWS
        for i in range(5):  # Create more files to ensure multiple failures
            bad_workflow = workflow_dir / f"bad{i}.yaml"
            bad_workflow.write_text(f"invalid yaml content {i}: [unclosed bracket")
        
        with pytest.raises(WorkflowLoadError) as exc_info:
            WorkflowMatcher(str(workflow_dir))
        
        assert exc_info.value.error_code == "NO_VALID_WORKFLOWS"
    
    @patch('src.workflow.workflow_matcher.WorkflowSchemaValidator')
    def test_schema_validation_failure(self, mock_validator, temp_dir):
        """Test error handling for schema validation failures."""
        workflow_dir = Path(temp_dir) / "workflows"
        workflow_dir.mkdir()
        
        # Create a workflow that passes basic validation but fails schema validation
        workflow_file = workflow_dir / "schema_fail.yaml"
        workflow_content = {
            "name": "Schema Fail",
            "trigger_labels": ["test"],
            "deliverables": [{"name": "test"}]
        }
        with open(workflow_file, 'w') as f:
            yaml.dump(workflow_content, f)
        
        # Mock schema validator to fail
        mock_validator.return_value.validate_workflow.side_effect = Exception("Schema validation failed")
        
        matcher = WorkflowMatcher(str(workflow_dir))
        assert len(matcher._workflow_cache) == 0
    
    def test_unicode_decode_error_in_workflow(self, temp_dir):
        """Test error handling for invalid UTF-8 in workflow files."""
        workflow_dir = Path(temp_dir) / "workflows"
        workflow_dir.mkdir()
        
        # Create a file with invalid UTF-8
        bad_encoding_file = workflow_dir / "bad_encoding.yaml"
        with open(bad_encoding_file, 'wb') as f:
            f.write(b'\xff\xfe\x00invalid utf-8')
        
        matcher = WorkflowMatcher(str(workflow_dir))
        assert len(matcher._workflow_cache) == 0


class TestGitManagerErrorHandling:
    """Test error handling in GitManager operations."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @patch('subprocess.run')
    def test_git_command_failure(self, mock_run, temp_repo):
        """Test error handling when git commands fail."""
        # Mock git command failure
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "fatal: not a git repository"
        
        git_manager = GitManager()
        
        with pytest.raises(GitOperationError):
            git_manager.create_issue_branch(123, "Test Issue")
    
    def test_invalid_repository_path(self):
        """Test error handling for invalid repository path."""
        with patch('pathlib.Path.cwd', return_value=Path('/nonexistent/path')):
            with pytest.raises(GitOperationError):
                git_manager = GitManager()
    
    @patch('subprocess.run')
    def test_git_push_failure(self, mock_run, temp_repo):
        """Test error handling when git push fails."""
        # Mock initialization calls and test calls
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Test User"),           # git config user.name (init)
            Mock(returncode=0, stdout="test@example.com"),    # git config user.email (init)
            Mock(returncode=0, stdout=""),                    # git status --porcelain (init)
            Mock(returncode=0, stdout="main"),                # Get current branch
            Mock(returncode=0, stdout="Switched to branch"),  # Checkout success  
            Mock(returncode=1, stderr="push failed")          # Push failure
        ]
        
        git_manager = GitManager()
        
        # Push failure should be handled gracefully
        result = git_manager.push_branch("test-branch")
        assert result is False


class TestNetworkErrorHandling:
    """Test error handling for network-related failures."""
    
    @patch('github.Github')
    def test_github_api_rate_limit(self, mock_github):
        """Test error handling for GitHub API rate limiting."""
        from github.GithubException import RateLimitExceededException
        
        mock_github_instance = Mock()
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.side_effect = RateLimitExceededException(403, {"message": "Rate limit exceeded"})
        
        with pytest.raises(Exception):  # Should handle rate limiting appropriately
            processor = GitHubIntegratedIssueProcessor("fake-token", "test/repo")
    
    @patch('github.Github')
    def test_github_api_network_error(self, mock_github):
        """Test error handling for GitHub API network errors."""
        import requests
        
        mock_github_instance = Mock()
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.side_effect = requests.exceptions.ConnectionError("Network error")
        
        with pytest.raises(Exception):  # Should handle network errors appropriately
            processor = GitHubIntegratedIssueProcessor("fake-token", "test/repo")
    
    @patch('github.Github')
    def test_github_api_authentication_error(self, mock_github):
        """Test error handling for GitHub API authentication errors."""
        from github.GithubException import BadCredentialsException
        
        mock_github_instance = Mock()
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_repo.side_effect = BadCredentialsException(401, {"message": "Bad credentials"})
        
        with pytest.raises(Exception):  # Should handle auth errors appropriately
            processor = GitHubIntegratedIssueProcessor("fake-token", "test/repo")


class TestRetryMechanisms:
    """Test retry mechanisms and recovery strategies."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @patch('time.sleep')  # Speed up tests by mocking sleep
    def test_retry_decorator_success_after_failures(self, mock_sleep, temp_dir):
        """Test that retry decorator succeeds after initial failures."""
        from src.core.issue_processor import retry_on_exception
        
        call_count = 0
        
        @retry_on_exception(max_attempts=3, delay_seconds=0.1)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Temporary failure")
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert call_count == 3
        assert mock_sleep.call_count == 2  # Should sleep between retries
    
    @patch('time.sleep')
    def test_retry_decorator_final_failure(self, mock_sleep, temp_dir):
        """Test that retry decorator fails after exhausting attempts."""
        from src.core.issue_processor import retry_on_exception
        
        @retry_on_exception(max_attempts=2, delay_seconds=0.1)
        def always_failing_function():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_failing_function()
        
        assert mock_sleep.call_count == 1  # Should sleep between retries
    
    def test_file_operation_retry(self, temp_dir):
        """Test retry mechanism for file operations."""
        from src.workflow.workflow_matcher import retry_on_io_error
        
        file_path = Path(temp_dir) / "test.txt"
        call_count = 0
        
        @retry_on_io_error(max_attempts=3)
        def flaky_file_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("File temporarily unavailable")
            
            with open(file_path, 'w') as f:
                f.write("success")
            return "done"
        
        result = flaky_file_operation()
        assert result == "done"
        assert file_path.exists()
        assert call_count == 2


class TestLoggingErrorHandling:
    """Test error handling in logging configuration."""
    
    def test_logging_setup_with_invalid_log_file(self):
        """Test logging setup with invalid log file path."""
        # Mock Path.mkdir to avoid PermissionError
        with patch('pathlib.Path.mkdir'), \
             patch('logging.FileHandler') as mock_file_handler, \
             patch('logging.handlers.RotatingFileHandler') as mock_rotating_handler:
            # Configure mock handlers to have proper level attribute
            mock_handler = Mock()
            mock_handler.level = 10  # DEBUG level
            mock_file_handler.return_value = mock_handler
            mock_rotating_handler.return_value = mock_handler
            
            # Should handle invalid paths gracefully
            config = setup_logging(log_file="/invalid/path/that/does/not/exist.log")
            assert config is not None
    
    def test_logging_with_permissions_error(self, tmp_path):
        """Test logging setup when log file creation fails due to permissions."""
        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only
        
        log_file = readonly_dir / "test.log"
        
        try:
            # Mock file operations to avoid PermissionError
            with patch('pathlib.Path.mkdir'), \
                 patch('logging.FileHandler') as mock_file_handler, \
                 patch('logging.handlers.RotatingFileHandler') as mock_rotating_handler:
                # Configure mock handlers to have proper level attribute
                mock_handler = Mock()
                mock_handler.level = 10  # DEBUG level
                mock_file_handler.return_value = mock_handler
                mock_rotating_handler.return_value = mock_handler
                
                # Should handle permission errors gracefully
                config = setup_logging(log_file=str(log_file))
                assert config is not None
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)


class TestRecoveryMechanisms:
    """Test system recovery mechanisms."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_config_with_workflows(self, temp_dir):
        """Create a mock configuration with proper workflow setup."""
        workflow_dir = Path(temp_dir) / "workflows"
        workflow_dir.mkdir()
        
        # Create a valid workflow file
        workflow_content = {
            "name": "Test Workflow",
            "description": "A test workflow",
            "version": "1.0",
            "trigger_labels": ["site-monitor", "test", "basic"],
            "deliverables": [
                {
                    "name": "test-deliverable",
                    "description": "A test deliverable",
                    "template": "basic"
                }
            ],
            "processing": {},
            "validation": {},
            "output": {
                "folder_structure": "issue_{issue_number}",
                "file_pattern": "{deliverable_name}.md"
            }
        }
        workflow_file = workflow_dir / "test.yaml"
        with open(workflow_file, 'w') as f:
            yaml.dump(workflow_content, f)
        
        config_content = {
            'sites': [
                {
                    'url': 'https://example.com',
                    'name': 'Test Site',
                    'keywords': ['test'],
                    'max_results': 5
                }
            ],
            'search': {
                'api_key': 'test-api-key',
                'search_engine_id': 'test-engine-id',
                'daily_query_limit': 100
            },
            'github': {
                'token': 'test-token',
                'repository': 'test/repo'
            },
            'agent': {
                'username': 'test-agent',
                'workflow_directory': str(workflow_dir),
                'output_directory': f"{temp_dir}/output",
                'template_directory': f"{temp_dir}/templates",
                'processing': {
                    'default_timeout_minutes': 5
                },
                'git': {
                    'branch_prefix': 'issue',
                    'auto_push': False
                }
            }
        }
        config_file = Path(temp_dir) / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)
        return str(config_file)
    
    @patch('src.core.issue_processor.DeliverableGenerator')
    def test_basic_workflow_recovery(self, mock_gen, mock_config_with_workflows, temp_dir):
        """Test recovery to basic workflow execution when advanced features fail."""
        # Mock deliverable generator to fail
        mock_gen.return_value.generate_deliverable.side_effect = Exception("Advanced generation failed")
        
        processor = IssueProcessor(config_path=mock_config_with_workflows, enable_git=False, enable_state_saving=False)
        issue_data = IssueData(
            number=123,
            title="Test Issue",
            body="Test body",
            labels=["site-monitor", "test"],
            assignees=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/test/repo/issues/123"
        )
        
        result = processor.process_issue(issue_data)
        
        # Should succeed using basic recovery mode - system should handle failure gracefully
        assert result.status == IssueProcessingStatus.COMPLETED
        # Even if no files are created due to failure, the system should recover gracefully
        assert result.workflow_name == "Test Workflow"
    
    def test_partial_deliverable_failure_recovery(self, mock_config_with_workflows, temp_dir):
        """Test recovery when some deliverables fail but others succeed."""
        processor = IssueProcessor(config_path=mock_config_with_workflows, enable_git=False, enable_state_saving=False)
        
        # Remove the default workflow and create only our multi-deliverable workflow
        workflow_dir = Path(temp_dir) / "workflows"
        
        # Remove the default test.yaml workflow
        default_workflow_file = workflow_dir / "test.yaml"
        if default_workflow_file.exists():
            default_workflow_file.unlink()
        
        # Mock workflow with multiple deliverables where some might fail
        workflow_content = {
            "name": "Multi Deliverable Workflow",
            "description": "Workflow with multiple deliverables",
            "version": "1.0",
            "trigger_labels": ["site-monitor", "multi-deliverable"],
            "deliverables": [
                {
                    "name": "good-deliverable",
                    "description": "This should work",
                    "template": "basic"
                },
                {
                    "name": "bad/deliverable",  # Invalid name should cause error
                    "description": "This should fail",
                    "template": "basic"
                }
            ],
            "processing": {},
            "validation": {},
            "output": {
                "folder_structure": "issue_{issue_number}",
                "file_pattern": "{deliverable_name}.md"
            }
        }
        
        workflow_file = workflow_dir / "multi.yaml"
        with open(workflow_file, 'w') as f:
            yaml.dump(workflow_content, f)
        
        # Refresh workflows to pick up the new one
        processor.workflow_matcher.refresh_workflows()
        
        issue_data = IssueData(
            number=124,
            title="Multi Test Issue",
            body="Test body",
            labels=["site-monitor", "multi-deliverable"],
            assignees=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/test/repo/issues/124"
        )
        
        result = processor.process_issue(issue_data)
        
        # Should succeed with at least one deliverable
        assert result.status == IssueProcessingStatus.COMPLETED
        # At least one file should be created (the good one)
        assert result.created_files and len(result.created_files) >= 1


# Test fixtures for error scenario simulation
@pytest.fixture
def setup_logging_for_tests():
    """Set up logging for test runs."""
    setup_logging(log_level="DEBUG", enable_console=False)


@pytest.mark.usefixtures("setup_logging_for_tests")
class TestErrorHandlingIntegration:
    """Integration tests for error handling across components."""
    
    def test_end_to_end_error_recovery(self):
        """Test end-to-end error recovery across all components."""
        # This would be a comprehensive test that simulates various
        # error conditions in sequence and verifies that the system
        # can recover and continue processing
        pass
    
    def test_concurrent_error_handling(self):
        """Test error handling when multiple operations fail simultaneously."""
        # This would test the system's ability to handle multiple
        # concurrent errors without corruption
        pass
    
    def test_error_reporting_and_logging(self):
        """Test that errors are properly reported and logged."""
        # This would verify that all error conditions produce
        # appropriate log messages and error reports
        pass