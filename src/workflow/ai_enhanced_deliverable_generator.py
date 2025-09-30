"""
AI-Enhanced Deliverable Generator

This module extends the basic deliverable generator with AI-powered content generation
capabilities. It integrates with GitHub Models API to enhance document creation with
intelligent content synthesis, specialist analysis integration, and quality validation.

Key Features:
- AI-powered content generation using GitHub Models API
- Integration with specialist agents (Intelligence Analyst, OSINT Researcher)
- Content enhancement and quality improvement
- Template-based structure with AI-generated content
- Professional document standards compliance
- Quality validation and completeness checking

The AI enhancement focuses on improving content quality while maintaining the
structured approach of the original deliverable generator.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum

from .deliverable_generator import DeliverableGenerator, DeliverableSpec
from .workflow_matcher import WorkflowInfo
from ..clients.github_models_client import GitHubModelsClient, AIResponse
from ..agents.specialist_agents import AnalysisResult, SpecialistType
from ..utils.logging_config import get_logger
from ..utils.config_manager import ConfigManager


class ContentType(Enum):
    """Types of content that can be AI-generated"""
    EXECUTIVE_SUMMARY = "executive_summary"
    ANALYSIS = "analysis"
    RECOMMENDATIONS = "recommendations"
    TECHNICAL_DETAILS = "technical_details"
    RISK_ASSESSMENT = "risk_assessment"
    METHODOLOGY = "methodology"
    FINDINGS = "findings"
    CONCLUSION = "conclusion"


@dataclass
class ContentGenerationSpec:
    """
    Specification for AI content generation
    
    Attributes:
        content_type: Type of content to generate
        prompt_template: Template for AI prompts
        max_tokens: Maximum tokens for generation
        temperature: AI creativity parameter
        required_elements: Required elements in content
        quality_criteria: Quality validation criteria
        specialist_integration: Whether to integrate specialist analysis
    """
    content_type: ContentType
    prompt_template: str
    max_tokens: int = 2000
    temperature: float = 0.3
    required_elements: Optional[List[str]] = None
    quality_criteria: Optional[Dict[str, Any]] = None
    specialist_integration: bool = True
    
    def __post_init__(self):
        if self.required_elements is None:
            self.required_elements = []
        if self.quality_criteria is None:
            self.quality_criteria = {}


@dataclass
class ContentQuality:
    """
    Content quality assessment
    
    Attributes:
        score: Quality score (0.0 to 1.0)
        completeness: Content completeness score
        professionalism: Professional standard compliance
        accuracy: Information accuracy assessment
        issues: List of quality issues found
        recommendations: Improvement recommendations
    """
    score: float
    completeness: float
    professionalism: float
    accuracy: float
    issues: List[str]
    recommendations: List[str]


class AIEnhancedDeliverableGenerator(DeliverableGenerator):
    """
    AI-Enhanced deliverable generator with intelligent content creation.
    
    This class extends the basic deliverable generator with AI-powered content
    generation, specialist analysis integration, and quality validation.
    It maintains compatibility with the existing template system while adding
    sophisticated AI capabilities.
    
    Attributes:
        ai_client: GitHub Models client for AI generation
        specialist_results: Cache of specialist analysis results
        content_specs: Content generation specifications
        quality_thresholds: Quality validation thresholds
    """
    
    def __init__(self,
                 github_token: Optional[str] = None,
                 ai_model: str = "gpt-4o",
                 templates_dir: Optional[Union[str, Path]] = None,
                 output_dir: Optional[Union[str, Path]] = None,
                 config_manager: Optional[ConfigManager] = None):
        """
        Initialize AI-enhanced deliverable generator.
        
        Args:
            github_token: GitHub token for AI API access
            ai_model: AI model to use for generation
            templates_dir: Directory containing deliverable templates
            output_dir: Base output directory for generated files
            config_manager: Configuration manager instance
        """
        super().__init__(templates_dir, output_dir)
        
        self.logger = get_logger(__name__)
        self.config_manager = config_manager or ConfigManager()
        
        # Initialize AI client if token provided
        self.ai_client = None
        if github_token:
            try:
                self.ai_client = GitHubModelsClient(
                    github_token=github_token,
                    model=ai_model,
                    timeout=60,  # Longer timeout for content generation
                    max_retries=2
                )
                self.logger.info(f"AI client initialized with model: {ai_model}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize AI client: {e}")
                self.ai_client = None
        
        # Cache for specialist analysis results
        self.specialist_results: Dict[int, Dict[SpecialistType, AnalysisResult]] = {}
        
        # Content generation specifications
        self.content_specs = self._initialize_content_specs()
        
        # Quality validation thresholds
        self.quality_thresholds = {
            "minimum_score": 0.7,
            "minimum_completeness": 0.8,
            "minimum_professionalism": 0.9,
            "minimum_accuracy": 0.8
        }
        
        # AI enhancement enabled flag
        self.ai_enabled = self.ai_client is not None
        
    def _initialize_content_specs(self) -> Dict[ContentType, ContentGenerationSpec]:
        """Initialize content generation specifications"""
        return {
            ContentType.EXECUTIVE_SUMMARY: ContentGenerationSpec(
                content_type=ContentType.EXECUTIVE_SUMMARY,
                prompt_template="""Create a professional executive summary for this intelligence report.

Issue Context:
- Title: {issue_title}
- Priority: {issue_priority}
- Type: {issue_type}

Specialist Analysis:
{specialist_analysis}

Requirements:
- Professional intelligence community standards
- Clear, concise executive-level language
- Key findings highlighted
- Actionable insights emphasized
- 200-400 words maximum

Generate a comprehensive executive summary that captures the most critical information for senior decision-makers.""",
                max_tokens=800,
                temperature=0.2,
                required_elements=["key_findings", "critical_insights", "recommendations"],
                quality_criteria={"clarity": 0.9, "conciseness": 0.8, "actionability": 0.9}
            ),
            
            ContentType.ANALYSIS: ContentGenerationSpec(
                content_type=ContentType.ANALYSIS,
                prompt_template="""Provide detailed analytical content based on the specialist analysis.

Issue Context:
- Title: {issue_title}
- Description: {issue_description}
- Labels: {issue_labels}

Specialist Analysis:
{specialist_analysis}

Content Requirements:
- Detailed analytical assessment
- Evidence-based conclusions
- Cross-reference specialist findings
- Professional intelligence analysis standards
- Logical flow and structure

Generate comprehensive analytical content that synthesizes the specialist findings into coherent intelligence assessment.""",
                max_tokens=2000,
                temperature=0.3,
                required_elements=["analysis", "evidence", "conclusions"],
                quality_criteria={"depth": 0.8, "accuracy": 0.9, "coherence": 0.8}
            ),
            
            ContentType.RECOMMENDATIONS: ContentGenerationSpec(
                content_type=ContentType.RECOMMENDATIONS,
                prompt_template="""Generate actionable recommendations based on the analysis.

Issue Context:
- Title: {issue_title}
- Priority: {issue_priority}

Analysis Summary:
{analysis_summary}

Specialist Recommendations:
{specialist_recommendations}

Requirements:
- Actionable, specific recommendations
- Prioritized by impact and feasibility
- Clear implementation guidance
- Risk considerations included
- Timeline estimates where appropriate

Create professional recommendations that provide clear next steps and actionable guidance.""",
                max_tokens=1500,
                temperature=0.2,
                required_elements=["actions", "priorities", "timelines"],
                quality_criteria={"actionability": 0.9, "specificity": 0.8, "feasibility": 0.8}
            ),
            
            ContentType.RISK_ASSESSMENT: ContentGenerationSpec(
                content_type=ContentType.RISK_ASSESSMENT,
                prompt_template="""Provide comprehensive risk assessment based on the analysis.

Issue Context:
- Title: {issue_title}
- Type: {issue_type}
- Severity: {issue_severity}

Specialist Analysis:
{specialist_analysis}

Risk Assessment Requirements:
- Identify key risk factors
- Assess probability and impact
- Provide risk mitigation strategies
- Consider timeline and urgency
- Professional risk assessment standards

Generate a thorough risk assessment that helps stakeholders understand and prepare for potential risks.""",
                max_tokens=1800,
                temperature=0.25,
                required_elements=["risks", "mitigation", "timeline"],
                quality_criteria={"comprehensiveness": 0.8, "accuracy": 0.9, "usefulness": 0.8}
            )
        }
    
    def generate_deliverable(self,
                           issue_data: Any,
                           deliverable_spec: DeliverableSpec,
                           workflow_info: WorkflowInfo,
                           additional_context: Optional[Dict[str, Any]] = None,
                           specialist_results: Optional[Dict[SpecialistType, AnalysisResult]] = None) -> str:
        """
        Generate AI-enhanced deliverable content.
        
        Args:
            issue_data: Issue data for context
            deliverable_spec: Specification for the deliverable to generate
            workflow_info: Workflow information
            additional_context: Additional context for content generation
            specialist_results: Results from specialist agents
            
        Returns:
            AI-enhanced deliverable content as string
            
        Raises:
            ValueError: If deliverable spec is invalid
            RuntimeError: If content generation fails
        """
        try:
            # Validate inputs
            if not issue_data or not deliverable_spec:
                raise ValueError("Issue data and deliverable spec are required")
            
            # Cache specialist results if provided
            issue_number = getattr(issue_data, 'number', 'unknown')
            if specialist_results and issue_number != 'unknown':
                self.specialist_results[issue_number] = specialist_results
            
            # Prepare enhanced template context
            context = self._prepare_ai_enhanced_context(
                issue_data, deliverable_spec, workflow_info, additional_context, specialist_results
            )
            
            # Generate base content using parent class
            base_content = super().generate_deliverable(
                issue_data, deliverable_spec, workflow_info, additional_context
            )
            
            # Enhance content with AI if available
            if self.ai_enabled and self._should_enhance_content(deliverable_spec):
                enhanced_content = self._enhance_content_with_ai(
                    base_content, context, deliverable_spec
                )
                
                # Validate enhanced content quality
                quality = self._validate_content_quality(enhanced_content, context)
                
                if quality.score >= self.quality_thresholds["minimum_score"]:
                    self.logger.info(f"AI enhancement successful (quality: {quality.score:.2f})")
                    return enhanced_content
                else:
                    self.logger.warning(f"AI enhancement quality below threshold ({quality.score:.2f}), using base content")
                    return base_content
            
            return base_content
            
        except Exception as e:
            self.logger.error(f"Failed to generate AI-enhanced deliverable: {e}")
            # Fallback to parent class generation
            return super().generate_deliverable(issue_data, deliverable_spec, workflow_info, additional_context)
    
    def _prepare_ai_enhanced_context(self,
                                   issue_data: Any,
                                   deliverable_spec: DeliverableSpec,
                                   workflow_info: WorkflowInfo,
                                   additional_context: Optional[Dict[str, Any]],
                                   specialist_results: Optional[Dict[SpecialistType, AnalysisResult]]) -> Dict[str, Any]:
        """Prepare enhanced context with AI-specific data"""
        # Get base context from parent
        context = self._prepare_template_context(issue_data, deliverable_spec, workflow_info, additional_context)
        
        # Add AI enhancement data
        context["ai_enhanced"] = True
        context["ai_model"] = self.ai_client.model if self.ai_client else None
        
        # Add specialist analysis if available
        if specialist_results:
            context["specialist_analysis"] = self._format_specialist_analysis(specialist_results)
            context["specialist_recommendations"] = self._extract_specialist_recommendations(specialist_results)
        elif isinstance(issue_data, dict) and issue_data.get('number') in self.specialist_results:
            # Use cached specialist results
            cached_results = self.specialist_results[issue_data['number']]
            context["specialist_analysis"] = self._format_specialist_analysis(cached_results)
            context["specialist_recommendations"] = self._extract_specialist_recommendations(cached_results)
        else:
            context["specialist_analysis"] = "No specialist analysis available"
            context["specialist_recommendations"] = []
        
        # Add content generation metadata
        context["content_generation"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ai_enabled": self.ai_enabled,
            "quality_threshold": self.quality_thresholds["minimum_score"]
        }
        
        return context
    
    def _format_specialist_analysis(self, specialist_results: Dict[SpecialistType, AnalysisResult]) -> str:
        """Format specialist analysis results for AI prompts"""
        if not specialist_results:
            return "No specialist analysis available"
        
        formatted_sections = []
        
        for specialist_type, result in specialist_results.items():
            # Format specialist title by replacing hyphens with spaces and title case
            # Special handling for acronyms like OSINT
            title = specialist_type.value.replace('-', ' ').title()
            title = title.replace('Osint', 'OSINT')  # Fix OSINT acronym
            section = f"\n## {title} Analysis\n"
            section += f"**Confidence**: {result.confidence_score:.2f}\n"
            section += f"**Priority**: {getattr(result, 'priority_score', 'N/A')}\n\n"
            
            if result.key_findings:
                section += "**Key Findings**:\n"
                for finding in result.key_findings[:3]:  # Limit for prompt size
                    section += f"- {finding}\n"
                section += "\n"
            
            if result.recommendations:
                section += "**Recommendations**:\n"
                for rec in result.recommendations[:3]:  # Limit for prompt size
                    section += f"- {rec}\n"
                section += "\n"
            
            if result.summary:
                section += f"**Summary**: {result.summary[:300]}...\n\n"
            
            formatted_sections.append(section)
        
        return "\n".join(formatted_sections)
    
    def _extract_specialist_recommendations(self, specialist_results: Dict[SpecialistType, AnalysisResult]) -> List[str]:
        """Extract all recommendations from specialist results"""
        all_recommendations = []
        
        for result in specialist_results.values():
            if result.recommendations:
                all_recommendations.extend(result.recommendations)
        
        return all_recommendations
    
    def _should_enhance_content(self, deliverable_spec: DeliverableSpec) -> bool:
        """Determine if content should be AI enhanced"""
        if not self.ai_enabled:
            return False
        
        # Enhance specific deliverable types
        enhance_types = {
            "intelligence_assessment",
            "osint_research",
            "threat_analysis", 
            "risk_assessment",
            "executive_summary",
            "analytical_report"
        }
        
        return (deliverable_spec.name in enhance_types or
                deliverable_spec.type in enhance_types or
                deliverable_spec.template in enhance_types)
    
    def _enhance_content_with_ai(self,
                               base_content: str,
                               context: Dict[str, Any],
                               deliverable_spec: DeliverableSpec) -> str:
        """Enhance content using AI generation"""
        try:
            # Determine content types to enhance
            enhancement_sections = self._identify_enhancement_sections(base_content, deliverable_spec)
            
            enhanced_content = base_content
            
            for content_type in enhancement_sections:
                if content_type in self.content_specs:
                    # Generate AI content for this section
                    ai_content = self._generate_ai_content(content_type, context)
                    
                    if ai_content:
                        # Replace or enhance the relevant section
                        enhanced_content = self._integrate_ai_content(
                            enhanced_content, content_type, ai_content
                        )
            
            return enhanced_content
            
        except Exception as e:
            self.logger.error(f"AI content enhancement failed: {e}")
            return base_content
    
    def _identify_enhancement_sections(self, 
                                     content: str, 
                                     deliverable_spec: DeliverableSpec) -> Set[ContentType]:
        """Identify which sections should be AI enhanced"""
        sections = set()
        
        # Check for common section patterns
        content_lower = content.lower()
        
        if any(pattern in content_lower for pattern in ["executive summary", "summary", "overview"]):
            sections.add(ContentType.EXECUTIVE_SUMMARY)
            
        if any(pattern in content_lower for pattern in ["analysis", "assessment", "findings"]):
            sections.add(ContentType.ANALYSIS)
            
        if any(pattern in content_lower for pattern in ["recommendations", "actions", "next steps"]):
            sections.add(ContentType.RECOMMENDATIONS)
            
        if any(pattern in content_lower for pattern in ["risk", "threat", "vulnerability"]):
            sections.add(ContentType.RISK_ASSESSMENT)
        
        # Default enhancement for intelligence deliverables
        if deliverable_spec.type == "intelligence" or "intelligence" in deliverable_spec.name:
            sections.update([ContentType.EXECUTIVE_SUMMARY, ContentType.ANALYSIS])
        
        return sections
    
    def _generate_ai_content(self, content_type: ContentType, context: Dict[str, Any]) -> Optional[str]:
        """Generate AI content for a specific content type"""
        if not self.ai_client:
            return None
        
        try:
            spec = self.content_specs[content_type]
            
            # Format the prompt with context
            prompt = spec.prompt_template.format(
                issue_title=context.get("issue", {}).get("title", "Unknown"),
                issue_description=context.get("issue", {}).get("body", "No description")[:500],
                issue_labels=", ".join(context.get("issue", {}).get("labels", [])),
                issue_priority=self._determine_priority(context),
                issue_type=self._determine_type(context),
                issue_severity=self._determine_severity(context),
                specialist_analysis=context.get("specialist_analysis", "No analysis available"),
                specialist_recommendations="\n".join([f"- {rec}" for rec in context.get("specialist_recommendations", [])]),
                analysis_summary=context.get("specialist_analysis", "")[:300] + "..."
            )
            
            # Generate content
            response = self.ai_client.chat_completion(
                prompt=prompt,
                max_tokens=spec.max_tokens,
                temperature=spec.temperature
            )
            
            if response and response.content:
                self.logger.debug(f"Generated AI content for {content_type.value}")
                return response.content.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to generate AI content for {content_type.value}: {e}")
        
        return None
    
    def _integrate_ai_content(self, base_content: str, content_type: ContentType, ai_content: str) -> str:
        """Integrate AI-generated content into the base content"""
        try:
            # Define section markers for different content types
            section_markers = {
                ContentType.EXECUTIVE_SUMMARY: ["# Executive Summary", "## Executive Summary", "### Executive Summary"],
                ContentType.ANALYSIS: ["# Analysis", "## Analysis", "### Analysis", "# Findings", "## Findings"],
                ContentType.RECOMMENDATIONS: ["# Recommendations", "## Recommendations", "### Recommendations"],
                ContentType.RISK_ASSESSMENT: ["# Risk Assessment", "## Risk Assessment", "### Risk Assessment"]
            }
            
            markers = section_markers.get(content_type, [])
            
            for marker in markers:
                if marker in base_content:
                    # Find the section and replace/enhance it
                    lines = base_content.split('\n')
                    marker_index = -1
                    
                    for i, line in enumerate(lines):
                        if line.strip() == marker:
                            marker_index = i
                            break
                    
                    if marker_index >= 0:
                        # Find end of section (next header or end of content)
                        end_index = len(lines)
                        for i in range(marker_index + 1, len(lines)):
                            if lines[i].startswith('#') and not lines[i].startswith(marker.split()[0] + '#'):
                                end_index = i
                                break
                        
                        # Replace section content
                        new_lines = (
                            lines[:marker_index + 1] +
                            [ai_content] +
                            lines[end_index:]
                        )
                        
                        return '\n'.join(new_lines)
            
            # If no section found, append AI content with appropriate header
            header_map = {
                ContentType.EXECUTIVE_SUMMARY: "## Executive Summary",
                ContentType.ANALYSIS: "## Analysis",
                ContentType.RECOMMENDATIONS: "## Recommendations",
                ContentType.RISK_ASSESSMENT: "## Risk Assessment"
            }
            
            header = header_map.get(content_type, "## Enhanced Content")
            return f"{base_content}\n\n{header}\n\n{ai_content}\n"
            
        except Exception as e:
            self.logger.error(f"Failed to integrate AI content: {e}")
            return base_content
    
    def _validate_content_quality(self, content: str, context: Dict[str, Any]) -> ContentQuality:
        """Validate the quality of generated content"""
        try:
            # Basic quality metrics
            word_count = len(content.split())
            has_structure = bool(re.search(r'^#+\s', content, re.MULTILINE))
            has_sections = content.count('#') >= 2
            
            # Completeness check
            completeness = min(1.0, word_count / 500)  # Assume 500 words is complete
            if has_structure:
                completeness = min(1.0, completeness + 0.2)
            if has_sections:
                completeness = min(1.0, completeness + 0.1)
            
            # Professionalism check (basic patterns)
            professional_indicators = [
                re.search(r'\b(analysis|assessment|recommendation|finding)\b', content.lower()),
                re.search(r'\b(based on|according to|evidence suggests)\b', content.lower()),
                len(re.findall(r'[.!?]', content)) >= 5  # Proper sentence structure
            ]
            professionalism = sum(1 for indicator in professional_indicators if indicator) / len(professional_indicators)
            
            # Accuracy check (presence of specialist integration)
            specialist_integration = "specialist_analysis" in context and context["specialist_analysis"] != "No specialist analysis available"
            accuracy = 0.9 if specialist_integration else 0.7
            
            # Overall score
            score = (completeness * 0.3 + professionalism * 0.4 + accuracy * 0.3)
            
            # Issues and recommendations
            issues = []
            recommendations = []
            
            if completeness < 0.8:
                issues.append("Content appears incomplete")
                recommendations.append("Add more detailed analysis")
            
            if professionalism < 0.8:
                issues.append("Content lacks professional terminology")
                recommendations.append("Use more formal, analytical language")
            
            if not specialist_integration:
                issues.append("No specialist analysis integration")
                recommendations.append("Integrate findings from specialist agents")
            
            return ContentQuality(
                score=score,
                completeness=completeness,
                professionalism=professionalism,
                accuracy=accuracy,
                issues=issues,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Content quality validation failed: {e}")
            return ContentQuality(
                score=0.5,
                completeness=0.5,
                professionalism=0.5,
                accuracy=0.5,
                issues=["Quality validation failed"],
                recommendations=["Manual review required"]
            )
    
    def _determine_priority(self, context: Dict[str, Any]) -> str:
        """Determine issue priority from context"""
        labels = context.get("issue", {}).get("labels", [])
        
        if any("high" in str(label).lower() or "urgent" in str(label).lower() for label in labels):
            return "High"
        elif any("medium" in str(label).lower() for label in labels):
            return "Medium"
        elif any("low" in str(label).lower() for label in labels):
            return "Low"
        
        return "Medium"  # Default
    
    def _determine_type(self, context: Dict[str, Any]) -> str:
        """Determine issue type from context"""
        title = context.get("issue", {}).get("title", "").lower()
        labels = context.get("issue", {}).get("labels", [])
        
        if any("security" in str(item).lower() or "threat" in str(item).lower() for item in [title] + labels):
            return "Security"
        elif any("intelligence" in str(item).lower() for item in [title] + labels):
            return "Intelligence"
        elif any("osint" in str(item).lower() for item in [title] + labels):
            return "OSINT"
        
        return "General"
    
    def _determine_severity(self, context: Dict[str, Any]) -> str:
        """Determine issue severity from context"""
        labels = context.get("issue", {}).get("labels", [])
        
        if any("critical" in str(label).lower() or "severe" in str(label).lower() for label in labels):
            return "Critical"
        elif any("major" in str(label).lower() for label in labels):
            return "Major"
        elif any("minor" in str(label).lower() for label in labels):
            return "Minor"
        
        return "Medium"  # Default
    
    def generate_quality_report(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive quality report for content"""
        quality = self._validate_content_quality(content, context)
        
        return {
            "quality_score": quality.score,
            "metrics": {
                "completeness": quality.completeness,
                "professionalism": quality.professionalism,
                "accuracy": quality.accuracy
            },
            "issues": quality.issues,
            "recommendations": quality.recommendations,
            "meets_threshold": quality.score >= self.quality_thresholds["minimum_score"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ai_enhanced": self.ai_enabled
        }
    
    def set_quality_thresholds(self, thresholds: Dict[str, float]):
        """Update quality validation thresholds"""
        self.quality_thresholds.update(thresholds)
        self.logger.info(f"Updated quality thresholds: {self.quality_thresholds}")
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI client status and capabilities"""
        return {
            "ai_enabled": self.ai_enabled,
            "model": self.ai_client.model if self.ai_client else None,
            "content_types_supported": [ct.value for ct in self.content_specs.keys()],
            "quality_thresholds": self.quality_thresholds,
            "specialist_cache_size": len(self.specialist_results)
        }