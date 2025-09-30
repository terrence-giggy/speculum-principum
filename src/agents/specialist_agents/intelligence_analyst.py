"""
Intelligence Analyst Specialist Agent

This module provides an AI-powered intelligence analyst agent that specializes in:
- Threat landscape analysis and assessment
- Strategic intelligence evaluation  
- Risk assessment and mitigation recommendations
- Intelligence collection gap analysis
- Actionable intelligence reporting

The agent follows Intelligence Community (IC) standards and produces professional-grade
analysis suitable for decision-makers and operational personnel.
"""

import json
import uuid
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import SpecialistAgent, SpecialistType, AnalysisResult, AnalysisStatus
from ...utils.ai_prompt_builder import AIPromptBuilder, PromptType
from ...clients.github_models_client import GitHubModelsClient


class IntelligenceAnalystAgent(SpecialistAgent):
    """
    Intelligence Analyst specialist agent for threat assessment and strategic analysis.
    
    This agent provides comprehensive intelligence analysis including:
    - Threat actor profiling and attribution
    - Attack vector assessment and risk evaluation
    - Strategic implications and operational impact analysis
    - Intelligence collection requirements and gaps
    - Actionable recommendations for decision makers
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Intelligence Analyst agent.
        
        Args:
            config: Configuration dictionary containing AI client settings
        """
        super().__init__(config)
        self.ai_client = self._initialize_ai_client()
        self.prompt_builder = AIPromptBuilder()
        
    @property
    def specialist_type(self) -> SpecialistType:
        """Return specialist type for intelligence analysis."""
        return SpecialistType.INTELLIGENCE_ANALYST
    
    @property
    def supported_labels(self) -> List[str]:
        """Return GitHub labels this specialist can analyze."""
        return [
            'intelligence',
            'intelligence-analyst',
            'threat-assessment',
            'strategic-analysis',
            'risk-assessment',
            'threat-actor',
            'threat-landscape', 
            'security-intelligence',
            'tactical-intelligence',
            'operational-intelligence',
            'strategic-intelligence',
            'geopolitical',
            'attribution',
            'adversary',
            'campaign-analysis',
            'threat-hunting',
            'indicators',
            'ioc',
            'ttp',
            'mitre-attack'
        ]
    
    @property
    def required_capabilities(self) -> List[str]:
        """Return required AI capabilities for intelligence analysis."""
        return [
            'content_extraction',
            'threat_analysis', 
            'risk_assessment',
            'strategic_planning',
            'pattern_recognition',
            'entity_relationship_analysis'
        ]
    
    def validate_issue_compatibility(self, issue_data: Dict[str, Any]) -> bool:
        """
        Validate if this issue is suitable for intelligence analysis.
        
        Args:
            issue_data: GitHub issue data
            
        Returns:
            True if issue contains intelligence-relevant content
        """
        # Extract issue content for analysis
        title = issue_data.get('title', '').lower()
        body = issue_data.get('body', '').lower()
        
        # Get issue labels
        labels = []
        for label in issue_data.get('labels', []):
            if isinstance(label, dict):
                labels.append(label.get('name', '').lower())
            else:
                labels.append(str(label).lower())
        
        # Check for supported labels
        supported_labels_lower = [label.lower() for label in self.supported_labels]
        if any(label in supported_labels_lower for label in labels):
            return True
        
        # Check for intelligence-related keywords in title/body
        intelligence_keywords = [
            'threat', 'attack', 'adversary', 'campaign', 'attribution',
            'intelligence', 'analysis', 'risk', 'security', 'vulnerability',
            'malware', 'apt', 'actor', 'group', 'tactics', 'techniques',
            'procedures', 'ttp', 'mitre', 'ioc', 'indicator', 'compromise',
            'breach', 'incident', 'surveillance', 'espionage', 'cyber',
            'geopolitical', 'strategic', 'operational', 'tactical'
        ]
        
        content = title + ' ' + body
        if any(keyword in content for keyword in intelligence_keywords):
            return True
            
        return False
    
    def get_analysis_priority(self, issue_data: Dict[str, Any]) -> int:
        """
        Calculate analysis priority for intelligence-relevant issues.
        
        Args:
            issue_data: GitHub issue data
            
        Returns:
            Priority score (0-100), higher means more urgent/important
        """
        base_priority = super().get_analysis_priority(issue_data)
        
        # Extract content for priority assessment
        title = issue_data.get('title', '').lower()
        body = issue_data.get('body', '').lower()
        content = title + ' ' + body
        
        # Get labels
        labels = []
        for label in issue_data.get('labels', []):
            if isinstance(label, dict):
                labels.append(label.get('name', '').lower())
            else:
                labels.append(str(label).lower())
        
        # Priority boosters
        priority_boost = 0
        
        # High priority indicators
        high_priority_terms = ['urgent', 'critical', 'immediate', 'active', 'ongoing', 'zero-day']
        if any(term in content for term in high_priority_terms):
            priority_boost += 25
            
        # Threat level indicators  
        threat_indicators = ['apt', 'nation-state', 'advanced', 'targeted', 'campaign']
        if any(indicator in content for indicator in threat_indicators):
            priority_boost += 20
            
        # Strategic importance indicators
        strategic_terms = ['strategic', 'geopolitical', 'national-security', 'infrastructure']
        if any(term in content for term in strategic_terms):
            priority_boost += 15
            
        # Recent/time-sensitive indicators
        time_sensitive = ['recent', 'latest', 'current', 'emerging', 'new']
        if any(term in content for term in time_sensitive):
            priority_boost += 10
            
        return min(base_priority + priority_boost, 100)
    
    def analyze_issue(self, 
                     issue_data: Dict[str, Any],
                     extracted_content: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Perform comprehensive intelligence analysis on an issue.
        
        Args:
            issue_data: GitHub issue data
            extracted_content: Previously extracted structured content
            
        Returns:
            AnalysisResult with intelligence findings and assessments
        """
        start_time = datetime.utcnow()
        issue_number = issue_data.get('number', 0)
        
        # Create analysis result using base class method
        result = self.create_analysis_result(issue_number)
        result.status = AnalysisStatus.IN_PROGRESS
        result.extracted_content = extracted_content
        
        try:
            self.logger.info("Starting intelligence analysis for issue #%s", issue_number)
            
            # Build comprehensive analysis prompt
            analysis_prompt = self._build_analysis_prompt(issue_data, extracted_content)
            
            # Get AI analysis
            if self.ai_client:
                try:
                    ai_response = self.ai_client.simple_completion(
                        prompt=analysis_prompt,
                        system_message=self._get_system_message(),
                        temperature=0.3,  # Lower temperature for more consistent analysis
                        max_tokens=2000
                    )
                    
                    # Parse AI response into structured analysis
                    self._parse_ai_analysis(ai_response.content, result)
                    
                except (ValueError, requests.exceptions.RequestException, json.JSONDecodeError) as e:
                    self.logger.error("AI analysis failed: %s", e)
                    # Fallback to rule-based analysis on AI failure
                    self.logger.warning("AI analysis failed, using fallback analysis")
                    self._perform_fallback_analysis(issue_data, extracted_content, result)
            else:
                # Fallback to rule-based analysis
                self.logger.warning("No AI client available, using fallback analysis")
                self._perform_fallback_analysis(issue_data, extracted_content, result)
            
            # Calculate processing time and mark completed
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            result.mark_completed(processing_time)
            
            self.logger.info("Intelligence analysis completed for issue #%s in %.2fs", issue_number, processing_time)
            
        except Exception as e:
            self.logger.error("Intelligence analysis failed for issue #%s: %s", issue_number, e)
            result.mark_failed(str(e))
        
        return result
    
    def _initialize_ai_client(self) -> Optional[GitHubModelsClient]:
        """Initialize GitHub Models client for AI analysis."""
        try:
            github_token = self.config.get('github_token')
            if not github_token:
                self.logger.warning("No GitHub token provided, AI analysis will be limited")
                return None
                
            ai_config = self.config.get('ai', {})
            
            return GitHubModelsClient(
                github_token=github_token,
                model=ai_config.get('model', 'gpt-4o'),
                timeout=ai_config.get('timeout', 60),
                max_retries=ai_config.get('max_retries', 3)
            )
        except Exception as e:
            self.logger.error("Failed to initialize AI client: %s", e)
            return None
    
    def _get_system_message(self) -> str:
        """Get system message for intelligence analyst AI prompts."""
        return """You are an expert Intelligence Analyst with extensive experience in threat assessment, strategic analysis, and intelligence reporting. You follow Intelligence Community (IC) standards and produce professional-grade analysis.

Your analysis should be:
- Objective and evidence-based
- Clear and actionable for decision makers  
- Structured according to intelligence reporting standards
- Focused on threats, risks, and strategic implications
- Comprehensive yet concise

When analyzing content, focus on:
1. Threat actors, techniques, and capabilities
2. Attack vectors and vulnerabilities
3. Strategic and operational implications  
4. Risk assessment and impact analysis
5. Intelligence gaps and collection requirements
6. Actionable recommendations for stakeholders

Format your response as a structured intelligence report."""
    
    def _build_analysis_prompt(self, 
                              issue_data: Dict[str, Any], 
                              extracted_content: Optional[Dict[str, Any]]) -> str:
        """Build comprehensive analysis prompt for AI processing."""
        
        # Start with issue content
        title = issue_data.get('title', '')
        body = issue_data.get('body', '')
        
        # Get labels
        labels = []
        for label in issue_data.get('labels', []):
            if isinstance(label, dict):
                labels.append(label.get('name', ''))
            else:
                labels.append(str(label))
        
        prompt = f"""# Intelligence Analysis Request

## Issue Information
**Title**: {title}
**Labels**: {', '.join(labels)}
**Number**: #{issue_data.get('number', 'N/A')}

## Content to Analyze
{body}

"""
        
        # Add extracted content if available
        if extracted_content:
            entities = extracted_content.get('entities', [])
            relationships = extracted_content.get('relationships', [])
            events = extracted_content.get('events', [])
            indicators = extracted_content.get('indicators', [])
            
            if entities:
                prompt += f"""## Extracted Entities
{self._format_entities(entities)}

"""
            
            if relationships:
                prompt += f"""## Identified Relationships  
{self._format_relationships(relationships)}

"""
            
            if events:
                prompt += f"""## Event Timeline
{self._format_events(events)}

"""
            
            if indicators:
                prompt += f"""## Technical Indicators
{self._format_indicators(indicators)}

"""
        
        # Analysis instructions
        prompt += """## Analysis Requirements

Provide a comprehensive intelligence analysis with the following structure:

1. **EXECUTIVE SUMMARY** (2-3 sentences)
   - Key threat/situation overview
   - Primary concerns and implications

2. **THREAT ASSESSMENT**  
   - Threat actors (if identifiable)
   - Capabilities and intent
   - Attack vectors and methods
   - Threat level (High/Medium/Low)

3. **RISK EVALUATION**
   - Impact assessment (Critical/High/Medium/Low)
   - Vulnerability factors
   - Potential consequences
   - Timeline considerations

4. **STRATEGIC IMPLICATIONS**
   - Broader context and trends
   - Geopolitical considerations (if applicable)
   - Long-term implications

5. **KEY FINDINGS** (bullet points)
   - Most important discoveries
   - Critical vulnerabilities
   - Attribution indicators
   - Notable patterns or anomalies

6. **RECOMMENDATIONS** (bullet points)  
   - Immediate actions
   - Strategic responses
   - Defensive measures
   - Intelligence collection priorities

7. **CONFIDENCE ASSESSMENT**
   - Overall confidence level (High/Medium/Low)
   - Key assumptions
   - Information gaps
   - Collection requirements

Ensure analysis is professional, actionable, and follows intelligence community standards.
"""
        
        return prompt
    
    def _format_entities(self, entities: List[Dict[str, Any]]) -> str:
        """Format entities for prompt inclusion."""
        formatted = []
        for entity in entities[:10]:  # Limit to top 10 entities
            name = entity.get('name', 'Unknown')
            entity_type = entity.get('type', 'Unknown')
            confidence = entity.get('confidence', 0)
            formatted.append(f"- **{name}** ({entity_type}) - Confidence: {confidence:.2f}")
        return '\n'.join(formatted)
    
    def _format_relationships(self, relationships: List[Dict[str, Any]]) -> str:
        """Format relationships for prompt inclusion."""
        formatted = []
        for rel in relationships[:8]:  # Limit to top 8 relationships
            source = rel.get('source', 'Unknown')
            target = rel.get('target', 'Unknown') 
            rel_type = rel.get('type', 'related_to')
            confidence = rel.get('confidence', 0)
            formatted.append(f"- {source} --{rel_type}--> {target} (Confidence: {confidence:.2f})")
        return '\n'.join(formatted)
    
    def _format_events(self, events: List[Dict[str, Any]]) -> str:
        """Format events for prompt inclusion."""
        formatted = []
        for event in events[:6]:  # Limit to top 6 events
            description = event.get('description', 'Unknown event')
            timestamp = event.get('timestamp', 'Unknown time')
            event_type = event.get('type', 'Unknown')
            formatted.append(f"- **{timestamp}**: {description} ({event_type})")
        return '\n'.join(formatted)
    
    def _format_indicators(self, indicators: List[Dict[str, Any]]) -> str:
        """Format indicators for prompt inclusion."""
        formatted = []
        for indicator in indicators[:12]:  # Limit to top 12 indicators
            value = indicator.get('value', 'Unknown')
            ioc_type = indicator.get('type', 'Unknown')
            confidence = indicator.get('confidence', 0)
            formatted.append(f"- **{value}** ({ioc_type}) - Confidence: {confidence:.2f}")
        return '\n'.join(formatted)
    
    def _parse_ai_analysis(self, ai_content: str, result: AnalysisResult) -> None:
        """Parse AI-generated analysis into structured result."""
        try:
            # Extract key sections from AI response
            sections = self._extract_analysis_sections(ai_content)
            
            # Set summary from executive summary
            result.summary = sections.get('executive_summary', 
                                        'Intelligence analysis completed via AI processing')
            
            # Extract key findings
            findings_section = sections.get('key_findings', '')
            result.key_findings = self._extract_bullet_points(findings_section)
            
            # Extract recommendations
            recommendations_section = sections.get('recommendations', '')
            result.recommendations = self._extract_bullet_points(recommendations_section)
            
            # Build risk assessment
            threat_section = sections.get('threat_assessment', '')
            risk_section = sections.get('risk_evaluation', '')
            
            result.risk_assessment = {
                'threat_level': self._extract_threat_level(threat_section),
                'impact_level': self._extract_impact_level(risk_section),
                'threat_assessment': threat_section,
                'risk_evaluation': risk_section,
                'strategic_implications': sections.get('strategic_implications', ''),
                'full_analysis': ai_content
            }
            
            # Extract confidence score
            confidence_section = sections.get('confidence_assessment', '')
            result.confidence_score = self._extract_confidence_score(confidence_section)
            
            # Store analysis sections in specialist notes
            result.specialist_notes = {
                'analysis_sections': sections,
                'analysis_type': 'ai_powered',
                'model_used': self.ai_client.model if self.ai_client else 'unknown'
            }
            
        except Exception as e:
            self.logger.error("Failed to parse AI analysis: %s", e)
            # Fallback to basic parsing
            result.summary = ai_content[:200] + "..." if len(ai_content) > 200 else ai_content
            result.confidence_score = 0.5
            result.specialist_notes = {'parse_error': str(e), 'raw_content': ai_content}
    
    def _extract_analysis_sections(self, content: str) -> Dict[str, str]:
        """Extract structured sections from AI analysis."""
        sections = {}
        current_section = None
        current_content = []
        
        lines = content.split('\n')
        
        section_headers = {
            'executive summary': 'executive_summary',
            'threat assessment': 'threat_assessment', 
            'risk evaluation': 'risk_evaluation',
            'strategic implications': 'strategic_implications',
            'key findings': 'key_findings',
            'recommendations': 'recommendations',
            'confidence assessment': 'confidence_assessment'
        }
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if this line is a section header
            found_section = None
            for header, key in section_headers.items():
                if header in line_lower and ('**' in line or '#' in line or line_lower.startswith(header)):
                    found_section = key
                    break
            
            if found_section:
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = found_section
                current_content = []
            else:
                # Add content to current section
                if current_section:
                    current_content.append(line)
        
        # Save final section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _extract_bullet_points(self, text: str) -> List[str]:
        """Extract bullet points from text."""
        bullet_points = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith(('-', '*', '•')) or line.startswith(tuple(f"{i}." for i in range(1, 10))):
                # Clean up bullet point formatting
                cleaned = line.lstrip('-*•0123456789. ').strip()
                if cleaned:
                    bullet_points.append(cleaned)
        
        return bullet_points[:8]  # Limit to 8 bullet points
    
    def _extract_threat_level(self, threat_text: str) -> str:
        """Extract threat level from threat assessment text."""
        text_lower = threat_text.lower()
        
        if 'critical' in text_lower or 'severe' in text_lower:
            return 'Critical'
        elif 'high' in text_lower:
            return 'High'
        elif 'medium' in text_lower or 'moderate' in text_lower:
            return 'Medium'
        elif 'low' in text_lower or 'minimal' in text_lower:
            return 'Low'
        else:
            return 'Unknown'
    
    def _extract_impact_level(self, risk_text: str) -> str:
        """Extract impact level from risk evaluation text."""
        text_lower = risk_text.lower()
        
        if 'critical' in text_lower or 'severe' in text_lower:
            return 'Critical'
        elif 'high' in text_lower:
            return 'High' 
        elif 'medium' in text_lower or 'moderate' in text_lower:
            return 'Medium'
        elif 'low' in text_lower or 'minimal' in text_lower:
            return 'Low'
        else:
            return 'Unknown'
    
    def _extract_confidence_score(self, confidence_text: str) -> float:
        """Extract confidence score from confidence assessment text."""
        text_lower = confidence_text.lower()
        
        if 'high confidence' in text_lower or 'high' in text_lower:
            return 0.8
        elif 'medium confidence' in text_lower or 'medium' in text_lower or 'moderate' in text_lower:
            return 0.6
        elif 'low confidence' in text_lower or 'low' in text_lower:
            return 0.4
        else:
            return 0.5  # Default confidence
    
    def _perform_fallback_analysis(self, 
                                  issue_data: Dict[str, Any],
                                  extracted_content: Optional[Dict[str, Any]],
                                  result: AnalysisResult) -> None:
        """Perform rule-based analysis when AI is unavailable."""
        
        title = issue_data.get('title', '')
        body = issue_data.get('body', '')
        content = title + ' ' + body
        content_lower = content.lower()
        
        # Use extracted content if available for enhanced analysis
        entities_count = len(extracted_content.get('entities', [])) if extracted_content else 0
        
        # Basic threat assessment
        threat_keywords = ['malware', 'attack', 'breach', 'vulnerability', 'exploit']
        threat_score = sum(1 for keyword in threat_keywords if keyword in content_lower)
        
        # Generate basic analysis
        result.summary = f"Rule-based intelligence analysis of issue #{issue_data.get('number', 'N/A')}: {title}"
        
        # Basic findings
        findings = []
        if 'urgent' in content_lower or 'critical' in content_lower:
            findings.append("High priority security concern identified")
        if 'apt' in content_lower or 'nation-state' in content_lower:
            findings.append("Potential advanced persistent threat indicators")
        if threat_score > 2:
            findings.append("Multiple threat indicators present")
        if entities_count > 0:
            findings.append(f"AI extracted {entities_count} relevant entities")
        
        result.key_findings = findings or ["Standard intelligence review completed"]
        
        # Basic recommendations
        result.recommendations = [
            "Conduct detailed threat analysis",
            "Review security controls and monitoring", 
            "Consider additional intelligence collection"
        ]
        
        # Risk assessment
        risk_level = 'Medium'
        if threat_score > 3 or 'critical' in content_lower:
            risk_level = 'High'
        elif threat_score < 2:
            risk_level = 'Low'
        
        result.risk_assessment = {
            'threat_level': risk_level,
            'impact_level': risk_level,
            'analysis_method': 'rule_based_fallback'
        }
        
        result.confidence_score = 0.3  # Lower confidence for rule-based analysis
        result.specialist_notes = {
            'analysis_type': 'rule_based_fallback',
            'threat_keyword_score': threat_score
        }