"""
Content Extraction Agent

AI-powered agent for extracting structured information from GitHub issues
and preparing data for specialist analysis workflows.
"""

import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime

from ..clients.github_models_client import GitHubModelsClient, AIResponse
from ..utils.ai_prompt_builder import (
    AIPromptBuilder, IssueContent, ExtractionFocus, 
    PromptType, SpecialistType
)
from ..utils.logging_config import get_logger, log_exception
from ..utils.config_manager import AIConfig


@dataclass
class Entity:
    """Extracted entity with metadata"""
    name: str
    type: str  # person, organization, location, technology, domain, other
    confidence: float
    context: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


@dataclass
class Relationship:
    """Relationship between entities"""
    entity1: str
    entity2: str
    relationship: str
    confidence: float
    context: Optional[str] = None


@dataclass
class Event:
    """Timeline event or activity"""
    description: str
    timestamp: Optional[str] = None
    entities_involved: Optional[List[str]] = None
    confidence: float = 0.8
    event_type: Optional[str] = None


@dataclass
class Indicator:
    """Security or intelligence indicator"""
    type: str  # IOC, TTP, behavior, pattern
    value: str
    confidence: float
    description: Optional[str] = None
    source: Optional[str] = None


@dataclass
class StructuredContent:
    """Complete structured content extracted from an issue"""
    summary: str
    entities: List[Entity]
    relationships: List[Relationship]
    events: List[Event]
    indicators: List[Indicator]
    key_topics: List[str]
    urgency_level: str  # low, medium, high, critical
    content_type: str  # research, intelligence, security, target, osint
    confidence_score: float
    extraction_timestamp: str
    
    def __post_init__(self):
        if not self.extraction_timestamp:
            self.extraction_timestamp = datetime.utcnow().isoformat()


@dataclass
class ExtractionResult:
    """Result of content extraction process"""
    success: bool
    structured_content: Optional[StructuredContent] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    ai_response_metadata: Optional[Dict[str, Any]] = None


class ContentExtractionAgent:
    """
    AI-powered content extraction agent for GitHub issues.
    
    Extracts structured information including entities, relationships, events,
    and indicators from issue content for specialist analysis workflows.
    
    Features:
    - Multi-stage extraction with validation
    - Specialist-specific extraction focus
    - Quality confidence scoring
    - Incremental extraction refinement
    """
    
    def __init__(self,
                 github_token: str,
                 ai_config: AIConfig,
                 enable_validation: bool = True):
        """
        Initialize content extraction agent.
        
        Args:
            github_token: GitHub token for AI models access
            ai_config: AI configuration settings
            enable_validation: Whether to validate extracted content
        """
        self.logger = get_logger(__name__)
        self.ai_config = ai_config
        self.enable_validation = enable_validation
        
        # Initialize AI client
        model = ai_config.models.content_extraction if ai_config.models else "gpt-4o"
        timeout = ai_config.settings.timeout_seconds if ai_config.settings else 30
        retries = ai_config.settings.retry_count if ai_config.settings else 3
        
        self.ai_client = GitHubModelsClient(
            github_token=github_token,
            model=model,
            timeout=timeout,
            max_retries=retries,
            enable_logging=ai_config.settings.enable_logging if ai_config.settings else True
        )
        
        # Initialize prompt builder
        self.prompt_builder = AIPromptBuilder()
        
        # Configuration
        self.confidence_threshold = (
            ai_config.confidence_thresholds.entity_extraction 
            if ai_config.confidence_thresholds else 0.7
        )
        
        self.logger.info(f"Initialized ContentExtractionAgent with model: {model}")
    
    def extract_content(self,
                       issue_data: Dict[str, Any],
                       extraction_focus: Optional[ExtractionFocus] = None,
                       specialist_context: Optional[str] = None) -> ExtractionResult:
        """
        Extract structured content from a GitHub issue.
        
        Args:
            issue_data: GitHub issue data dictionary
            extraction_focus: Specific areas to focus extraction on
            specialist_context: Context for specialist workflows
            
        Returns:
            ExtractionResult with structured content or error information
        """
        start_time = datetime.now()
        
        try:
            # Convert issue data to structured format
            issue_content = self._convert_issue_data(issue_data)
            
            # Build extraction prompt
            prompt_data = self.prompt_builder.build_content_extraction_prompt(
                issue=issue_content,
                focus=extraction_focus,
                specialist_context=specialist_context
            )
            
            # Call AI for content extraction
            ai_response = self._call_ai_extraction(prompt_data)
            
            # Parse AI response into structured content
            structured_content = self._parse_extraction_response(ai_response.content)
            
            # Validate extracted content if enabled
            if self.enable_validation:
                self._validate_extracted_content(structured_content)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ExtractionResult(
                success=True,
                structured_content=structured_content,
                processing_time_ms=int(processing_time),
                ai_response_metadata={
                    "model": ai_response.model,
                    "usage": ai_response.usage,
                    "response_time_ms": ai_response.response_time_ms
                }
            )
            
        except Exception as e:
            log_exception(self.logger, f"Content extraction failed for issue {issue_data.get('number', 'unknown')}", e)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ExtractionResult(
                success=False,
                error_message=str(e),
                processing_time_ms=int(processing_time)
            )
    
    def extract_entities_only(self,
                            content: str,
                            entity_types: Optional[List[str]] = None) -> ExtractionResult:
        """
        Extract only entities from text content.
        
        Args:
            content: Text content to analyze
            entity_types: Specific entity types to focus on
            
        Returns:
            ExtractionResult with entity data
        """
        try:
            prompt_data = self.prompt_builder.build_entity_extraction_prompt(
                content=content,
                entity_types=entity_types
            )
            
            ai_response = self._call_ai_extraction(prompt_data)
            entity_data = json.loads(ai_response.content)
            
            # Convert to Entity objects
            entities = []
            confidence_scores = entity_data.get('confidence_scores', {})
            
            for entity_type, entity_names in entity_data.get('entities', {}).items():
                for name in entity_names:
                    entities.append(Entity(
                        name=name,
                        type=entity_type,
                        confidence=confidence_scores.get(name, 0.8)
                    ))
            
            structured_content = StructuredContent(
                summary="Entity extraction only",
                entities=entities,
                relationships=[],
                events=[],
                indicators=[],
                key_topics=[],
                urgency_level="medium",
                content_type="extraction",
                confidence_score=0.8,
                extraction_timestamp=datetime.utcnow().isoformat()
            )
            
            return ExtractionResult(
                success=True,
                structured_content=structured_content,
                ai_response_metadata={"model": ai_response.model}
            )
            
        except Exception as e:
            log_exception(self.logger, "Entity extraction failed", e)
            return ExtractionResult(
                success=False,
                error_message=str(e)
            )
    
    def validate_extraction(self,
                          original_content: str,
                          extracted_data: StructuredContent) -> Dict[str, Any]:
        """
        Validate extracted content against original source.
        
        Args:
            original_content: Original issue content
            extracted_data: Previously extracted structured data
            
        Returns:
            Validation results with quality scores
        """
        try:
            prompt_data = self.prompt_builder.build_validation_prompt(
                original_content=original_content,
                extracted_data=asdict(extracted_data)
            )
            
            ai_response = self._call_ai_extraction(prompt_data)
            validation_result = json.loads(ai_response.content)
            
            self.logger.info(f"Validation completed with overall quality: {validation_result.get('validation_results', {}).get('overall_quality', 'unknown')}")
            
            return validation_result
            
        except Exception as e:
            log_exception(self.logger, "Validation failed", e)
            return {
                "validation_results": {"overall_quality": 0.0},
                "issues_found": [{"type": "validation_error", "description": str(e)}],
                "validated": False
            }

    def extract_multi_stage(self,
                           issue_data: Dict[str, Any],
                           specialist_type: Optional[SpecialistType] = None,
                           enable_refinement: bool = True) -> ExtractionResult:
        """
        Multi-stage content extraction with specialist-specific focus and refinement.
        
        This method performs extraction in multiple passes:
        1. Initial broad extraction
        2. Specialist-focused extraction (if specialist_type provided)
        3. Quality validation and refinement (if enabled)
        
        Args:
            issue_data: GitHub issue data dictionary
            specialist_type: Specific specialist to optimize extraction for
            enable_refinement: Whether to perform refinement pass
            
        Returns:
            ExtractionResult with enhanced structured content
        """
        start_time = datetime.now()
        
        try:
            # Stage 1: Initial broad extraction
            self.logger.info("Starting multi-stage extraction - Stage 1: Broad extraction")
            initial_result = self.extract_content(
                issue_data=issue_data,
                extraction_focus=ExtractionFocus(
                    entities=True,
                    relationships=True,
                    events=True,
                    indicators=True,
                    timeline=True,
                    technical_details=True
                )
            )
            
            if not initial_result.success or not initial_result.structured_content:
                return initial_result
            
            enhanced_content = initial_result.structured_content
            
            # Stage 2: Specialist-focused extraction (if specified)
            if specialist_type:
                self.logger.info("Stage 2: Specialist-focused extraction for %s", specialist_type.value)
                specialist_result = self._extract_specialist_focused(
                    issue_data, 
                    enhanced_content,
                    specialist_type
                )
                
                if specialist_result.success and specialist_result.structured_content:
                    enhanced_content = self._merge_extraction_results(
                        enhanced_content,
                        specialist_result.structured_content
                    )
            
            # Stage 3: Quality validation and refinement (if enabled)
            if enable_refinement and enhanced_content.confidence_score < 0.85:
                self.logger.info("Stage 3: Quality refinement (confidence: %.2f)", enhanced_content.confidence_score)
                refined_result = self._refine_extraction(issue_data, enhanced_content)
                
                if refined_result.success and refined_result.structured_content:
                    enhanced_content = refined_result.structured_content
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ExtractionResult(
                success=True,
                structured_content=enhanced_content,
                processing_time_ms=int(processing_time),
                ai_response_metadata={
                    "extraction_stages": ["broad", "specialist" if specialist_type else None, "refinement" if enable_refinement else None],
                    "specialist_type": specialist_type.value if specialist_type else None,
                    "final_confidence": enhanced_content.confidence_score
                }
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            log_exception(self.logger, "Multi-stage extraction failed", e)
            
            return ExtractionResult(
                success=False,
                error_message=str(e),
                processing_time_ms=int(processing_time)
            )

    def _extract_specialist_focused(self,
                                   issue_data: Dict[str, Any],
                                   initial_content: StructuredContent,
                                   specialist_type: SpecialistType) -> ExtractionResult:
        """
        Perform specialist-focused extraction based on the specialist type.
        
        Args:
            issue_data: Original issue data
            initial_content: Previously extracted content to enhance
            specialist_type: Type of specialist to optimize for
            
        Returns:
            ExtractionResult with specialist-focused enhancements
        """
        try:
            # Get specialist-specific extraction focus
            specialist_focus = self._get_specialist_extraction_focus(specialist_type)
            
            # Use specialist analysis prompt with extracted context
            issue_content = self._convert_issue_data(issue_data)
            
            # Build specialist analysis prompt
            prompt_data = self.prompt_builder.build_specialist_analysis_prompt(
                issue=issue_content,
                specialist_type=specialist_type,
                extracted_content=asdict(initial_content),
                analysis_focus=specialist_focus
            )
            
            # Call AI for specialist extraction
            ai_response = self._call_ai_extraction(prompt_data)
            
            # Parse specialist response - enhance initial content with new findings
            specialist_content = self._parse_specialist_enhancement_response(
                ai_response.content,
                initial_content,
                specialist_type
            )
            
            return ExtractionResult(
                success=True,
                structured_content=specialist_content,
                ai_response_metadata={
                    "model": ai_response.model,
                    "specialist_type": specialist_type.value,
                    "usage": ai_response.usage
                }
            )
            
        except Exception as e:
            log_exception(self.logger, "Specialist-focused extraction failed", e)
            return ExtractionResult(
                success=False,
                error_message=str(e)
            )

    def _refine_extraction(self,
                          issue_data: Dict[str, Any],
                          initial_content: StructuredContent) -> ExtractionResult:
        """
        Refine extraction results to improve quality and confidence.
        
        Args:
            issue_data: Original issue data
            initial_content: Previously extracted content to refine
            
        Returns:
            ExtractionResult with refined content
        """
        try:
            # Convert issue data
            issue_content = self._convert_issue_data(issue_data)
            
            # Use validation prompt to identify improvements needed
            validation_result = self.validate_extraction(
                original_content=f"{issue_content.title}\n\n{issue_content.body}",
                extracted_data=initial_content
            )
            
            # If validation found issues, perform enhanced extraction
            if validation_result.get('validation_results', {}).get('overall_quality', 1.0) < 0.85:
                # Re-extract with more focused prompt
                enhanced_focus = ExtractionFocus(
                    entities=True,
                    relationships=True,
                    events=True,
                    indicators=True,
                    timeline=True,
                    technical_details=True
                )
                
                enhanced_result = self.extract_content(
                    issue_data=issue_data,
                    extraction_focus=enhanced_focus
                )
                
                if enhanced_result.success and enhanced_result.structured_content:
                    # Only use enhanced result if it's actually better
                    if enhanced_result.structured_content.confidence_score > initial_content.confidence_score:
                        return enhanced_result
            
            # Return original if refinement didn't improve or failed
            return ExtractionResult(
                success=True,
                structured_content=initial_content,
                ai_response_metadata={"refinement_result": "no_improvement_needed"}
            )
                
        except Exception as e:
            log_exception(self.logger, "Extraction refinement failed", e)
            return ExtractionResult(
                success=False,
                error_message=str(e)
            )

    def _get_specialist_extraction_focus(self, specialist_type: SpecialistType) -> List[str]:
        """Get extraction focus areas for a specific specialist type."""
        focus_mapping = {
            SpecialistType.INTELLIGENCE_ANALYST: [
                "threat_actors", "attack_vectors", "targets", "capabilities",
                "indicators_of_compromise", "tactics_techniques_procedures"
            ],
            SpecialistType.OSINT_RESEARCHER: [
                "digital_footprint", "public_records", "technical_infrastructure",
                "social_media_presence", "domain_information", "contact_details"
            ],
            SpecialistType.TARGET_PROFILER: [
                "organizational_structure", "key_personnel", "business_operations",
                "technology_stack", "security_posture", "relationships"
            ],
            SpecialistType.THREAT_HUNTER: [
                "iocs", "ttps", "attack_patterns", "threat_indicators",
                "behavioral_patterns", "anomalies"
            ]
        }
        
        return focus_mapping.get(specialist_type, [
            "entities", "relationships", "events", "indicators"
        ])

    def _merge_extraction_results(self,
                                 initial: StructuredContent,
                                 specialist: StructuredContent) -> StructuredContent:
        """
        Merge initial extraction with specialist-focused results.
        
        Args:
            initial: Initial broad extraction results
            specialist: Specialist-focused extraction results
            
        Returns:
            Merged StructuredContent with enhanced information
        """
        # Merge entities (avoid duplicates by name)
        merged_entities = {entity.name: entity for entity in initial.entities}
        for entity in specialist.entities:
            if entity.name not in merged_entities or entity.confidence > merged_entities[entity.name].confidence:
                merged_entities[entity.name] = entity
        
        # Merge relationships (avoid duplicates)
        relationship_keys = {(rel.entity1, rel.entity2, rel.relationship) for rel in initial.relationships}
        merged_relationships = list(initial.relationships)
        
        for rel in specialist.relationships:
            key = (rel.entity1, rel.entity2, rel.relationship)
            if key not in relationship_keys:
                merged_relationships.append(rel)
                relationship_keys.add(key)
        
        # Merge events (avoid duplicates by description)
        event_descriptions = {event.description for event in initial.events}
        merged_events = list(initial.events)
        
        for event in specialist.events:
            if event.description not in event_descriptions:
                merged_events.append(event)
                event_descriptions.add(event.description)
        
        # Merge indicators (avoid duplicates by value)
        indicator_values = {indicator.value for indicator in initial.indicators}
        merged_indicators = list(initial.indicators)
        
        for indicator in specialist.indicators:
            if indicator.value not in indicator_values:
                merged_indicators.append(indicator)
                indicator_values.add(indicator.value)
        
        # Merge topics
        merged_topics = list(set(initial.key_topics + specialist.key_topics))
        
        # Use the higher confidence score and more specific content type
        confidence_score = max(initial.confidence_score, specialist.confidence_score)
        content_type = specialist.content_type if specialist.confidence_score > initial.confidence_score else initial.content_type
        urgency_level = specialist.urgency_level if specialist.urgency_level != "medium" else initial.urgency_level
        
        return StructuredContent(
            summary=specialist.summary if len(specialist.summary) > len(initial.summary) else initial.summary,
            entities=list(merged_entities.values()),
            relationships=merged_relationships,
            events=merged_events,
            indicators=merged_indicators,
            key_topics=merged_topics,
            urgency_level=urgency_level,
            content_type=content_type,
            confidence_score=confidence_score,
            extraction_timestamp=datetime.utcnow().isoformat()
        )
    
    def _convert_issue_data(self, issue_data: Dict[str, Any]) -> IssueContent:
        """Convert GitHub issue data to IssueContent format"""
        return IssueContent(
            title=issue_data.get('title', ''),
            body=issue_data.get('body', ''),
            labels=[label.get('name', '') for label in issue_data.get('labels', [])],
            number=issue_data.get('number', 0),
            assignee=issue_data.get('assignee', {}).get('login') if issue_data.get('assignee') else None,
            created_at=issue_data.get('created_at'),
            updated_at=issue_data.get('updated_at')
        )
    
    def _call_ai_extraction(self, prompt_data: Dict[str, str]) -> AIResponse:
        """Make AI call for content extraction"""
        messages = [
            {"role": "system", "content": prompt_data["system"]},
            {"role": "user", "content": prompt_data["user"]}
        ]
        
        # Use AI config settings if available
        temperature = self.ai_config.settings.temperature if self.ai_config.settings else 0.3
        max_tokens = self.ai_config.settings.max_tokens if self.ai_config.settings else 3000
        
        return self.ai_client.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def _parse_extraction_response(self, ai_content: str) -> StructuredContent:
        """Parse AI response into StructuredContent object"""
        try:
            # Clean up response if needed
            content = ai_content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            data = json.loads(content)
            
            # Convert entities
            entities = []
            for entity_type, entity_list in data.get('entities', {}).items():
                for entity_name in entity_list:
                    entities.append(Entity(
                        name=entity_name,
                        type=entity_type,
                        confidence=0.8  # Default confidence
                    ))
            
            # Convert relationships
            relationships = []
            for rel_data in data.get('relationships', []):
                relationships.append(Relationship(
                    entity1=rel_data.get('entity1', ''),
                    entity2=rel_data.get('entity2', ''),
                    relationship=rel_data.get('relationship', ''),
                    confidence=rel_data.get('confidence', 0.8),
                    context=rel_data.get('context')
                ))
            
            # Convert events
            events = []
            for event_data in data.get('events', []):
                events.append(Event(
                    description=event_data.get('description', ''),
                    timestamp=event_data.get('timestamp'),
                    entities_involved=event_data.get('entities_involved', []),
                    confidence=event_data.get('confidence', 0.8)
                ))
            
            # Convert indicators
            indicators = []
            for ind_data in data.get('indicators', []):
                indicators.append(Indicator(
                    type=ind_data.get('type', ''),
                    value=ind_data.get('value', ''),
                    confidence=ind_data.get('confidence', 0.8),
                    description=ind_data.get('description')
                ))
            
            return StructuredContent(
                summary=data.get('summary', ''),
                entities=entities,
                relationships=relationships,
                events=events,
                indicators=indicators,
                key_topics=data.get('key_topics', []),
                urgency_level=data.get('urgency_level', 'medium'),
                content_type=data.get('content_type', 'research'),
                confidence_score=data.get('confidence_score', 0.8),
                extraction_timestamp=datetime.utcnow().isoformat()
            )
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse AI response as JSON: {e}")
            self.logger.error(f"Raw AI content: {ai_content}")
            raise ValueError(f"Invalid AI response format: {e}")
        except KeyError as e:
            self.logger.error(f"Missing required field in AI response: {e}")
            raise ValueError(f"Incomplete AI response: {e}")
    
    def _parse_specialist_enhancement_response(self,
                                              ai_content: str,
                                              initial_content: StructuredContent,
                                              specialist_type: SpecialistType) -> StructuredContent:
        """
        Parse specialist analysis response and enhance the initial content.
        
        Args:
            ai_content: Raw AI response content
            initial_content: Previously extracted content to enhance
            specialist_type: Type of specialist that performed the analysis
            
        Returns:
            Enhanced StructuredContent with specialist findings
        """
        try:
            # For now, parse as regular extraction and merge
            # In a full implementation, this would handle specialist-specific response format
            specialist_extraction = self._parse_extraction_response(ai_content)
            
            # Merge with initial content, giving preference to specialist findings
            return self._merge_extraction_results(initial_content, specialist_extraction)
            
        except Exception as e:
            # If specialist parsing fails, return enhanced initial content with specialist metadata
            self.logger.warning("Failed to parse specialist response, returning enhanced initial content: %s", str(e))
            
            # Create an enhanced copy of initial content with specialist context
            enhanced_summary = f"[{specialist_type.value.upper()} Analysis] {initial_content.summary}"
            
            return StructuredContent(
                summary=enhanced_summary,
                entities=initial_content.entities,
                relationships=initial_content.relationships,
                events=initial_content.events,
                indicators=initial_content.indicators,
                key_topics=initial_content.key_topics + [specialist_type.value],
                urgency_level=initial_content.urgency_level,
                content_type=initial_content.content_type,
                confidence_score=min(initial_content.confidence_score * 0.9, 1.0),  # Slight penalty for parsing failure
                extraction_timestamp=datetime.utcnow().isoformat()
            )

    def _validate_extracted_content(self, content: StructuredContent):
        """Validate extracted content meets quality requirements"""
        if content.confidence_score < self.confidence_threshold:
            self.logger.warning(f"Low confidence score: {content.confidence_score}")
        
        if not content.summary or len(content.summary) < 10:
            raise ValueError("Summary is too short or missing")
        
        if not content.entities and not content.events:
            self.logger.warning("No entities or events extracted - content may be sparse")
        
        # Validate entity confidence scores
        low_confidence_entities = [e for e in content.entities if e.confidence < self.confidence_threshold]
        if low_confidence_entities:
            self.logger.warning(f"Found {len(low_confidence_entities)} low-confidence entities")
    
    def get_extraction_statistics(self) -> Dict[str, Any]:
        """Get statistics about the extraction agent"""
        return {
            "agent_type": "ContentExtractionAgent",
            "ai_model": self.ai_client.model,
            "confidence_threshold": self.confidence_threshold,
            "validation_enabled": self.enable_validation,
            "rate_limit_status": self.ai_client.get_rate_limit_status()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the extraction agent"""
        try:
            # Test AI client
            ai_health = self.ai_client.health_check()
            
            return {
                "status": "healthy" if ai_health["status"] == "healthy" else "unhealthy",
                "agent_type": "ContentExtractionAgent",
                "ai_client_status": ai_health,
                "configuration": {
                    "model": self.ai_client.model,
                    "confidence_threshold": self.confidence_threshold,
                    "validation_enabled": self.enable_validation
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            log_exception(self.logger, "Health check failed", e)
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }