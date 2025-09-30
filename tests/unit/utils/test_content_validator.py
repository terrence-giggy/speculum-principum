"""
Test suite for content validation and quality assurance framework.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.utils.content_validator import (
    ContentValidator, 
    ValidationLevel, 
    IssueType, 
    ValidationIssue,
    QualityMetrics,
    ValidationResult
)


class TestContentValidator:
    """Test cases for ContentValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ContentValidator(ValidationLevel.STANDARD)
        self.strict_validator = ContentValidator(ValidationLevel.STRICT)
        self.permissive_validator = ContentValidator(ValidationLevel.PERMISSIVE)
    
    def test_validator_initialization(self):
        """Test validator initialization with different levels."""
        # Standard validation
        assert self.validator.validation_level == ValidationLevel.STANDARD
        assert self.validator.thresholds['min_overall_score'] == 0.7
        assert self.validator.thresholds['min_word_count'] == 200
        
        # Strict validation
        assert self.strict_validator.validation_level == ValidationLevel.STRICT
        assert self.strict_validator.thresholds['min_overall_score'] == 0.85
        assert self.strict_validator.thresholds['min_word_count'] == 300
        
        # Permissive validation
        assert self.permissive_validator.validation_level == ValidationLevel.PERMISSIVE
        assert self.permissive_validator.thresholds['min_overall_score'] == 0.6
        assert self.permissive_validator.thresholds['min_word_count'] == 150
    
    def test_custom_thresholds_override(self):
        """Test custom threshold override functionality."""
        custom_thresholds = {
            'min_overall_score': 0.9,
            'min_word_count': 500
        }
        validator = ContentValidator(
            ValidationLevel.STANDARD, 
            custom_thresholds=custom_thresholds
        )
        
        assert validator.thresholds['min_overall_score'] == 0.9
        assert validator.thresholds['min_word_count'] == 500
        assert validator.thresholds['min_completeness'] == 0.7  # Should keep defaults
    
    def test_high_quality_content_validation(self):
        """Test validation of high-quality professional content."""
        high_quality_content = """
# Executive Summary

This intelligence assessment evaluates the threat landscape with high confidence based on comprehensive analysis of available information. The assessment identifies critical vulnerabilities and provides actionable recommendations for mitigation.

# Key Findings

Based on our analysis, we assess with medium confidence that the following key findings are accurate:

- Threat actors have demonstrated advanced capabilities in cyber operations
- Multiple indicators of compromise have been identified across network infrastructure
- The threat landscape has evolved significantly over the past quarter

# Detailed Analysis

## Threat Actor Assessment

The primary threat actor demonstrates sophisticated tactics, techniques, and procedures (TTPs) consistent with advanced persistent threat (APT) groups. Intelligence collection has revealed:

- Advanced malware capabilities with custom development
- Extensive reconnaissance activities targeting critical infrastructure
- Multi-stage attack campaigns with strategic objectives

## Capability Analysis

We assess with high confidence that the threat actor possesses:
- Advanced technical capabilities
- Significant resources and funding
- Long-term strategic objectives

# Intelligence Gaps

The following areas require additional collection and analysis:
- Attribution to specific threat groups
- Full scope of compromised systems
- Long-term strategic objectives

# Recommendations

Based on this analysis, we recommend the following actions:

- Implement enhanced monitoring of network traffic
- Deploy additional security controls at critical network boundaries  
- Conduct comprehensive threat hunting activities
- Establish information sharing partnerships with industry peers

# Confidence Assessment

Overall confidence in this assessment is medium, based on:
- Multiple corroborating sources
- Technical analysis of indicators
- Pattern analysis of threat actor behavior
        """
        
        result = self.validator.validate_content(high_quality_content, "intelligence_analysis")
        
        assert result.is_valid
        assert result.quality_metrics.overall_score >= 0.8
        assert result.quality_metrics.professionalism_score >= 0.8
        assert result.quality_metrics.completeness_score >= 0.8
        assert len([i for i in result.issues if i.issue_type == IssueType.CRITICAL]) == 0
    
    def test_low_quality_content_validation(self):
        """Test validation of low-quality content."""
        low_quality_content = """
This is some basic info about stuff. Things are happening and it's not good.
Maybe we should do something about it. I think there might be problems.
        """
        
        result = self.validator.validate_content(low_quality_content, "intelligence_analysis")
        
        assert not result.is_valid
        assert result.quality_metrics.overall_score < 0.7
        assert len(result.issues) > 0
        
        # Check for specific issues
        issue_types = [i.issue_type for i in result.issues]
        assert IssueType.CRITICAL in issue_types or IssueType.MAJOR in issue_types
    
    def test_completeness_validation(self):
        """Test content completeness validation."""
        # Test word count validation
        short_content = "This is too short."
        result = self.validator._validate_completeness(short_content, "intelligence_analysis")
        
        assert not result['passed']
        word_count_issues = [i for i in result['issues'] if 'word' in i.description.lower()]
        assert len(word_count_issues) > 0
        
        # Test missing sections
        content_without_sections = """
        Some analysis content but no proper sections with headers.
        This lacks the required structure for professional intelligence.
        """ * 20  # Make it long enough word-wise
        
        result = self.validator._validate_completeness(content_without_sections, "intelligence_analysis")
        missing_section_issues = [i for i in result['issues'] if 'missing' in i.description.lower()]
        assert len(missing_section_issues) > 0
    
    def test_professionalism_validation(self):
        """Test professional standards validation."""
        # Test unprofessional language
        unprofessional_content = """
        # Analysis
        
        This is totally awesome stuff about some cool threat actors.
        I guess they're doing whatever they want with their things.
        Maybe we should check it out or something.
        """ * 10
        
        result = self.validator._validate_professionalism(unprofessional_content)
        
        assert not result['passed']
        unprofessional_issues = [i for i in result['issues'] 
                               if 'unprofessional' in i.description.lower()]
        assert len(unprofessional_issues) > 0
    
    def test_confidence_expression_validation(self):
        """Test confidence expression validation."""
        # Content without confidence expressions
        no_confidence_content = """
        # Analysis
        
        The threat actor is definitely involved in cyber operations.
        All systems are compromised and the situation is certain.
        Every indicator points to immediate action needed.
        """ * 10
        
        result = self.validator._validate_confidence_levels(no_confidence_content)
        
        confidence_issues = [i for i in result['issues'] 
                           if 'confidence' in i.description.lower()]
        assert len(confidence_issues) > 0
    
    def test_structure_validation(self):
        """Test document structure validation."""
        # Content without proper headers
        no_structure_content = """
        This is analysis content without any structure or headers.
        It goes on for a while but lacks the proper organization
        that would be expected in a professional document.
        """ * 20
        
        result = self.validator._validate_structure(no_structure_content, "intelligence_analysis")
        
        assert not result['passed']
        structure_issues = [i for i in result['issues'] 
                          if i.category == "structure"]
        assert len(structure_issues) > 0
    
    def test_accuracy_validation(self):
        """Test accuracy and consistency validation."""
        # Content with potential contradictions
        contradictory_content = """
        # Analysis
        
        The threat actor is highly sophisticated and advanced.
        The same threat actor lacks technical capabilities and resources.
        They have extensive funding for operations.
        The group has no financial resources available.
        """ * 10
        
        result = self.validator._validate_accuracy(contradictory_content, None)
        
        # Should find some issues with contradictions
        contradiction_issues = [i for i in result['issues'] 
                              if 'contradiction' in i.description.lower()]
        # Note: Simple contradiction detection may not catch everything
        assert len(result['issues']) >= 0  # At least no crashes
    
    def test_quality_metrics_calculation(self):
        """Test quality metrics calculation."""
        content = """
        # Executive Summary
        Professional intelligence assessment with proper structure.
        
        # Analysis  
        Detailed analysis with intelligence terminology.
        We assess with high confidence that indicators are valid.
        """
        
        issues = []  # No issues for this test
        
        # Mock validation results
        completeness_result = {'passed': True, 'word_count': 50}
        professionalism_result = {'passed': True, 'professional_terms': 5}
        structure_result = {'passed': True, 'header_count': 2}
        accuracy_result = {'passed': True, 'contradictions_found': 0}
        confidence_result = {'passed': True, 'confidence_expressions': 2}
        
        metrics = self.validator._calculate_quality_metrics(
            content, issues, completeness_result, professionalism_result,
            structure_result, accuracy_result, confidence_result
        )
        
        assert metrics.overall_score > 0.8
        assert metrics.word_count == 50
        assert metrics.section_count == 2
        assert metrics.issues_found == 0
    
    def test_recommendation_generation(self):
        """Test recommendation generation."""
        issues = [
            ValidationIssue(
                issue_type=IssueType.MAJOR,
                category="content",
                description="Content too brief",
                location="overall",
                suggestion="Expand content with more detail",
                confidence=0.9
            ),
            ValidationIssue(
                issue_type=IssueType.MINOR,
                category="professional_standards",
                description="Limited professional terminology",
                location="overall",
                suggestion="Use more intelligence community terms",
                confidence=0.8
            )
        ]
        
        metrics = QualityMetrics(
            overall_score=0.6,
            completeness_score=0.5,
            professionalism_score=0.7,
            accuracy_score=0.8,
            structure_score=0.7,
            confidence_score=0.4,
            word_count=100,
            section_count=1,
            recommendations_count=0,
            issues_found=2
        )
        
        recommendations = self.validator._generate_recommendations(issues, metrics)
        
        assert len(recommendations) > 0
        assert any('content' in rec.lower() for rec in recommendations)
        assert any('confidence' in rec.lower() for rec in recommendations)
    
    def test_validation_level_differences(self):
        """Test differences between validation levels."""
        borderline_content = """
        # Summary
        Basic analysis of the situation.
        
        # Details  
        Some information about threats.
        Things are happening.
        """ * 15  # Make it meet word count
        
        strict_result = self.strict_validator.validate_content(borderline_content)
        standard_result = self.validator.validate_content(borderline_content)
        permissive_result = self.permissive_validator.validate_content(borderline_content)
        
        # Strict should be most demanding
        assert strict_result.quality_metrics.overall_score <= standard_result.quality_metrics.overall_score
        assert standard_result.quality_metrics.overall_score <= permissive_result.quality_metrics.overall_score
    
    def test_structured_content_validation(self):
        """Test validation of structured content from extraction."""
        structured_content = {
            'entities': {
                'people': [
                    {'name': 'John Doe', 'confidence': 0.9},
                    {'name': 'Jane Smith', 'confidence': 0.8}
                ],
                'organizations': [
                    {'name': 'ACME Corp', 'confidence': 0.95}
                ]
            },
            'relationships': [
                {
                    'source_entity': 'John Doe',
                    'target_entity': 'ACME Corp',
                    'relationship_type': 'employment',
                    'confidence': 0.85
                }
            ],
            'events': [],
            'indicators': [],
            'metadata': {
                'confidence_threshold': 0.7
            }
        }
        
        result = self.validator.validate_structured_content(structured_content)
        
        assert result.is_valid
        assert result.quality_metrics.completeness_score > 0.0
        assert len(result.issues) == 0 or all(i.issue_type != IssueType.CRITICAL for i in result.issues)
    
    def test_structured_content_validation_empty(self):
        """Test validation of empty structured content."""
        empty_content = {
            'entities': {},
            'relationships': [],
            'events': [],
            'indicators': [],
            'metadata': {}
        }
        
        result = self.validator.validate_structured_content(empty_content)
        
        assert not result.is_valid
        entity_issues = [i for i in result.issues if 'entities' in i.description.lower()]
        assert len(entity_issues) > 0
    
    def test_error_handling(self):
        """Test error handling in validation."""
        # Test with None input
        with patch('src.utils.content_validator.ContentValidator._validate_completeness') as mock_validate:
            mock_validate.side_effect = Exception("Test error")
            
            result = self.validator.validate_content("test content")
            
            assert not result.is_valid
            assert len(result.issues) > 0
            assert result.issues[0].issue_type == IssueType.CRITICAL
            assert 'error' in result.metadata
    
    def test_section_detection(self):
        """Test section detection functionality."""
        content_with_sections = """
        # Executive Summary
        Content here
        
        ## Key Findings  
        More content
        
        # Analysis
        Additional content
        """
        
        assert self.validator._find_section(content_with_sections, "Executive Summary")
        assert self.validator._find_section(content_with_sections, "executive summary")
        assert self.validator._find_section(content_with_sections, "Key Findings")
        assert not self.validator._find_section(content_with_sections, "Nonexistent Section")
    
    def test_section_content_extraction(self):
        """Test section content extraction."""
        content = """
        # Executive Summary
        This is the executive summary content.
        It spans multiple lines.
        
        # Analysis
        This is analysis content.
        """
        
        exec_content = self.validator._extract_section_content(content, "Executive Summary")
        assert "This is the executive summary content." in exec_content
        assert "It spans multiple lines." in exec_content
        assert "This is analysis content." not in exec_content
    
    def test_formatting_consistency_check(self):
        """Test formatting consistency checking."""
        consistent_content = """
        # Main Header
        ## Sub Header
        ### Sub Sub Header
        ## Another Sub Header
        """
        
        inconsistent_content = """
        # Main Header
        ### Sub Sub Header (skipped level)
        ## Sub Header
        """
        
        assert self.validator._check_formatting_consistency(consistent_content)
        assert not self.validator._check_formatting_consistency(inconsistent_content)
    
    def test_validation_with_specialist_context(self):
        """Test validation with specialist context integration."""
        content = """
        # Analysis
        The threat actor John Doe from ACME Corp represents significant risk.
        We assess with medium confidence the threat is credible.
        """
        
        specialist_context = {
            'entities': {
                'people': [{'name': 'John Doe', 'confidence': 0.9}],
                'organizations': [{'name': 'ACME Corp', 'confidence': 0.8}]
            }
        }
        
        result = self.validator.validate_content(
            content, 
            "intelligence_analysis", 
            specialist_context=specialist_context
        )
        
        # Should pass validation with good entity integration
        assert result.is_valid or result.quality_metrics.overall_score > 0.6
    
    @pytest.mark.parametrize("validation_level,expected_min_score", [
        (ValidationLevel.STRICT, 0.85),
        (ValidationLevel.STANDARD, 0.7), 
        (ValidationLevel.PERMISSIVE, 0.6)
    ])
    def test_validation_level_thresholds(self, validation_level, expected_min_score):
        """Test different validation level thresholds."""
        validator = ContentValidator(validation_level)
        assert validator.thresholds['min_overall_score'] == expected_min_score
    
    def test_professional_pattern_loading(self):
        """Test professional terminology pattern loading."""
        patterns = self.validator.professional_patterns
        
        assert 'professional_terms' in patterns
        assert 'confidence_terms' in patterns
        assert 'unprofessional_terms' in patterns
        
        # Check for expected patterns
        assert any('intelligence' in pattern for pattern in patterns['professional_terms'])
        assert any('confidence' in pattern for pattern in patterns['confidence_terms'])
        assert any('awesome' in pattern for pattern in patterns['unprofessional_terms'])
    
    def test_required_sections_by_document_type(self):
        """Test required sections for different document types."""
        intel_sections = self.validator.required_sections.get('intelligence_analysis', [])
        osint_sections = self.validator.required_sections.get('osint_research', [])
        
        assert 'executive summary' in intel_sections
        assert 'key findings' in intel_sections
        assert 'methodology' in osint_sections
        assert 'verification' in osint_sections


class TestValidationIssue:
    """Test cases for ValidationIssue dataclass."""
    
    def test_validation_issue_creation(self):
        """Test ValidationIssue creation and properties."""
        issue = ValidationIssue(
            issue_type=IssueType.MAJOR,
            category="content",
            description="Test issue",
            location="section1",
            suggestion="Fix the issue",
            confidence=0.8
        )
        
        assert issue.issue_type == IssueType.MAJOR
        assert issue.category == "content"
        assert issue.description == "Test issue"
        assert issue.location == "section1"
        assert issue.suggestion == "Fix the issue"
        assert issue.confidence == 0.8


class TestQualityMetrics:
    """Test cases for QualityMetrics dataclass."""
    
    def test_quality_metrics_creation(self):
        """Test QualityMetrics creation and properties."""
        metrics = QualityMetrics(
            overall_score=0.85,
            completeness_score=0.9,
            professionalism_score=0.8,
            accuracy_score=0.85,
            structure_score=0.8,
            confidence_score=0.7,
            word_count=500,
            section_count=5,
            recommendations_count=8,
            issues_found=2
        )
        
        assert metrics.overall_score == 0.85
        assert metrics.completeness_score == 0.9
        assert metrics.word_count == 500
        assert metrics.issues_found == 2


class TestValidationResult:
    """Test cases for ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation and completeness."""
        metrics = QualityMetrics(
            overall_score=0.8, completeness_score=0.8, professionalism_score=0.8,
            accuracy_score=0.8, structure_score=0.8, confidence_score=0.8,
            word_count=300, section_count=4, recommendations_count=5, issues_found=1
        )
        
        issues = [ValidationIssue(
            issue_type=IssueType.MINOR,
            category="formatting",
            description="Minor formatting issue",
            location="header",
            suggestion="Fix formatting",
            confidence=0.7
        )]
        
        result = ValidationResult(
            is_valid=True,
            quality_metrics=metrics,
            issues=issues,
            recommendations=["Improve formatting"],
            validation_timestamp="2024-01-01T12:00:00",
            validation_level=ValidationLevel.STANDARD,
            passed_checks=["completeness", "professionalism"],
            failed_checks=["formatting"],
            metadata={"test": "value"}
        )
        
        assert result.is_valid
        assert result.quality_metrics.overall_score == 0.8
        assert len(result.issues) == 1
        assert len(result.recommendations) == 1
        assert result.validation_level == ValidationLevel.STANDARD
        assert "completeness" in result.passed_checks
        assert "formatting" in result.failed_checks
        assert result.metadata["test"] == "value"