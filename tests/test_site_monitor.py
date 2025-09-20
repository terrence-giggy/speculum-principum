"""
Unit tests for the site monitor service
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.site_monitor import SiteMonitorService, create_monitor_service_from_config
from src.config_manager import MonitorConfig, SiteConfig, GitHubConfig, SearchConfig
from src.search_client import SearchResult


class TestSiteMonitorService:
    """Test the SiteMonitorService class"""
    
    @patch('src.site_monitor.GoogleCustomSearchClient')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    def test_service_initialization(self, mock_github_creator, mock_dedup_manager, 
                                  mock_search_client, sample_config):
        """Test initializing the SiteMonitorService"""
        mock_github_instance = Mock()
        mock_dedup_instance = Mock()
        mock_search_instance = Mock()
        
        mock_github_creator.return_value = mock_github_instance
        mock_dedup_manager.return_value = mock_dedup_instance
        mock_search_client.return_value = mock_search_instance
        
        service = SiteMonitorService(sample_config, "test-token")
        
        assert service.config == sample_config
        assert service.github_token == "test-token"
        assert service.search_client == mock_search_instance
        assert service.dedup_manager == mock_dedup_instance
        assert service.github_client == mock_github_instance
        
        # Verify components were initialized correctly
        mock_search_client.assert_called_once_with(sample_config.search)
        mock_dedup_manager.assert_called_once_with(
            storage_path="test_processed.json",
            retention_days=30
        )
        mock_github_creator.assert_called_once_with(
            token="test-token",
            repository="owner/repo"
        )
    
    @patch('src.site_monitor.GoogleCustomSearchClient')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    def test_run_monitoring_cycle_success(self, mock_github_creator, mock_dedup_manager, 
                                        mock_search_client, sample_config):
        """Test successful monitoring cycle"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_dedup_instance = Mock()
        mock_search_instance = Mock()
        
        mock_github_creator.return_value = mock_github_instance
        mock_dedup_manager.return_value = mock_dedup_instance
        mock_search_client.return_value = mock_search_instance
        
        # Setup search results
        test_results = [
            SearchResult("Test Title 1", "https://example.com/page1", "Snippet 1"),
            SearchResult("Test Title 2", "https://example.com/page2", "Snippet 2")
        ]
        
        mock_search_instance.search_all_sites.return_value = {
            "Example Site": test_results
        }
        
        # Setup deduplication (all results are new)
        mock_dedup_instance.filter_new_results.side_effect = lambda results, site_name: results
        mock_dedup_instance.get_processed_stats.return_value = {
            'total_entries': 0,
            'entries_by_site': {},
            'entries_with_issues': 0
        }
        mock_dedup_instance.mark_result_processed.return_value = Mock()  # Mock ProcessedEntry
        mock_dedup_instance.save_processed_entries.return_value = None
        
        # Setup GitHub issue creation
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.title = "Site Update: Example Site - New Documentation Found"  # Set title as string, not Mock
        mock_github_instance.create_site_update_issue.return_value = mock_issue
        
        mock_summary_issue = Mock()
        mock_summary_issue.number = 124
        mock_github_instance.create_daily_summary_issue.return_value = mock_summary_issue
        
        # Setup rate limit status
        mock_search_instance.get_rate_limit_status.return_value = {
            'calls_made_today': 1,
            'daily_limit': 90,
            'calls_remaining': 89
        }
        
        # Run monitoring cycle
        service = SiteMonitorService(sample_config, "test-token")
        results = service.run_monitoring_cycle()
        
        # Verify results
        assert results['success'] is True
        assert results['sites_monitored'] == 1
        assert results['total_search_results'] == 2
        assert results['new_results_found'] == 2
        assert results['individual_issues_created'] == 1
        assert results['summary_issue_created'] is True
        assert results['summary_issue_number'] == 124
        assert 'cycle_duration_seconds' in results
        
        # Verify method calls
        mock_search_instance.search_all_sites.assert_called_once()
        mock_dedup_instance.filter_new_results.assert_called_once()
        mock_github_instance.create_site_update_issue.assert_called_once()
        mock_github_instance.create_daily_summary_issue.assert_called_once()
        mock_dedup_instance.save_processed_entries.assert_called_once()
    
    @patch('src.site_monitor.GoogleCustomSearchClient')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    def test_run_monitoring_cycle_no_new_results(self, mock_github_creator, mock_dedup_manager, 
                                                mock_search_client, sample_config):
        """Test monitoring cycle with no new results"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_dedup_instance = Mock()
        mock_search_instance = Mock()
        
        mock_github_creator.return_value = mock_github_instance
        mock_dedup_manager.return_value = mock_dedup_instance
        mock_search_client.return_value = mock_search_instance
        
        # Setup empty search results
        mock_search_instance.search_all_sites.return_value = {
            "Example Site": []
        }
        
        # Setup deduplication (no results to filter)
        mock_dedup_instance.filter_new_results.return_value = []
        mock_dedup_instance.get_processed_stats.return_value = {
            'total_entries': 10,
            'entries_by_site': {'Example Site': 10},
            'entries_with_issues': 8
        }
        
        # Setup summary issue creation
        mock_summary_issue = Mock()
        mock_summary_issue.number = 124
        mock_github_instance.create_daily_summary_issue.return_value = mock_summary_issue
        
        # Setup rate limit status
        mock_search_instance.get_rate_limit_status.return_value = {
            'calls_made_today': 1,
            'daily_limit': 90,
            'calls_remaining': 89
        }
        
        # Run monitoring cycle
        service = SiteMonitorService(sample_config, "test-token")
        results = service.run_monitoring_cycle()
        
        # Verify results
        assert results['success'] is True
        assert results['new_results_found'] == 0
        assert results['individual_issues_created'] == 0
        assert results['summary_issue_created'] is True
        
        # Verify no individual issues were created
        mock_github_instance.create_site_update_issue.assert_not_called()
        
        # But summary issue should still be created
        mock_github_instance.create_daily_summary_issue.assert_called_once()
    
    @patch('src.site_monitor.GoogleCustomSearchClient')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    def test_run_monitoring_cycle_skip_issues(self, mock_github_creator, mock_dedup_manager, 
                                            mock_search_client, sample_config):
        """Test monitoring cycle with issue creation disabled"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_dedup_instance = Mock()
        mock_search_instance = Mock()
        
        mock_github_creator.return_value = mock_github_instance
        mock_dedup_manager.return_value = mock_dedup_instance
        mock_search_client.return_value = mock_search_instance
        
        # Setup search results
        test_results = [
            SearchResult("Test Title", "https://example.com/page", "Snippet")
        ]
        
        mock_search_instance.search_all_sites.return_value = {
            "Example Site": test_results
        }
        mock_dedup_instance.filter_new_results.return_value = test_results
        mock_dedup_instance.get_processed_stats.return_value = {'total_entries': 0}
        mock_search_instance.get_rate_limit_status.return_value = {
            'calls_made_today': 1, 'daily_limit': 90, 'calls_remaining': 89
        }
        
        # Run monitoring cycle with both issue types disabled
        service = SiteMonitorService(sample_config, "test-token")
        results = service.run_monitoring_cycle(
            create_individual_issues=False,
            create_summary_issue=False
        )
        
        # Verify results
        assert results['success'] is True
        assert results['individual_issues_created'] == 0
        assert results['summary_issue_created'] is False
        assert results['summary_issue_number'] is None
        
        # Verify no issues were created
        mock_github_instance.create_site_update_issue.assert_not_called()
        mock_github_instance.create_daily_summary_issue.assert_not_called()
    
    @patch('src.site_monitor.GoogleCustomSearchClient')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    def test_run_monitoring_cycle_error_handling(self, mock_github_creator, mock_dedup_manager, 
                                                mock_search_client, sample_config):
        """Test monitoring cycle error handling"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_dedup_instance = Mock()
        mock_search_instance = Mock()
        
        mock_github_creator.return_value = mock_github_instance
        mock_dedup_manager.return_value = mock_dedup_instance
        mock_search_client.return_value = mock_search_instance
        
        # Setup search to raise an exception
        mock_search_instance.search_all_sites.side_effect = Exception("Search failed")
        
        # Run monitoring cycle
        service = SiteMonitorService(sample_config, "test-token")
        results = service.run_monitoring_cycle()
        
        # Verify error handling
        assert results['success'] is False
        assert 'Search failed' in results['error']
        assert 'cycle_start' in results
        assert 'cycle_end' in results
    
    @patch('src.site_monitor.GoogleCustomSearchClient')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    @patch('src.site_monitor.create_site_monitoring_labels')
    def test_setup_repository(self, mock_create_labels, mock_github_creator, 
                            mock_dedup_manager, mock_search_client, sample_config):
        """Test repository setup"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_dedup_instance = Mock()
        mock_search_instance = Mock()
        
        mock_github_creator.return_value = mock_github_instance
        mock_dedup_manager.return_value = mock_dedup_instance
        mock_search_client.return_value = mock_search_instance
        
        mock_create_labels.return_value = ['site-monitor', 'automated']
        
        # Run setup
        service = SiteMonitorService(sample_config, "test-token")
        service.setup_repository()
        
        # Verify setup was called
        mock_create_labels.assert_called_once_with(mock_github_instance)
    
    @patch('src.site_monitor.GoogleCustomSearchClient')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    def test_cleanup_old_data(self, mock_github_creator, mock_dedup_manager, 
                            mock_search_client, sample_config):
        """Test cleaning up old data"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_dedup_instance = Mock()
        mock_search_instance = Mock()
        
        mock_github_creator.return_value = mock_github_instance
        mock_dedup_manager.return_value = mock_dedup_instance
        mock_search_client.return_value = mock_search_instance
        
        # Setup cleanup behavior
        mock_dedup_instance.processed_entries = {'hash1': Mock(), 'hash2': Mock()}  # 2 entries initially
        mock_dedup_instance.cleanup_storage = Mock()
        
        # After cleanup, simulate 1 entry removed
        def cleanup_side_effect():
            mock_dedup_instance.processed_entries = {'hash1': Mock()}
        
        mock_dedup_instance.cleanup_storage.side_effect = cleanup_side_effect
        mock_github_instance.close_old_monitoring_issues.return_value = [123, 124]
        
        # Run cleanup
        service = SiteMonitorService(sample_config, "test-token")
        results = service.cleanup_old_data(days_old=7, dry_run=False)
        
        # Verify cleanup results
        assert results['success'] is True
        assert results['removed_dedup_entries'] == 1
        assert results['closed_issues'] == 2
        assert results['closed_issue_numbers'] == [123, 124]
        assert results['dry_run'] is False
        
        # Verify cleanup methods were called
        mock_dedup_instance.cleanup_storage.assert_called_once()
        mock_github_instance.close_old_monitoring_issues.assert_called_once_with(
            days_old=7, dry_run=False
        )
    
    @patch('src.site_monitor.GoogleCustomSearchClient')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    def test_get_monitoring_status(self, mock_github_creator, mock_dedup_manager, 
                                 mock_search_client, sample_config):
        """Test getting monitoring status"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_dedup_instance = Mock()
        mock_search_instance = Mock()
        
        mock_github_creator.return_value = mock_github_instance
        mock_dedup_manager.return_value = mock_dedup_instance
        mock_search_client.return_value = mock_search_instance
        
        # Setup status responses
        mock_search_instance.get_rate_limit_status.return_value = {
            'calls_made_today': 5,
            'daily_limit': 90,
            'calls_remaining': 85
        }
        
        mock_dedup_instance.get_processed_stats.return_value = {
            'total_entries': 50,
            'entries_by_site': {'Example Site': 50},
            'entries_with_issues': 40
        }
        
        # Get status
        service = SiteMonitorService(sample_config, "test-token")
        status = service.get_monitoring_status()
        
        # Verify status
        assert status['repository'] == "owner/repo"
        assert status['sites_configured'] == 1
        assert status['site_names'] == ["Example Site"]
        assert status['rate_limit_status']['calls_remaining'] == 85
        assert status['deduplication_stats']['total_entries'] == 50
        assert status['config']['daily_query_limit'] == 90


class TestServiceCreation:
    """Test service creation functions"""
    
    @patch('src.site_monitor.load_config_with_env_substitution')
    def test_create_monitor_service_from_config(self, mock_load_config):
        """Test creating service from config file"""
        # Setup mock config
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        
        with patch('src.site_monitor.SiteMonitorService') as mock_service_class:
            mock_service_instance = Mock()
            mock_service_class.return_value = mock_service_instance
            
            service = create_monitor_service_from_config("config.yaml", "test-token")
            
            # Verify config was loaded and service was created
            mock_load_config.assert_called_once_with("config.yaml")
            mock_service_class.assert_called_once_with(mock_config, "test-token")
            assert service == mock_service_instance


class TestFilterAndProcessing:
    """Test filtering and processing helper methods"""
    
    @patch('src.site_monitor.GoogleCustomSearchClient')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    def test_filter_new_results(self, mock_github_creator, mock_dedup_manager, 
                              mock_search_client, sample_config):
        """Test filtering new results"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_dedup_instance = Mock()
        mock_search_instance = Mock()
        
        mock_github_creator.return_value = mock_github_instance
        mock_dedup_manager.return_value = mock_dedup_instance
        mock_search_client.return_value = mock_search_instance
        
        # Setup test data
        all_results = {
            "Site A": [SearchResult("Title 1", "https://a.com/1", "Snippet 1")],
            "Site B": [SearchResult("Title 2", "https://b.com/2", "Snippet 2")],
            "Site C": []
        }
        
        # Setup deduplication behavior
        def filter_side_effect(results, site_name):
            if site_name == "Site A":
                return results  # All new
            elif site_name == "Site B":
                return []  # All filtered out
            else:
                return results  # Empty list stays empty
        
        mock_dedup_instance.filter_new_results.side_effect = filter_side_effect
        
        # Test filtering
        service = SiteMonitorService(sample_config, "test-token")
        new_results = service._filter_new_results(all_results)
        
        # Verify results
        assert len(new_results["Site A"]) == 1
        assert len(new_results["Site B"]) == 0
        assert len(new_results["Site C"]) == 0
        
        # Verify filter was called only for sites with results (Site A and Site B, not Site C which is empty)
        assert mock_dedup_instance.filter_new_results.call_count == 2
    
    @patch('src.site_monitor.GoogleCustomSearchClient')
    @patch('src.site_monitor.DeduplicationManager')
    @patch('src.site_monitor.SiteMonitorIssueCreator')
    def test_mark_results_processed(self, mock_github_creator, mock_dedup_manager, 
                                  mock_search_client, sample_config):
        """Test marking results as processed"""
        # Setup mocks
        mock_github_instance = Mock()
        mock_dedup_instance = Mock()
        mock_search_instance = Mock()
        
        mock_github_creator.return_value = mock_github_instance
        mock_dedup_manager.return_value = mock_dedup_instance
        mock_search_client.return_value = mock_search_instance
        
        # Setup test data
        new_results = {
            "Example Site": [
                SearchResult("Title 1", "https://example.com/1", "Snippet 1"),
                SearchResult("Title 2", "https://example.com/2", "Snippet 2")
            ]
        }
        
        # Setup mock issues
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.title = "📄 New updates found on Example Site"
        individual_issues = [mock_issue]
        
        # Setup deduplication behavior
        mock_entry1 = Mock()
        mock_entry2 = Mock()
        mock_dedup_instance.mark_result_processed.side_effect = [mock_entry1, mock_entry2]
        
        # Test marking as processed
        service = SiteMonitorService(sample_config, "test-token")
        processed_entries = service._mark_results_processed(new_results, individual_issues)
        
        # Verify results
        assert len(processed_entries) == 2
        assert processed_entries == [mock_entry1, mock_entry2]
        
        # Verify mark_result_processed was called correctly
        assert mock_dedup_instance.mark_result_processed.call_count == 2
        
        # Verify the issue number was passed correctly (extracted from title)
        calls = mock_dedup_instance.mark_result_processed.call_args_list
        assert calls[0][1]['issue_number'] == 123  # Should match the issue
        assert calls[1][1]['issue_number'] == 123  # Should match the issue