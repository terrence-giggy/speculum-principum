"""
OSINT Researcher Specialist Agent

This module provides an AI-powered OSINT (Open Source Intelligence) researcher agent that specializes in:
- Digital footprint analysis and reconnaissance
- Information verification and source credibility assessment
- Research gap identification and information collection planning
- Cross-reference validation with multiple sources
- Technical infrastructure analysis and domain intelligence

The agent focuses on verification, validation, and expanding intelligence collection
through open source methodologies and techniques.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import SpecialistAgent, SpecialistType, AnalysisResult, AnalysisStatus
from ...utils.ai_prompt_builder import AIPromptBuilder, PromptType
from ...clients.github_models_client import GitHubModelsClient


class OSINTResearcherAgent(SpecialistAgent):
    """
    OSINT Researcher specialist agent for information verification and digital reconnaissance.
    
    This agent provides comprehensive OSINT analysis including:
    - Digital footprint mapping and analysis
    - Source credibility assessment and verification
    - Technical infrastructure reconnaissance
    - Social media and public records analysis
    - Information gap identification and collection planning
    - Cross-reference validation with multiple sources
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize OSINT Researcher agent.
        
        Args:
            config: Configuration dictionary containing AI client settings
        """
        super().__init__(config)
        self.ai_client = self._initialize_ai_client()
        self.prompt_builder = AIPromptBuilder()
    
    def _initialize_ai_client(self):
        """Initialize AI client for OSINT analysis."""
        try:
            if self.config and 'ai' in self.config:
                return GitHubModelsClient(
                    github_token=self.config.get('github_token'),
                    model_config=self.config['ai']
                )
        except Exception as e:
            self.logger.warning(f"Failed to initialize AI client: {e}")
        return None
        
    @property
    def specialist_type(self) -> SpecialistType:
        """Return specialist type for OSINT research."""
        return SpecialistType.OSINT_RESEARCHER
    
    @property
    def supported_labels(self) -> List[str]:
        """Return GitHub labels this specialist can analyze."""
        return [
            'osint',
            'osint-researcher',
            'reconnaissance', 
            'digital-footprint',
            'verification',
            'source-analysis',
            'public-records',
            'social-media',
            'domain-analysis',
            'technical-infrastructure',
            'information-gathering',
            'research',
            'validation',
            'cross-reference',
            'investigation',
            'open-source-intelligence',
            'cyber-reconnaissance',
            'footprinting',
            'enumeration',
            'passive-reconnaissance'
        ]
    
    @property
    def required_capabilities(self) -> List[str]:
        """Return required AI capabilities for OSINT research."""
        return [
            'content_extraction',
            'source_verification',
            'digital_footprint_analysis',
            'research_gap_identification',
            'cross_referencing',
            'information_validation'
        ]
    
    def validate_issue_compatibility(self, issue_data: Dict[str, Any]) -> bool:
        """
        Validate if this issue is suitable for OSINT research analysis.
        
        Args:
            issue_data: GitHub issue data
            
        Returns:
            True if issue contains OSINT-relevant content
        """
        # Check labels for OSINT indicators
        labels = self._extract_labels(issue_data)
        
        # High priority OSINT labels
        high_priority_labels = {
            'osint', 'reconnaissance', 'digital-footprint', 'verification',
            'investigation', 'research', 'open-source-intelligence'
        }
        
        if high_priority_labels.intersection(labels):
            return True
        
        # Check content for OSINT keywords
        content = self._extract_content_text(issue_data)
        osint_keywords = [
            'osint', 'reconnaissance', 'footprint', 'verification', 'source',
            'digital', 'public records', 'social media', 'domain', 'whois',
            'dns', 'subdomain', 'email', 'phone', 'address', 'investigation',
            'research', 'validate', 'cross-reference', 'verify', 'confirm'
        ]
        
        keyword_matches = sum(1 for keyword in osint_keywords 
                            if keyword.lower() in content.lower())
        
        # Require at least 2 OSINT-related keywords for compatibility
        return keyword_matches >= 2
    
    def calculate_priority_score(self, issue_data: Dict[str, Any]) -> float:
        """
        Calculate priority score based on OSINT research value.
        
        Args:
            issue_data: GitHub issue data
            
        Returns:
            Priority score between 0.0 and 1.0
        """
        score = 0.0
        labels = self._extract_labels(issue_data)
        content = self._extract_content_text(issue_data)
        
        # Label-based scoring
        high_value_labels = {
            'osint': 0.3,
            'reconnaissance': 0.25, 
            'digital-footprint': 0.25,
            'verification': 0.2,
            'investigation': 0.2,
            'research': 0.15
        }
        
        for label in labels:
            if label in high_value_labels:
                score += high_value_labels[label]
        
        # Content-based indicators
        verification_indicators = [
            'verify', 'validate', 'confirm', 'cross-reference', 'source',
            'credibility', 'reliability', 'accuracy'
        ]
        
        digital_indicators = [
            'domain', 'email', 'phone', 'address', 'social media',
            'website', 'dns', 'whois', 'ip address'
        ]
        
        research_indicators = [
            'public records', 'investigation', 'background', 'profile',
            'footprint', 'trace', 'identify', 'locate'
        ]
        
        indicator_sets = [verification_indicators, digital_indicators, research_indicators]
        for indicator_set in indicator_sets:
            matches = sum(1 for indicator in indicator_set 
                         if indicator.lower() in content.lower())
            if matches > 0:
                score += min(matches * 0.05, 0.15)  # Cap contribution per set
        
        return min(score, 1.0)
    
    def analyze_issue(self, issue_data: Dict[str, Any], extracted_content: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Perform OSINT research analysis on issue content.
        
        Args:
            issue_data: Original GitHub issue data
            extracted_content: Previously extracted structured content (optional)
            
        Returns:
            AnalysisResult containing OSINT research findings
        """
        # Use extracted content if provided, otherwise use issue data directly
        structured_content = extracted_content or {}
        
        return self._perform_osint_analysis(structured_content, issue_data)
    
    def _perform_osint_analysis(self, structured_content: Dict[str, Any], issue_data: Dict[str, Any]) -> AnalysisResult:
        """
        Internal method to perform comprehensive OSINT analysis.
        
        Args:
            structured_content: Extracted entities, relationships, events, indicators
            issue_data: Original GitHub issue data
            
        Returns:
            AnalysisResult containing OSINT research findings
        """
        try:
            analysis_id = str(uuid.uuid4())[:8]
            issue_number = issue_data.get('number', 0)
            
            # Use AI analysis if available
            if self.ai_client:
                analysis = self._perform_ai_osint_analysis(structured_content, issue_data)
                if analysis:
                    # Extract findings for AnalysisResult
                    findings = analysis.get('findings', {})
                    recommendations_data = analysis.get('recommendations', {})
                    
                    return AnalysisResult(
                        specialist_type=self.specialist_type,
                        issue_number=issue_number,
                        analysis_id=analysis_id,
                        summary=f"OSINT research analysis completed for issue #{issue_number}",
                        key_findings=[
                            f"Digital footprint: {findings.get('digital_footprint', {}).get('assessment', 'Not assessed')}",
                            f"Source verification: {findings.get('source_verification', {}).get('reliability', 'Pending')}",
                            f"Research gaps identified: {len(analysis.get('intelligence_gaps', []))}"
                        ],
                        recommendations=[
                            action for action in recommendations_data.get('immediate_actions', [])
                        ],
                        confidence_score=analysis.get('confidence_assessment', {}).get('overall', 0.7),
                        status=AnalysisStatus.COMPLETED,
                        specialist_notes={
                            'osint_analysis': analysis,
                            'processing_method': 'ai_enhanced',
                            'model_version': getattr(self.ai_client, 'model_version', 'unknown')
                        }
                    )
            
            # Fallback to rule-based analysis
            fallback_analysis = self._perform_fallback_osint_analysis(structured_content, issue_data)
            findings = fallback_analysis.get('findings', {})
            recommendations_data = fallback_analysis.get('recommendations', {})
            
            result = AnalysisResult(
                specialist_type=self.specialist_type,
                issue_number=issue_number,
                analysis_id=analysis_id,
                summary=f"OSINT research analysis completed using fallback methods for issue #{issue_number}",
                key_findings=[
                    f"Digital entities identified: {len(findings.get('digital_footprint', {}).get('opportunities', []))}",
                    f"Verification targets: {len(findings.get('verification_status', {}).get('requires_verification', []))}",
                    f"Research gaps: {len(fallback_analysis.get('intelligence_gaps', []))}"
                ],
                recommendations=[
                    action for action in recommendations_data.get('immediate_actions', [])
                ],
                confidence_score=fallback_analysis.get('confidence_assessment', {}).get('overall', 0.6),
                status=AnalysisStatus.COMPLETED,
                specialist_notes={
                    'osint_analysis': fallback_analysis,
                    'processing_method': 'fallback_analysis'
                }
            )
            
            result.mark_completed()
            return result
            
        except Exception as e:
            self.logger.error(f"OSINT analysis failed: {e}")
            result = AnalysisResult(
                specialist_type=self.specialist_type,
                issue_number=issue_data.get('number', 0),
                analysis_id=str(uuid.uuid4())[:8],
                summary=f"OSINT analysis failed due to error: {str(e)}",
                key_findings=[],
                recommendations=[],
                confidence_score=0.0,
                status=AnalysisStatus.FAILED,
                error_message=str(e)
            )
            result.mark_failed(str(e))
            return result
    
    def _perform_ai_osint_analysis(self, structured_content: Dict[str, Any], issue_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Perform AI-powered OSINT research analysis."""
        try:
            analysis_prompt = self._build_osint_analysis_prompt(structured_content, issue_data)
            
            response = self.ai_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": self._get_osint_researcher_persona()
                    },
                    {
                        "role": "user", 
                        "content": analysis_prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=4000
            )
            
            if response and response.content:
                return self._parse_osint_analysis_response(response.content)
            
            return None
            
        except Exception as e:
            self.logger.error(f"AI OSINT analysis failed: {e}")
            return None
    
    def _get_osint_researcher_persona(self) -> str:
        """Return OSINT researcher persona for AI interactions."""
        return """You are a senior OSINT researcher with 12+ years of experience in:
        - Digital footprint analysis and reconnaissance
        - Information verification and source credibility assessment
        - Technical infrastructure analysis and domain intelligence
        - Social media intelligence and public records research
        - Cross-reference validation and information triangulation
        - Research gap identification and collection planning
        
        Your analysis should be thorough, methodical, and focused on verification.
        Use OSINT methodologies and maintain ethical research practices.
        Provide specific research recommendations and identify information gaps."""
    
    def _build_osint_analysis_prompt(self, content: Dict[str, Any], issue_data: Dict[str, Any]) -> str:
        """Build OSINT analysis prompt from structured content."""
        entities = content.get('entities', {})
        relationships = content.get('relationships', [])
        events = content.get('events', [])
        indicators = content.get('indicators', [])
        
        return f"""
        Conduct comprehensive OSINT research analysis on the following extracted data:
        
        ENTITIES: {json.dumps(entities, indent=2)}
        RELATIONSHIPS: {json.dumps(relationships, indent=2)}
        EVENTS: {json.dumps(events, indent=2)}
        INDICATORS: {json.dumps(indicators, indent=2)}
        
        Provide OSINT analysis covering:
        
        1. DIGITAL FOOTPRINT ASSESSMENT
           - Online presence and digital traces
           - Social media footprint and activity patterns
           - Domain and subdomain enumeration opportunities
           - Technical infrastructure and hosting analysis
           
        2. SOURCE VERIFICATION AND CREDIBILITY
           - Information source reliability assessment
           - Cross-reference opportunities with public records
           - Verification methodologies and techniques
           - Source bias and credibility indicators
           
        3. RESEARCH GAP ANALYSIS
           - Missing information and intelligence gaps
           - Additional collection opportunities
           - Recommended OSINT techniques and tools
           - Priority research targets and objectives
           
        4. VERIFICATION RECOMMENDATIONS
           - Specific verification steps and procedures
           - Cross-reference sources and methodologies
           - Information validation techniques
           - Confidence levels and reliability assessment
        
        Format your response as JSON with these sections:
        {{
            "findings": {{
                "digital_footprint": {{"assessment": "text", "opportunities": ["list"]}},
                "source_verification": {{"reliability": "assessment", "credibility_factors": ["list"]}},
                "research_gaps": {{"missing_info": ["list"], "collection_opportunities": ["list"]}},
                "verification_status": {{"verified_info": ["list"], "requires_verification": ["list"]}}
            }},
            "recommendations": {{
                "immediate_actions": ["prioritized list"],
                "research_techniques": ["recommended OSINT methods"],
                "collection_targets": ["specific targets for further research"],
                "verification_steps": ["actionable verification procedures"]
            }},
            "confidence_assessment": {{
                "overall": 0.0,
                "source_reliability": 0.0,
                "information_completeness": 0.0,
                "verification_confidence": 0.0
            }},
            "intelligence_gaps": ["specific information gaps identified"],
            "analysis_report": "Comprehensive OSINT research report with findings, methodology, and recommendations suitable for intelligence professionals."
        }}
        """
    
    def _perform_fallback_osint_analysis(self, structured_content: Dict[str, Any], issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform rule-based OSINT analysis when AI is unavailable."""
        entities = structured_content.get('entities', {})
        relationships = structured_content.get('relationships', [])
        indicators = structured_content.get('indicators', [])
        
        # Analyze digital footprint potential
        digital_entities = []
        for entity_type, entity_list in entities.items():
            if entity_type in ['domain', 'email', 'phone', 'organization', 'technology']:
                digital_entities.extend([e.get('name', '') for e in entity_list])
        
        # Identify verification opportunities
        verification_targets = []
        for entity_type, entity_list in entities.items():
            if entity_type in ['person', 'organization', 'location']:
                for entity in entity_list:
                    if entity.get('confidence', 0) < 0.8:  # Lower confidence needs verification
                        verification_targets.append(entity.get('name', ''))
        
        # Research gap analysis
        intelligence_gaps = []
        if not entities.get('person', []):
            intelligence_gaps.append("No personnel identified - human intelligence gap")
        if not entities.get('organization', []):
            intelligence_gaps.append("No organizational entities identified")
        if not entities.get('location', []):
            intelligence_gaps.append("No geographical context established")
        
        analysis_report = self._generate_fallback_osint_report(
            digital_entities, verification_targets, intelligence_gaps
        )
        
        return {
            'findings': {
                'digital_footprint': {
                    'assessment': f"Identified {len(digital_entities)} digital entities for analysis",
                    'opportunities': digital_entities[:5]  # Top 5
                },
                'source_verification': {
                    'reliability': 'Requires verification through multiple sources',
                    'credibility_factors': ['Original source unknown', 'Context limited']
                },
                'research_gaps': {
                    'missing_info': intelligence_gaps,
                    'collection_opportunities': ['Public records search', 'Social media analysis', 'Domain intelligence']
                },
                'verification_status': {
                    'verified_info': [],
                    'requires_verification': verification_targets
                }
            },
            'recommendations': {
                'immediate_actions': [
                    'Verify high-value entities through multiple sources',
                    'Conduct digital footprint analysis',
                    'Cross-reference with public databases'
                ],
                'research_techniques': ['WHOIS lookup', 'DNS enumeration', 'Social media search', 'Public records search'],
                'collection_targets': digital_entities[:3],
                'verification_steps': ['Cross-reference with known sources', 'Verify through multiple channels']
            },
            'confidence_assessment': {
                'overall': 0.6,
                'source_reliability': 0.5,
                'information_completeness': 0.4,
                'verification_confidence': 0.3
            },
            'intelligence_gaps': intelligence_gaps,
            'analysis_report': analysis_report
        }
    
    def _generate_fallback_osint_report(self, digital_entities: List[str], verification_targets: List[str], gaps: List[str]) -> str:
        """Generate fallback OSINT analysis report."""
        return f"""# OSINT Research Analysis Report

## Digital Footprint Assessment
- **Digital Entities Identified**: {len(digital_entities)}
- **Primary Targets**: {', '.join(digital_entities[:3]) if digital_entities else 'None identified'}

## Verification Requirements
- **Entities Requiring Verification**: {len(verification_targets)}
- **High-Priority Verification Targets**: {', '.join(verification_targets[:3]) if verification_targets else 'None identified'}

## Research Gaps Identified
{chr(10).join(f'- {gap}' for gap in gaps) if gaps else '- No significant gaps identified'}

## Recommended OSINT Collection
1. **Digital Footprint Analysis**
   - Conduct comprehensive domain and subdomain enumeration
   - Analyze social media presence and activity patterns
   - Investigate technical infrastructure and hosting details

2. **Information Verification**
   - Cross-reference entities with public records
   - Validate information through multiple independent sources
   - Assess source credibility and reliability

3. **Gap Filling**
   - Targeted collection to address identified intelligence gaps
   - Expand entity relationships and context
   - Develop comprehensive target profile

## Confidence Assessment
- **Overall Confidence**: Medium (60%)
- **Verification Status**: Low - Requires additional validation
- **Information Completeness**: Moderate - Significant gaps remain

*Note: This analysis was generated using rule-based fallback methods. AI-enhanced analysis recommended for higher fidelity results.*
"""
    
    def _parse_osint_analysis_response(self, response_content: str) -> Optional[Dict[str, Any]]:
        """Parse AI response for OSINT analysis."""
        try:
            # Try to parse as JSON first
            if response_content.strip().startswith('{'):
                return json.loads(response_content)
            
            # If not JSON, create structured response from text
            return {
                'findings': {
                    'digital_footprint': {'assessment': 'Analysis completed', 'opportunities': []},
                    'source_verification': {'reliability': 'Requires verification', 'credibility_factors': []},
                    'research_gaps': {'missing_info': [], 'collection_opportunities': []},
                    'verification_status': {'verified_info': [], 'requires_verification': []}
                },
                'recommendations': {
                    'immediate_actions': ['Review analysis results'],
                    'research_techniques': ['OSINT methodology'],
                    'collection_targets': [],
                    'verification_steps': ['Cross-reference sources']
                },
                'confidence_assessment': {
                    'overall': 0.7,
                    'source_reliability': 0.6,
                    'information_completeness': 0.5,
                    'verification_confidence': 0.6
                },
                'intelligence_gaps': [],
                'analysis_report': response_content
            }
            
        except json.JSONDecodeError:
            self.logger.warning("Failed to parse OSINT analysis response as JSON")
            return None
    
    def _extract_labels(self, issue_data: Dict[str, Any]) -> List[str]:
        """Extract labels from issue data."""
        labels = issue_data.get('labels', [])
        if isinstance(labels, list):
            return [label.get('name', str(label)) if isinstance(label, dict) else str(label) 
                   for label in labels]
        return []
    
    def _extract_content_text(self, issue_data: Dict[str, Any]) -> str:
        """Extract text content from issue data."""
        title = issue_data.get('title', '')
        body = issue_data.get('body', '')
        return f"{title} {body}"