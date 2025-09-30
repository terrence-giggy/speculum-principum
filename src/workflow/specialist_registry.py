"""
Specialist Workflow Registry

This module provides a centralized registry for managing specialist workflows
and integrating with the existing WorkflowMatcher system. Implements the
coordination layer for Task 3.3.
"""

import os
import yaml
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from .specialist_workflow_config import (
    SpecialistWorkflowConfigManager, 
    SpecialistType, 
    AssignmentRule,
    DeliverableSpec,
    QualityRequirement
)
from .workflow_matcher import WorkflowMatcher, WorkflowInfo
from ..utils.logging_config import get_logger, log_exception


@dataclass
class SpecialistAssignment:
    """Result of specialist assignment process."""
    specialist_type: SpecialistType
    confidence: float
    workflow_name: str
    trigger_labels: List[str]
    recommended_deliverables: List[str]
    quality_threshold: float
    assignment_reason: str


class SpecialistWorkflowRegistry:
    """
    Registry for managing specialist workflows and assignments.
    
    Integrates specialist configuration with the existing workflow system
    to provide unified workflow management.
    """
    
    def __init__(self, 
                 config_path: str = "config.yaml",
                 workflow_directory: str = "docs/workflow/deliverables"):
        """
        Initialize the specialist workflow registry.
        
        Args:
            config_path: Path to main configuration file
            workflow_directory: Directory containing workflow definitions
        """
        self.logger = get_logger(__name__)
        self.config_manager = SpecialistWorkflowConfigManager(config_path, workflow_directory)
        self.workflow_matcher = WorkflowMatcher(workflow_directory)
        self.workflow_directory = Path(workflow_directory)
        
        # Registry state
        self._initialized = False
        self._specialist_workflows: Dict[SpecialistType, List[WorkflowInfo]] = {}
        self._workflow_to_specialist: Dict[str, SpecialistType] = {}
    
    def initialize(self, force_reload: bool = False) -> None:
        """
        Initialize the registry by loading all configurations.
        
        Args:
            force_reload: Force reload even if already initialized
        """
        if self._initialized and not force_reload:
            return
        
        try:
            self.logger.info("Initializing specialist workflow registry...")
            
            # Load specialist configurations
            self.config_manager.load_configurations(force_reload)
            
            # WorkflowMatcher loads workflows automatically on initialization
            # Build specialist-workflow mapping
            self._build_specialist_workflow_mapping()
            
            self._initialized = True
            self.logger.info("Specialist workflow registry initialized successfully")
            
        except Exception as e:
            log_exception(self.logger, "Failed to initialize specialist workflow registry", e)
            raise
    
    def _build_specialist_workflow_mapping(self) -> None:
        """Build mapping between specialists and their workflows."""
        self._specialist_workflows.clear()
        self._workflow_to_specialist.clear()
        
        # Get all available workflows
        available_workflows = self.workflow_matcher.get_available_workflows()
        specialist_configs = self.config_manager.get_all_specialist_configs()
        
        # Map workflows to specialists based on labels
        for workflow in available_workflows:
            workflow_labels = set(workflow.trigger_labels)
            
            # Find matching specialist based on trigger labels
            best_match = None
            best_score = 0.0
            
            for specialist_type, config in specialist_configs.items():
                for rule in config.assignment_rules:
                    rule_labels = set(rule.trigger_labels)
                    overlap = len(workflow_labels.intersection(rule_labels))
                    
                    if overlap > 0:
                        score = overlap / len(rule_labels) if rule_labels else 0
                        if score > best_score:
                            best_score = score
                            best_match = specialist_type
            
            # Assign workflow to best matching specialist
            if best_match and best_score >= 0.5:  # Minimum 50% label overlap
                if best_match not in self._specialist_workflows:
                    self._specialist_workflows[best_match] = []
                
                self._specialist_workflows[best_match].append(workflow)
                self._workflow_to_specialist[workflow.name] = best_match
                
                self.logger.debug(
                    f"Mapped workflow '{workflow.name}' to specialist '{best_match.value}' "
                    f"(score: {best_score:.2f})"
                )
    
    def assign_specialist_to_issue(self, 
                                 issue_labels: List[str],
                                 issue_content: Optional[str] = None,
                                 min_confidence: float = 0.6) -> Optional[SpecialistAssignment]:
        """
        Assign a specialist to an issue based on labels and content.
        
        Args:
            issue_labels: Labels attached to the issue
            issue_content: Issue title and body content
            min_confidence: Minimum confidence threshold for assignment
            
        Returns:
            SpecialistAssignment if match found, None otherwise
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # Extract keywords from content if provided
            content_keywords = []
            if issue_content:
                content_keywords = self._extract_content_keywords(issue_content)
            
            # Find matching specialists
            matches = self.config_manager.find_matching_specialists(issue_labels, content_keywords)
            
            if not matches:
                self.logger.debug("No specialist matches found")
                return None
            
            # Get the best match
            specialist_type, confidence = matches[0]
            
            if confidence < min_confidence:
                self.logger.debug(f"Best match confidence {confidence:.2f} below threshold {min_confidence}")
                return None
            
            # Get specialist configuration
            config = self.config_manager.get_specialist_config(specialist_type)
            if not config:
                self.logger.warning(f"No configuration found for specialist {specialist_type.value}")
                return None
            
            # Find matching workflow
            specialist_workflows = self._specialist_workflows.get(specialist_type, [])
            if not specialist_workflows:
                self.logger.warning(f"No workflows found for specialist {specialist_type.value}")
                return None
            
            # Get the primary workflow for this specialist
            primary_workflow = specialist_workflows[0]  # First workflow is primary
            
            # Determine recommended deliverables based on labels
            recommended_deliverables = []
            for spec in config.deliverable_specs:
                if self._matches_deliverable_conditions(spec, issue_labels):
                    recommended_deliverables.append(spec.name)
            
            # Build trigger labels for workflow assignment
            trigger_labels = []
            for rule in config.assignment_rules:
                if set(issue_labels).intersection(set(rule.trigger_labels)):
                    trigger_labels.extend(rule.trigger_labels)
            
            # Remove duplicates and filter to labels that match
            trigger_labels = list(set(trigger_labels).intersection(set(issue_labels)))
            
            # If no direct trigger labels, use the first rule's labels
            if not trigger_labels and config.assignment_rules:
                trigger_labels = config.assignment_rules[0].trigger_labels[:2]  # Use first 2 labels
            
            assignment = SpecialistAssignment(
                specialist_type=specialist_type,
                confidence=confidence,
                workflow_name=primary_workflow.name,
                trigger_labels=trigger_labels,
                recommended_deliverables=recommended_deliverables,
                quality_threshold=config.quality_requirements.min_confidence_score,
                assignment_reason=f"Matched {len(matches)} specialists, selected {config.name} with {confidence:.2f} confidence"
            )
            
            self.logger.info(
                f"Assigned specialist '{specialist_type.value}' with confidence {confidence:.2f} "
                f"for workflow '{primary_workflow.name}'"
            )
            
            return assignment
            
        except Exception as e:
            log_exception(self.logger, "Failed to assign specialist to issue", e)
            return None
    
    def _extract_content_keywords(self, content: str) -> List[str]:
        """
        Extract relevant keywords from issue content.
        
        Args:
            content: Issue content (title + body)
            
        Returns:
            List of extracted keywords
        """
        if not content:
            return []
        
        # Simple keyword extraction - can be enhanced with NLP
        content_lower = content.lower()
        
        # Predefined intelligence keywords
        intelligence_keywords = [
            "threat", "analysis", "intelligence", "strategic", "geopolitical",
            "campaign", "apt", "threat-actor", "adversary", "attack"
        ]
        
        osint_keywords = [
            "osint", "reconnaissance", "verification", "research", "investigation",
            "digital footprint", "social media", "public records", "source analysis"
        ]
        
        profiler_keywords = [
            "target", "organization", "profile", "stakeholder", "business",
            "company", "personnel", "leadership", "organizational"
        ]
        
        found_keywords = []
        all_keywords = intelligence_keywords + osint_keywords + profiler_keywords
        
        for keyword in all_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _matches_deliverable_conditions(self, 
                                      deliverable_spec: DeliverableSpec, 
                                      issue_labels: List[str]) -> bool:
        """
        Check if deliverable conditions are met by issue labels.
        
        Args:
            deliverable_spec: Deliverable specification
            issue_labels: Issue labels
            
        Returns:
            True if conditions are met
        """
        if not deliverable_spec.conditions:
            return True  # No conditions means always match
        
        issue_label_set = set(issue_labels)
        
        for condition in deliverable_spec.conditions:
            if condition.get("type") == "label":
                required_labels = set(condition.get("values", []))
                if required_labels.intersection(issue_label_set):
                    return True
        
        return False
    
    def get_specialist_workflows(self, specialist_type: SpecialistType) -> List[WorkflowInfo]:
        """
        Get workflows available for a specific specialist.
        
        Args:
            specialist_type: Type of specialist
            
        Returns:
            List of workflow information
        """
        if not self._initialized:
            self.initialize()
        
        return self._specialist_workflows.get(specialist_type, [])
    
    def get_workflow_specialist(self, workflow_name: str) -> Optional[SpecialistType]:
        """
        Get the specialist type associated with a workflow.
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Specialist type or None if not found
        """
        if not self._initialized:
            self.initialize()
        
        return self._workflow_to_specialist.get(workflow_name)
    
    def get_all_specialist_workflows(self) -> Dict[SpecialistType, List[WorkflowInfo]]:
        """
        Get all specialist-workflow mappings.
        
        Returns:
            Dictionary mapping specialist types to their workflows
        """
        if not self._initialized:
            self.initialize()
        
        return self._specialist_workflows.copy()
    
    def validate_registry(self) -> Dict[str, Any]:
        """
        Validate the registry configuration and mappings.
        
        Returns:
            Validation results
        """
        if not self._initialized:
            self.initialize()
        
        # Validate specialist configurations
        config_validation = self.config_manager.validate_configuration()
        
        # Additional registry-specific validation
        registry_validation = {
            "specialist_workflow_mappings": len(self._specialist_workflows),
            "workflow_specialist_mappings": len(self._workflow_to_specialist),
            "unmapped_workflows": [],
            "specialists_without_workflows": []
        }
        
        # Find unmapped workflows
        all_workflows = self.workflow_matcher.get_available_workflows()
        mapped_workflows = set(self._workflow_to_specialist.keys())
        
        for workflow in all_workflows:
            if workflow.name not in mapped_workflows:
                registry_validation["unmapped_workflows"].append(workflow.name)
        
        # Find specialists without workflows
        all_specialists = set(self.config_manager.get_all_specialist_configs().keys())
        specialists_with_workflows = set(self._specialist_workflows.keys())
        
        for specialist_type in all_specialists:
            if specialist_type not in specialists_with_workflows:
                registry_validation["specialists_without_workflows"].append(specialist_type.value)
        
        # Combine validations
        validation_result = {
            "timestamp": str(datetime.now()),
            "registry_valid": len(registry_validation["unmapped_workflows"]) == 0,
            "config_validation": config_validation,
            "registry_validation": registry_validation
        }
        
        return validation_result
    
    def get_registry_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive registry statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self._initialized:
            self.initialize()
        
        # Get configuration summary
        config_summary = self.config_manager.export_configuration_summary()
        
        # Add registry-specific statistics
        stats = {
            "timestamp": str(datetime.now()),
            "total_specialists": len(self.config_manager.get_all_specialist_configs()),
            "total_workflows": len(self.workflow_matcher.get_available_workflows()),
            "mapped_workflows": len(self._workflow_to_specialist),
            "specialists_with_workflows": len(self._specialist_workflows),
            "average_workflows_per_specialist": 0,
            "specialist_breakdown": {},
            "workflow_distribution": {},
            "configuration_summary": config_summary
        }
        
        # Calculate average workflows per specialist
        if self._specialist_workflows:
            total_workflow_assignments = sum(len(workflows) for workflows in self._specialist_workflows.values())
            stats["average_workflows_per_specialist"] = total_workflow_assignments / len(self._specialist_workflows)
        
        # Specialist breakdown
        for specialist_type, workflows in self._specialist_workflows.items():
            stats["specialist_breakdown"][specialist_type.value] = {
                "workflow_count": len(workflows),
                "workflow_names": [w.name for w in workflows],
                "configuration_loaded": specialist_type in self.config_manager.get_all_specialist_configs()
            }
        
        # Workflow distribution
        for workflow_name, specialist_type in self._workflow_to_specialist.items():
            if specialist_type.value not in stats["workflow_distribution"]:
                stats["workflow_distribution"][specialist_type.value] = []
            stats["workflow_distribution"][specialist_type.value].append(workflow_name)
        
        return stats


# Module-level convenience functions
def create_registry(config_path: str = "config.yaml") -> SpecialistWorkflowRegistry:
    """
    Create and initialize a specialist workflow registry.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Initialized SpecialistWorkflowRegistry
    """
    registry = SpecialistWorkflowRegistry(config_path)
    registry.initialize()
    return registry


def assign_specialist_for_issue(issue_labels: List[str],
                               issue_content: Optional[str] = None,
                               config_path: str = "config.yaml") -> Optional[SpecialistAssignment]:
    """
    Convenience function to assign specialist to an issue.
    
    Args:
        issue_labels: Issue labels
        issue_content: Issue content
        config_path: Path to configuration file
        
    Returns:
        SpecialistAssignment if match found
    """
    registry = create_registry(config_path)
    return registry.assign_specialist_to_issue(issue_labels, issue_content)