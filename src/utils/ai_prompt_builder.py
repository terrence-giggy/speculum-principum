"""
AI Prompt Builder

Centralized prompt construction utilities for consistent AI interactions across
the system, supporting content extraction, workflow assignment, and document generation.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json


class PromptType(Enum):
    """Types of AI prompts supported by the system"""
    CONTENT_EXTRACTION = "content_extraction"
    WORKFLOW_ASSIGNMENT = "workflow_assignment"
    SPECIALIST_ANALYSIS = "specialist_analysis"
    DOCUMENT_GENERATION = "document_generation"
    ENTITY_EXTRACTION = "entity_extraction"
    RELATIONSHIP_MAPPING = "relationship_mapping"


class SpecialistType(Enum):
    """Specialist agent types for analysis"""
    INTELLIGENCE_ANALYST = "intelligence-analyst"
    OSINT_RESEARCHER = "osint-researcher"
    TARGET_PROFILER = "target-profiler"
    THREAT_HUNTER = "threat-hunter"
    BUSINESS_ANALYST = "business-analyst"


@dataclass
class IssueContent:
    """Structured issue content for prompt building"""
    title: str
    body: str
    labels: List[str]
    number: int
    assignee: Optional[str] = None
    comments: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass 
class WorkflowInfo:
    """Workflow information for prompt context"""
    name: str
    description: str
    trigger_labels: List[str]
    deliverables: List[str]
    specialist_type: Optional[str] = None


@dataclass
class ExtractionFocus:
    """Focus areas for content extraction"""
    entities: bool = True
    relationships: bool = True
    events: bool = True
    indicators: bool = True
    timeline: bool = False
    technical_details: bool = False


class AIPromptBuilder:
    """
    Centralized AI prompt builder for consistent prompt generation across the system.
    
    Provides structured prompt templates for:
    - Content extraction from GitHub issues
    - Workflow assignment recommendations
    - Specialist analysis tasks
    - Document generation
    - Entity and relationship extraction
    """
    
    def __init__(self):
        self.system_context = (
            "You are an AI assistant specialized in intelligence analysis and "
            "information processing. You analyze GitHub issues containing intelligence "
            "information and help organize, extract, and structure data for various "
            "specialist workflows."
        )
    
    def build_content_extraction_prompt(self,
                                      issue: IssueContent,
                                      focus: Optional[ExtractionFocus] = None,
                                      specialist_context: Optional[str] = None) -> Dict[str, str]:
        """
        Build a comprehensive content extraction prompt.
        
        Args:
            issue: Issue content to analyze
            focus: Areas to focus extraction on
            specialist_context: Additional context for specialist workflows
            
        Returns:
            Dict with system and user messages
        """
        if focus is None:
            focus = ExtractionFocus()
        
        system_message = f"""{self.system_context}

Your task is to extract structured information from GitHub issue content. Focus on:
{self._format_extraction_focus(focus)}

{f"Specialist Context: {specialist_context}" if specialist_context else ""}

Return your analysis as valid JSON with the following structure:
{{
  "summary": "Brief summary of the issue content",
  "entities": {{
    "people": [list of person names mentioned],
    "organizations": [list of organization names],
    "locations": [list of places/locations],
    "technologies": [list of technical systems/tools],
    "domains": [list of websites/domains],
    "other": [other significant entities]
  }},
  "relationships": [
    {{"entity1": "name", "entity2": "name", "relationship": "description", "confidence": 0.8}}
  ],
  "events": [
    {{"description": "event description", "timestamp": "if available", "entities_involved": ["list"]}}
  ],
  "indicators": [
    {{"type": "IOC/TTP/behavior", "value": "indicator value", "confidence": 0.9}}
  ],
  "key_topics": ["topic1", "topic2"],
  "urgency_level": "low|medium|high|critical",
  "content_type": "research|intelligence|security|target|osint",
  "confidence_score": 0.85
}}"""

        user_message = self._format_issue_content(issue, include_comments=True)
        
        return {
            "system": system_message,
            "user": user_message
        }
    
    def build_workflow_assignment_prompt(self,
                                       issue: IssueContent,
                                       available_workflows: List[WorkflowInfo],
                                       confidence_threshold: float = 0.7) -> Dict[str, str]:
        """
        Build workflow assignment recommendation prompt.
        
        Args:
            issue: Issue to analyze for workflow assignment
            available_workflows: List of available workflows
            confidence_threshold: Minimum confidence for recommendations
            
        Returns:
            Dict with system and user messages
        """
        system_message = f"""{self.system_context}

Your task is to analyze a GitHub issue and recommend the most appropriate workflow(s) 
from the available options. Consider:
- Issue content and context
- Existing labels and assignments
- Workflow trigger criteria
- Specialist expertise required

Only recommend workflows with confidence >= {confidence_threshold}.

Return your analysis as valid JSON:
{{
  "summary": "Brief analysis of the issue",
  "key_topics": ["topic1", "topic2"],
  "suggested_workflows": ["workflow_name1", "workflow_name2"],
  "confidence_scores": {{"workflow_name1": 0.9, "workflow_name2": 0.7}},
  "reasoning": "Explanation for recommendations",
  "technical_indicators": ["indicator1", "indicator2"],
  "urgency_level": "low|medium|high|critical",
  "content_type": "research|intelligence|security|target|osint"
}}"""

        # Format available workflows
        workflow_descriptions = []
        for wf in available_workflows:
            workflow_descriptions.append(
                f"- **{wf.name}**: {wf.description}\n"
                f"  Trigger labels: {', '.join(wf.trigger_labels)}\n"
                f"  Deliverables: {', '.join(wf.deliverables[:3])}\n"
                f"  Specialist: {wf.specialist_type or 'General'}"
            )

        user_message = f"""{self._format_issue_content(issue)}

AVAILABLE WORKFLOWS:
{chr(10).join(workflow_descriptions)}

Analyze this issue and recommend the most appropriate workflow(s)."""

        return {
            "system": system_message,
            "user": user_message
        }
    
    def build_specialist_analysis_prompt(self,
                                       issue: IssueContent,
                                       specialist_type: SpecialistType,
                                       extracted_content: Optional[Dict[str, Any]] = None,
                                       analysis_focus: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Build specialist analysis prompt for specific agent types.
        
        Args:
            issue: Issue content to analyze
            specialist_type: Type of specialist analysis
            extracted_content: Previously extracted structured content
            analysis_focus: Specific areas to focus analysis on
            
        Returns:
            Dict with system and user messages
        """
        specialist_contexts = {
            SpecialistType.INTELLIGENCE_ANALYST: {
                "role": "Intelligence Analyst",
                "focus": "threat assessment, risk analysis, strategic implications",
                "output": "threat profiles, risk assessments, intelligence summaries"
            },
            SpecialistType.OSINT_RESEARCHER: {
                "role": "OSINT Researcher", 
                "focus": "open source intelligence, verification, digital footprint analysis",
                "output": "OSINT reports, source validation, digital intelligence"
            },
            SpecialistType.TARGET_PROFILER: {
                "role": "Target Profiler",
                "focus": "organizational analysis, key personnel, operational capabilities", 
                "output": "target profiles, organizational charts, capability assessments"
            },
            SpecialistType.THREAT_HUNTER: {
                "role": "Threat Hunter",
                "focus": "IOCs, TTPs, attack patterns, security indicators",
                "output": "threat intelligence, IOC lists, hunting queries"
            },
            SpecialistType.BUSINESS_ANALYST: {
                "role": "Business Analyst",
                "focus": "commercial intelligence, market analysis, business operations",
                "output": "business intelligence, competitive analysis, market reports"
            }
        }
        
        context = specialist_contexts[specialist_type]
        
        system_message = f"""{self.system_context}

You are acting as a {context['role']} analyzing intelligence information.

SPECIALIST FOCUS: {context['focus']}
EXPECTED OUTPUT: {context['output']}

{f"ANALYSIS FOCUS: {', '.join(analysis_focus)}" if analysis_focus else ""}

Provide detailed analysis from your specialist perspective. Return as valid JSON:
{{
  "specialist_analysis": {{
    "summary": "Key findings from specialist perspective",
    "key_insights": ["insight1", "insight2"],
    "recommendations": ["action1", "action2"],
    "threat_level": "low|medium|high|critical",
    "confidence": 0.85,
    "specialist_notes": "Additional specialist observations"
  }},
  "deliverables": {{
    "primary_output": "Main deliverable content",
    "supporting_data": ["data1", "data2"],
    "follow_up_actions": ["action1", "action2"]
  }},
  "quality_indicators": {{
    "completeness": 0.9,
    "accuracy": 0.85,
    "actionability": 0.8
  }}
}}"""

        user_content = self._format_issue_content(issue)
        
        if extracted_content:
            user_content += f"\n\nPREVIOUSLY EXTRACTED CONTENT:\n{json.dumps(extracted_content, indent=2)}"
        
        return {
            "system": system_message,
            "user": user_content
        }
    
    def build_document_generation_prompt(self,
                                       template_name: str,
                                       extracted_data: Dict[str, Any],
                                       specialist_analysis: Optional[Dict[str, Any]] = None,
                                       target_audience: str = "intelligence analyst") -> Dict[str, str]:
        """
        Build document generation prompt for creating deliverables.
        
        Args:
            template_name: Name of the document template/type
            extracted_data: Structured data extracted from issue
            specialist_analysis: Analysis from specialist agent
            target_audience: Intended audience for the document
            
        Returns:
            Dict with system and user messages
        """
        system_message = f"""{self.system_context}

You are generating a professional intelligence document of type: {template_name}

TARGET AUDIENCE: {target_audience}

Generate a well-structured, professional document that:
1. Incorporates all relevant extracted data
2. Follows intelligence reporting standards  
3. Is clear, actionable, and properly formatted
4. Includes appropriate sections and headers
5. Cites sources where applicable
6. Maintains professional tone and accuracy

Return the document content as valid JSON:
{{
  "document": {{
    "title": "Document title",
    "executive_summary": "Key findings and recommendations",
    "content": "Full document content in markdown format",
    "metadata": {{
      "document_type": "{template_name}",
      "classification": "appropriate classification level",
      "confidence": 0.85,
      "sources": ["source1", "source2"],
      "generated_at": "timestamp"
    }}
  }}
}}"""

        specialist_section = f"SPECIALIST ANALYSIS:\n{json.dumps(specialist_analysis, indent=2)}" if specialist_analysis else ""
        
        user_message = f"""Generate a {template_name} document using the following data:

EXTRACTED DATA:
{json.dumps(extracted_data, indent=2)}

{specialist_section}

Create a comprehensive, professional document appropriate for {target_audience}."""

        return {
            "system": system_message,
            "user": user_message
        }
    
    def build_entity_extraction_prompt(self,
                                     content: str,
                                     entity_types: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Build focused entity extraction prompt.
        
        Args:
            content: Text content to analyze
            entity_types: Specific entity types to focus on
            
        Returns:
            Dict with system and user messages
        """
        if entity_types is None:
            entity_types = ["people", "organizations", "locations", "technologies", "domains"]
        
        system_message = f"""{self.system_context}

Extract entities of these types: {', '.join(entity_types)}

Return as valid JSON:
{{
  "entities": {{
    {', '.join(f'"{et}": []' for et in entity_types)}
  }},
  "confidence_scores": {{
    "entity_name": 0.95
  }}
}}"""

        user_message = f"Extract entities from this content:\n\n{content}"
        
        return {
            "system": system_message,
            "user": user_message
        }
    
    def _format_issue_content(self, issue: IssueContent, include_comments: bool = False) -> str:
        """Format issue content for prompt inclusion"""
        content = f"""ISSUE #{issue.number}:
Title: {issue.title}
Labels: {', '.join(issue.labels) if issue.labels else 'None'}
{f"Assignee: {issue.assignee}" if issue.assignee else ""}
{f"Created: {issue.created_at}" if issue.created_at else ""}

CONTENT:
{issue.body or 'No description provided'}"""

        if include_comments and issue.comments:
            content += "\n\nCOMMENTS:\n" + "\n---\n".join(issue.comments)
        
        return content
    
    def _format_extraction_focus(self, focus: ExtractionFocus) -> str:
        """Format extraction focus areas for prompt"""
        focus_areas = []
        if focus.entities:
            focus_areas.append("- Entities (people, organizations, locations, technologies)")
        if focus.relationships:
            focus_areas.append("- Relationships between entities")  
        if focus.events:
            focus_areas.append("- Events and timeline information")
        if focus.indicators:
            focus_areas.append("- Indicators of Compromise (IOCs) and TTPs")
        if focus.timeline:
            focus_areas.append("- Temporal analysis and timelines")
        if focus.technical_details:
            focus_areas.append("- Technical systems and infrastructure details")
        
        return "\n".join(focus_areas) if focus_areas else "- General content analysis"
    
    def build_validation_prompt(self,
                              original_content: str,
                              extracted_data: Dict[str, Any],
                              validation_criteria: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Build prompt for validating extracted content.
        
        Args:
            original_content: Original source content
            extracted_data: Previously extracted structured data  
            validation_criteria: Specific criteria to validate against
            
        Returns:
            Dict with system and user messages for validation
        """
        if validation_criteria is None:
            validation_criteria = [
                "accuracy of extracted entities",
                "completeness of information",
                "correct relationship mappings",
                "appropriate confidence scores"
            ]
        
        system_message = f"""{self.system_context}

Validate extracted data against the original content. Check:
{chr(10).join(f"- {criteria}" for criteria in validation_criteria)}

Return validation results as JSON:
{{
  "validation_results": {{
    "accuracy_score": 0.9,
    "completeness_score": 0.8,
    "consistency_score": 0.95,
    "overall_quality": 0.88
  }},
  "issues_found": [
    {{"type": "missing_entity", "description": "Person X not extracted", "severity": "medium"}}
  ],
  "recommendations": [
    "Add missing entities", "Verify relationship Y"  
  ],
  "validated": true
}}"""

        user_message = f"""Validate this extracted data against the original content:

ORIGINAL CONTENT:
{original_content}

EXTRACTED DATA:
{json.dumps(extracted_data, indent=2)}

Check for accuracy, completeness, and consistency."""

        return {
            "system": system_message,
            "user": user_message
        }