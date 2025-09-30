"""
Unit tests for the Specialist Agent Framework.

Tests the base SpecialistAgent class, AnalysisResult data structures,
and SpecialistRegistry system.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.agents.specialist_agents import (
    SpecialistType,
    AnalysisStatus,
    AnalysisResult,
    SpecialistAgent,
    SpecialistRegistry,
    get_specialist_registry,
    get_specialist
)


class TestAnalysisResult:
    """Test AnalysisResult data structure."""
    
    def test_analysis_result_creation(self):
        """Test basic AnalysisResult creation and properties."""
        result = AnalysisResult(
            specialist_type=SpecialistType.INTELLIGENCE_ANALYST,
            issue_number=123,
            analysis_id="test-analysis-001",
            summary="Test analysis summary"
        )
        
        assert result.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
        assert result.issue_number == 123
        assert result.analysis_id == "test-analysis-001"
        assert result.summary == "Test analysis summary"
        assert result.status == AnalysisStatus.PENDING
        assert result.confidence_score == 0.0
        assert len(result.key_findings) == 0
        assert len(result.recommendations) == 0
    
    def test_mark_completed(self):
        """Test marking analysis as completed."""
        result = AnalysisResult(
            specialist_type=SpecialistType.OSINT_RESEARCHER,
            issue_number=456,
            analysis_id="test-analysis-002",
            summary="OSINT analysis"
        )
        
        processing_time = 15.5
        result.mark_completed(processing_time=processing_time)
        
        assert result.status == AnalysisStatus.COMPLETED
        assert result.completed_at is not None
        assert result.processing_time_seconds == processing_time
        assert (datetime.utcnow() - result.completed_at).seconds < 5  # Recent completion
    
    def test_mark_failed(self):
        """Test marking analysis as failed."""
        result = AnalysisResult(
            specialist_type=SpecialistType.THREAT_HUNTER,
            issue_number=789,
            analysis_id="test-analysis-003",
            summary="Threat hunting analysis"
        )
        
        error_msg = "AI analysis service unavailable"
        result.mark_failed(error_msg)
        
        assert result.status == AnalysisStatus.FAILED
        assert result.error_message == error_msg
        assert result.completed_at is not None
    
    def test_to_dict_serialization(self):
        """Test conversion to dictionary format."""
        result = AnalysisResult(
            specialist_type=SpecialistType.BUSINESS_ANALYST,
            issue_number=101,
            analysis_id="biz-analysis-001",
            summary="Business impact analysis",
            key_findings=["Finding 1", "Finding 2"],
            recommendations=["Recommendation 1"],
            confidence_score=0.85
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["specialist_type"] == "business-analyst"
        assert result_dict["issue_number"] == 101
        assert result_dict["analysis_id"] == "biz-analysis-001"
        assert result_dict["summary"] == "Business impact analysis"
        assert result_dict["key_findings"] == ["Finding 1", "Finding 2"]
        assert result_dict["recommendations"] == ["Recommendation 1"]
        assert result_dict["confidence_score"] == 0.85
        assert result_dict["status"] == "pending"


class MockSpecialistAgent(SpecialistAgent):
    """Mock specialist agent for testing."""
    
    @property
    def specialist_type(self) -> SpecialistType:
        return SpecialistType.INTELLIGENCE_ANALYST
    
    @property
    def supported_labels(self) -> List[str]:
        return ["intelligence", "threat", "analysis", "security"]
    
    @property
    def required_capabilities(self) -> List[str]:
        return ["content_extraction", "threat_analysis"]
    
    def analyze_issue(self, issue_data: Dict[str, Any], extracted_content=None) -> AnalysisResult:
        result = self.create_analysis_result(issue_data.get('number', 0))
        result.summary = f"Mock analysis of issue {issue_data.get('number', 'unknown')}"
        result.confidence_score = 0.9
        result.mark_completed()
        return result
    
    def validate_issue_compatibility(self, issue_data: Dict[str, Any]) -> bool:
        labels = [label.get('name', '') if isinstance(label, dict) else str(label) 
                 for label in issue_data.get('labels', [])]
        return any(label in self.supported_labels for label in labels)


class TestSpecialistAgent:
    """Test SpecialistAgent base class functionality."""
    
    def test_specialist_agent_initialization(self):
        """Test specialist agent creation with configuration."""
        config = {"max_entities": 50, "confidence_threshold": 0.7}
        agent = MockSpecialistAgent(config=config)
        
        assert agent.config == config
        assert agent.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
        assert "intelligence" in agent.supported_labels
        assert "content_extraction" in agent.required_capabilities
    
    def test_get_analysis_priority_with_matching_labels(self):
        """Test priority calculation with matching labels."""
        agent = MockSpecialistAgent()
        
        issue_data = {
            "number": 123,
            "labels": ["intelligence", "threat", "urgent"]
        }
        
        priority = agent.get_analysis_priority(issue_data)
        assert priority > 0  # Should have some priority due to matching labels
    
    def test_get_analysis_priority_with_specialist_type_match(self):
        """Test priority calculation with exact specialist type match."""
        agent = MockSpecialistAgent()
        
        issue_data = {
            "number": 123,
            "labels": ["intelligence-analyst", "analysis"]
        }
        
        priority = agent.get_analysis_priority(issue_data)
        assert priority >= 50  # Should get bonus for specialist type match
    
    def test_get_analysis_priority_no_match(self):
        """Test priority calculation with no matching labels."""
        agent = MockSpecialistAgent()
        
        issue_data = {
            "number": 123,
            "labels": ["documentation", "enhancement"]
        }
        
        priority = agent.get_analysis_priority(issue_data)
        assert priority == 0  # No matching labels
    
    def test_create_analysis_result(self):
        """Test analysis result creation with auto-generated ID."""
        agent = MockSpecialistAgent()
        
        result = agent.create_analysis_result(issue_number=456)
        
        assert result.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
        assert result.issue_number == 456
        assert result.analysis_id.startswith("intelligence-analyst-456-")
        assert result.status == AnalysisStatus.PENDING
    
    def test_create_analysis_result_with_custom_id(self):
        """Test analysis result creation with custom ID."""
        agent = MockSpecialistAgent()
        
        custom_id = "custom-analysis-789"
        result = agent.create_analysis_result(issue_number=789, analysis_id=custom_id)
        
        assert result.analysis_id == custom_id
        assert result.issue_number == 789
    
    def test_validate_issue_compatibility_positive(self):
        """Test issue compatibility validation - compatible case."""
        agent = MockSpecialistAgent()
        
        issue_data = {
            "number": 123,
            "title": "Security threat analysis needed",
            "labels": ["intelligence", "security"]
        }
        
        assert agent.validate_issue_compatibility(issue_data) is True
    
    def test_validate_issue_compatibility_negative(self):
        """Test issue compatibility validation - incompatible case."""
        agent = MockSpecialistAgent()
        
        issue_data = {
            "number": 123,
            "title": "Documentation update",
            "labels": ["documentation", "minor"]
        }
        
        assert agent.validate_issue_compatibility(issue_data) is False


class TestSpecialistRegistry:
    """Test SpecialistRegistry functionality."""
    
    def test_registry_initialization(self):
        """Test registry creation."""
        registry = SpecialistRegistry()
        
        assert isinstance(registry, SpecialistRegistry)
        assert len(registry.get_registered_types()) >= 0  # May have auto-loaded specialists
    
    def test_register_and_get_specialist(self):
        """Test registering and retrieving a specialist."""
        registry = SpecialistRegistry()
        
        # Register mock specialist
        registry.register_specialist(MockSpecialistAgent)
        
        # Retrieve the specialist
        specialist = registry.get_specialist(SpecialistType.INTELLIGENCE_ANALYST)
        
        assert specialist is not None
        assert isinstance(specialist, MockSpecialistAgent)
        assert specialist.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
    
    def test_get_specialist_with_config(self):
        """Test getting specialist with custom configuration."""
        registry = SpecialistRegistry()
        registry.register_specialist(MockSpecialistAgent)
        
        config = {"custom_setting": "test_value"}
        specialist = registry.get_specialist(
            SpecialistType.INTELLIGENCE_ANALYST, 
            config=config,
            create_new=True
        )
        
        assert specialist is not None
        assert specialist.config == config
    
    def test_get_specialist_string_type(self):
        """Test getting specialist using string type."""
        registry = SpecialistRegistry()
        registry.register_specialist(MockSpecialistAgent)
        
        specialist = registry.get_specialist("intelligence-analyst")
        
        assert specialist is not None
        assert specialist.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
    
    def test_get_specialist_invalid_type(self):
        """Test getting specialist with invalid type."""
        registry = SpecialistRegistry()
        
        specialist = registry.get_specialist("invalid-specialist-type")
        
        assert specialist is None
    
    def test_get_suitable_specialists(self):
        """Test finding suitable specialists for an issue."""
        registry = SpecialistRegistry()
        registry.register_specialist(MockSpecialistAgent)
        
        issue_data = {
            "number": 123,
            "title": "Security intelligence analysis",
            "labels": ["intelligence", "threat"]
        }
        
        suitable = registry.get_suitable_specialists(issue_data)
        
        assert len(suitable) > 0
        assert all(isinstance(s, SpecialistAgent) for s in suitable)
        assert all(s.validate_issue_compatibility(issue_data) for s in suitable)
    
    def test_get_suitable_specialists_with_priority_filter(self):
        """Test finding suitable specialists with minimum priority."""
        registry = SpecialistRegistry()
        registry.register_specialist(MockSpecialistAgent)
        
        issue_data = {
            "number": 123,
            "labels": ["intelligence"]  # Should match MockSpecialistAgent
        }
        
        # Should find specialists with default min_priority=1
        suitable = registry.get_suitable_specialists(issue_data, min_priority=1)
        assert len(suitable) > 0
        
        # Should find no specialists with very high min_priority
        suitable_high_priority = registry.get_suitable_specialists(issue_data, min_priority=99)
        assert len(suitable_high_priority) == 0
    
    def test_get_registered_types(self):
        """Test getting list of registered specialist types."""
        registry = SpecialistRegistry()
        initial_count = len(registry.get_registered_types())
        
        # Since MockSpecialistAgent uses same type as IntelligenceAnalyst,
        # registering it will overwrite the existing registration
        registry.register_specialist(MockSpecialistAgent)
        
        types = registry.get_registered_types()
        # Count should be the same since we're overwriting, not adding new
        assert len(types) == initial_count
        assert SpecialistType.INTELLIGENCE_ANALYST in types


class TestGlobalRegistry:
    """Test global registry functions."""
    
    def test_get_specialist_registry_singleton(self):
        """Test that global registry returns same instance."""
        registry1 = get_specialist_registry()
        registry2 = get_specialist_registry()
        
        assert registry1 is registry2
        assert isinstance(registry1, SpecialistRegistry)
    
    def test_get_specialist_convenience_function(self):
        """Test convenience function for getting specialists."""
        # Register a specialist in global registry
        global_registry = get_specialist_registry()
        global_registry.register_specialist(MockSpecialistAgent)
        
        # Use convenience function
        specialist = get_specialist(SpecialistType.INTELLIGENCE_ANALYST)
        
        assert specialist is not None
        assert isinstance(specialist, MockSpecialistAgent)
    
    def test_get_specialist_with_config_convenience(self):
        """Test convenience function with config."""
        global_registry = get_specialist_registry()
        global_registry.register_specialist(MockSpecialistAgent)
        
        config = {"test_config": "value"}
        specialist = get_specialist("intelligence-analyst", config=config)
        
        assert specialist is not None
        assert specialist.config == config


class TestSpecialistTypes:
    """Test SpecialistType enum values."""
    
    def test_specialist_type_values(self):
        """Test that all expected specialist types are defined."""
        expected_types = {
            "intelligence-analyst",
            "osint-researcher", 
            "target-profiler",
            "threat-hunter",
            "business-analyst"
        }
        
        actual_types = {st.value for st in SpecialistType}
        
        assert expected_types == actual_types
    
    def test_specialist_type_from_string(self):
        """Test creating SpecialistType from string."""
        st = SpecialistType("intelligence-analyst")
        assert st == SpecialistType.INTELLIGENCE_ANALYST
        
        with pytest.raises(ValueError):
            SpecialistType("invalid-type")


class TestAnalysisStatus:
    """Test AnalysisStatus enum values."""
    
    def test_analysis_status_values(self):
        """Test that all expected analysis statuses are defined."""
        expected_statuses = {
            "pending",
            "in_progress", 
            "completed",
            "failed",
            "skipped"
        }
        
        actual_statuses = {status.value for status in AnalysisStatus}
        
        assert expected_statuses == actual_statuses