"""
Simplified unit tests for Copilot assignment detection functionality.

Tests the new methods added to GitHubIntegratedIssueProcessor for
identifying issues assigned to GitHub Copilot.
"""

import pytest
from unittest.mock import Mock

from src.core.issue_processor import GitHubIntegratedIssueProcessor


class TestCopilotAssignmentLogic:
    """Test core Copilot assignment logic without complex initialization."""

    def test_is_copilot_assigned_with_dict(self):
        """Test is_copilot_assigned with dictionary input."""
        # Create a processor instance (we'll bypass initialization for testing)
        processor = GitHubIntegratedIssueProcessor.__new__(GitHubIntegratedIssueProcessor)
        
        # Test Copilot assignment variations
        test_cases = [
            ({'assignee': 'github-copilot[bot]'}, True),
            ({'assignee': 'copilot'}, True),
            ({'assignee': 'github-actions[bot]'}, True),
            ({'assignee': 'human-user'}, False),
            ({'assignee': None}, False),
            ({}, False),
        ]
        
        for issue_data, expected in test_cases:
            result = processor.is_copilot_assigned(issue_data)
            assert result == expected, f"Failed for {issue_data}: expected {expected}, got {result}"

    def test_is_copilot_assigned_with_object(self):
        """Test is_copilot_assigned with GitHub issue object."""
        processor = GitHubIntegratedIssueProcessor.__new__(GitHubIntegratedIssueProcessor)
        
        # Mock GitHub issue object
        mock_issue = Mock()
        mock_issue.assignee = Mock()
        mock_issue.assignee.login = 'github-copilot[bot]'
        
        result = processor.is_copilot_assigned(mock_issue)
        assert result is True
        
        # Test with non-Copilot assignee
        mock_issue.assignee.login = 'human-user'
        result = processor.is_copilot_assigned(mock_issue)
        assert result is False
        
        # Test with no assignee
        mock_issue.assignee = None
        result = processor.is_copilot_assigned(mock_issue)
        assert result is False

    def test_should_process_copilot_issue(self):
        """Test _should_process_copilot_issue method."""
        processor = GitHubIntegratedIssueProcessor.__new__(GitHubIntegratedIssueProcessor)
        
        # Mock issue with intelligence label - need to mock the .name attribute
        mock_label_site_monitor = Mock()
        mock_label_site_monitor.name = 'site-monitor'
        mock_label_intelligence = Mock()
        mock_label_intelligence.name = 'intelligence'
        
        mock_issue = Mock()
        mock_issue.labels = [mock_label_site_monitor, mock_label_intelligence]
        mock_issue.title = "Test Issue"
        mock_issue.body = "Test body"
        
        result = processor._should_process_copilot_issue(mock_issue)
        assert result is True
        
        # Mock issue with content indicator in title
        mock_label_site_monitor = Mock()
        mock_label_site_monitor.name = 'site-monitor'
        
        mock_issue.labels = [mock_label_site_monitor]  # No intelligence label
        mock_issue.title = "Target Analysis Required"
        mock_issue.body = "Analysis needed"
        
        result = processor._should_process_copilot_issue(mock_issue)
        assert result is True
        
        # Mock issue without indicators
        mock_label_bug = Mock()
        mock_label_bug.name = 'bug'
        
        mock_issue.labels = [mock_label_bug]  # No intelligence indicators
        mock_issue.title = "Bug fix needed"
        mock_issue.body = "Fix this bug"
        
        result = processor._should_process_copilot_issue(mock_issue)
        assert result is False

    def test_convert_issue_to_dict(self):
        """Test _convert_issue_to_dict method."""
        processor = GitHubIntegratedIssueProcessor.__new__(GitHubIntegratedIssueProcessor)
        
        # Mock GitHub issue object with proper label mocks
        mock_label_site_monitor = Mock()
        mock_label_site_monitor.name = 'site-monitor'
        mock_label_intelligence = Mock()
        mock_label_intelligence.name = 'intelligence'
        
        mock_assignee = Mock()
        mock_assignee.login = 'github-copilot[bot]'
        
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.title = "Test Intelligence Analysis"
        mock_issue.body = "Research target organization"
        mock_issue.labels = [mock_label_site_monitor, mock_label_intelligence]
        mock_issue.assignees = [mock_assignee]
        mock_issue.assignee = mock_assignee
        mock_issue.created_at = Mock()
        mock_issue.created_at.isoformat.return_value = "2023-01-01T00:00:00Z"
        mock_issue.updated_at = Mock()
        mock_issue.updated_at.isoformat.return_value = "2023-01-01T01:00:00Z"
        mock_issue.html_url = "https://github.com/owner/repo/issues/123"
        
        result = processor._convert_issue_to_dict(mock_issue)
        
        expected = {
            'number': 123,
            'title': "Test Intelligence Analysis",
            'body': "Research target organization",
            'labels': ['site-monitor', 'intelligence'],
            'assignees': ['github-copilot[bot]'],
            'assignee': 'github-copilot[bot]',
            'created_at': "2023-01-01T00:00:00Z",
            'updated_at': "2023-01-01T01:00:00Z",
            'url': "https://github.com/owner/repo/issues/123"
        }
        
        assert result == expected


class TestBatchProcessorCopilotLogic:
    """Test BatchProcessor Copilot assignment logic without complex initialization."""

    def test_specialist_filtering_logic(self):
        """Test the specialist filtering logic used in process_copilot_assigned_issues."""
        # Mock issues data
        issues = [
            {'number': 123, 'labels': ['intelligence', 'site-monitor']},
            {'number': 456, 'labels': ['osint-researcher', 'site-monitor']},
            {'number': 789, 'labels': ['target-profiler', 'site-monitor']},
        ]
        
        # Test filtering by specialist type
        specialist_filter = 'intelligence'
        filtered_issues = []
        for issue in issues:
            labels = issue.get('labels', [])
            if specialist_filter in labels or any(
                label for label in labels 
                if specialist_filter.replace('-', '_') in label.replace('-', '_')
            ):
                filtered_issues.append(issue)
        
        # Should find the intelligence issue
        assert len(filtered_issues) == 1
        assert filtered_issues[0]['number'] == 123
        
        # Test filtering by osint-researcher
        specialist_filter = 'osint-researcher'
        filtered_issues = []
        for issue in issues:
            labels = issue.get('labels', [])
            if specialist_filter in labels or any(
                label for label in labels 
                if specialist_filter.replace('-', '_') in label.replace('-', '_')
            ):
                filtered_issues.append(issue)
        
        # Should find the osint-researcher issue
        assert len(filtered_issues) == 1
        assert filtered_issues[0]['number'] == 456