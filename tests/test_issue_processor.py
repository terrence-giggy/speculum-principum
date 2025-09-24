"""
Test suite for IssueProcessor class
Tests core issue processing logic without GitHub integration
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from src.core.issue_processor import (
    IssueProcessor, IssueProcessingStatus, ProcessingResult, IssueData,
    IssueProcessingError, ProcessingTimeoutError
)
from src.workflow.workflow_matcher import WorkflowInfo, WorkflowValidationError


class TestIssueData:
    """Test IssueData dataclass functionality."""
    
    def test_create_issue_data(self):
        """Test creating IssueData instance."""
        issue_data = IssueData(
            number=123,
            title="Test Issue",
            body="Test description",
            labels=["site-monitor", "research"],
            assignees=["user1"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            url="https://github.com/test/repo/issues/123"
        )
        
        assert issue_data.number == 123
        assert issue_data.title == "Test Issue"
        assert "site-monitor" in issue_data.labels
    
    def test_from_dict(self):
        """Test creating IssueData from dictionary."""
        data = {
            "number": 456,
            "title": "Dict Issue",
            "body": "From dict",
            "labels": ["site-monitor"],
            "assignees": [],
            "created_at": "2023-01-01T00:00:00+00:00",
            "updated_at": "2023-01-01T00:00:00+00:00",
            "url": "https://github.com/test/repo/issues/456"
        }
        
        issue_data = IssueData.from_dict(data)
        assert issue_data.number == 456
        assert issue_data.title == "Dict Issue"
        assert isinstance(issue_data.created_at, datetime)


class TestProcessingResult:
    """Test ProcessingResult dataclass functionality."""
    
    def test_create_processing_result(self):
        """Test creating ProcessingResult with defaults."""
        result = ProcessingResult(
            issue_number=123,
            status=IssueProcessingStatus.COMPLETED
        )
        
        assert result.issue_number == 123
        assert result.status == IssueProcessingStatus.COMPLETED
        assert result.created_files == []
        assert result.workflow_name is None
    
    def test_processing_result_with_files(self):
        """Test ProcessingResult with created files."""
        result = ProcessingResult(
            issue_number=123,
            status=IssueProcessingStatus.COMPLETED,
            created_files=["file1.md", "file2.md"]
        )
        
        assert result.created_files is not None
        assert len(result.created_files) == 2
        assert "file1.md" in result.created_files


class TestIssueProcessor:
    """Test IssueProcessor class functionality."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory with config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create config file
            config_file = temp_path / "test_config.yaml"
            config_content = """
sites:
  - url: "https://example.com"
    name: "Test Site"
    keywords: ["test"]

github:
  repository: "test/repo"

search:
  api_key: "test_key"
  search_engine_id: "test_engine"

agent:
  username: "test-agent"
  workflow_directory: "docs/workflow/deliverables"
  output_directory: "study"
  processing:
    default_timeout_minutes: 5
  git:
    branch_prefix: "agent"
  validation:
    min_word_count: 100
"""
            config_file.write_text(config_content)
            
            # Create workflow directory
            workflow_dir = temp_path / "docs" / "workflow" / "deliverables"
            workflow_dir.mkdir(parents=True)
            
            # Create sample workflow
            workflow_file = workflow_dir / "research.yaml"
            workflow_content = """
name: "Research Analysis"
description: "Research and analysis workflow"
version: "1.0"
trigger_labels:
  - "research"
  - "analysis"
deliverables:
  - name: "Initial Research"
    description: "Basic research document"
    type: "document"
    format: "markdown"
    required_sections: ["overview", "findings"]
processing:
  timeout_minutes: 30
validation:
  min_word_count: 200
output:
  folder_structure: "issue_{issue_number}"
  file_pattern: "{deliverable_name}.md"
"""
            workflow_file.write_text(workflow_content)
            
            # Create output directory
            output_dir = temp_path / "study"
            output_dir.mkdir()
            
            yield temp_path
    
    @pytest.fixture
    def mock_workflow_matcher(self):
        """Create mock WorkflowMatcher."""
        mock_matcher = Mock()
        
        # Mock workflow info
        mock_workflow = WorkflowInfo(
            path="test/workflow.yaml",
            name="Test Workflow",
            description="Test workflow description",
            version="1.0",
            trigger_labels=["research"],
            deliverables=[{
                "name": "Research Document",
                "description": "Test research doc",
                "type": "document",
                "format": "markdown"
            }],
            processing={"timeout_minutes": 30},
            validation={"min_word_count": 100},
            output={
                "folder_structure": "issue_{issue_number}",
                "file_pattern": "{deliverable_name}.md"
            }
        )
        
        mock_matcher.get_best_workflow_match.return_value = (mock_workflow, "Test workflow selected")
        mock_matcher.get_available_workflows.return_value = [mock_workflow]
        
        return mock_matcher
    
    @pytest.fixture
    def sample_issue_data(self):
        """Create sample issue data for testing."""
        return IssueData(
            number=123,
            title="Test Research Issue",
            body="This is a test issue for research workflow",
            labels=["site-monitor", "research"],
            assignees=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            url="https://github.com/test/repo/issues/123"
        )
    
    def test_init_with_temp_config(self, temp_config_dir):
        """Test IssueProcessor initialization with temp config."""
        config_file = temp_config_dir / "test_config.yaml"
        
        with patch('src.core.issue_processor.WorkflowMatcher'):
            processor = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=str(temp_config_dir / "study")
            )
            
            assert processor.agent_username == "test-agent"
            assert processor.processing_timeout == 300  # 5 minutes * 60
    
    def test_process_issue_without_site_monitor_label(self, temp_config_dir, mock_workflow_matcher):
        """Test processing issue without site-monitor label."""
        config_file = temp_config_dir / "test_config.yaml"
        
        with patch('src.core.issue_processor.WorkflowMatcher', return_value=mock_workflow_matcher):
            processor = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=str(temp_config_dir / "study")
            )
            
            issue_data = IssueData(
                number=123,
                title="Test Issue",
                body="Test",
                labels=["bug"],  # No site-monitor label
                assignees=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                url="https://github.com/test/repo/issues/123"
            )
            
            result = processor.process_issue(issue_data)
            
            assert result.status == IssueProcessingStatus.PENDING
            assert result.error_message is not None
            assert "site-monitor" in result.error_message
    
    def test_process_issue_needs_clarification(self, temp_config_dir, sample_issue_data):
        """Test processing issue that needs clarification."""
        config_file = temp_config_dir / "test_config.yaml"
        
        # Mock workflow matcher to return no workflow
        mock_matcher = Mock()
        mock_matcher.get_best_workflow_match.return_value = (None, "No clear match")
        mock_matcher.get_available_workflows.return_value = []
        
        with patch('src.core.issue_processor.WorkflowMatcher', return_value=mock_matcher):
            processor = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=str(temp_config_dir / "study")
            )
            
            result = processor.process_issue(sample_issue_data)
            
            assert result.status == IssueProcessingStatus.NEEDS_CLARIFICATION
            assert result.clarification_needed is not None
            assert "Workflow Selection Required" in result.clarification_needed
    
    def test_process_issue_successful(self, temp_config_dir, sample_issue_data, mock_workflow_matcher):
        """Test successful issue processing."""
        config_file = temp_config_dir / "test_config.yaml"
        
        with patch('src.core.issue_processor.WorkflowMatcher', return_value=mock_workflow_matcher):
            processor = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=str(temp_config_dir / "study")
            )
            
            result = processor.process_issue(sample_issue_data)
            
            assert result.status == IssueProcessingStatus.COMPLETED
            assert result.workflow_name == "Test Workflow"
            assert result.created_files is not None
            assert len(result.created_files) > 0
            assert result.processing_time_seconds is not None
    
    def test_process_issue_error_handling(self, temp_config_dir, sample_issue_data):
        """Test error handling during issue processing."""
        config_file = temp_config_dir / "test_config.yaml"
        
        # Mock workflow matcher to raise exception
        mock_matcher = Mock()
        mock_matcher.get_best_workflow_match.side_effect = Exception("Test error")
        
        with patch('src.core.issue_processor.WorkflowMatcher', return_value=mock_matcher):
            processor = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=str(temp_config_dir / "study")
            )
            
            result = processor.process_issue(sample_issue_data)
            
            assert result.status == IssueProcessingStatus.ERROR
            assert result.error_message == "Failed to find matching workflow: Test error"
    
    def test_slugify(self, temp_config_dir):
        """Test text slugification."""
        config_file = temp_config_dir / "test_config.yaml"
        
        with patch('src.core.issue_processor.WorkflowMatcher'):
            processor = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=str(temp_config_dir / "study")
            )
            
            # Test various inputs
            assert processor._slugify("Test Title") == "test-title"
            assert processor._slugify("Complex Title With Symbols!@#") == "complex-title-with-symbols"
            assert processor._slugify("  Multiple   Spaces  ") == "multiple-spaces"
            assert processor._slugify("hyphen-already-here") == "hyphen-already-here"
    
    def test_issue_state_management(self, temp_config_dir, sample_issue_data, mock_workflow_matcher):
        """Test issue state tracking and persistence."""
        config_file = temp_config_dir / "test_config.yaml"
        
        with patch('src.core.issue_processor.WorkflowMatcher', return_value=mock_workflow_matcher):
            processor = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=str(temp_config_dir / "study")
            )
            
            # Process issue
            result = processor.process_issue(sample_issue_data)
            
            # Check state was saved
            state = processor.get_issue_processing_state(123)
            assert state is not None
            assert state['status'] == IssueProcessingStatus.COMPLETED.value
            assert 'completed_at' in state
            
            # Test listing issues
            issues = processor.list_processing_issues()
            assert len(issues) == 1
            assert issues[0]['issue_number'] == 123
            
            # Test filtering by status
            completed_issues = processor.list_processing_issues(IssueProcessingStatus.COMPLETED)
            assert len(completed_issues) == 1
            
            pending_issues = processor.list_processing_issues(IssueProcessingStatus.PENDING)
            assert len(pending_issues) == 0
    
    def test_clear_issue_state(self, temp_config_dir):
        """Test clearing issue state."""
        config_file = temp_config_dir / "test_config.yaml"
        
        with patch('src.core.issue_processor.WorkflowMatcher'):
            processor = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=str(temp_config_dir / "study")
            )
            
            # Manually add some state
            processor._update_issue_status(123, IssueProcessingStatus.PENDING)
            
            # Verify state exists
            assert processor.get_issue_processing_state(123) is not None
            
            # Clear state
            cleared = processor.clear_issue_state(123)
            assert cleared is True
            
            # Verify state is gone
            assert processor.get_issue_processing_state(123) is None
            
            # Try clearing non-existent state
            cleared = processor.clear_issue_state(999)
            assert cleared is False
    
    def test_reset_all_processing_state(self, temp_config_dir):
        """Test resetting all processing state."""
        config_file = temp_config_dir / "test_config.yaml"
        
        with patch('src.core.issue_processor.WorkflowMatcher'):
            processor = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=str(temp_config_dir / "study")
            )
            
            # Add multiple states
            processor._update_issue_status(123, IssueProcessingStatus.PENDING)
            processor._update_issue_status(456, IssueProcessingStatus.PROCESSING)
            processor._update_issue_status(789, IssueProcessingStatus.COMPLETED)
            
            # Verify states exist
            assert len(processor.list_processing_issues()) == 3
            
            # Reset all
            count = processor.reset_all_processing_state()
            assert count == 3
            
            # Verify all states are gone
            assert len(processor.list_processing_issues()) == 0
    
    def test_generate_deliverable_content(self, temp_config_dir, sample_issue_data, mock_workflow_matcher):
        """Test deliverable content generation."""
        config_file = temp_config_dir / "test_config.yaml"
        
        with patch('src.core.issue_processor.WorkflowMatcher', return_value=mock_workflow_matcher):
            processor = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=str(temp_config_dir / "study")
            )
            
            deliverable_spec = {
                "name": "Test Deliverable",
                "description": "Test description",
                "type": "document",
                "format": "markdown",
                "required_sections": ["overview", "analysis"]
            }
            
            # Get workflow info from mock
            workflow_info = mock_workflow_matcher.get_best_workflow_match.return_value[0]
            
            content = processor._generate_deliverable_content(
                sample_issue_data, 
                deliverable_spec, 
                workflow_info
            )
            
            # Verify content structure
            assert f"# {deliverable_spec['name']}" in content
            assert f"#{sample_issue_data.number}" in content
            assert workflow_info.name in content
            assert sample_issue_data.title in content
            assert sample_issue_data.body in content
    
    def test_state_persistence(self, temp_config_dir):
        """Test that processing state persists across processor instances."""
        config_file = temp_config_dir / "test_config.yaml"
        output_dir = str(temp_config_dir / "study")
        
        with patch('src.core.issue_processor.WorkflowMatcher'):
            # Create first processor and add state
            processor1 = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=output_dir
            )
            processor1._update_issue_status(123, IssueProcessingStatus.PENDING, {
                'test_data': 'test_value'
            })
            
            # Create second processor (should load existing state)
            processor2 = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=output_dir
            )
            
            # Verify state was loaded
            state = processor2.get_issue_processing_state(123)
            assert state is not None
            assert state['status'] == IssueProcessingStatus.PENDING.value
            assert state['test_data'] == 'test_value'
    
    def test_file_creation_and_structure(self, temp_config_dir, sample_issue_data, mock_workflow_matcher):
        """Test that files are created with correct structure."""
        config_file = temp_config_dir / "test_config.yaml"
        
        with patch('src.core.issue_processor.WorkflowMatcher', return_value=mock_workflow_matcher):
            processor = IssueProcessor(
                config_path=str(config_file),
                output_base_dir=str(temp_config_dir / "study")
            )
            
            result = processor.process_issue(sample_issue_data)
            
            # Verify files were created
            assert result.status == IssueProcessingStatus.COMPLETED
            assert result.created_files is not None
            assert len(result.created_files) > 0
            
            # Check if files actually exist
            for file_path in result.created_files:
                file_obj = Path(file_path)
                assert file_obj.exists()
                assert file_obj.suffix == '.md'
                
                # Check file content
                content = file_obj.read_text()
                assert sample_issue_data.title in content
                assert str(sample_issue_data.number) in content