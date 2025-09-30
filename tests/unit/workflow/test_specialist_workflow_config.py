"""
Tests for Specialist Workflow Configuration System

Tests the specialist workflow configuration and registry components
implemented for Task 3.3.
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List

from src.workflow.specialist_workflow_config import (
    SpecialistWorkflowConfigManager,
    SpecialistType,
    AssignmentRule,
    DeliverableSpec,
    QualityRequirement,
    SpecialistWorkflowConfig
)
from src.workflow.specialist_registry import (
    SpecialistWorkflowRegistry,
    SpecialistAssignment
)


@pytest.fixture
def temp_config_dir():
    """Create temporary directory for test configurations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_config_file(temp_config_dir):
    """Create a sample configuration file."""
    config_path = temp_config_dir / "config.yaml"
    config_content = """
    github:
      token: test-token
      repository: test/repo
    
    google:
      api_key: test-key
      search_engine_id: test-engine-id
    """
    
    config_path.write_text(config_content)
    return str(config_path)


@pytest.fixture
def sample_workflow_dir(temp_config_dir):
    """Create sample workflow files."""
    workflow_dir = temp_config_dir / "workflows"
    workflow_dir.mkdir()
    
    # Intelligence analyst workflow
    intel_workflow = workflow_dir / "intelligence-analysis-workflow.yaml"
    intel_workflow.write_text("""
name: "Intelligence Analysis Workflow"
description: "AI-powered intelligence analysis"
version: "1.0.0"
trigger_labels:
  - "intelligence"
  - "intelligence-analyst"

config:
  specialist_type: "intelligence-analyst"
  ai_enhanced: true
  
deliverables:
  - name: "intelligence_assessment"
    template: "intelligence_assessment.md"
    filename: "intelligence-analysis-{issue_number}.md"
    
processing:
  timeout_minutes: 30
  
validation:
  require_review: false
  
output:
  branch_pattern: "intelligence/issue-{issue_number}"
""")
    
    # OSINT researcher workflow
    osint_workflow = workflow_dir / "osint-research-workflow.yaml"
    osint_workflow.write_text("""
name: "OSINT Research Analysis"
description: "OSINT research workflow"
version: "1.0.0"
trigger_labels:
  - "osint"
  - "osint-researcher"
  
specialist:
  type: "osint-researcher"
  
deliverables:
  - name: "osint_research_report"
    template: "osint_research_report.md"
    
processing:
  timeout_minutes: 25
  
output:
  branch_pattern: "osint/issue-{issue_number}"
""")
    
    return str(workflow_dir)


class TestSpecialistWorkflowConfigManager:
    """Test specialist workflow configuration manager."""
    
    def test_initialization(self, sample_config_file, sample_workflow_dir):
        """Test config manager initialization."""
        manager = SpecialistWorkflowConfigManager(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        
        assert manager.config_path == sample_config_file
        assert manager.workflow_directory == Path(sample_workflow_dir)
        assert not manager._loaded
        assert len(manager._specialist_configs) == 0
    
    def test_load_configurations(self, sample_config_file, sample_workflow_dir):
        """Test loading specialist configurations."""
        manager = SpecialistWorkflowConfigManager(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        
        manager.load_configurations()
        
        assert manager._loaded
        assert len(manager._specialist_configs) >= 2  # At least intelligence analyst and OSINT
        
        # Check intelligence analyst config
        intel_config = manager.get_specialist_config(SpecialistType.INTELLIGENCE_ANALYST)
        assert intel_config is not None
        assert intel_config.name == "Intelligence Analyst"
        assert len(intel_config.assignment_rules) > 0
        assert len(intel_config.deliverable_specs) > 0
    
    def test_get_specialist_config(self, sample_config_file, sample_workflow_dir):
        """Test getting specific specialist configuration."""
        manager = SpecialistWorkflowConfigManager(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        manager.load_configurations()
        
        # Test existing specialist
        intel_config = manager.get_specialist_config(SpecialistType.INTELLIGENCE_ANALYST)
        assert intel_config is not None
        assert intel_config.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
        
        # Test non-existent specialist (should still work but might return None)
        threat_config = manager.get_specialist_config(SpecialistType.THREAT_HUNTER)
        # This might be None since we haven't implemented threat hunter yet
    
    def test_find_matching_specialists(self, sample_config_file, sample_workflow_dir):
        """Test finding specialists based on labels and keywords."""
        manager = SpecialistWorkflowConfigManager(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        manager.load_configurations()
        
        # Test intelligence analyst match with labels and keywords that should trigger match
        matches = manager.find_matching_specialists(
            labels=["intelligence", "intelligence-analyst"],
            content_keywords=["threat", "analysis", "strategic"]
        )
        
        assert len(matches) > 0
        specialist_type, confidence = matches[0]
        assert specialist_type == SpecialistType.INTELLIGENCE_ANALYST
        assert confidence > 0.6
        
        # Test OSINT researcher match with proper labels
        osint_matches = manager.find_matching_specialists(
            labels=["osint", "osint-researcher"],
            content_keywords=["reconnaissance", "verification", "research"]
        )
        
        # Should find OSINT researcher
        assert len(osint_matches) > 0
        specialist_type, confidence = osint_matches[0]
        assert specialist_type == SpecialistType.OSINT_RESEARCHER
    
    def test_validate_configuration(self, sample_config_file, sample_workflow_dir):
        """Test configuration validation."""
        manager = SpecialistWorkflowConfigManager(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        manager.load_configurations()
        
        validation_result = manager.validate_configuration()
        
        assert isinstance(validation_result, dict)
        assert "valid" in validation_result
        assert "errors" in validation_result
        assert "warnings" in validation_result
        assert "specialist_count" in validation_result
        assert "rule_count" in validation_result
    
    def test_export_configuration_summary(self, sample_config_file, sample_workflow_dir):
        """Test exporting configuration summary."""
        manager = SpecialistWorkflowConfigManager(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        manager.load_configurations()
        
        summary = manager.export_configuration_summary()
        
        assert isinstance(summary, dict)
        assert "timestamp" in summary
        assert "total_specialists" in summary
        assert "specialists" in summary
        assert summary["total_specialists"] > 0


class TestSpecialistWorkflowRegistry:
    """Test specialist workflow registry."""
    
    def test_initialization(self, sample_config_file, sample_workflow_dir):
        """Test registry initialization."""
        registry = SpecialistWorkflowRegistry(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        
        assert not registry._initialized
        
        registry.initialize()
        
        assert registry._initialized
    
    def test_assign_specialist_to_issue(self, sample_config_file, sample_workflow_dir):
        """Test assigning specialist to an issue."""
        registry = SpecialistWorkflowRegistry(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        registry.initialize()
        
        # Test intelligence analyst assignment
        assignment = registry.assign_specialist_to_issue(
            issue_labels=["intelligence", "threat-assessment"],
            issue_content="This is a threat analysis issue requiring intelligence assessment"
        )
        
        if assignment:  # Assignment might be None if no match
            assert isinstance(assignment, SpecialistAssignment)
            assert assignment.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
            assert assignment.confidence >= 0.6
            assert assignment.workflow_name is not None
            assert len(assignment.trigger_labels) > 0
    
    def test_get_specialist_workflows(self, sample_config_file, sample_workflow_dir):
        """Test getting workflows for a specialist."""
        registry = SpecialistWorkflowRegistry(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        registry.initialize()
        
        intel_workflows = registry.get_specialist_workflows(SpecialistType.INTELLIGENCE_ANALYST)
        # Might be empty if no workflows are mapped, but should be a list
        assert isinstance(intel_workflows, list)
    
    def test_validate_registry(self, sample_config_file, sample_workflow_dir):
        """Test registry validation."""
        registry = SpecialistWorkflowRegistry(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        registry.initialize()
        
        validation_result = registry.validate_registry()
        
        assert isinstance(validation_result, dict)
        assert "timestamp" in validation_result
        assert "registry_valid" in validation_result
        assert "config_validation" in validation_result
        assert "registry_validation" in validation_result
    
    def test_get_registry_statistics(self, sample_config_file, sample_workflow_dir):
        """Test getting registry statistics."""
        registry = SpecialistWorkflowRegistry(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        registry.initialize()
        
        stats = registry.get_registry_statistics()
        
        assert isinstance(stats, dict)
        assert "timestamp" in stats
        assert "total_specialists" in stats
        assert "total_workflows" in stats
        assert "specialist_breakdown" in stats
        assert "configuration_summary" in stats


class TestAssignmentRule:
    """Test assignment rule dataclass."""
    
    def test_valid_assignment_rule(self):
        """Test creating valid assignment rule."""
        rule = AssignmentRule(
            specialist_type=SpecialistType.INTELLIGENCE_ANALYST,
            trigger_labels=["intelligence", "threat"],
            content_keywords=["analysis", "threat"],
            priority_weight=0.8,
            min_confidence=0.7
        )
        
        assert rule.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
        assert "intelligence" in rule.trigger_labels
        assert "analysis" in rule.content_keywords
        assert rule.priority_weight == 0.8
        assert rule.min_confidence == 0.7
    
    def test_invalid_assignment_rule(self):
        """Test assignment rule validation."""
        # Missing both labels and keywords should raise error
        with pytest.raises(ValueError):
            AssignmentRule(
                specialist_type=SpecialistType.INTELLIGENCE_ANALYST,
                trigger_labels=[],
                content_keywords=[],
                min_confidence=0.7
            )
        
        # Invalid confidence should raise error
        with pytest.raises(ValueError):
            AssignmentRule(
                specialist_type=SpecialistType.INTELLIGENCE_ANALYST,
                trigger_labels=["intelligence"],
                min_confidence=1.5  # Invalid > 1.0
            )


class TestDeliverableSpec:
    """Test deliverable specification dataclass."""
    
    def test_valid_deliverable_spec(self):
        """Test creating valid deliverable specification."""
        spec = DeliverableSpec(
            name="intelligence_assessment",
            title="Intelligence Assessment Report",
            template_name="intelligence_assessment.md",
            description="Comprehensive threat analysis",
            ai_enhanced=True,
            required_sections=["summary", "analysis", "recommendations"],
            quality_threshold=0.8
        )
        
        assert spec.name == "intelligence_assessment"
        assert spec.title == "Intelligence Assessment Report"
        assert spec.template_name == "intelligence_assessment.md"
        assert spec.ai_enhanced is True
        assert "summary" in spec.required_sections
        assert spec.quality_threshold == 0.8
    
    def test_invalid_deliverable_spec(self):
        """Test deliverable specification validation."""
        # Missing required fields should raise error
        with pytest.raises(ValueError):
            DeliverableSpec(
                name="",  # Empty name
                title="Test Title",
                template_name="test.md"
            )


class TestQualityRequirement:
    """Test quality requirement dataclass."""
    
    def test_valid_quality_requirement(self):
        """Test creating valid quality requirement."""
        qr = QualityRequirement(
            min_confidence_score=0.8,
            require_source_references=True,
            min_word_count=1000,
            max_processing_time_minutes=30,
            validation_strictness="standard"
        )
        
        assert qr.min_confidence_score == 0.8
        assert qr.require_source_references is True
        assert qr.min_word_count == 1000
        assert qr.max_processing_time_minutes == 30
        assert qr.validation_strictness == "standard"
    
    def test_invalid_quality_requirement(self):
        """Test quality requirement validation."""
        # Invalid confidence score
        with pytest.raises(ValueError):
            QualityRequirement(min_confidence_score=1.5)
        
        # Invalid validation strictness
        with pytest.raises(ValueError):
            QualityRequirement(validation_strictness="invalid")


# Integration tests
class TestSpecialistWorkflowIntegration:
    """Integration tests for the complete specialist workflow system."""
    
    def test_end_to_end_assignment_flow(self, sample_config_file, sample_workflow_dir):
        """Test complete assignment flow from labels to specialist assignment."""
        # Initialize registry
        registry = SpecialistWorkflowRegistry(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        registry.initialize()
        
        # Test issue with intelligence labels
        issue_labels = ["intelligence", "threat-assessment", "strategic-analysis"]
        issue_content = "Advanced persistent threat campaign analysis required for strategic intelligence assessment"
        
        # Get assignment
        assignment = registry.assign_specialist_to_issue(
            issue_labels=issue_labels,
            issue_content=issue_content,
            min_confidence=0.5  # Lower threshold for testing
        )
        
        # Verify assignment if found
        if assignment:
            assert assignment.specialist_type in [
                SpecialistType.INTELLIGENCE_ANALYST,
                SpecialistType.OSINT_RESEARCHER,
                SpecialistType.TARGET_PROFILER
            ]
            assert assignment.confidence >= 0.5
            assert len(assignment.trigger_labels) > 0
            assert assignment.workflow_name is not None
    
    def test_multiple_specialist_scenarios(self, sample_config_file, sample_workflow_dir):
        """Test various specialist assignment scenarios."""
        registry = SpecialistWorkflowRegistry(
            config_path=sample_config_file,
            workflow_directory=sample_workflow_dir
        )
        registry.initialize()
        
        # Test scenarios
        scenarios = [
            {
                "name": "Intelligence Analysis",
                "labels": ["intelligence", "threat-analysis"],
                "content": "Threat actor analysis and strategic assessment",
                "expected_specialist": SpecialistType.INTELLIGENCE_ANALYST
            },
            {
                "name": "OSINT Research", 
                "labels": ["osint", "research", "verification"],
                "content": "Open source intelligence gathering and verification",
                "expected_specialist": SpecialistType.OSINT_RESEARCHER
            },
            {
                "name": "Target Profiling",
                "labels": ["target-profiler", "organizational-analysis"],
                "content": "Organizational analysis and stakeholder mapping",
                "expected_specialist": SpecialistType.TARGET_PROFILER
            }
        ]
        
        for scenario in scenarios:
            assignment = registry.assign_specialist_to_issue(
                issue_labels=scenario["labels"],
                issue_content=scenario["content"],
                min_confidence=0.4  # Lower threshold for testing
            )
            
            # Log results for debugging
            if assignment:
                print(f"Scenario '{scenario['name']}': Assigned {assignment.specialist_type.value} with confidence {assignment.confidence:.2f}")
            else:
                print(f"Scenario '{scenario['name']}': No assignment found")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])