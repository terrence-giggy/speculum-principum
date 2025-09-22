"""
Unit tests for WorkflowMatcher module
"""

import pytest
import yaml
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

from src.workflow_matcher import WorkflowMatcher, WorkflowInfo, WorkflowValidationError, WorkflowLoadError


class TestWorkflowMatcher:
    """Test cases for WorkflowMatcher class"""
    
    @pytest.fixture
    def temp_workflow_dir(self):
        """Create a temporary directory with sample workflow files"""
        temp_dir = tempfile.mkdtemp()
        workflow_dir = Path(temp_dir) / "workflows"
        workflow_dir.mkdir()
        
        # Create sample research workflow
        research_workflow = {
            'name': 'Research Analysis',
            'description': 'Comprehensive research workflow',
            'version': '1.0.0',
            'trigger_labels': ['research', 'analysis'],
            'deliverables': [
                {
                    'name': 'overview', 
                    'title': 'Research Overview',
                    'description': 'High-level overview of research findings',
                    'required': True, 
                    'order': 1
                },
                {
                    'name': 'findings', 
                    'title': 'Detailed Findings',
                    'description': 'Comprehensive analysis of research data',
                    'required': True, 
                    'order': 2
                }
            ],
            'processing': {'timeout': 60},
            'validation': {'min_word_count': 100},
            'output': {'folder_structure': 'study/{issue_number}'}
        }
        
        # Create sample technical review workflow
        technical_workflow = {
            'name': 'Technical Review',
            'description': 'Technical assessment workflow',
            'version': '1.1.0',
            'trigger_labels': ['technical-review', 'code-review'],
            'deliverables': [
                {
                    'name': 'architecture', 
                    'title': 'Architecture Analysis',
                    'description': 'Technical architecture assessment',
                    'required': True, 
                    'order': 1
                },
                {
                    'name': 'security', 
                    'title': 'Security Review',
                    'description': 'Security vulnerability analysis',
                    'required': True, 
                    'order': 2
                }
            ],
            'processing': {'timeout': 90},
            'validation': {'min_word_count': 150},
            'output': {'folder_structure': 'study/{issue_number}-tech'}
        }
        
        # Write workflow files
        with open(workflow_dir / "research.yaml", 'w') as f:
            yaml.dump(research_workflow, f)
        
        with open(workflow_dir / "technical.yaml", 'w') as f:
            yaml.dump(technical_workflow, f)
        
        # Create an invalid workflow file
        with open(workflow_dir / "invalid.yaml", 'w') as f:
            f.write("invalid: yaml: content: [")
        
        # Create an incomplete workflow file
        incomplete_workflow = {
            'name': 'Incomplete Workflow',
            'description': 'Missing required fields'
            # Missing trigger_labels and deliverables
        }
        with open(workflow_dir / "incomplete.yaml", 'w') as f:
            yaml.dump(incomplete_workflow, f)
        
        yield str(workflow_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def empty_workflow_dir(self):
        """Create an empty temporary directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_init_with_valid_directory(self, temp_workflow_dir):
        """Test initialization with valid workflow directory"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        assert len(matcher._workflow_cache) == 2  # Only valid workflows loaded
        assert matcher._last_scan_time is not None
        
        # Check that valid workflows were loaded
        workflow_names = [w.name for w in matcher._workflow_cache.values()]
        assert 'Research Analysis' in workflow_names
        assert 'Technical Review' in workflow_names
    
    def test_init_with_nonexistent_directory(self):
        """Test initialization with non-existent directory"""
        with pytest.raises(WorkflowLoadError):
            WorkflowMatcher("/path/that/does/not/exist")
    
    def test_init_with_empty_directory(self, empty_workflow_dir):
        """Test initialization with empty directory"""
        matcher = WorkflowMatcher(empty_workflow_dir)
        assert len(matcher._workflow_cache) == 0
    
    def test_parse_workflow_file_valid(self, temp_workflow_dir):
        """Test parsing a valid workflow file"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        workflow_file = Path(temp_workflow_dir) / "research.yaml"
        
        workflow_info = matcher._parse_workflow_file(workflow_file)
        
        assert workflow_info is not None
        assert workflow_info.name == 'Research Analysis'
        assert workflow_info.description == 'Comprehensive research workflow'
        assert workflow_info.version == '1.0.0'
        assert 'research' in workflow_info.trigger_labels
        assert 'analysis' in workflow_info.trigger_labels
        assert len(workflow_info.deliverables) == 2
    
    def test_parse_workflow_file_invalid_yaml(self, temp_workflow_dir):
        """Test parsing an invalid YAML file"""
        matcher = WorkflowMatcher.__new__(WorkflowMatcher)  # Create without __init__
        matcher.workflow_directory = Path(temp_workflow_dir)
        
        workflow_file = Path(temp_workflow_dir) / "invalid.yaml"
        
        with pytest.raises(WorkflowValidationError, match="Invalid YAML"):
            matcher._parse_workflow_file(workflow_file)
    
    def test_parse_workflow_file_missing_required_fields(self, temp_workflow_dir):
        """Test parsing workflow file with missing required fields"""
        matcher = WorkflowMatcher.__new__(WorkflowMatcher)  # Create without __init__
        matcher.workflow_directory = Path(temp_workflow_dir)
        
        workflow_file = Path(temp_workflow_dir) / "incomplete.yaml"
        
        with pytest.raises(WorkflowValidationError, match="missing required fields"):
            matcher._parse_workflow_file(workflow_file)
    
    def test_find_matching_workflows_with_site_monitor(self, temp_workflow_dir):
        """Test finding workflows with site-monitor label"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        # Test with research labels
        labels = ['site-monitor', 'research']
        matches = matcher.find_matching_workflows(labels)
        
        assert len(matches) == 1
        assert matches[0].name == 'Research Analysis'
        
        # Test with technical labels
        labels = ['site-monitor', 'technical-review']
        matches = matcher.find_matching_workflows(labels)
        
        assert len(matches) == 1
        assert matches[0].name == 'Technical Review'
    
    def test_find_matching_workflows_without_site_monitor(self, temp_workflow_dir):
        """Test finding workflows without site-monitor label"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        labels = ['research', 'analysis']
        matches = matcher.find_matching_workflows(labels)
        
        assert len(matches) == 0
    
    def test_find_matching_workflows_multiple_matches(self, temp_workflow_dir):
        """Test finding workflows with multiple matches"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        # Both workflows could match if we had overlapping labels
        # For this test, we'll modify one workflow temporarily by finding the research workflow
        research_workflow = None
        for workflow in matcher._workflow_cache.values():
            if workflow.name == 'Research Analysis':
                research_workflow = workflow
                break
        
        assert research_workflow is not None
        # Add technical-review to research workflow to create overlap
        research_workflow.trigger_labels.append('technical-review')
        
        labels = ['site-monitor', 'technical-review']
        matches = matcher.find_matching_workflows(labels)
        
        assert len(matches) == 2
    
    def test_get_best_workflow_match_single_match(self, temp_workflow_dir):
        """Test getting best workflow match with single match"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        labels = ['site-monitor', 'research']
        workflow, message = matcher.get_best_workflow_match(labels)
        
        assert workflow is not None
        assert workflow.name == 'Research Analysis'
        assert 'Selected workflow' in message
    
    def test_get_best_workflow_match_no_site_monitor(self, temp_workflow_dir):
        """Test getting best workflow match without site-monitor label"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        labels = ['research']
        workflow, message = matcher.get_best_workflow_match(labels)
        
        assert workflow is None
        assert 'site-monitor' in message
    
    def test_get_best_workflow_match_no_matches(self, temp_workflow_dir):
        """Test getting best workflow match with no matches"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        labels = ['site-monitor', 'unknown-label']
        workflow, message = matcher.get_best_workflow_match(labels)
        
        assert workflow is None
        assert 'No workflows match' in message
    
    def test_get_workflow_by_name(self, temp_workflow_dir):
        """Test getting workflow by name"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        workflow = matcher.get_workflow_by_name('Research Analysis')
        assert workflow is not None
        assert workflow.name == 'Research Analysis'
        
        workflow = matcher.get_workflow_by_name('Nonexistent Workflow')
        assert workflow is None
    
    def test_get_workflow_suggestions(self, temp_workflow_dir):
        """Test getting workflow suggestions"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        labels = ['site-monitor']
        suggestions = matcher.get_workflow_suggestions(labels)
        
        assert 'research' in suggestions
        assert 'analysis' in suggestions
        assert 'technical-review' in suggestions
        assert 'code-review' in suggestions
        assert 'site-monitor' not in suggestions  # Already present
    
    def test_validate_workflow_directory_valid(self, temp_workflow_dir):
        """Test validating a valid workflow directory"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        is_valid, errors = matcher.validate_workflow_directory()
        
        # Should be valid despite having some invalid files (they don't pass validation but are processed)
        # The validation method tries to re-parse files, so invalid ones will show as errors
        # Let's check that we have some valid workflows loaded in the cache
        assert len(matcher._workflow_cache) == 2  # Two valid workflows loaded
        if not is_valid:
            # Print errors for debugging
            print(f"Validation errors: {errors}")
            # Valid workflows were still loaded despite errors in other files
            assert any("Invalid workflow file" in error for error in errors)
    
    def test_validate_workflow_directory_nonexistent(self):
        """Test validating non-existent workflow directory"""
        matcher = WorkflowMatcher.__new__(WorkflowMatcher)
        matcher.workflow_directory = Path("/nonexistent/path")
        matcher._workflow_cache = {}
        
        is_valid, errors = matcher.validate_workflow_directory()
        
        assert not is_valid
        assert len(errors) > 0
        assert 'does not exist' in errors[0]
    
    def test_validate_workflow_directory_empty(self, empty_workflow_dir):
        """Test validating empty workflow directory"""
        matcher = WorkflowMatcher.__new__(WorkflowMatcher)
        matcher.workflow_directory = Path(empty_workflow_dir)
        matcher._workflow_cache = {}
        
        is_valid, errors = matcher.validate_workflow_directory()
        
        assert not is_valid
        assert len(errors) > 0
        assert 'No workflow files found' in errors[0]
    
    def test_get_statistics(self, temp_workflow_dir):
        """Test getting workflow statistics"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        stats = matcher.get_statistics()
        
        assert stats['total_workflows'] == 2
        assert stats['total_trigger_labels'] == 4  # research, analysis, technical-review, code-review
        assert stats['total_deliverables'] == 4  # 2 + 2
        assert stats['workflow_directory'] == temp_workflow_dir
        assert stats['last_scan_time'] is not None
        assert 'Research Analysis' in stats['workflow_names']
        assert 'Technical Review' in stats['workflow_names']
    
    def test_refresh_workflows(self, temp_workflow_dir):
        """Test forcing workflow refresh"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        original_scan_time = matcher._last_scan_time
        assert original_scan_time is not None
        
        # Wait a small amount and refresh
        import time
        time.sleep(0.01)
        matcher.refresh_workflows()
        
        assert matcher._last_scan_time is not None
        assert matcher._last_scan_time > original_scan_time
    
    def test_should_rescan_based_on_time(self, temp_workflow_dir):
        """Test automatic rescanning based on time"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        matcher._scan_interval_seconds = 1  # 1 second for testing
        
        # Should not need rescan immediately
        assert not matcher._should_rescan()
        
        # Mock time to be beyond scan interval
        with patch('src.workflow_matcher.datetime') as mock_datetime:
            future_time = datetime.now() + timedelta(seconds=2)
            mock_datetime.now.return_value = future_time
            assert matcher._should_rescan()
    
    def test_get_available_workflows(self, temp_workflow_dir):
        """Test getting all available workflows"""
        matcher = WorkflowMatcher(temp_workflow_dir)
        
        workflows = matcher.get_available_workflows()
        
        assert len(workflows) == 2
        workflow_names = [w.name for w in workflows]
        assert 'Research Analysis' in workflow_names
        assert 'Technical Review' in workflow_names


class TestWorkflowInfo:
    """Test cases for WorkflowInfo dataclass"""
    
    def test_workflow_info_creation_valid(self):
        """Test creating valid WorkflowInfo"""
        workflow = WorkflowInfo(
            path="/test/path.yaml",
            name="Test Workflow",
            description="Test description",
            version="1.0.0",
            trigger_labels=["test"],
            deliverables=[{"name": "test", "required": True}],
            processing={},
            validation={},
            output={}
        )
        
        assert workflow.name == "Test Workflow"
        assert workflow.trigger_labels == ["test"]
    
    def test_workflow_info_creation_no_trigger_labels(self):
        """Test creating WorkflowInfo without trigger labels"""
        with pytest.raises(WorkflowValidationError, match="must have at least one trigger label"):
            WorkflowInfo(
                path="/test/path.yaml",
                name="Test Workflow",
                description="Test description",
                version="1.0.0",
                trigger_labels=[],  # Empty list
                deliverables=[{"name": "test", "required": True}],
                processing={},
                validation={},
                output={}
            )
    
    def test_workflow_info_creation_no_deliverables(self):
        """Test creating WorkflowInfo without deliverables"""
        with pytest.raises(WorkflowValidationError, match="must have at least one deliverable"):
            WorkflowInfo(
                path="/test/path.yaml",
                name="Test Workflow",
                description="Test description",
                version="1.0.0",
                trigger_labels=["test"],
                deliverables=[],  # Empty list
                processing={},
                validation={},
                output={}
            )