"""
Content validation and quality assurance framework for intelligence analysis.

This module provides comprehensive content validation for AI-generated analysis,
ensuring professional standards, completeness, and reliability before delivery.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from .logging_config import get_logger, log_exception


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"
    STANDARD = "standard"
    PERMISSIVE = "permissive"


class IssueType(Enum):
    """Types of content quality issues."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    """Represents a content validation issue."""
    issue_type: IssueType
    category: str  # content, formatting, structure, professional_standards
    description: str
    location: Optional[str]  # section, line, etc.
    suggestion: Optional[str]  # how to fix
    confidence: float  # confidence in this being an issue (0.0-1.0)


@dataclass
class QualityMetrics:
    """Quality metrics for content assessment."""
    overall_score: float  # 0.0-1.0
    completeness_score: float
    professionalism_score: float
    accuracy_score: float
    structure_score: float
    confidence_score: float
    word_count: int
    section_count: int
    recommendations_count: int
    issues_found: int


@dataclass
class ValidationResult:
    """Complete validation result."""
    is_valid: bool
    quality_metrics: QualityMetrics
    issues: List[ValidationIssue]
    recommendations: List[str]
    validation_timestamp: str
    validation_level: ValidationLevel
    passed_checks: List[str]
    failed_checks: List[str]
    metadata: Dict[str, Any]


class ContentValidator:
    """
    Comprehensive content validation and quality assurance system.
    
    Validates AI-generated intelligence analysis for professional standards,
    completeness, structure, and reliability.
    """
    
    def __init__(self, 
                 validation_level: ValidationLevel = ValidationLevel.STANDARD,
                 custom_thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize content validator.
        
        Args:
            validation_level: Strictness level for validation
            custom_thresholds: Custom quality thresholds override
        """
        self.logger = get_logger(__name__)
        self.validation_level = validation_level
        
        # Default quality thresholds by validation level
        self.thresholds = self._get_default_thresholds(validation_level)
        if custom_thresholds:
            self.thresholds.update(custom_thresholds)
        
        # Professional standards patterns
        self.professional_patterns = self._load_professional_patterns()
        
        # Required sections for different document types
        self.required_sections = self._get_required_sections()
    
    def validate_content(self, 
                        content: str,
                        document_type: str = "intelligence_analysis",
                        specialist_context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Perform comprehensive content validation.
        
        Args:
            content: Content to validate
            document_type: Type of document being validated
            specialist_context: Context from specialist analysis
            
        Returns:
            ValidationResult with quality metrics and issues
        """
        try:
            self.logger.info(f"Starting validation for {document_type} document")
            
            issues = []
            passed_checks = []
            failed_checks = []
            
            # Run validation checks
            completeness_result = self._validate_completeness(content, document_type)
            issues.extend(completeness_result['issues'])
            (passed_checks if completeness_result['passed'] else failed_checks).append('completeness')
            
            professionalism_result = self._validate_professionalism(content)
            issues.extend(professionalism_result['issues'])
            (passed_checks if professionalism_result['passed'] else failed_checks).append('professionalism')
            
            structure_result = self._validate_structure(content, document_type)
            issues.extend(structure_result['issues'])
            (passed_checks if structure_result['passed'] else failed_checks).append('structure')
            
            accuracy_result = self._validate_accuracy(content, specialist_context)
            issues.extend(accuracy_result['issues'])
            (passed_checks if accuracy_result['passed'] else failed_checks).append('accuracy')
            
            confidence_result = self._validate_confidence_levels(content)
            issues.extend(confidence_result['issues'])
            (passed_checks if confidence_result['passed'] else failed_checks).append('confidence')
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(
                content, issues, completeness_result, professionalism_result,
                structure_result, accuracy_result, confidence_result
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(issues, quality_metrics)
            
            # Determine overall validity
            is_valid = self._determine_validity(quality_metrics, issues)
            
            result = ValidationResult(
                is_valid=is_valid,
                quality_metrics=quality_metrics,
                issues=issues,
                recommendations=recommendations,
                validation_timestamp=datetime.now().isoformat(),
                validation_level=self.validation_level,
                passed_checks=passed_checks,
                failed_checks=failed_checks,
                metadata={
                    'document_type': document_type,
                    'validation_version': '1.0',
                    'thresholds_used': self.thresholds
                }
            )
            
            self.logger.info(
                f"Validation complete: {'PASS' if is_valid else 'FAIL'} "
                f"(Score: {quality_metrics.overall_score:.2f}, Issues: {len(issues)})"
            )
            
            return result
            
        except Exception as e:
            log_exception(self.logger, "Content validation failed", e)
            return self._create_error_result(str(e))
    
    def _validate_completeness(self, content: str, document_type: str) -> Dict[str, Any]:
        """Validate content completeness against requirements."""
        issues = []
        
        # Word count validation
        word_count = len(content.split())
        min_words = self.thresholds.get('min_word_count', 200)
        if word_count < min_words:
            issues.append(ValidationIssue(
                issue_type=IssueType.MAJOR,
                category="content",
                description=f"Content too brief: {word_count} words (minimum: {min_words})",
                location="overall",
                suggestion=f"Expand content to at least {min_words} words",
                confidence=0.95
            ))
        
        # Required sections validation
        required = self.required_sections.get(document_type, [])
        missing_sections = []
        
        for section in required:
            if not self._find_section(content, section):
                missing_sections.append(section)
                issues.append(ValidationIssue(
                    issue_type=IssueType.CRITICAL,
                    category="structure",
                    description=f"Missing required section: {section}",
                    location="structure",
                    suggestion=f"Add {section} section with relevant content",
                    confidence=0.9
                ))
        
        # Executive summary validation (if present)
        if self._find_section(content, "executive summary"):
            exec_summary = self._extract_section_content(content, "executive summary")
            if exec_summary and len(exec_summary.split()) < 30:  # Reduced from 50
                issues.append(ValidationIssue(
                    issue_type=IssueType.MINOR,  # Reduced from MAJOR
                    category="content",
                    description=f"Executive summary brief ({len(exec_summary.split())} words)",
                    location="executive summary",
                    suggestion="Consider expanding executive summary to 30-100 words",
                    confidence=0.7  # Reduced confidence
                ))
        
        # Recommendations validation
        if "recommendation" in content.lower():
            rec_count = len(re.findall(r'(?:^|\n)\s*[-•*]\s*', content))
            if rec_count == 0:
                issues.append(ValidationIssue(
                    issue_type=IssueType.MINOR,
                    category="content",
                    description="No structured recommendations found",
                    location="recommendations",
                    suggestion="Use bullet points for clear recommendation formatting",
                    confidence=0.7
                ))
        
        passed = len([i for i in issues if i.issue_type in [IssueType.CRITICAL, IssueType.MAJOR]]) == 0
        
        return {
            'passed': passed,
            'issues': issues,
            'word_count': word_count,
            'missing_sections': missing_sections
        }
    
    def _validate_professionalism(self, content: str) -> Dict[str, Any]:
        """Validate professional standards and terminology."""
        issues = []
        
        # Check for professional terminology
        professional_terms = 0
        for pattern in self.professional_patterns['professional_terms']:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            professional_terms += matches
        
        if professional_terms < 3:
            issues.append(ValidationIssue(
                issue_type=IssueType.MINOR,
                category="professional_standards",
                description="Limited use of professional intelligence terminology",
                location="overall",
                suggestion="Include more intelligence community standard terms",
                confidence=0.6
            ))
        
        # Check for confidence expressions
        confidence_expressions = 0
        for pattern in self.professional_patterns['confidence_terms']:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            confidence_expressions += matches
        
        if confidence_expressions == 0:
            issues.append(ValidationIssue(
                issue_type=IssueType.MAJOR,
                category="professional_standards",
                description="No confidence expressions found",
                location="overall",
                suggestion="Include confidence levels (High/Medium/Low confidence)",
                confidence=0.85
            ))
        
        # Check for unprofessional elements
        unprofessional_patterns = self.professional_patterns.get('unprofessional_terms', [])
        for pattern in unprofessional_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(ValidationIssue(
                    issue_type=IssueType.MAJOR,
                    category="professional_standards",
                    description=f"Unprofessional language found: {matches[0]}",
                    location="content",
                    suggestion="Use professional intelligence terminology",
                    confidence=0.9
                ))
        
        # Check formatting consistency
        if not self._check_formatting_consistency(content):
            issues.append(ValidationIssue(
                issue_type=IssueType.MINOR,
                category="formatting",
                description="Inconsistent formatting detected",
                location="overall",
                suggestion="Ensure consistent heading styles and bullet formatting",
                confidence=0.7
            ))
        
        passed = len([i for i in issues if i.issue_type == IssueType.MAJOR]) == 0
        
        return {
            'passed': passed,
            'issues': issues,
            'professional_terms': professional_terms,
            'confidence_expressions': confidence_expressions
        }
    
    def _validate_structure(self, content: str, document_type: str) -> Dict[str, Any]:
        """Validate document structure and organization."""
        issues = []
        
        # Check for clear section headers
        headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        if len(headers) < 2:
            issues.append(ValidationIssue(
                issue_type=IssueType.MAJOR,
                category="structure",
                description="Insufficient section structure (< 2 headers)",
                location="overall",
                suggestion="Add clear section headers with # markdown formatting",
                confidence=0.85
            ))
        
        # Check for logical flow
        expected_order = self._get_expected_section_order(document_type)
        if expected_order:
            actual_order = [h.lower() for h in headers]
            order_score = self._calculate_order_score(actual_order, expected_order)
            if order_score < 0.6:
                issues.append(ValidationIssue(
                    issue_type=IssueType.MINOR,
                    category="structure",
                    description="Section order doesn't follow standard format",
                    location="structure",
                    suggestion="Reorganize sections in logical order",
                    confidence=0.7
                ))
        
        # Check for balanced section lengths
        section_lengths = []
        content_parts = re.split(r'^#+\s+', content, flags=re.MULTILINE)[1:]  # Skip content before first header
        for part in content_parts:
            section_lengths.append(len(part.split()))
        
        if section_lengths:
            avg_length = sum(section_lengths) / len(section_lengths)
            for i, length in enumerate(section_lengths):
                if length < avg_length * 0.1 and length < 10:  # Only flag very short sections
                    issues.append(ValidationIssue(
                        issue_type=IssueType.MINOR,
                        category="structure",
                        description=f"Section {i+1} appears very brief ({length} words)",
                        location=f"section_{i+1}",
                        suggestion="Consider expanding section with more detailed content",
                        confidence=0.5  # Lower confidence
                    ))
        
        passed = len([i for i in issues if i.issue_type == IssueType.MAJOR]) == 0
        
        return {
            'passed': passed,
            'issues': issues,
            'header_count': len(headers),
            'section_balance_score': self._calculate_section_balance(section_lengths)
        }
    
    def _validate_accuracy(self, content: str, specialist_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate content accuracy and consistency."""
        issues = []
        
        # Check for internal contradictions
        contradictions = self._find_contradictions(content)
        for contradiction in contradictions:
            issues.append(ValidationIssue(
                issue_type=IssueType.MAJOR,
                category="accuracy",
                description=f"Potential contradiction found: {contradiction}",
                location="content",
                suggestion="Review and resolve contradictory statements",
                confidence=0.7
            ))
        
        # Validate against specialist context if available
        if specialist_context:
            context_issues = self._validate_against_context(content, specialist_context)
            issues.extend(context_issues)
        
        # Check for unsupported claims
        unsupported_claims = self._find_unsupported_claims(content)
        if len(unsupported_claims) > 3:
            issues.append(ValidationIssue(
                issue_type=IssueType.MINOR,
                category="accuracy",
                description=f"Multiple unsupported claims detected ({len(unsupported_claims)})",
                location="content",
                suggestion="Provide evidence or qualify statements with confidence levels",
                confidence=0.6
            ))
        
        passed = len([i for i in issues if i.issue_type == IssueType.MAJOR]) == 0
        
        return {
            'passed': passed,
            'issues': issues,
            'contradictions_found': len(contradictions),
            'unsupported_claims': len(unsupported_claims)
        }
    
    def _validate_confidence_levels(self, content: str) -> Dict[str, Any]:
        """Validate proper use of confidence expressions."""
        issues = []
        
        # Look for confidence expressions
        confidence_patterns = [
            r'high\s+confidence',
            r'medium\s+confidence', 
            r'low\s+confidence',
            r'assess\s+with\s+\w+\s+confidence',
            r'likely',
            r'probable',
            r'possible',
            r'uncertain'
        ]
        
        confidence_count = 0
        for pattern in confidence_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            confidence_count += len(matches)
        
        # Validate confidence usage
        if confidence_count == 0:
            issues.append(ValidationIssue(
                issue_type=IssueType.MAJOR,
                category="professional_standards",
                description="No confidence expressions used",
                location="overall",
                suggestion="Include confidence levels for key assessments",
                confidence=0.9
            ))
        elif confidence_count < 2:
            issues.append(ValidationIssue(
                issue_type=IssueType.MINOR,
                category="professional_standards",
                description="Limited confidence expressions used",
                location="overall",
                suggestion="Use confidence levels for major analytical judgments",
                confidence=0.7
            ))
        
        # Check for overconfidence
        high_confidence_count = len(re.findall(r'high\s+confidence|certain|definitely', content, re.IGNORECASE))
        total_assessments = len(re.findall(r'assess|conclude|determine|likely|probable', content, re.IGNORECASE))
        
        if total_assessments > 0 and (high_confidence_count / total_assessments) > 0.7:
            issues.append(ValidationIssue(
                issue_type=IssueType.WARNING,
                category="professional_standards",
                description="Potentially overconfident assessments",
                location="overall",
                suggestion="Consider using more moderate confidence levels",
                confidence=0.6
            ))
        
        passed = len([i for i in issues if i.issue_type == IssueType.MAJOR]) == 0
        
        return {
            'passed': passed,
            'issues': issues,
            'confidence_expressions': confidence_count,
            'high_confidence_ratio': high_confidence_count / max(total_assessments, 1)
        }
    
    def _calculate_quality_metrics(self, content: str, issues: List[ValidationIssue], 
                                 *validation_results) -> QualityMetrics:
        """Calculate comprehensive quality metrics."""
        
        # Extract metrics from validation results
        completeness_result, professionalism_result, structure_result, accuracy_result, confidence_result = validation_results
        
        # Base scores from validation results
        completeness_score = 1.0 - (len([i for i in issues if i.category == "content"]) * 0.1)
        professionalism_score = 1.0 - (len([i for i in issues if i.category == "professional_standards"]) * 0.15)
        structure_score = 1.0 - (len([i for i in issues if i.category == "structure"]) * 0.1)
        accuracy_score = 1.0 - (len([i for i in issues if i.category == "accuracy"]) * 0.2)
        
        # Confidence score based on confidence expressions
        confidence_expressions = confidence_result.get('confidence_expressions', 0)
        confidence_score = min(1.0, confidence_expressions / 5.0)  # Normalized to 5 expressions
        
        # Clamp scores to 0.0-1.0 range
        completeness_score = max(0.0, min(1.0, completeness_score))
        professionalism_score = max(0.0, min(1.0, professionalism_score))
        structure_score = max(0.0, min(1.0, structure_score))
        accuracy_score = max(0.0, min(1.0, accuracy_score))
        confidence_score = max(0.0, min(1.0, confidence_score))
        
        # Calculate overall score with weights
        weights = {
            'completeness': 0.25,
            'professionalism': 0.20,
            'structure': 0.15,
            'accuracy': 0.30,
            'confidence': 0.10
        }
        
        overall_score = (
            completeness_score * weights['completeness'] +
            professionalism_score * weights['professionalism'] +
            structure_score * weights['structure'] +
            accuracy_score * weights['accuracy'] +
            confidence_score * weights['confidence']
        )
        
        # Content statistics
        word_count = completeness_result.get('word_count', len(content.split()))
        section_count = len(re.findall(r'^\s*#+\s+', content, re.MULTILINE))
        recommendations_count = len(re.findall(r'(?:^|\n)\s*[-•*]\s*', content))
        
        return QualityMetrics(
            overall_score=overall_score,
            completeness_score=completeness_score,
            professionalism_score=professionalism_score,
            accuracy_score=accuracy_score,
            structure_score=structure_score,
            confidence_score=confidence_score,
            word_count=word_count,
            section_count=section_count,
            recommendations_count=recommendations_count,
            issues_found=len(issues)
        )
    
    def _generate_recommendations(self, issues: List[ValidationIssue], 
                                quality_metrics: QualityMetrics) -> List[str]:
        """Generate actionable recommendations for content improvement."""
        recommendations = []
        
        # Add recommendations based on issues
        for issue in issues:
            if issue.suggestion and issue.confidence > 0.7:
                recommendations.append(f"{issue.category.title()}: {issue.suggestion}")
        
        # Add recommendations based on scores
        if quality_metrics.completeness_score < 0.8:
            recommendations.append("Content: Expand analysis with more detailed findings and supporting evidence")
        
        if quality_metrics.professionalism_score < 0.8:
            recommendations.append("Professional Standards: Use more intelligence community terminology and confidence expressions")
        
        if quality_metrics.structure_score < 0.8:
            recommendations.append("Structure: Improve document organization with clear sections and logical flow")
        
        if quality_metrics.accuracy_score < 0.8:
            recommendations.append("Accuracy: Review content for consistency and support claims with evidence")
        
        if quality_metrics.confidence_score < 0.5:
            recommendations.append("Confidence: Add confidence levels for key analytical judgments")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations[:10]  # Limit to top 10 recommendations
    
    def _determine_validity(self, quality_metrics: QualityMetrics, 
                          issues: List[ValidationIssue]) -> bool:
        """Determine if content meets validation standards."""
        
        # Check critical issues
        critical_issues = [i for i in issues if i.issue_type == IssueType.CRITICAL]
        if critical_issues:
            return False
        
        # For standard validation, only fail on major structure issues
        major_structure_issues = [i for i in issues if i.issue_type == IssueType.MAJOR and i.category == "structure"]
        if major_structure_issues and self.validation_level != ValidationLevel.PERMISSIVE:
            return False
            
        # Check overall score threshold
        min_score = self.thresholds.get('min_overall_score', 0.7)
        if quality_metrics.overall_score < min_score:
            return False
        
        # Check individual score thresholds for strict validation
        if self.validation_level == ValidationLevel.STRICT:
            if (quality_metrics.completeness_score < 0.8 or 
                quality_metrics.professionalism_score < 0.8 or
                quality_metrics.accuracy_score < 0.8):
                return False
        
        return True
    
    def _get_default_thresholds(self, level: ValidationLevel) -> Dict[str, float]:
        """Get default quality thresholds by validation level."""
        thresholds = {
            ValidationLevel.STRICT: {
                'min_overall_score': 0.85,
                'min_word_count': 300,
                'min_completeness': 0.8,
                'min_professionalism': 0.8,
                'min_accuracy': 0.8
            },
            ValidationLevel.STANDARD: {
                'min_overall_score': 0.7,
                'min_word_count': 200,
                'min_completeness': 0.7,
                'min_professionalism': 0.7,
                'min_accuracy': 0.7
            },
            ValidationLevel.PERMISSIVE: {
                'min_overall_score': 0.6,
                'min_word_count': 150,
                'min_completeness': 0.6,
                'min_professionalism': 0.6,
                'min_accuracy': 0.6
            }
        }
        return thresholds.get(level, thresholds[ValidationLevel.STANDARD])
    
    def _load_professional_patterns(self) -> Dict[str, List[str]]:
        """Load professional terminology patterns."""
        return {
            'professional_terms': [
                r'intelligence\s+assessment',
                r'threat\s+actor',
                r'indicators?\s+of\s+compromise',
                r'tactics,?\s+techniques,?\s+and\s+procedures',
                r'ttps?',
                r'iocs?',
                r'osint',
                r'geoint',
                r'sigint',
                r'collection\s+requirements?',
                r'analytical\s+judgment',
                r'key\s+findings?',
                r'intelligence\s+gaps?',
                r'threat\s+landscape',
                r'adversary',
                r'attribution',
                r'capability\s+assessment'
            ],
            'confidence_terms': [
                r'high\s+confidence',
                r'medium\s+confidence',
                r'low\s+confidence',
                r'assess\s+with\s+\w+\s+confidence',
                r'likely',
                r'probable',
                r'possible',
                r'uncertain',
                r'we\s+assess',
                r'likely\s+to',
                r'probably'
            ],
            'unprofessional_terms': [
                r'\bawesome\b',
                r'\bcool\b',
                r'\bstuff\b',
                r'\bthings\b',
                r'\bokay\b',
                r'\bguess\b',
                r'\bmaybe\b(?!\s+\w+\s+confidence)',
                r'\bwhatever\b'
            ]
        }
    
    def _get_required_sections(self) -> Dict[str, List[str]]:
        """Get required sections by document type."""
        return {
            'intelligence_analysis': [
                'executive summary',
                'key findings',
                'analysis',
                'recommendations'
            ],
            'osint_research': [
                'executive summary',
                'methodology',
                'findings',
                'verification',
                'recommendations'
            ],
            'threat_assessment': [
                'executive summary',
                'threat overview',
                'capability assessment',
                'risk analysis',
                'mitigation'
            ]
        }
    
    def _find_section(self, content: str, section_name: str) -> bool:
        """Check if a section exists in content."""
        # Check for exact match first
        pattern = rf'^\s*#+\s*{re.escape(section_name)}'
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            return True
        
        # Check for section name as part of a longer title
        # e.g., "analysis" should match "Detailed Analysis"
        pattern = rf'^\s*#+\s*.*{re.escape(section_name)}'
        return bool(re.search(pattern, content, re.IGNORECASE | re.MULTILINE))
    
    def _extract_section_content(self, content: str, section_name: str) -> str:
        """Extract content from a specific section."""
        pattern = rf'^\s*#+\s*{re.escape(section_name)}\s*\n(.*?)(?=^\s*#+|\Z)'
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        return match.group(1).strip() if match else ""
    
    def _check_formatting_consistency(self, content: str) -> bool:
        """Check for consistent formatting throughout document."""
        # Check header consistency
        headers = re.findall(r'^\s*(#+)\s+(.+)$', content, re.MULTILINE)
        if not headers:
            return True
        
        header_levels = [len(h[0]) for h in headers]
        # Should have consistent hierarchy (not jumping levels)
        for i in range(1, len(header_levels)):
            if header_levels[i] - header_levels[i-1] > 1:
                return False
        
        return True
    
    def _get_expected_section_order(self, document_type: str) -> List[str]:
        """Get expected section order for document type."""
        orders = {
            'intelligence_analysis': [
                'executive summary',
                'key findings',
                'analysis',
                'intelligence gaps',
                'recommendations'
            ]
        }
        return orders.get(document_type, [])
    
    def _calculate_order_score(self, actual: List[str], expected: List[str]) -> float:
        """Calculate how well actual order matches expected order."""
        if not expected:
            return 1.0
        
        score = 0.0
        for i, expected_section in enumerate(expected):
            for j, actual_section in enumerate(actual):
                if expected_section in actual_section.lower():
                    # Score based on position match
                    position_score = 1.0 - abs(i - j) / max(len(expected), len(actual))
                    score += position_score
                    break
        
        return score / len(expected)
    
    def _calculate_section_balance(self, section_lengths: List[int]) -> float:
        """Calculate section balance score."""
        if not section_lengths:
            return 1.0
        
        avg_length = sum(section_lengths) / len(section_lengths)
        variance = sum((l - avg_length) ** 2 for l in section_lengths) / len(section_lengths)
        coefficient_of_variation = (variance ** 0.5) / avg_length if avg_length > 0 else 0
        
        # Lower CV = better balance
        return max(0.0, 1.0 - coefficient_of_variation)
    
    def _find_contradictions(self, content: str) -> List[str]:
        """Find potential contradictions in content."""
        # This is a simplified implementation - could be enhanced with NLP
        contradictions = []
        
        # Look for contradictory statements
        positive_statements = re.findall(r'[^.!?]*\b(?:is|are|will|does|has|have)\b[^.!?]*', content)
        negative_statements = re.findall(r'[^.!?]*\b(?:not|no|never|unlikely|improbable)\b[^.!?]*', content)
        
        # Simple contradiction detection (could be improved)
        for pos in positive_statements:
            for neg in negative_statements:
                common_words = set(pos.lower().split()) & set(neg.lower().split())
                if len(common_words) > 3:  # Arbitrary threshold
                    contradictions.append(f"Potential contradiction between: '{pos[:50]}...' and '{neg[:50]}...'")
                    if len(contradictions) >= 3:  # Limit to avoid noise
                        break
            if len(contradictions) >= 3:
                break
        
        return contradictions
    
    def _validate_against_context(self, content: str, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate content against specialist context."""
        issues = []
        
        # Check if content aligns with extracted entities
        if 'entities' in context:
            mentioned_entities = []
            entities = context['entities']
            
            for entity_type, entity_list in entities.items():
                for entity in entity_list:
                    entity_name = entity.get('name', '') if isinstance(entity, dict) else str(entity)
                    if entity_name.lower() in content.lower():
                        mentioned_entities.append(entity_name)
            
            if len(mentioned_entities) / max(1, sum(len(elist) for elist in entities.values())) < 0.5:
                issues.append(ValidationIssue(
                    issue_type=IssueType.MINOR,
                    category="accuracy",
                    description="Low integration of extracted entity information",
                    location="content",
                    suggestion="Reference more extracted entities in analysis",
                    confidence=0.6
                ))
        
        return issues
    
    def _find_unsupported_claims(self, content: str) -> List[str]:
        """Find claims that may need more support."""
        # Look for definitive statements without qualification
        unsupported_patterns = [
            r'[^.!?]*\b(?:will|must|always|never|all|none|every|definitely)\b[^.!?]*[.!?]'
        ]
        
        unsupported = []
        for pattern in unsupported_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            unsupported.extend([m.strip() for m in matches])
        
        return unsupported[:10]  # Limit to avoid noise
    
    def _create_error_result(self, error_message: str) -> ValidationResult:
        """Create validation result for error cases."""
        return ValidationResult(
            is_valid=False,
            quality_metrics=QualityMetrics(
                overall_score=0.0,
                completeness_score=0.0,
                professionalism_score=0.0,
                accuracy_score=0.0,
                structure_score=0.0,
                confidence_score=0.0,
                word_count=0,
                section_count=0,
                recommendations_count=0,
                issues_found=1
            ),
            issues=[ValidationIssue(
                issue_type=IssueType.CRITICAL,
                category="validation_error",
                description=f"Validation failed: {error_message}",
                location="system",
                suggestion="Check content format and try again",
                confidence=1.0
            )],
            recommendations=["Fix validation error and retry"],
            validation_timestamp=datetime.now().isoformat(),
            validation_level=self.validation_level,
            passed_checks=[],
            failed_checks=["validation"],
            metadata={'error': error_message}
        )

    def validate_structured_content(self, structured_content: Dict[str, Any]) -> ValidationResult:
        """
        Validate structured content from content extraction.
        
        Args:
            structured_content: Structured content dictionary
            
        Returns:
            ValidationResult for the structured data
        """
        try:
            issues = []
            
            # Validate entities
            entities = structured_content.get('entities', {})
            if not entities:
                issues.append(ValidationIssue(
                    issue_type=IssueType.MAJOR,
                    category="content",
                    description="No entities extracted",
                    location="entities",
                    suggestion="Ensure content has identifiable entities (people, places, organizations)",
                    confidence=0.9
                ))
            else:
                total_entities = sum(len(entity_list) for entity_list in entities.values())
                if total_entities < 3:
                    issues.append(ValidationIssue(
                        issue_type=IssueType.MINOR,
                        category="content",
                        description=f"Limited entity extraction ({total_entities} entities)",
                        location="entities",
                        suggestion="Review content for additional entities",
                        confidence=0.7
                    ))
            
            # Validate relationships
            relationships = structured_content.get('relationships', [])
            if not relationships and entities:
                issues.append(ValidationIssue(
                    issue_type=IssueType.MINOR,
                    category="content",
                    description="No relationships identified between entities",
                    location="relationships",
                    suggestion="Look for connections between identified entities",
                    confidence=0.6
                ))
            
            # Validate confidence scores
            metadata = structured_content.get('metadata', {})
            confidence_threshold = metadata.get('confidence_threshold', 0.7)
            
            low_confidence_items = 0
            for entity_type, entity_list in entities.items():
                for entity in entity_list:
                    if isinstance(entity, dict) and entity.get('confidence', 1.0) < confidence_threshold:
                        low_confidence_items += 1
            
            if low_confidence_items > len([item for sublist in entities.values() for item in sublist]) * 0.5:
                issues.append(ValidationIssue(
                    issue_type=IssueType.WARNING,
                    category="accuracy",
                    description="Many low-confidence extractions",
                    location="confidence",
                    suggestion="Review extraction quality and consider re-processing",
                    confidence=0.8
                ))
            
            # Calculate quality score for structured content
            entity_score = min(1.0, total_entities / 5.0)  # Normalize to 5 entities
            relationship_score = min(1.0, len(relationships) / 3.0)  # Normalize to 3 relationships
            confidence_score = 1.0 - (low_confidence_items / max(1, total_entities))
            
            overall_score = (entity_score * 0.5 + relationship_score * 0.2 + confidence_score * 0.3)
            
            quality_metrics = QualityMetrics(
                overall_score=overall_score,
                completeness_score=entity_score,
                professionalism_score=1.0,  # N/A for structured data
                accuracy_score=confidence_score,
                structure_score=relationship_score,
                confidence_score=confidence_score,
                word_count=0,  # N/A for structured data
                section_count=len(entities),
                recommendations_count=len(relationships),
                issues_found=len(issues)
            )
            
            is_valid = overall_score >= 0.6  # Lower threshold for structured content
            
            return ValidationResult(
                is_valid=is_valid,
                quality_metrics=quality_metrics,
                issues=issues,
                recommendations=self._generate_recommendations(issues, quality_metrics),
                validation_timestamp=datetime.now().isoformat(),
                validation_level=self.validation_level,
                passed_checks=['entities'] if entities else [],
                failed_checks=[] if entities else ['entities'],
                metadata={'structured_content_validation': True}
            )
            
        except Exception as e:
            log_exception(self.logger, "Structured content validation failed", e)
            return self._create_error_result(str(e))