"""
Integration tests for site monitor and issue processor integration.

These tests verify that the site monitoring service properly integrates with
the issue processor for automated workflow execution.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

from src.site_monitor import SiteMonitorService
from src.config_manager import MonitorConfig
from src.search_client import SearchResult
from src.issue_processor import ProcessingResult, IssueProcessingStatus


class TestSiteMonitorIntegration:
    """Test integration between site monitor and issue processor."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration with agent enabled."""
        config = Mock()
        config.sites = [Mock(name="test-site")]
        config.github = Mock()
        config.github.repository = "test/repo"
        config.search = Mock()
        config.search.daily_query_limit = 100
        config.search.results_per_query = 10
        config.search.date_range_days = 7
        config.storage_path = "test_processed_urls.json"
        config.log_level = "INFO"
        
        # Agent configuration
        config.agent = Mock()
        config.agent.enabled = True
        config.agent.workflow_dir = "docs/workflow/deliverables"
        config.agent.output_dir = "study"
        config.agent.enable_git = True
        
        return config
    
    @pytest.fixture
    def mock_config_no_agent(self):
        """Create a mock configuration with agent disabled."""
        config = Mock()
        config.sites = [Mock(name="test-site")]
        config.github = Mock()
        config.github.repository = "test/repo"
        config.search = Mock()
        config.search.daily_query_limit = 100
        config.search.results_per_query = 10
        config.search.date_range_days = 7
        config.storage_path = "test_processed_urls.json"
        config.log_level = "INFO"
        
        # No agent configuration or agent disabled
        config.agent = Mock()
        config.agent.enabled = False
        
        return config
    
    @pytest.fixture
    def mock_search_result(self):
        """Create a mock search result."""
        return SearchResult(
            title="Test Article",
            link="https://example.com/test",
            snippet="Test article snippet"
        )
    
    @pytest.fixture
    def mock_github_issue(self):
        """Create a mock GitHub issue."""
        issue = Mock()
        issue.number = 123
        issue.title = "Test Issue"
        issue.labels = [Mock(name="site-monitor")]
        issue.assignee = None
        return issue
    
    @patch('src.site_monitor.IssueProcessor')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.GoogleCustomSearchClient')
    def test_monitoring_cycle_with_issue_processing(
        self, 
        mock_search_client,
        mock_dedup_manager,
        mock_github_client,
        mock_issue_processor_class,
        mock_config,
        mock_search_result,
        mock_github_issue
    ):
        """Test complete monitoring cycle with issue processing enabled."""
        # Setup mocks
        mock_search_client.return_value.search_all_sites.return_value = {
            "test-site": [mock_search_result]
        }
        mock_search_client.return_value.get_rate_limit_status.return_value = {
            'calls_remaining': 90,
            'daily_limit': 100
        }
        
        mock_dedup_manager.return_value.filter_new_results.return_value = [mock_search_result]
        mock_dedup_manager.return_value.get_processed_stats.return_value = {
            'total_entries': 5
        }
        
        mock_github_client.return_value.create_individual_result_issue.return_value = mock_github_issue
        
        # Setup issue processor mock
        mock_issue_processor = Mock()
        processing_result = ProcessingResult(
            issue_number=123,
            status=IssueProcessingStatus.COMPLETED,
            workflow_name="test-workflow",
            created_files=["study/123/analysis.md"],
            error_message=None
        )
        mock_issue_processor.process_issue.return_value = processing_result
        mock_issue_processor_class.return_value = mock_issue_processor
        
        # Create service and run monitoring cycle
        service = SiteMonitorService(mock_config, "fake-token")
        result = service.run_monitoring_cycle(create_individual_issues=True)
        
        # Verify monitoring cycle completed successfully
        assert result['success'] is True
        assert result['individual_issues_created'] == 1
        assert len(result['issue_processing_results']) == 1
        
        # Verify issue processing was called
        mock_issue_processor.process_issue.assert_called_once_with(123)
        
        # Verify processing result structure
        processing_result_dict = result['issue_processing_results'][0]
        assert processing_result_dict['issue_number'] == 123
        assert processing_result_dict['status'] == 'completed'
        assert processing_result_dict['workflow'] == 'test-workflow'
        assert len(processing_result_dict['deliverables']) == 1
        assert processing_result_dict['error'] is None
    
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.GoogleCustomSearchClient')
    def test_monitoring_cycle_without_issue_processor(
        self,
        mock_search_client,
        mock_dedup_manager,
        mock_github_client,
        mock_config_no_agent,
        mock_search_result,
        mock_github_issue
    ):
        """Test monitoring cycle works without issue processor enabled."""
        # Setup mocks
        mock_search_client.return_value.search_all_sites.return_value = {
            "test-site": [mock_search_result]
        }
        mock_search_client.return_value.get_rate_limit_status.return_value = {
            'calls_remaining': 90,
            'daily_limit': 100
        }
        
        mock_dedup_manager.return_value.filter_new_results.return_value = [mock_search_result]
        mock_dedup_manager.return_value.get_processed_stats.return_value = {
            'total_entries': 5
        }
        
        mock_github_client.return_value.create_individual_result_issue.return_value = mock_github_issue
        
        # Create service and run monitoring cycle
        service = SiteMonitorService(mock_config_no_agent, "fake-token")
        
        # Verify issue processor is not initialized
        assert service.issue_processor is None
        
        result = service.run_monitoring_cycle(create_individual_issues=True)
        
        # Verify monitoring cycle completed successfully
        assert result['success'] is True
        assert result['individual_issues_created'] == 1
        
        # Verify no issue processing results (empty list)
        assert result['issue_processing_results'] == []
    
    @patch('src.site_monitor.IssueProcessor')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.GoogleCustomSearchClient')
    def test_issue_processing_error_handling(
        self,
        mock_search_client,
        mock_dedup_manager,
        mock_github_client,
        mock_issue_processor_class,
        mock_config,
        mock_search_result,
        mock_github_issue
    ):
        """Test error handling during issue processing."""
        # Setup mocks
        mock_search_client.return_value.search_all_sites.return_value = {
            "test-site": [mock_search_result]
        }
        mock_search_client.return_value.get_rate_limit_status.return_value = {
            'calls_remaining': 90,
            'daily_limit': 100
        }
        
        mock_dedup_manager.return_value.filter_new_results.return_value = [mock_search_result]
        mock_dedup_manager.return_value.get_processed_stats.return_value = {
            'total_entries': 5
        }
        
        mock_github_client.return_value.create_individual_result_issue.return_value = mock_github_issue
        
        # Setup issue processor to raise exception
        mock_issue_processor = Mock()
        mock_issue_processor.process_issue.side_effect = Exception("Processing failed")
        mock_issue_processor_class.return_value = mock_issue_processor
        
        # Create service and run monitoring cycle
        service = SiteMonitorService(mock_config, "fake-token")
        result = service.run_monitoring_cycle(create_individual_issues=True)
        
        # Verify monitoring cycle completed successfully despite processing error
        assert result['success'] is True
        assert result['individual_issues_created'] == 1
        assert len(result['issue_processing_results']) == 1
        
        # Verify error was captured in processing result
        processing_result_dict = result['issue_processing_results'][0]
        assert processing_result_dict['issue_number'] == 123
        assert processing_result_dict['status'] == 'error'
        assert 'Processing failed' in processing_result_dict['error']
    
    @patch('src.site_monitor.IssueProcessor')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.GoogleCustomSearchClient')
    def test_process_existing_issues(
        self,
        mock_search_client,
        mock_dedup_manager,
        mock_github_client,
        mock_issue_processor_class,
        mock_config,
        mock_github_issue
    ):
        """Test processing of existing issues."""
        # Setup GitHub client mock to return existing issues
        mock_github_client.return_value.get_unprocessed_monitoring_issues.return_value = [
            mock_github_issue
        ]
        
        # Setup issue processor mock
        mock_issue_processor = Mock()
        processing_result = ProcessingResult(
            issue_number=123,
            status=IssueProcessingStatus.COMPLETED,
            workflow_name="existing-workflow",
            created_files=["study/123/existing.md"],
            error_message=None
        )
        mock_issue_processor.process_issue.return_value = processing_result
        mock_issue_processor_class.return_value = mock_issue_processor
        
        # Create service and process existing issues
        service = SiteMonitorService(mock_config, "fake-token")
        result = service.process_existing_issues(limit=10, force_reprocess=False)
        
        # Verify processing completed successfully
        assert result['success'] is True
        assert result['total_found'] == 1
        assert result['successful_processes'] == 1
        assert len(result['processed_issues']) == 1
        
        # Verify GitHub client was called correctly
        mock_github_client.return_value.get_unprocessed_monitoring_issues.assert_called_once_with(
            limit=10,
            force_reprocess=False
        )
        
        # Verify issue processor was called
        mock_issue_processor.process_issue.assert_called_once_with(123)
    
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.GoogleCustomSearchClient')
    def test_process_existing_issues_without_processor(
        self,
        mock_search_client,
        mock_dedup_manager,
        mock_github_client,
        mock_config_no_agent
    ):
        """Test processing existing issues when processor is not available."""
        # Create service without issue processor
        service = SiteMonitorService(mock_config_no_agent, "fake-token")
        result = service.process_existing_issues()
        
        # Verify appropriate error response
        assert result['success'] is False
        assert 'Issue processor not available' in result['error']
        assert result['processed_issues'] == []


class TestSiteMonitorGitHubIntegration:
    """Test GitHub-specific integration features."""
    
    @pytest.fixture
    def mock_repo(self):
        """Create a mock GitHub repository."""
        repo = Mock()
        
        # Mock issue with site-monitor label
        issue = Mock()
        issue.number = 456
        issue.assignee = None
        issue.get_comments.return_value = []
        
        repo.get_issues.return_value = [issue]
        repo.get_issue.return_value = issue
        
        return repo
    
    @patch('src.github_issue_creator.Github')
    def test_get_unprocessed_monitoring_issues(self, mock_github_class, mock_repo):
        """Test finding unprocessed monitoring issues."""
        from src.site_monitor_github import SiteMonitorIssueCreator
        
        # Setup GitHub mock - mock the class itself
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance
        
        # Create GitHub client
        github_client = SiteMonitorIssueCreator("fake-token", "test/repo")
        
        # Get unprocessed issues
        issues = github_client.get_unprocessed_monitoring_issues(limit=5)
        
        # Verify correct GitHub API calls
        mock_repo.get_issues.assert_called_once_with(
            state='open',
            labels=['site-monitor'],
            sort='created',
            direction='desc'
        )
        
        # Verify issues returned
        assert len(issues) == 1
        assert issues[0].number == 456
    
    @patch('src.github_issue_creator.Github')
    def test_assign_unassign_issue_to_agent(self, mock_github_class, mock_repo):
        """Test assigning and unassigning issues to/from agent."""
        from src.site_monitor_github import SiteMonitorIssueCreator
        
        # Setup GitHub mock - mock the class itself
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance
        
        # Create GitHub client
        github_client = SiteMonitorIssueCreator("fake-token", "test/repo")
        
        # Test assignment
        result = github_client.assign_issue_to_agent(456, "test-agent")
        assert result is True
        mock_repo.get_issue.return_value.add_to_assignees.assert_called_once_with("test-agent")
        
        # Test unassignment
        result = github_client.unassign_issue_from_agent(456, "test-agent")
        assert result is True
        mock_repo.get_issue.return_value.remove_from_assignees.assert_called_once_with("test-agent")
    
    @patch('src.github_issue_creator.Github')
    def test_issue_has_agent_activity_detection(self, mock_github_class, mock_repo):
        """Test detection of agent activity in issues."""
        from src.site_monitor_github import SiteMonitorIssueCreator
        
        # Setup GitHub mock - mock the class itself
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance
        
        # Create GitHub client
        github_client = SiteMonitorIssueCreator("fake-token", "test/repo")
        
        # Test issue without agent activity
        issue = Mock()
        comment = Mock()
        comment.body = "This is a regular comment"
        comment.user.login = "human-user"
        issue.get_comments.return_value = [comment]
        
        has_activity = github_client._issue_has_agent_activity(issue)
        assert has_activity is False
        
        # Test issue with bot comment
        bot_comment = Mock()
        bot_comment.body = "Automated workflow processing"
        bot_comment.user.login = "github-actions[bot]"
        issue.get_comments.return_value = [bot_comment]
        
        has_activity = github_client._issue_has_agent_activity(issue)
        assert has_activity is True
        
        # Test issue with agent indicator in comment
        agent_comment = Mock()
        agent_comment.body = "🤖 Processing this issue with automated workflow"
        agent_comment.user.login = "human-user"
        issue.get_comments.return_value = [agent_comment]
        
        has_activity = github_client._issue_has_agent_activity(issue)
        assert has_activity is True