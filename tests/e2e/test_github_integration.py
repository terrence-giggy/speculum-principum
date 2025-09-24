"""
End-to-end integration tests for GitHub functionality.
These tests focus on real integration scenarios without excessive mocking.
"""

import pytest
from unittest.mock import Mock, patch
import tempfile
import os
from pathlib import Path

from src.issue_processor import GitHubIntegratedIssueProcessor, IssueProcessingStatus
from src.config_manager import MonitorConfig, ConfigManager


class TestGitHubE2EIntegration:
    """End-to-end GitHub integration tests."""
    
    @pytest.fixture
    def e2e_temp_dir(self):
        """Create temporary directory for e2e tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def e2e_config(self, e2e_temp_dir):
        """Create test configuration for e2e tests."""
        config_content = """
sites:
  - name: "Example Site"
    url: "https://example.com"
    max_results: 2

github:
  repository: "testorg/testrepo"

search:
  api_key: "test-api-key"
  search_engine_id: "test-search-engine"
  daily_query_limit: 90
  results_per_query: 10
  date_range_days: 30
  
agent:
  username: "testuser"
  workflow_directory: "workflows"
  output_directory: "output"

storage_path: "test_processed.json"
log_level: "INFO"
"""
        config_path = e2e_temp_dir / "config.yaml"
        config_path.write_text(config_content)
        return config_path
    
    @pytest.mark.e2e
    @patch('src.issue_processor.GitHubIssueCreator')
    def test_issue_processor_initialization(
        self,
        mock_github_creator,
        e2e_config,
        e2e_temp_dir
    ):
        """Test that issue processor can be initialized properly."""
        # Setup workflow directory
        workflow_dir = e2e_temp_dir / "workflows"
        workflow_dir.mkdir()
        
        output_dir = e2e_temp_dir / "output"
        output_dir.mkdir()
        
        # Mock GitHub creator
        mock_creator_instance = Mock()
        mock_github_creator.return_value = mock_creator_instance
        
        # Create processor
        processor = GitHubIntegratedIssueProcessor(
            github_token="test-token",
            repository="testorg/testrepo",
            config_path=str(e2e_config),
            workflow_dir=str(workflow_dir),
            output_base_dir=str(output_dir)
        )
        
        # Verify initialization
        assert processor.repository == "testorg/testrepo"
        mock_github_creator.assert_called_once_with("test-token", "testorg/testrepo")
    
    @pytest.mark.e2e
    def test_config_loading_integration(self, e2e_config, e2e_temp_dir):
        """Test that configuration loading works end-to-end."""
        config = ConfigManager.load_config(str(e2e_config))
        
        assert config.github.repository == "testorg/testrepo"
        assert config.storage_path == "test_processed.json"
        assert config.sites[0].name == "Example Site"
        assert config.search.api_key == "test-api-key"