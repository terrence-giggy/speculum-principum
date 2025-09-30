"""
Specialist Workflow Configuration System

This module provides centralized configuration for specialist workflows,
including assignment rules, deliverable specifications, and quality requirements.
Implements Task 3.3 from the AI Content Extraction roadmap.
"""

import os
import yaml
import logging
from typing import Dict, List, Optional, Any, Union, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..utils.config_manager import ConfigManager
from ..utils.logging_config import get_logger, log_exception


class SpecialistType(Enum):
    """Available specialist types in the system."""
    INTELLIGENCE_ANALYST = "intelligence-analyst"
    OSINT_RESEARCHER = "osint-researcher"
    TARGET_PROFILER = "target-profiler"
    THREAT_HUNTER = "threat-hunter"  # For future implementation
    BUSINESS_ANALYST = "business-analyst"  # For future implementation


class AssignmentConfidenceLevel(Enum):
    """Confidence levels for specialist assignments."""
    HIGH = "high"      # 0.8+
    MEDIUM = "medium"  # 0.6-0.79
    LOW = "low"        # 0.4-0.59


@dataclass
class AssignmentRule:
    """Rule for assigning specialists to issues."""
    specialist_type: SpecialistType
    trigger_labels: List[str] = field(default_factory=list)
    content_keywords: List[str] = field(default_factory=list)
    priority_weight: float = 1.0
    min_confidence: float = 0.6
    max_issues_per_batch: int = 10
    
    def __post_init__(self):
        """Validate assignment rule parameters."""
        if not self.trigger_labels and not self.content_keywords:
            raise ValueError("AssignmentRule must have either trigger_labels or content_keywords")
        
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0.0 and 1.0")
        
        if not 0.0 <= self.priority_weight <= 10.0:
            raise ValueError("priority_weight must be between 0.0 and 10.0")


@dataclass
class DeliverableSpec:
    """Specification for a workflow deliverable."""
    name: str
    title: str
    template_name: str
    description: str = ""
    ai_enhanced: bool = True
    required_sections: List[str] = field(default_factory=list)
    quality_threshold: float = 0.7
    max_tokens: int = 4000
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate deliverable specification."""
        if not self.name or not self.title or not self.template_name:
            raise ValueError("name, title, and template_name are required for DeliverableSpec")


@dataclass
class QualityRequirement:
    """Quality requirements for specialist workflows."""
    min_confidence_score: float = 0.6
    require_source_references: bool = True
    min_word_count: int = 500
    max_processing_time_minutes: int = 30
    require_executive_summary: bool = True
    require_recommendations: bool = True
    validation_strictness: str = "standard"  # strict, standard, permissive
    
    def __post_init__(self):
        """Validate quality requirements."""
        if not 0.0 <= self.min_confidence_score <= 1.0:
            raise ValueError("min_confidence_score must be between 0.0 and 1.0")
        
        if self.validation_strictness not in ["strict", "standard", "permissive"]:
            raise ValueError("validation_strictness must be 'strict', 'standard', or 'permissive'")


@dataclass 
class SpecialistWorkflowConfig:
    """Complete workflow configuration for a specialist."""
    specialist_type: SpecialistType
    name: str
    description: str
    version: str = "1.0.0"
    persona: str = ""
    assignment_rules: List[AssignmentRule] = field(default_factory=list)
    deliverable_specs: List[DeliverableSpec] = field(default_factory=list)
    quality_requirements: QualityRequirement = field(default_factory=QualityRequirement)
    ai_config: Dict[str, Any] = field(default_factory=dict)
    git_config: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    
    def __post_init__(self):
        """Set default configurations if not provided."""
        if not self.ai_config:
            self.ai_config = {
                "extraction_temperature": 0.2,
                "analysis_temperature": 0.4,
                "max_extraction_tokens": 2000,
                "max_analysis_tokens": 4000
            }
        
        if not self.git_config:
            self.git_config = {
                "branch_pattern": f"{self.specialist_type.value}/issue-{{issue_number}}",
                "commit_message": f"{self.name} analysis for issue #{{issue_number}}"
            }


class SpecialistWorkflowConfigManager:
    """
    Manager for specialist workflow configurations.
    
    Provides centralized management of specialist assignments, deliverable
    specifications, and quality requirements.
    """
    
    def __init__(self, config_path: str = "config.yaml", workflow_directory: str = "docs/workflow/deliverables"):
        """
        Initialize the workflow configuration manager.
        
        Args:
            config_path: Path to main configuration file
            workflow_directory: Directory containing workflow YAML definitions
        """
        self.logger = get_logger(__name__)
        self.config_path = config_path
        self.workflow_directory = Path(workflow_directory)
        
        # Cache for loaded configurations
        self._specialist_configs: Dict[SpecialistType, SpecialistWorkflowConfig] = {}
        self._assignment_rules: List[AssignmentRule] = []
        self._loaded = False
        
        # Default quality requirements by specialist type
        self._default_quality_requirements = {
            SpecialistType.INTELLIGENCE_ANALYST: QualityRequirement(
                min_confidence_score=0.75,
                require_source_references=True,
                min_word_count=1000,
                require_executive_summary=True,
                require_recommendations=True,
                validation_strictness="standard"
            ),
            SpecialistType.OSINT_RESEARCHER: QualityRequirement(
                min_confidence_score=0.70,
                require_source_references=True,
                min_word_count=800,
                require_executive_summary=False,
                require_recommendations=True,
                validation_strictness="standard"
            ),
            SpecialistType.TARGET_PROFILER: QualityRequirement(
                min_confidence_score=0.65,
                require_source_references=True,
                min_word_count=750,
                require_executive_summary=True,
                require_recommendations=False,
                validation_strictness="standard"
            )
        }
    
    def load_configurations(self, force_reload: bool = False) -> None:
        """
        Load all specialist workflow configurations.
        
        Args:
            force_reload: Force reload even if already loaded
        """
        if self._loaded and not force_reload:
            return
        
        try:
            self.logger.info("Loading specialist workflow configurations...")
            
            # Clear existing configurations
            self._specialist_configs.clear()
            self._assignment_rules.clear()
            
            # Load each specialist configuration
            self._load_intelligence_analyst_config()
            self._load_osint_researcher_config()
            self._load_target_profiler_config()
            
            # Load assignment rules from configurations
            self._build_assignment_rules()
            
            self._loaded = True
            self.logger.info(f"Loaded {len(self._specialist_configs)} specialist configurations")
            
        except Exception as e:
            log_exception(self.logger, "Failed to load specialist configurations", e)
            raise
    
    def _load_intelligence_analyst_config(self) -> None:
        """Load Intelligence Analyst workflow configuration."""
        specialist_type = SpecialistType.INTELLIGENCE_ANALYST
        
        # Assignment rules for Intelligence Analyst
        assignment_rules = [
            AssignmentRule(
                specialist_type=specialist_type,
                trigger_labels=["intelligence", "intelligence-analyst"],
                content_keywords=["threat", "analysis", "intelligence", "strategic"],
                priority_weight=1.0,
                min_confidence=0.75
            ),
            AssignmentRule(
                specialist_type=specialist_type,
                trigger_labels=["threat-assessment", "strategic-analysis"],
                content_keywords=["apt", "campaign", "threat-actor", "geopolitical"],
                priority_weight=0.9,
                min_confidence=0.70
            )
        ]
        
        # Deliverable specifications
        deliverable_specs = [
            DeliverableSpec(
                name="intelligence_assessment",
                title="Intelligence Assessment Report",
                template_name="intelligence_assessment.md",
                description="Comprehensive intelligence analysis with threat assessment",
                ai_enhanced=True,
                required_sections=[
                    "executive_summary", "threat_landscape", "actor_analysis",
                    "capabilities_assessment", "intentions_analysis", "risk_assessment",
                    "recommendations", "intelligence_gaps"
                ],
                quality_threshold=0.75,
                max_tokens=4000,
                conditions=[{"type": "label", "values": ["intelligence", "threat-assessment"]}]
            ),
            DeliverableSpec(
                name="executive_briefing",
                title="Executive Intelligence Briefing",
                template_name="executive_briefing.md",
                description="Strategic intelligence briefing for decision-makers",
                ai_enhanced=True,
                required_sections=[
                    "executive_summary", "key_assessments", "strategic_implications",
                    "recommended_actions"
                ],
                quality_threshold=0.80,
                max_tokens=2000,
                conditions=[{"type": "label", "values": ["strategic-analysis", "geopolitical"]}]
            )
        ]
        
        # Create configuration
        config = SpecialistWorkflowConfig(
            specialist_type=specialist_type,
            name="Intelligence Analyst",
            description="AI-powered intelligence analysis for threat assessment and strategic evaluation",
            version="2.0.0",
            persona=(
                "You are a senior intelligence analyst with 15+ years of experience in threat "
                "assessment, geopolitical analysis, and strategic intelligence. You specialize in "
                "synthesizing complex information from multiple sources into actionable intelligence "
                "products for decision-makers."
            ),
            assignment_rules=assignment_rules,
            deliverable_specs=deliverable_specs,
            quality_requirements=self._default_quality_requirements[specialist_type],
            ai_config={
                "extraction_temperature": 0.2,
                "analysis_temperature": 0.4,
                "max_extraction_tokens": 2000,
                "max_analysis_tokens": 4000,
                "confidence_threshold": 0.75
            },
            git_config={
                "branch_pattern": "intelligence/issue-{issue_number}",
                "commit_message": "Intelligence analysis for issue #{issue_number}"
            }
        )
        
        self._specialist_configs[specialist_type] = config
        self.logger.debug(f"Loaded {specialist_type.value} configuration")
    
    def _load_osint_researcher_config(self) -> None:
        """Load OSINT Researcher workflow configuration."""
        specialist_type = SpecialistType.OSINT_RESEARCHER
        
        # Assignment rules for OSINT Researcher
        assignment_rules = [
            AssignmentRule(
                specialist_type=specialist_type,
                trigger_labels=["osint", "osint-researcher"],
                content_keywords=["osint", "reconnaissance", "verification", "research"],
                priority_weight=0.8,
                min_confidence=0.70
            ),
            AssignmentRule(
                specialist_type=specialist_type,
                trigger_labels=["reconnaissance", "verification", "digital-footprint"],
                content_keywords=["digital footprint", "social media", "public records", "investigate"],
                priority_weight=0.7,
                min_confidence=0.65
            )
        ]
        
        # Deliverable specifications
        deliverable_specs = [
            DeliverableSpec(
                name="osint_research_report",
                title="OSINT Research Report",
                template_name="osint_research_report.md",
                description="Comprehensive OSINT research with verification assessment",
                ai_enhanced=True,
                required_sections=[
                    "research_summary", "digital_footprint_analysis", "source_verification",
                    "information_assessment", "research_gaps", "collection_recommendations"
                ],
                quality_threshold=0.70,
                max_tokens=3500,
                conditions=[{"type": "label", "values": ["osint", "research"]}]
            ),
            DeliverableSpec(
                name="verification_assessment",
                title="Information Verification Assessment",
                template_name="verification_assessment.md",
                description="Source credibility and information verification analysis",
                ai_enhanced=True,
                required_sections=[
                    "verification_summary", "source_analysis", "credibility_assessment",
                    "cross_reference_analysis", "verification_recommendations"
                ],
                quality_threshold=0.75,
                max_tokens=2500,
                conditions=[{"type": "label", "values": ["verification", "source-analysis"]}]
            )
        ]
        
        # Create configuration
        config = SpecialistWorkflowConfig(
            specialist_type=specialist_type,
            name="OSINT Researcher",
            description="Open source intelligence research with information verification",
            version="2.0.0",
            persona=(
                "You are an expert OSINT researcher with deep knowledge of open source intelligence "
                "techniques, digital forensics, and information verification methodologies. You excel "
                "at finding, analyzing, and verifying information from publicly available sources."
            ),
            assignment_rules=assignment_rules,
            deliverable_specs=deliverable_specs,
            quality_requirements=self._default_quality_requirements[specialist_type],
            ai_config={
                "extraction_temperature": 0.3,
                "analysis_temperature": 0.4,
                "max_extraction_tokens": 1800,
                "max_analysis_tokens": 3500,
                "confidence_threshold": 0.70
            },
            git_config={
                "branch_pattern": "osint/issue-{issue_number}",
                "commit_message": "OSINT research for issue #{issue_number}"
            }
        )
        
        self._specialist_configs[specialist_type] = config
        self.logger.debug(f"Loaded {specialist_type.value} configuration")
    
    def _load_target_profiler_config(self) -> None:
        """Load Target Profiler workflow configuration."""
        specialist_type = SpecialistType.TARGET_PROFILER
        
        # Assignment rules for Target Profiler
        assignment_rules = [
            AssignmentRule(
                specialist_type=specialist_type,
                trigger_labels=["target-profiler", "organizational-analysis"],
                content_keywords=["target", "organization", "profile", "stakeholder"],
                priority_weight=0.7,
                min_confidence=0.65
            ),
            AssignmentRule(
                specialist_type=specialist_type,
                trigger_labels=["business-intelligence", "stakeholder-analysis"],
                content_keywords=["business", "company", "personnel", "leadership"],
                priority_weight=0.6,
                min_confidence=0.60
            )
        ]
        
        # Deliverable specifications
        deliverable_specs = [
            DeliverableSpec(
                name="organizational_profile",
                title="Organizational Profile Report",
                template_name="organizational_profile.md",
                description="Comprehensive organizational analysis with stakeholder mapping",
                ai_enhanced=True,
                required_sections=[
                    "executive_summary", "organizational_overview", "key_personnel",
                    "business_intelligence", "stakeholder_network", "risk_factors",
                    "recommendations"
                ],
                quality_threshold=0.65,
                max_tokens=3000,
                conditions=[{"type": "label", "values": ["target-profiler", "organizational-analysis"]}]
            ),
            DeliverableSpec(
                name="stakeholder_analysis",
                title="Stakeholder Analysis Report",
                template_name="stakeholder_analysis.md",
                description="Detailed stakeholder mapping and relationship analysis",
                ai_enhanced=True,
                required_sections=[
                    "stakeholder_summary", "key_relationships", "influence_mapping",
                    "contact_intelligence", "engagement_recommendations"
                ],
                quality_threshold=0.70,
                max_tokens=2500,
                conditions=[{"type": "label", "values": ["stakeholder-analysis", "business-intelligence"]}]
            )
        ]
        
        # Create configuration
        config = SpecialistWorkflowConfig(
            specialist_type=specialist_type,
            name="Target Profiler",
            description="Organizational analysis and stakeholder mapping specialist",
            version="2.0.0",
            persona=(
                "You are an expert organizational analyst specializing in business intelligence, "
                "stakeholder mapping, and organizational profiling. You excel at extracting and "
                "analyzing organizational structures, key personnel, and business relationships "
                "from various sources."
            ),
            assignment_rules=assignment_rules,
            deliverable_specs=deliverable_specs,
            quality_requirements=self._default_quality_requirements[specialist_type],
            ai_config={
                "extraction_temperature": 0.25,
                "analysis_temperature": 0.35,
                "max_extraction_tokens": 1500,
                "max_analysis_tokens": 3000,
                "confidence_threshold": 0.65
            },
            git_config={
                "branch_pattern": "profiling/issue-{issue_number}",
                "commit_message": "Target profiling analysis for issue #{issue_number}"
            }
        )
        
        self._specialist_configs[specialist_type] = config
        self.logger.debug(f"Loaded {specialist_type.value} configuration")
    
    def _build_assignment_rules(self) -> None:
        """Build consolidated assignment rules from all specialist configurations."""
        for config in self._specialist_configs.values():
            self._assignment_rules.extend(config.assignment_rules)
        
        # Sort by priority weight (highest first)
        self._assignment_rules.sort(key=lambda rule: rule.priority_weight, reverse=True)
        
        self.logger.debug(f"Built {len(self._assignment_rules)} assignment rules")
    
    def get_specialist_config(self, specialist_type: SpecialistType) -> Optional[SpecialistWorkflowConfig]:
        """
        Get configuration for a specific specialist type.
        
        Args:
            specialist_type: Type of specialist
            
        Returns:
            Specialist configuration or None if not found
        """
        if not self._loaded:
            self.load_configurations()
        
        return self._specialist_configs.get(specialist_type)
    
    def get_all_specialist_configs(self) -> Dict[SpecialistType, SpecialistWorkflowConfig]:
        """
        Get all specialist configurations.
        
        Returns:
            Dictionary mapping specialist types to their configurations
        """
        if not self._loaded:
            self.load_configurations()
        
        return self._specialist_configs.copy()
    
    def get_assignment_rules(self) -> List[AssignmentRule]:
        """
        Get all assignment rules sorted by priority.
        
        Returns:
            List of assignment rules
        """
        if not self._loaded:
            self.load_configurations()
        
        return self._assignment_rules.copy()
    
    def find_matching_specialists(self, 
                                labels: List[str], 
                                content_keywords: Optional[List[str]] = None) -> List[Tuple[SpecialistType, float]]:
        """
        Find specialists that match the given labels and content.
        
        Args:
            labels: Issue labels
            content_keywords: Keywords extracted from issue content
            
        Returns:
            List of (specialist_type, confidence_score) tuples sorted by confidence
        """
        if not self._loaded:
            self.load_configurations()
        
        if content_keywords is None:
            content_keywords = []
        
        label_set = set(labels)
        keyword_set = set(keyword.lower() for keyword in content_keywords)
        
        matches = []
        
        for rule in self._assignment_rules:
            # Calculate label match score
            label_matches = len(label_set.intersection(set(rule.trigger_labels)))
            label_score = label_matches / max(len(rule.trigger_labels), 1) if rule.trigger_labels else 0
            
            # Calculate keyword match score
            keyword_matches = len(keyword_set.intersection(set(kw.lower() for kw in rule.content_keywords)))
            keyword_score = keyword_matches / max(len(rule.content_keywords), 1) if rule.content_keywords else 0
            
            # Combined confidence score with priority weighting
            if label_score > 0 or keyword_score > 0:
                confidence = (label_score * 0.6 + keyword_score * 0.4) * rule.priority_weight
                
                # Only include if meets minimum confidence threshold
                if confidence >= rule.min_confidence:
                    matches.append((rule.specialist_type, confidence))
        
        # Remove duplicates and sort by confidence
        unique_matches = {}
        for specialist_type, confidence in matches:
            if specialist_type not in unique_matches or confidence > unique_matches[specialist_type]:
                unique_matches[specialist_type] = confidence
        
        return sorted(unique_matches.items(), key=lambda x: x[1], reverse=True)
    
    def get_deliverable_specs(self, specialist_type: SpecialistType) -> List[DeliverableSpec]:
        """
        Get deliverable specifications for a specialist.
        
        Args:
            specialist_type: Type of specialist
            
        Returns:
            List of deliverable specifications
        """
        config = self.get_specialist_config(specialist_type)
        return config.deliverable_specs if config else []
    
    def get_quality_requirements(self, specialist_type: SpecialistType) -> Optional[QualityRequirement]:
        """
        Get quality requirements for a specialist.
        
        Args:
            specialist_type: Type of specialist
            
        Returns:
            Quality requirements or None if not found
        """
        config = self.get_specialist_config(specialist_type)
        return config.quality_requirements if config else None
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate all loaded configurations.
        
        Returns:
            Validation results dictionary
        """
        if not self._loaded:
            self.load_configurations()
        
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "specialist_count": len(self._specialist_configs),
            "rule_count": len(self._assignment_rules)
        }
        
        try:
            # Validate each specialist configuration
            for specialist_type, config in self._specialist_configs.items():
                # Check required fields
                if not config.name or not config.description:
                    results["errors"].append(f"{specialist_type.value}: Missing name or description")
                
                # Check assignment rules
                if not config.assignment_rules:
                    results["warnings"].append(f"{specialist_type.value}: No assignment rules defined")
                
                # Check deliverable specs
                if not config.deliverable_specs:
                    results["warnings"].append(f"{specialist_type.value}: No deliverable specs defined")
                
                # Validate deliverable templates exist
                for spec in config.deliverable_specs:
                    template_path = Path("templates/deliverables") / spec.template_name
                    if not template_path.exists():
                        results["warnings"].append(
                            f"{specialist_type.value}: Template '{spec.template_name}' not found"
                        )
            
            # Check for overlapping assignment rules
            label_usage = {}
            for rule in self._assignment_rules:
                for label in rule.trigger_labels:
                    if label not in label_usage:
                        label_usage[label] = []
                    label_usage[label].append(rule.specialist_type.value)
            
            for label, specialists in label_usage.items():
                if len(specialists) > 1:
                    results["warnings"].append(
                        f"Label '{label}' is used by multiple specialists: {', '.join(specialists)}"
                    )
            
            if results["errors"]:
                results["valid"] = False
            
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Validation error: {e}")
        
        return results
    
    def export_configuration_summary(self) -> Dict[str, Any]:
        """
        Export a comprehensive configuration summary.
        
        Returns:
            Configuration summary dictionary
        """
        if not self._loaded:
            self.load_configurations()
        
        summary = {
            "timestamp": str(datetime.now()),
            "total_specialists": len(self._specialist_configs),
            "total_assignment_rules": len(self._assignment_rules),
            "specialists": {}
        }
        
        for specialist_type, config in self._specialist_configs.items():
            specialist_summary = {
                "name": config.name,
                "description": config.description,
                "version": config.version,
                "enabled": config.enabled,
                "assignment_rules": len(config.assignment_rules),
                "deliverable_specs": len(config.deliverable_specs),
                "trigger_labels": [],
                "content_keywords": [],
                "quality_threshold": config.quality_requirements.min_confidence_score
            }
            
            # Collect all trigger labels and keywords
            for rule in config.assignment_rules:
                specialist_summary["trigger_labels"].extend(rule.trigger_labels)
                specialist_summary["content_keywords"].extend(rule.content_keywords)
            
            # Remove duplicates
            specialist_summary["trigger_labels"] = list(set(specialist_summary["trigger_labels"]))
            specialist_summary["content_keywords"] = list(set(specialist_summary["content_keywords"]))
            
            summary["specialists"][specialist_type.value] = specialist_summary
        
        return summary


# Module-level convenience functions
def load_specialist_configs(config_path: str = "config.yaml") -> SpecialistWorkflowConfigManager:
    """
    Load specialist workflow configurations.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configured SpecialistWorkflowConfigManager
    """
    manager = SpecialistWorkflowConfigManager(config_path)
    manager.load_configurations()
    return manager


def get_matching_specialists(labels: List[str], 
                           content_keywords: Optional[List[str]] = None,
                           config_path: str = "config.yaml") -> List[Tuple[SpecialistType, float]]:
    """
    Convenience function to find matching specialists.
    
    Args:
        labels: Issue labels
        content_keywords: Keywords from issue content
        config_path: Path to configuration file
        
    Returns:
        List of (specialist_type, confidence_score) tuples
    """
    manager = load_specialist_configs(config_path)
    return manager.find_matching_specialists(labels, content_keywords)