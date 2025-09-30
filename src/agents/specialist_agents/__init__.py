"""
Specialist Agent Framework

This module provides the base framework for specialist analysis agents that can analyze
GitHub issues and provide domain-specific insights using AI-powered content extraction.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Type
import logging
import importlib
from pathlib import Path


class SpecialistType(Enum):
    """Types of specialist agents available in the system."""
    INTELLIGENCE_ANALYST = "intelligence-analyst"
    OSINT_RESEARCHER = "osint-researcher" 
    TARGET_PROFILER = "target-profiler"
    THREAT_HUNTER = "threat-hunter"
    BUSINESS_ANALYST = "business-analyst"


class AnalysisStatus(Enum):
    """Status of specialist analysis."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AnalysisResult:
    """Result of specialist agent analysis."""
    
    # Core identification
    specialist_type: SpecialistType
    issue_number: int
    analysis_id: str
    
    # Analysis content
    summary: str
    key_findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risk_assessment: Optional[Dict[str, Any]] = None
    confidence_score: float = 0.0
    
    # Technical details
    indicators: List[str] = field(default_factory=list)
    entities_analyzed: List[str] = field(default_factory=list)
    relationships_identified: List[str] = field(default_factory=list)
    
    # Metadata
    status: AnalysisStatus = AnalysisStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    
    # Additional context
    extracted_content: Optional[Dict[str, Any]] = None
    specialist_notes: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def mark_completed(self, processing_time: Optional[float] = None) -> None:
        """Mark analysis as completed with optional timing information."""
        self.status = AnalysisStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if processing_time is not None:
            self.processing_time_seconds = processing_time
    
    def mark_failed(self, error_message: str) -> None:
        """Mark analysis as failed with error details."""
        self.status = AnalysisStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "specialist_type": self.specialist_type.value,
            "issue_number": self.issue_number,
            "analysis_id": self.analysis_id,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "recommendations": self.recommendations,
            "risk_assessment": self.risk_assessment,
            "confidence_score": self.confidence_score,
            "indicators": self.indicators,
            "entities_analyzed": self.entities_analyzed,
            "relationships_identified": self.relationships_identified,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time_seconds": self.processing_time_seconds,
            "specialist_notes": self.specialist_notes,
            "error_message": self.error_message
        }


class SpecialistAgent(ABC):
    """
    Abstract base class for all specialist analysis agents.
    
    Specialist agents analyze extracted content from GitHub issues and provide
    domain-specific insights, recommendations, and risk assessments.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize specialist agent.
        
        Args:
            config: Configuration dictionary for the specialist
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._setup_specialist()
    
    @property
    @abstractmethod
    def specialist_type(self) -> SpecialistType:
        """Return the type of specialist this agent represents."""
        pass
    
    @property
    @abstractmethod
    def supported_labels(self) -> List[str]:
        """Return list of GitHub labels this specialist can handle."""
        pass
    
    @property
    @abstractmethod
    def required_capabilities(self) -> List[str]:
        """Return list of required AI capabilities (e.g., 'content_extraction', 'threat_analysis')."""
        pass
    
    @abstractmethod
    def analyze_issue(self, 
                     issue_data: Dict[str, Any],
                     extracted_content: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Perform specialist analysis on an issue.
        
        Args:
            issue_data: GitHub issue data
            extracted_content: Previously extracted structured content
            
        Returns:
            AnalysisResult with specialist findings and recommendations
        """
        pass
    
    @abstractmethod
    def validate_issue_compatibility(self, issue_data: Dict[str, Any]) -> bool:
        """
        Check if this specialist can analyze the given issue.
        
        Args:
            issue_data: GitHub issue data
            
        Returns:
            True if specialist can analyze this issue
        """
        pass
    
    def _setup_specialist(self) -> None:
        """Setup specialist-specific configuration. Override if needed."""
        pass
    
    def get_analysis_priority(self, issue_data: Dict[str, Any]) -> int:
        """
        Get priority score for analyzing this issue (higher = more priority).
        
        Args:
            issue_data: GitHub issue data
            
        Returns:
            Priority score (0-100)
        """
        # Default implementation based on label matching
        issue_labels = [label.get('name', '') if isinstance(label, dict) else str(label) 
                       for label in issue_data.get('labels', [])]
        
        matching_labels = set(issue_labels) & set(self.supported_labels)
        
        if not matching_labels:
            return 0
            
        # Base priority on number of matching labels
        base_priority = min(len(matching_labels) * 25, 75)
        
        # Bonus for exact specialist type match
        if self.specialist_type.value in issue_labels:
            base_priority += 25
            
        return min(base_priority, 100)
    
    def create_analysis_result(self, 
                             issue_number: int,
                             analysis_id: Optional[str] = None) -> AnalysisResult:
        """
        Create a new AnalysisResult instance for this specialist.
        
        Args:
            issue_number: GitHub issue number
            analysis_id: Unique analysis identifier (auto-generated if None)
            
        Returns:
            New AnalysisResult instance
        """
        if analysis_id is None:
            analysis_id = f"{self.specialist_type.value}-{issue_number}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            
        return AnalysisResult(
            specialist_type=self.specialist_type,
            issue_number=issue_number,
            analysis_id=analysis_id,
            summary="",  # To be filled by analysis
            extracted_content=None
        )


class SpecialistRegistry:
    """Registry for managing and dynamically loading specialist agents."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._specialists: Dict[SpecialistType, Type[SpecialistAgent]] = {}
        self._instances: Dict[SpecialistType, SpecialistAgent] = {}
        self._load_builtin_specialists()
    
    def register_specialist(self, 
                          specialist_class: Type[SpecialistAgent],
                          specialist_type: Optional[SpecialistType] = None) -> None:
        """
        Register a specialist agent class.
        
        Args:
            specialist_class: Specialist agent class to register
            specialist_type: Override specialist type (uses class property if None)
        """
        if specialist_type is None:
            # Get specialist type from class (need to create temporary instance)
            try:
                temp_instance = specialist_class()
                specialist_type = temp_instance.specialist_type
            except Exception as e:
                self.logger.error(f"Failed to determine specialist type for {specialist_class}: {e}")
                return
        
        self.logger.info(f"Registering specialist: {specialist_type.value} -> {specialist_class.__name__}")
        self._specialists[specialist_type] = specialist_class
    
    def get_specialist(self, 
                      specialist_type: Union[SpecialistType, str],
                      config: Optional[Dict[str, Any]] = None,
                      create_new: bool = False) -> Optional[SpecialistAgent]:
        """
        Get a specialist agent instance.
        
        Args:
            specialist_type: Type of specialist to retrieve
            config: Configuration for the specialist
            create_new: If True, always create new instance
            
        Returns:
            SpecialistAgent instance or None if not found
        """
        if isinstance(specialist_type, str):
            try:
                specialist_type = SpecialistType(specialist_type)
            except ValueError:
                self.logger.error(f"Unknown specialist type: {specialist_type}")
                return None
        
        if specialist_type not in self._specialists:
            self.logger.warning(f"Specialist type not registered: {specialist_type.value}")
            return None
        
        # Return existing instance if available and not creating new
        if not create_new and specialist_type in self._instances:
            return self._instances[specialist_type]
        
        # Create new instance
        try:
            specialist_class = self._specialists[specialist_type]
            instance = specialist_class(config=config)
            
            if not create_new:
                self._instances[specialist_type] = instance
                
            self.logger.debug(f"Created specialist instance: {specialist_type.value}")
            return instance
            
        except Exception as e:
            self.logger.error(f"Failed to create specialist {specialist_type.value}: {e}")
            return None
    
    def get_suitable_specialists(self, 
                               issue_data: Dict[str, Any],
                               min_priority: int = 1) -> List[SpecialistAgent]:
        """
        Get all specialists suitable for analyzing an issue, ranked by priority.
        
        Args:
            issue_data: GitHub issue data
            min_priority: Minimum priority score required
            
        Returns:
            List of specialist agents sorted by priority (highest first)
        """
        suitable_specialists = []
        
        for specialist_type in self._specialists:
            specialist = self.get_specialist(specialist_type)
            if specialist is None:
                continue
                
            if not specialist.validate_issue_compatibility(issue_data):
                continue
                
            priority = specialist.get_analysis_priority(issue_data)
            if priority >= min_priority:
                suitable_specialists.append((priority, specialist))
        
        # Sort by priority (highest first)
        suitable_specialists.sort(key=lambda x: x[0], reverse=True)
        
        return [specialist for priority, specialist in suitable_specialists]
    
    def get_registered_types(self) -> List[SpecialistType]:
        """Get list of all registered specialist types."""
        return list(self._specialists.keys())
    
    def _load_builtin_specialists(self) -> None:
        """Load built-in specialist agents from the specialist_agents module."""
        try:
            # Look for specialist agent modules in the current directory
            specialist_dir = Path(__file__).parent
            
            for module_file in specialist_dir.glob("*.py"):
                if module_file.name.startswith("_") or module_file.name == "__init__.py":
                    continue
                
                module_name = module_file.stem
                try:
                    # Import the module
                    full_module_name = f"src.agents.specialist_agents.{module_name}"
                    module = importlib.import_module(full_module_name)
                    
                    # Look for SpecialistAgent subclasses
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, SpecialistAgent) and 
                            attr != SpecialistAgent):
                            
                            self.logger.debug(f"Auto-registering specialist from {module_name}: {attr.__name__}")
                            self.register_specialist(attr)
                            
                except Exception as e:
                    self.logger.debug(f"Could not load specialist module {module_name}: {e}")
        
        except Exception as e:
            self.logger.debug(f"Could not scan for specialist modules: {e}")


# Global registry instance
_global_registry = None

def get_specialist_registry() -> SpecialistRegistry:
    """Get the global specialist registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = SpecialistRegistry()
    return _global_registry


def get_specialist(specialist_type: Union[SpecialistType, str], 
                  config: Optional[Dict[str, Any]] = None) -> Optional[SpecialistAgent]:
    """Convenience function to get a specialist from the global registry."""
    return get_specialist_registry().get_specialist(specialist_type, config=config, create_new=True)


# Export main classes and functions
__all__ = [
    'SpecialistType',
    'AnalysisStatus', 
    'AnalysisResult',
    'SpecialistAgent',
    'SpecialistRegistry',
    'get_specialist_registry',
    'get_specialist'
]