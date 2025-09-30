"""
Target Profiler Specialist Agent

This specialist agent focuses on organizational analysis, stakeholder mapping,
and business intelligence for comprehensive target profiling in intelligence operations.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from . import SpecialistAgent, SpecialistType, AnalysisResult, AnalysisStatus
from ...clients.github_models_client import GitHubModelsClient, AIResponse
from ...utils.logging_config import get_logger, log_exception


class TargetProfilerAgent(SpecialistAgent):
    """
    Target Profiler Agent specializing in organizational analysis and stakeholder mapping.
    
    This agent provides comprehensive target profiling capabilities including:
    - Organizational structure analysis
    - Key personnel identification and mapping
    - Business relationship analysis
    - Revenue streams and financial analysis
    - Risk assessment from organizational perspective
    - Decision-maker influence mapping
    - Competitive landscape analysis
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Target Profiler Agent
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.ai_client = self._initialize_ai_client()
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
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
    
    @property 
    def specialist_type(self) -> SpecialistType:
        """Return specialist type for target profiler analysis."""
        return SpecialistType.TARGET_PROFILER
    
    @property
    def supported_labels(self) -> List[str]:
        """Return GitHub labels this specialist can analyze."""
        return [
            'target-profiler',
            'organizational',
            'business',
            'corporate',
            'stakeholder',
            'organizational-analysis',
            'business-intelligence',
            'competitive-analysis',
            'market-analysis',
            'financial-analysis',
            'leadership',
            'executive',
            'management',
            'personnel',
            'company',
            'enterprise',
            'firm',
            'agency',
            'department',
            'division',
            'subsidiary'
        ]
    
    @property
    def required_capabilities(self) -> List[str]:
        """Return list of required AI capabilities."""
        return [
            'organizational_analysis',
            'stakeholder_mapping',
            'business_intelligence',
            'competitive_analysis'
        ]
    
    def validate_issue_compatibility(self, issue_data: Dict[str, Any]) -> bool:
        """
        Check if this specialist can analyze the given issue.
        
        Args:
            issue_data: GitHub issue data dictionary
            
        Returns:
            bool: True if issue contains organizational/business intelligence content
        """
        return self.is_compatible_issue(issue_data)
    
    def analyze_issue(self, issue_data: Dict[str, Any], 
                     extracted_content: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Perform specialist analysis on an issue.
        
        Args:
            issue_data: GitHub issue data
            extracted_content: Previously extracted structured content
            
        Returns:
            AnalysisResult with specialist findings and recommendations
        """
        return self.perform_analysis(issue_data, extracted_content)
    
    def is_compatible_issue(self, issue_data: Dict[str, Any]) -> bool:
        """
        Determine if this issue is suitable for target profiler analysis.
        
        Args:
            issue_data: GitHub issue data dictionary
            
        Returns:
            bool: True if issue contains organizational/business intelligence content
        """
        try:
            # Check issue title and body for organizational/business keywords
            content = f"{issue_data.get('title', '')} {issue_data.get('body', '')}".lower()
            
            # Target profiler keywords
            organizational_keywords = [
                'company', 'organization', 'corporate', 'business', 'enterprise',
                'firm', 'agency', 'department', 'division', 'subsidiary',
                'management', 'executive', 'ceo', 'cto', 'director', 'leadership',
                'stakeholder', 'personnel', 'employee', 'staff', 'team',
                'organizational', 'structure', 'hierarchy', 'reporting',
                'financial', 'revenue', 'funding', 'investor', 'shareholder',
                'competitive', 'market', 'industry', 'sector', 'competitor',
                'partnership', 'alliance', 'vendor', 'supplier', 'customer',
                'acquisition', 'merger', 'expansion', 'strategy'
            ]
            
            # Check for organizational/business content
            keyword_matches = sum(1 for keyword in organizational_keywords if keyword in content)
            
            # Check labels for business/organizational indicators
            labels = [label.get('name', '').lower() for label in issue_data.get('labels', [])]
            business_labels = [
                'business', 'corporate', 'organizational', 'company', 'enterprise',
                'financial', 'competitive', 'market', 'strategic', 'leadership'
            ]
            label_matches = sum(1 for label in business_labels if any(bl in label for bl in business_labels))
            
            # Require significant organizational/business content
            return keyword_matches >= 4 or label_matches >= 1
            
        except Exception as e:
            log_exception(self.logger, "Error in compatibility check", e)
            return False
    
    def calculate_priority(self, issue_data: Dict[str, Any]) -> int:
        """
        Calculate priority score for target profiler analysis (1-10).
        
        Args:
            issue_data: GitHub issue data dictionary
            
        Returns:
            int: Priority score from 1-10 (10 = highest priority)
        """
        try:
            priority = 5  # Base priority
            
            content = f"{issue_data.get('title', '')} {issue_data.get('body', '')}".lower()
            labels = [label.get('name', '').lower() for label in issue_data.get('labels', [])]
            
            # High priority indicators
            high_priority_terms = [
                'executive', 'leadership', 'ceo', 'cto', 'director', 'board',
                'financial', 'revenue', 'funding', 'acquisition', 'merger',
                'strategic', 'competitive', 'market leader', 'key player'
            ]
            
            # Medium priority indicators  
            medium_priority_terms = [
                'organizational', 'structure', 'management', 'stakeholder',
                'business', 'corporate', 'partnership', 'alliance'
            ]
            
            # Count high-priority matches
            high_matches = sum(1 for term in high_priority_terms if term in content)
            medium_matches = sum(1 for term in medium_priority_terms if term in content)
            
            # Adjust priority based on content
            priority += min(high_matches * 2, 4)  # Max +4 for high priority terms
            priority += min(medium_matches, 2)    # Max +2 for medium priority terms
            
            # Label-based adjustments
            priority_labels = ['critical', 'urgent', 'high-priority', 'strategic']
            if any(pl in ' '.join(labels) for pl in priority_labels):
                priority += 1
                
            return min(max(priority, 1), 10)  # Clamp to 1-10 range
            
        except Exception as e:
            log_exception(self.logger, "Error calculating priority", e)
            return 5
    
    def perform_analysis(self, issue_data: Dict[str, Any], 
                        extracted_content: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Perform comprehensive target profiler analysis.
        
        Args:
            issue_data: GitHub issue data dictionary
            extracted_content: Optional pre-extracted structured content
            
        Returns:
            AnalysisResult: Analysis results with organizational insights
        """
        analysis_id = f"target_profiler_{issue_data.get('number', 'unknown')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        result = AnalysisResult(
            specialist_type=self.specialist_type,
            issue_number=issue_data.get('number', 0),
            analysis_id=analysis_id,
            summary="Target profiler analysis in progress",
            status=AnalysisStatus.IN_PROGRESS
        )
        
        try:
            # Perform AI-enhanced analysis if available
            if self.ai_client:
                result = self._perform_ai_analysis(issue_data, extracted_content, result)
            else:
                result = self._perform_fallback_analysis(issue_data, extracted_content, result)
                
            result.mark_completed()
            self.logger.info(f"Target profiler analysis completed for issue {issue_data.get('number')}")
            
        except Exception as e:
            error_msg = f"Target profiler analysis failed: {str(e)}"
            result.mark_failed(error_msg)
            log_exception(self.logger, error_msg, e)
            
        return result
    
    def _perform_ai_analysis(self, issue_data: Dict[str, Any], 
                           extracted_content: Optional[Dict[str, Any]],
                           result: AnalysisResult) -> AnalysisResult:
        """
        Perform AI-enhanced target profiler analysis using GitHub Models.
        
        Args:
            issue_data: GitHub issue data dictionary
            extracted_content: Optional pre-extracted content
            result: Analysis result object to populate
            
        Returns:
            AnalysisResult: Enhanced analysis results
        """
        try:
            # Build comprehensive analysis prompt
            prompt = self._build_analysis_prompt(issue_data, extracted_content)
            
            # Request AI analysis
            messages = [{"role": "user", "content": prompt}]
            response = self.ai_client.chat_completion(
                messages=messages,
                temperature=0.3,  # Lower temperature for more focused analysis
                max_tokens=2000
            )
            
            if response and response.content:
                # Parse AI response into structured analysis
                analysis = self._parse_ai_response(response.content)
                
                # Populate result with AI analysis
                result.summary = analysis.get('summary', 'Target profiler analysis completed')
                result.key_findings = analysis.get('key_findings', [])
                result.recommendations = analysis.get('recommendations', [])
                result.risk_assessment = analysis.get('risk_assessment', {})
                result.confidence_score = analysis.get('confidence', 0.8)
                
                # Target profiler specific analysis
                result.entities_analyzed = analysis.get('organizations', [])
                result.relationships_identified = analysis.get('relationships', [])
                result.specialist_notes = {
                    'analysis_type': 'ai_enhanced',
                    'model_used': self.ai_client.model if self.ai_client else 'unknown',
                    'stakeholder_count': len(analysis.get('stakeholders', [])),
                    'organizational_levels': analysis.get('organizational_levels', 0),
                    'financial_indicators': analysis.get('financial_indicators', [])
                }
                
                self.logger.debug("AI-enhanced target profiler analysis completed")
                
            else:
                raise Exception("AI response was empty or invalid")
                
        except Exception as e:
            log_exception(self.logger, "AI analysis failed, falling back to basic analysis", e)
            result = self._perform_fallback_analysis(issue_data, extracted_content, result)
            
        return result
    
    def _perform_fallback_analysis(self, issue_data: Dict[str, Any],
                                 extracted_content: Optional[Dict[str, Any]], 
                                 result: AnalysisResult) -> AnalysisResult:
        """
        Perform basic target profiler analysis without AI enhancement.
        
        Args:
            issue_data: GitHub issue data dictionary
            extracted_content: Optional pre-extracted content
            result: Analysis result object to populate
            
        Returns:
            AnalysisResult: Basic analysis results
        """
        try:
            content = f"{issue_data.get('title', '')} {issue_data.get('body', '')}"
            
            # Basic organizational entity extraction
            organizations = self._extract_organizations(content)
            personnel = self._extract_personnel(content)
            financial_terms = self._extract_financial_indicators(content)
            
            # Generate basic analysis
            result.summary = (f"Target profiler analysis identified {len(organizations)} organizations, "
                            f"{len(personnel)} key personnel, and {len(financial_terms)} financial indicators")
            
            result.key_findings = [
                f"Organizations mentioned: {', '.join(organizations[:5])}" if organizations else "No organizations explicitly mentioned",
                f"Key personnel identified: {', '.join(personnel[:5])}" if personnel else "No key personnel identified",
                f"Financial indicators: {', '.join(financial_terms[:3])}" if financial_terms else "No financial indicators found"
            ]
            
            result.recommendations = [
                "Conduct deeper organizational structure analysis",
                "Map stakeholder relationships and influence networks", 
                "Analyze competitive positioning and market dynamics",
                "Assess organizational risk factors and vulnerabilities"
            ]
            
            result.confidence_score = 0.6
            result.entities_analyzed = organizations
            result.specialist_notes = {
                'analysis_type': 'basic_pattern_matching',
                'organizations_found': len(organizations),
                'personnel_found': len(personnel),
                'financial_terms_found': len(financial_terms)
            }
            
            self.logger.debug("Fallback target profiler analysis completed")
            
        except Exception as e:
            log_exception(self.logger, "Fallback analysis failed", e)
            result.summary = "Target profiler analysis encountered errors"
            result.key_findings = ["Analysis could not be completed due to processing errors"]
            result.recommendations = ["Manual review recommended"]
            result.confidence_score = 0.3
            
        return result
    
    def _build_analysis_prompt(self, issue_data: Dict[str, Any], 
                             extracted_content: Optional[Dict[str, Any]]) -> str:
        """Build comprehensive analysis prompt for AI processing."""
        
        title = issue_data.get('title', 'No title')
        body = issue_data.get('body', 'No content')[:2000]  # Limit content size
        labels = [label.get('name', '') for label in issue_data.get('labels', [])]
        
        prompt = f"""You are a professional Target Profiler analyst specializing in organizational analysis and business intelligence. 
Analyze the following content for organizational structure, stakeholder mapping, and business intelligence insights.

CONTENT TO ANALYZE:
Title: {title}
Body: {body}
Labels: {', '.join(labels)}

REQUIRED ANALYSIS:
1. ORGANIZATIONAL STRUCTURE:
   - Identify organizations, companies, agencies mentioned
   - Determine organizational hierarchy and reporting relationships
   - Map divisions, departments, or business units

2. KEY PERSONNEL:
   - Identify executives, managers, decision-makers
   - Determine roles, responsibilities, and influence levels
   - Map reporting relationships and authority structures

3. STAKEHOLDER ANALYSIS:
   - Identify internal and external stakeholders
   - Assess stakeholder influence and interests
   - Map stakeholder relationships and dependencies

4. BUSINESS INTELLIGENCE:
   - Analyze business models and revenue streams
   - Identify competitive positioning and market factors
   - Assess financial health and investment patterns

5. RISK ASSESSMENT:
   - Organizational vulnerabilities and risk factors
   - Leadership risks and succession planning
   - Competitive threats and market risks

6. STRATEGIC INSIGHTS:
   - Decision-making processes and authority
   - Strategic partnerships and alliances
   - Growth opportunities and expansion plans

Return your analysis in this exact JSON format:
{{
    "summary": "Brief overall assessment of the organizational landscape",
    "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
    "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"],
    "organizations": ["Org1", "Org2", "Org3"],
    "stakeholders": ["Stakeholder1", "Stakeholder2", "Stakeholder3"],
    "relationships": ["Relationship1", "Relationship2"],
    "financial_indicators": ["Indicator1", "Indicator2"],
    "organizational_levels": 3,
    "risk_assessment": {{
        "organizational_risk": "low/medium/high",
        "leadership_risk": "low/medium/high", 
        "competitive_risk": "low/medium/high"
    }},
    "confidence": 0.85
}}

Focus on actionable intelligence for decision-makers and strategic planning."""
        
        return prompt
    
    def _parse_ai_response(self, response_content: str) -> Dict[str, Any]:
        """Parse AI response into structured analysis data."""
        
        try:
            import json
            
            # Try to extract JSON from response
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_content = response_content[json_start:json_end]
                return json.loads(json_content)
            else:
                # Fallback parsing if JSON structure is not found
                return self._fallback_parse_response(response_content)
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON parsing failed: {e}")
            return self._fallback_parse_response(response_content)
        except Exception as e:
            log_exception(self.logger, "Failed to parse AI response", e)
            return self._fallback_parse_response(response_content)
    
    def _fallback_parse_response(self, content: str) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails."""
        
        return {
            'summary': content[:200] + "..." if len(content) > 200 else content,
            'key_findings': ["AI analysis completed", "Detailed findings available in summary"],
            'recommendations': ["Review full analysis", "Consider follow-up analysis"],
            'organizations': [],
            'stakeholders': [],
            'relationships': [],
            'financial_indicators': [],
            'organizational_levels': 1,
            'risk_assessment': {'organizational_risk': 'medium', 'leadership_risk': 'medium', 'competitive_risk': 'medium'},
            'confidence': 0.7
        }
    
    def _extract_organizations(self, content: str) -> List[str]:
        """Extract organizational names using pattern matching."""
        import re
        
        # Common organizational suffixes
        org_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc|Corp|Company|Corporation|LLC|Ltd|Agency|Department|Division)\b',
            r'\b([A-Z][A-Z0-9]+)\b',  # Acronyms like FBI, CIA, etc.
        ]
        
        organizations = set()
        for pattern in org_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            organizations.update(matches)
            
        return list(organizations)[:10]  # Limit results
    
    def _extract_personnel(self, content: str) -> List[str]:
        """Extract personnel names and titles using pattern matching.""" 
        import re
        
        # Look for titles followed by names
        title_patterns = [
            r'(?:CEO|CTO|CFO|Director|Manager|President|VP|Vice President|Executive)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+(?:CEO|CTO|CFO|Director|Manager|President)'
        ]
        
        personnel = set()
        for pattern in title_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            personnel.update(matches)
            
        return list(personnel)[:10]  # Limit results
    
    def _extract_financial_indicators(self, content: str) -> List[str]:
        """Extract financial indicators and terms."""
        
        financial_terms = [
            'revenue', 'profit', 'funding', 'investment', 'valuation', 'budget',
            'financial', 'earnings', 'costs', 'expenses', 'income', 'capital'
        ]
        
        found_terms = []
        content_lower = content.lower()
        
        for term in financial_terms:
            if term in content_lower:
                found_terms.append(term)
                
        return found_terms[:5]  # Limit results