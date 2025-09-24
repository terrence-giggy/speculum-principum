"""
Tests for the batch processing functionality.

This module contains comprehensive tests for the BatchProcessor class,
including batch configuration, progress reporting, error handling,
and integration with the issue processing pipeline.

The tests cover:
- Batch configuration and validation
- Progress reporting and metrics
- Error handling and retry logic
- Integration with GitHubIssueCreator and IssueProcessor
- Dry run functionality
- Filtering and sorting capabilities
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.core.batch_processor import (
    BatchProcessor, BatchConfig, BatchMetrics, BatchProgressReporter,
    BatchProgressReporter
)
from src.core.issue_processor import (
    IssueProcessor, IssueProcessingStatus, ProcessingResult, IssueData
)
from src.clients.github_issue_creator import GitHubIssueCreator


class TestBatchConfig:
    """Test BatchConfig dataclass functionality."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = BatchConfig()
        
        assert config.max_batch_size == 10
        assert config.max_concurrent_workers == 3
        assert config.retry_count == 2
        assert config.retry_delay_seconds == 1.0
        assert config.rate_limit_delay == 0.5
        assert config.timeout_seconds == 300
        assert config.stop_on_first_error is False
        assert config.include_assigned is False
        assert config.priority_labels == ['urgent', 'high-priority']
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = BatchConfig(
            max_batch_size=5,
            max_concurrent_workers=2,
            retry_count=3,
            priority_labels=['critical', 'urgent']
        )
        
        assert config.max_batch_size == 5
        assert config.max_concurrent_workers == 2
        assert config.retry_count == 3
        assert config.priority_labels == ['critical', 'urgent']


class TestBatchMetrics:
    """Test BatchMetrics dataclass functionality."""
    
    def test_default_metrics(self):
        """Test default metrics initialization."""
        metrics = BatchMetrics()
        
        assert metrics.total_issues == 0
        assert metrics.processed_count == 0
        assert metrics.success_count == 0
        assert metrics.error_count == 0
        assert metrics.skipped_count == 0
        assert metrics.clarification_count == 0
        assert metrics.start_time is None
        assert metrics.end_time is None
        assert metrics.processing_times == []
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        start_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 10, 0, 30, tzinfo=timezone.utc)
        
        metrics = BatchMetrics(start_time=start_time, end_time=end_time)
        
        assert metrics.duration_seconds == 30.0
    
    def test_average_processing_time(self):
        """Test average processing time calculation."""
        metrics = BatchMetrics()
        metrics.processing_times = [1.0, 2.0, 3.0]
        
        assert metrics.average_processing_time == 2.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = BatchMetrics()
        metrics.processed_count = 10
        metrics.success_count = 8
        
        assert metrics.success_rate == 80.0
    
    def test_success_rate_zero_processed(self):
        """Test success rate when no issues processed."""
        metrics = BatchMetrics()
        
        assert metrics.success_rate == 0.0


class TestBatchProgressReporter:
    """Test BatchProgressReporter functionality."""
    
    def test_reporter_initialization(self):
        """Test reporter initialization."""
        reporter = BatchProgressReporter(verbose=True)
        
        assert reporter.verbose is True
        assert reporter.progress_callback is None
    
    def test_reporter_with_callback(self):
        """Test reporter with progress callback."""
        callback = Mock()
        reporter = BatchProgressReporter(progress_callback=callback)
        
        reporter.report_start(10, 5)
        
        callback.assert_called_once_with({
            'type': 'start',
            'total_issues': 10,
            'batch_size': 5
        })
    
    def test_report_methods(self):
        """Test all reporting methods."""
        callback = Mock()
        reporter = BatchProgressReporter(progress_callback=callback)
        
        # Test different report types
        reporter.report_start(10, 5)
        reporter.report_batch_start(1, 5)
        reporter.report_issue_complete(123, 'completed', 2.5)
        
        metrics = BatchMetrics(success_count=5, error_count=0)
        reporter.report_batch_complete(1, metrics)
        reporter.report_final_summary(metrics)
        
        assert callback.call_count == 5


class TestBatchProcessor:
    """Test BatchProcessor functionality."""
    
    @pytest.fixture
    def mock_issue_processor(self):
        """Create mock issue processor."""
        processor = Mock(spec=IssueProcessor)
        return processor
    
    @pytest.fixture
    def mock_github_client(self):
        """Create mock GitHub client."""
        client = Mock(spec=GitHubIssueCreator)
        return client
    
    @pytest.fixture
    def batch_config(self):
        """Create test batch configuration."""
        return BatchConfig(
            max_batch_size=2,
            max_concurrent_workers=1,
            retry_count=1,
            timeout_seconds=10
        )
    
    @pytest.fixture
    def batch_processor(self, mock_issue_processor, mock_github_client, batch_config):
        """Create BatchProcessor instance for testing."""
        return BatchProcessor(
            issue_processor=mock_issue_processor,
            github_client=mock_github_client,
            config=batch_config
        )
    
    def test_initialization(self, batch_processor, mock_issue_processor, mock_github_client):
        """Test BatchProcessor initialization."""
        assert batch_processor.issue_processor == mock_issue_processor
        assert batch_processor.github_client == mock_github_client
        assert batch_processor._cancelled is False
    
    def test_create_batches(self, batch_processor):
        """Test batch creation."""
        issue_numbers = [1, 2, 3, 4, 5]
        batches = batch_processor._create_batches(issue_numbers)
        
        # With batch size 2, should create 3 batches
        assert len(batches) == 3
        assert batches[0] == [1, 2]
        assert batches[1] == [3, 4]
        assert batches[2] == [5]
    
    def test_find_site_monitor_issues(self, batch_processor, mock_github_client):
        """Test finding site-monitor issues."""
        # Mock GitHub API response
        mock_label1 = Mock()
        mock_label1.name = 'site-monitor'
        mock_label2 = Mock()
        mock_label2.name = 'urgent'
        
        mock_issue1 = Mock()
        mock_issue1.number = 123
        mock_issue1.assignee = None
        mock_issue1.labels = [mock_label1, mock_label2]
        
        mock_label3 = Mock()
        mock_label3.name = 'site-monitor'
        
        mock_issue2 = Mock()
        mock_issue2.number = 124
        mock_issue2.assignee = Mock(login='user1')
        mock_issue2.labels = [mock_label3]
        
        mock_github_client.get_issues_with_labels.return_value = [mock_issue1, mock_issue2]
        
        # Test with default filters (should exclude assigned issues)
        issue_numbers = batch_processor._find_site_monitor_issues({})
        
        assert issue_numbers == [123]  # Only unassigned issue
        mock_github_client.get_issues_with_labels.assert_called_once_with(['site-monitor'], state='open')
    
    def test_find_site_monitor_issues_with_assignee_filter(self, batch_processor, mock_github_client):
        """Test finding issues with assignee filter."""
        mock_label = Mock()
        mock_label.name = 'site-monitor'
        
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.assignee = Mock(login='user1')
        mock_issue.labels = [mock_label]
        
        mock_github_client.get_issues_with_labels.return_value = [mock_issue]
        
        # Test with specific assignee filter
        filters = {'assignee': 'user1'}
        issue_numbers = batch_processor._find_site_monitor_issues(filters)
        
        assert issue_numbers == [123]
    
    def test_find_site_monitor_issues_with_label_filter(self, batch_processor, mock_github_client):
        """Test finding issues with additional label filter."""
        # Create mock labels properly
        mock_site_label1 = Mock()
        mock_site_label1.name = 'site-monitor'
        mock_urgent_label = Mock()
        mock_urgent_label.name = 'urgent'
        
        mock_issue1 = Mock()
        mock_issue1.number = 123
        mock_issue1.assignee = None
        mock_issue1.labels = [mock_site_label1, mock_urgent_label]
        
        mock_site_label2 = Mock()
        mock_site_label2.name = 'site-monitor'
        
        mock_issue2 = Mock()
        mock_issue2.number = 124
        mock_issue2.assignee = None
        mock_issue2.labels = [mock_site_label2]
        
        mock_github_client.get_issues_with_labels.return_value = [mock_issue1, mock_issue2]
        
        # Test with additional label filter
        filters = {'additional_labels': ['urgent']}
        issue_numbers = batch_processor._find_site_monitor_issues(filters)
        
        assert issue_numbers == [123]  # Only issue with urgent label
    
    def test_process_single_issue_success(self, batch_processor, mock_issue_processor, mock_github_client):
        """Test successful single issue processing."""
        # Mock issue data
        issue_data_dict = {
            'title': 'Test Issue',
            'body': 'Test body',
            'labels': ['site-monitor'],
            'assignees': [],
            'url': 'https://github.com/repo/issues/123'
        }
        mock_github_client.get_issue_data.return_value = issue_data_dict
        
        # Mock processing result
        expected_result = ProcessingResult(
            issue_number=123,
            status=IssueProcessingStatus.COMPLETED,
            workflow_name='test-workflow',
            created_files=['file1.md'],
            processing_time_seconds=2.5
        )
        mock_issue_processor.process_issue.return_value = expected_result
        
        # Test processing
        result = batch_processor._process_single_issue_with_retry(123, dry_run=False)
        
        assert result == expected_result
        mock_github_client.get_issue_data.assert_called_once_with(123)
        mock_issue_processor.process_issue.assert_called_once()
    
    def test_process_single_issue_dry_run(self, batch_processor, mock_issue_processor, mock_github_client):
        """Test dry run processing."""
        # Mock issue data
        issue_data_dict = {
            'title': 'Test Issue',
            'body': 'Test body',
            'labels': ['site-monitor'],
            'assignees': [],
            'url': 'https://github.com/repo/issues/123'
        }
        mock_github_client.get_issue_data.return_value = issue_data_dict
        
        # Test dry run
        result = batch_processor._process_single_issue_with_retry(123, dry_run=True)
        
        assert result.issue_number == 123
        assert result.status == IssueProcessingStatus.PENDING
        assert result.processing_time_seconds == 0.0
        
        # Should not call process_issue in dry run
        mock_issue_processor.process_issue.assert_not_called()
    
    def test_process_single_issue_with_retry(self, batch_processor, mock_issue_processor, mock_github_client):
        """Test retry logic for failed processing."""
        # Mock issue data
        issue_data_dict = {
            'title': 'Test Issue',
            'body': 'Test body',
            'labels': ['site-monitor'],
            'assignees': [],
            'url': 'https://github.com/repo/issues/123'
        }
        mock_github_client.get_issue_data.return_value = issue_data_dict
        
        # Mock first call to fail, second to succeed
        mock_issue_processor.process_issue.side_effect = [
            Exception("First attempt failed"),
            ProcessingResult(
                issue_number=123,
                status=IssueProcessingStatus.COMPLETED,
                processing_time_seconds=1.0
            )
        ]
        
        # Test with retry
        result = batch_processor._process_single_issue_with_retry(123, dry_run=False)
        
        assert result.status == IssueProcessingStatus.COMPLETED
        assert mock_issue_processor.process_issue.call_count == 2
    
    def test_process_single_issue_all_retries_fail(self, batch_processor, mock_issue_processor, mock_github_client):
        """Test when all retry attempts fail."""
        # Mock issue data
        issue_data_dict = {
            'title': 'Test Issue',
            'body': 'Test body',
            'labels': ['site-monitor'],
            'assignees': [],
            'url': 'https://github.com/repo/issues/123'
        }
        mock_github_client.get_issue_data.return_value = issue_data_dict
        
        # Mock all calls to fail
        mock_issue_processor.process_issue.side_effect = Exception("Processing failed")
        
        # Test when all retries fail
        result = batch_processor._process_single_issue_with_retry(123, dry_run=False)
        
        assert result.status == IssueProcessingStatus.ERROR
        assert "Failed after" in result.error_message
        # Should retry once (retry_count = 1 in config)
        assert mock_issue_processor.process_issue.call_count == 2
    
    def test_process_issues_empty_list(self, batch_processor):
        """Test processing empty issue list."""
        metrics, results = batch_processor.process_issues([])
        
        assert metrics.total_issues == 0
        assert metrics.processed_count == 0
        assert results == []
    
    def test_process_issues_batch(self, batch_processor, mock_issue_processor, mock_github_client):
        """Test batch processing of multiple issues."""
        # Mock issue data
        issue_data_dict = {
            'title': 'Test Issue',
            'body': 'Test body',
            'labels': ['site-monitor'],
            'assignees': [],
            'url': 'https://github.com/repo/issues/123'
        }
        mock_github_client.get_issue_data.return_value = issue_data_dict
        
        # Mock processing results
        results = [
            ProcessingResult(
                issue_number=123,
                status=IssueProcessingStatus.COMPLETED,
                processing_time_seconds=1.0
            ),
            ProcessingResult(
                issue_number=124,
                status=IssueProcessingStatus.ERROR,
                error_message="Processing failed",
                processing_time_seconds=0.5
            )
        ]
        mock_issue_processor.process_issue.side_effect = results
        
        # Test batch processing
        metrics, batch_results = batch_processor.process_issues([123, 124])
        
        assert metrics.total_issues == 2
        assert metrics.processed_count == 2
        assert metrics.success_count == 1
        assert metrics.error_count == 1
        assert len(batch_results) == 2
    
    def test_process_site_monitor_issues(self, batch_processor, mock_github_client):
        """Test processing all site-monitor issues."""
        # Mock finding issues
        mock_label = Mock()
        mock_label.name = 'site-monitor'
        
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.assignee = None
        mock_issue.labels = [mock_label]
        
        mock_github_client.get_issues_with_labels.return_value = [mock_issue]
        
        # Mock batch processing
        with patch.object(batch_processor, 'process_issues') as mock_process:
            mock_metrics = BatchMetrics(total_issues=1, success_count=1)
            mock_results = [ProcessingResult(issue_number=123, status=IssueProcessingStatus.COMPLETED)]
            mock_process.return_value = (mock_metrics, mock_results)
            
            metrics, results = batch_processor.process_site_monitor_issues()
            
            mock_process.assert_called_once_with([123], dry_run=False)
            assert metrics.total_issues == 1
            assert len(results) == 1
    
    def test_cancel_processing(self, batch_processor):
        """Test cancelling batch processing."""
        batch_processor.cancel_processing()
        
        assert batch_processor._cancelled is True
    
    def test_update_metrics_from_batch(self, batch_processor):
        """Test metrics update from batch results."""
        metrics = BatchMetrics()
        batch_results = [
            ProcessingResult(
                issue_number=123,
                status=IssueProcessingStatus.COMPLETED,
                processing_time_seconds=1.0
            ),
            ProcessingResult(
                issue_number=124,
                status=IssueProcessingStatus.ERROR,
                processing_time_seconds=0.5
            ),
            ProcessingResult(
                issue_number=125,
                status=IssueProcessingStatus.NEEDS_CLARIFICATION,
                processing_time_seconds=0.3
            )
        ]
        
        batch_processor._update_metrics_from_batch(metrics, batch_results)
        
        assert metrics.processed_count == 3
        assert metrics.success_count == 1
        assert metrics.error_count == 1
        assert metrics.clarification_count == 1
        assert metrics.processing_times == [1.0, 0.5, 0.3]
    
    def test_save_batch_results(self, batch_processor, tmp_path):
        """Test saving batch results to file."""
        results = [
            ProcessingResult(
                issue_number=123,
                status=IssueProcessingStatus.COMPLETED,
                workflow_name='test-workflow',
                created_files=['file1.md'],
                processing_time_seconds=1.0
            )
        ]
        
        output_path = tmp_path / "results.json"
        batch_processor.save_batch_results(results, str(output_path))
        
        assert output_path.exists()
        
        # Verify file content
        import json
        with open(output_path) as f:
            data = json.load(f)
        
        assert data['total_issues'] == 1
        assert len(data['results']) == 1
        assert data['results'][0]['issue_number'] == 123
        assert data['results'][0]['status'] == 'completed'
    
    def test_priority_sorting(self, batch_processor):
        """Test priority-based issue sorting."""
        # Create mock GitHub issue objects
        mock_label1 = Mock()
        mock_label1.name = 'site-monitor'
        
        mock_label2 = Mock()
        mock_label2.name = 'site-monitor'
        mock_label3 = Mock()
        mock_label3.name = 'urgent'
        
        mock_label4 = Mock()
        mock_label4.name = 'site-monitor'
        mock_label5 = Mock()
        mock_label5.name = 'high-priority'
        
        issues = [
            Mock(number=123, labels=[mock_label1]),
            Mock(number=124, labels=[mock_label2, mock_label3]),
            Mock(number=125, labels=[mock_label4, mock_label5])
        ]
        
        # Test sorting
        sorted_numbers = batch_processor._sort_by_priority([123, 124, 125], issues)
        
        # Should be sorted by priority: urgent (124), high-priority (125), then normal (123)
        assert sorted_numbers == [124, 125, 123]


class TestBatchProcessorIntegration:
    """Integration tests for BatchProcessor with real components."""
    
    @pytest.fixture
    def integration_setup(self, mock_github_issue):
        """Set up integration test environment."""
        # Create real IssueProcessor with mocked dependencies
        from src.utils.config_manager import ConfigManager
        from src.workflow.workflow_matcher import WorkflowMatcher
        
        # Mock configuration
        config = Mock()
        config.agent = Mock()
        config.agent.workflow_directory = 'docs/workflow/deliverables'
        config.agent.output_directory = 'study'
        config.agent.agent_username = 'test-agent'
        
        # Create processor with mocked components
        processor = Mock(spec=IssueProcessor)
        github_client = Mock(spec=GitHubIssueCreator)
        
        batch_config = BatchConfig(max_batch_size=2, max_concurrent_workers=1)
        batch_processor = BatchProcessor(
            issue_processor=processor,
            github_client=github_client,
            config=batch_config
        )
        
        return {
            'processor': processor,
            'github_client': github_client,
            'batch_processor': batch_processor,
            'config': config
        }
    
    def test_end_to_end_batch_processing(self, integration_setup):
        """Test complete batch processing workflow."""
        setup = integration_setup
        batch_processor = setup['batch_processor']
        github_client = setup['github_client']
        processor = setup['processor']
        
        # Mock GitHub API responses
        mock_label = Mock()
        mock_label.name = 'site-monitor'
        
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.assignee = None
        mock_issue.labels = [mock_label]
        
        github_client.get_issues_with_labels.return_value = [mock_issue]
        github_client.get_issue_data.return_value = {
            'title': 'Test Issue',
            'body': 'Test body',
            'labels': ['site-monitor'],
            'assignees': [],
            'url': 'https://github.com/repo/issues/123'
        }
        
        # Mock processing result
        processor.process_issue.return_value = ProcessingResult(
            issue_number=123,
            status=IssueProcessingStatus.COMPLETED,
            workflow_name='test-workflow',
            created_files=['deliverable.md'],
            processing_time_seconds=2.0
        )
        
        # Execute batch processing
        metrics, results = batch_processor.process_site_monitor_issues()
        
        # Verify results
        assert metrics.total_issues == 1
        assert metrics.processed_count == 1
        assert metrics.success_count == 1
        assert len(results) == 1
        assert results[0].status == IssueProcessingStatus.COMPLETED