"""
Tests for Intelligence Analyst Specialist Agent

This module tests the IntelligenceAnalystAgent functionality including:
- Specialist type and configuration validation
- Issue compatibility assessment
- Priority calculation logic
- AI-powered and fallback analysis workflows
- Analysis result parsing and structuring
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.agents.specialist_agents.intelligence_analyst import IntelligenceAnalystAgent
from src.agents.specialist_agents import SpecialistType, AnalysisStatus, AnalysisResult
from src.clients.github_models_client import AIResponse


class TestIntelligenceAnalystAgent:
    """Test suite for Intelligence Analyst Agent"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        return {
            'github_token': 'test_token',
            'ai': {
                'model': 'gpt-4o',
                'timeout': 30,
                'max_retries': 2
            }
        }
    
    @pytest.fixture
    def intelligence_analyst(self, mock_config):
        """Create Intelligence Analyst instance for testing"""
        with patch('src.agents.specialist_agents.intelligence_analyst.GitHubModelsClient'):
            return IntelligenceAnalystAgent(config=mock_config)
    
    @pytest.fixture
    def sample_intelligence_issue(self):
        """Sample intelligence-related GitHub issue"""
        return {
            'number': 123,
            'title': 'APT29 Threat Assessment - New Campaign Analysis',
            'body': '''
            Recent intelligence indicates APT29 (Cozy Bear) has launched a new campaign 
            targeting government infrastructure. Key indicators include:
            
            - IOCs: malicious-domain.com, 192.168.1.100
            - TTPs: Spear phishing, credential harvesting
            - Geopolitical context: Election interference activities
            - Risk level: HIGH - Critical infrastructure targeted
            
            Requires immediate strategic analysis and response planning.
            ''',
            'labels': [
                {'name': 'intelligence'},
                {'name': 'threat-assessment'},
                {'name': 'apt'},
                {'name': 'strategic-intelligence'},
                {'name': 'urgent'}
            ],
            'assignee': 'github-copilot[bot]',
            'created_at': '2024-12-27T10:00:00Z'
        }
    
    @pytest.fixture
    def sample_extracted_content(self):
        """Sample extracted content for intelligence analysis"""
        return {
            'entities': [
                {'name': 'APT29', 'type': 'threat_actor', 'confidence': 0.95},
                {'name': 'Cozy Bear', 'type': 'threat_actor', 'confidence': 0.90},
                {'name': 'malicious-domain.com', 'type': 'domain', 'confidence': 0.85},
                {'name': '192.168.1.100', 'type': 'ip_address', 'confidence': 0.80}
            ],
            'relationships': [
                {
                    'source': 'APT29',
                    'target': 'Cozy Bear',
                    'type': 'alias_of',
                    'confidence': 0.95
                },
                {
                    'source': 'APT29', 
                    'target': 'government infrastructure',
                    'type': 'targets',
                    'confidence': 0.85
                }
            ],
            'events': [
                {
                    'description': 'New campaign launch',
                    'timestamp': '2024-12-20',
                    'type': 'attack_campaign',
                    'confidence': 0.80
                }
            ],
            'indicators': [
                {'value': 'malicious-domain.com', 'type': 'domain', 'confidence': 0.85},
                {'value': '192.168.1.100', 'type': 'ip_address', 'confidence': 0.80}
            ],
            'confidence_score': 0.87
        }
    
    def test_specialist_properties(self, intelligence_analyst):
        """Test specialist type and property configuration"""
        assert intelligence_analyst.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
        
        expected_labels = [
            'intelligence', 'intelligence-analyst', 'threat-assessment',
            'strategic-analysis', 'threat-actor', 'mitre-attack'
        ]
        
        # Check that all expected labels are in supported labels
        for label in expected_labels:
            assert label in intelligence_analyst.supported_labels
        
        expected_capabilities = [
            'content_extraction', 'threat_analysis', 'risk_assessment',
            'strategic_planning', 'pattern_recognition'
        ]
        
        for capability in expected_capabilities:
            assert capability in intelligence_analyst.required_capabilities
    
    def test_issue_compatibility_validation(self, intelligence_analyst):
        """Test issue compatibility validation logic"""
        
        # Test compatible issue with intelligence labels
        compatible_issue = {
            'title': 'Threat Analysis Required',
            'body': 'Analysis of emerging threat landscape',
            'labels': [{'name': 'intelligence'}, {'name': 'threat-assessment'}]
        }
        assert intelligence_analyst.validate_issue_compatibility(compatible_issue) is True
        
        # Test compatible issue with keywords in content
        keyword_issue = {
            'title': 'APT Campaign Analysis',
            'body': 'Strategic intelligence assessment of adversary tactics',
            'labels': []
        }
        assert intelligence_analyst.validate_issue_compatibility(keyword_issue) is True
        
        # Test incompatible issue
        incompatible_issue = {
            'title': 'Update documentation',
            'body': 'Fix typos in README file',
            'labels': [{'name': 'documentation'}, {'name': 'bug'}]
        }
        assert intelligence_analyst.validate_issue_compatibility(incompatible_issue) is False
    
    def test_priority_calculation(self, intelligence_analyst):
        """Test analysis priority calculation"""
        
        # High priority issue (urgent + strategic + threat indicators)
        high_priority_issue = {
            'title': 'URGENT: APT Attack on Critical Infrastructure', 
            'body': 'Nation-state actor targeting strategic assets. Immediate analysis required.',
            'labels': [
                {'name': 'intelligence'},
                {'name': 'urgent'},
                {'name': 'strategic-intelligence'}
            ]
        }
        
        high_priority = intelligence_analyst.get_analysis_priority(high_priority_issue)
        assert high_priority >= 80  # Should be high priority
        
        # Medium priority issue  
        medium_priority_issue = {
            'title': 'Threat Assessment Request',
            'body': 'Routine analysis of recent threat intelligence',
            'labels': [{'name': 'threat-assessment'}]
        }
        
        medium_priority = intelligence_analyst.get_analysis_priority(medium_priority_issue)
        assert 30 <= medium_priority < 80  # Should be medium priority
        
        # Low priority issue
        low_priority_issue = {
            'title': 'General security review',
            'body': 'Review security policies',
            'labels': []
        }
        
        low_priority = intelligence_analyst.get_analysis_priority(low_priority_issue)
        assert low_priority < 30  # Should be low priority
    
    @patch('src.agents.specialist_agents.intelligence_analyst.GitHubModelsClient')
    def test_ai_powered_analysis_success(self, mock_client_class, mock_config, 
                                       sample_intelligence_issue, sample_extracted_content):
        """Test successful AI-powered intelligence analysis"""
        
        # Mock successful AI response
        mock_ai_response = AIResponse(
            content="""# Intelligence Analysis Report
            
## EXECUTIVE SUMMARY
APT29 (Cozy Bear) has launched a sophisticated campaign targeting government infrastructure with high strategic implications.

## THREAT ASSESSMENT
**Threat Actors**: APT29/Cozy Bear - Nation-state sponsored Russian group
**Capabilities**: Advanced persistent threats, sophisticated TTPs
**Intent**: Government espionage and infrastructure disruption
**Threat Level**: High

## RISK EVALUATION
**Impact Assessment**: Critical - Government infrastructure targeted
**Vulnerability Factors**: Spear phishing, credential harvesting vectors
**Potential Consequences**: Data exfiltration, system compromise
**Timeline**: Active ongoing campaign

## KEY FINDINGS
- Confirmed APT29 attribution with high confidence
- Critical infrastructure in scope of targeting
- Multiple IOCs identified with verified malicious activity
- Campaign shows characteristics of election interference

## RECOMMENDATIONS
- Immediate containment and mitigation measures
- Enhanced monitoring of identified IOCs
- Strategic coordination with government partners
- Intelligence sharing with allied organizations

## CONFIDENCE ASSESSMENT
**Overall Confidence Level**: High
**Key Assumptions**: Attribution based on TTP analysis
**Information Gaps**: Full scope of campaign unknown
""",
            model="gpt-4o",
            response_time_ms=1500
        )
        
        # Configure mock client
        mock_client = Mock()
        mock_client.simple_completion.return_value = mock_ai_response
        mock_client_class.return_value = mock_client
        
        # Create intelligence analyst and run analysis
        analyst = IntelligenceAnalystAgent(config=mock_config)
        analyst.ai_client = mock_client
        
        result = analyst.analyze_issue(sample_intelligence_issue, sample_extracted_content)
        
        # Verify analysis result
        assert result.status == AnalysisStatus.COMPLETED
        assert result.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
        assert result.issue_number == 123
        assert len(result.analysis_id) > 0
        
        # Verify content parsing
        assert 'APT29' in result.summary
        assert len(result.key_findings) > 0
        assert len(result.recommendations) > 0
        assert result.risk_assessment is not None
        assert result.confidence_score > 0.5
        
        # Verify risk assessment structure
        risk_assessment = result.risk_assessment
        assert 'threat_level' in risk_assessment
        assert 'impact_level' in risk_assessment
        assert risk_assessment['threat_level'] in ['Critical', 'High', 'Medium', 'Low']
        
        # Verify processing metadata
        assert result.processing_time_seconds is not None
        assert result.completed_at is not None
        assert result.extracted_content == sample_extracted_content
    
    @patch('src.agents.specialist_agents.intelligence_analyst.GitHubModelsClient')
    def test_ai_analysis_failure_fallback(self, mock_client_class, mock_config,
                                        sample_intelligence_issue, sample_extracted_content):
        """Test fallback to rule-based analysis when AI fails"""
        
        # Mock AI client that raises exception
        mock_client = Mock()
        mock_client.simple_completion.side_effect = ValueError("AI API Error")
        mock_client_class.return_value = mock_client
        
        # Create intelligence analyst and run analysis
        analyst = IntelligenceAnalystAgent(config=mock_config)
        analyst.ai_client = mock_client
        
        result = analyst.analyze_issue(sample_intelligence_issue, sample_extracted_content)
        
        # Verify fallback analysis completed
        assert result.status == AnalysisStatus.COMPLETED
        assert result.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
        assert 'Rule-based intelligence analysis' in result.summary
        
        # Verify fallback analysis content
        assert len(result.key_findings) > 0
        assert len(result.recommendations) > 0
        assert result.confidence_score < 0.5  # Lower confidence for fallback
        
        # Should identify extracted entities if provided
        if sample_extracted_content:
            entities_count = len(sample_extracted_content['entities'])
            assert any(f"AI extracted {entities_count}" in finding for finding in result.key_findings)
    
    def test_no_ai_client_fallback_analysis(self, mock_config, sample_intelligence_issue):
        """Test rule-based analysis when no AI client is available"""
        
        # Create analyst without AI client
        with patch('src.agents.specialist_agents.intelligence_analyst.GitHubModelsClient') as mock_client_class:
            mock_client_class.return_value = None
            
            config_no_token = {**mock_config}
            config_no_token.pop('github_token', None)
            
            analyst = IntelligenceAnalystAgent(config=config_no_token)
            result = analyst.analyze_issue(sample_intelligence_issue)
            
            # Verify fallback analysis
            assert result.status == AnalysisStatus.COMPLETED
            assert 'Rule-based intelligence analysis' in result.summary
            assert result.confidence_score <= 0.3  # Low confidence for rule-based
    
    def test_analysis_result_creation(self, intelligence_analyst):
        """Test analysis result creation and metadata"""
        
        issue_number = 456
        result = intelligence_analyst.create_analysis_result(issue_number)
        
        assert result.specialist_type == SpecialistType.INTELLIGENCE_ANALYST
        assert result.issue_number == issue_number
        assert result.status == AnalysisStatus.PENDING
        assert result.created_at is not None
        assert len(result.analysis_id) > 0
        # The base class uses the full specialist type name
        assert 'intelligence-analyst-456' in result.analysis_id
    
    def test_prompt_building_components(self, intelligence_analyst, sample_intelligence_issue, 
                                      sample_extracted_content):
        """Test AI prompt building with extracted content"""
        
        prompt = intelligence_analyst._build_analysis_prompt(
            sample_intelligence_issue, 
            sample_extracted_content
        )
        
        # Verify prompt contains issue information
        assert 'APT29 Threat Assessment' in prompt
        assert str(sample_intelligence_issue['number']) in prompt
        
        # Verify extracted content is included
        assert 'Extracted Entities' in prompt
        assert 'APT29' in prompt
        assert 'Cozy Bear' in prompt
        assert 'malicious-domain.com' in prompt
        
        # Verify analysis requirements are present
        assert 'EXECUTIVE SUMMARY' in prompt
        assert 'THREAT ASSESSMENT' in prompt
        assert 'KEY FINDINGS' in prompt
        assert 'RECOMMENDATIONS' in prompt
    
    def test_system_message_quality(self, intelligence_analyst):
        """Test system message for AI prompts"""
        
        system_message = intelligence_analyst._get_system_message()
        
        # Verify professional standards
        assert 'Intelligence Community' in system_message or 'IC standards' in system_message
        assert 'objective' in system_message.lower()
        assert 'evidence-based' in system_message.lower()
        assert 'threat' in system_message.lower()
        assert 'strategic' in system_message.lower()
    
    def test_section_extraction_parsing(self, intelligence_analyst):
        """Test parsing of AI analysis sections"""
        
        sample_analysis = """
## EXECUTIVE SUMMARY  
Critical threat assessment of APT29 campaign.

## THREAT ASSESSMENT
**Threat Level**: High
Nation-state sponsored activities detected.

## KEY FINDINGS
- Confirmed APT29 attribution
- Government infrastructure targeted
- Multiple IOCs verified

## RECOMMENDATIONS
- Immediate containment measures
- Enhanced monitoring protocols
- Strategic coordination required
        """
        
        sections = intelligence_analyst._extract_analysis_sections(sample_analysis)
        
        assert 'executive_summary' in sections
        assert 'threat_assessment' in sections  
        assert 'key_findings' in sections
        assert 'recommendations' in sections
        
        # Verify content extraction
        assert 'Critical threat assessment' in sections['executive_summary']
        assert 'High' in sections['threat_assessment']
    
    def test_bullet_point_extraction(self, intelligence_analyst):
        """Test extraction of bullet points from analysis text"""
        
        test_text = """
        Key findings include:
        - Confirmed APT29 attribution with high confidence
        - Government infrastructure targeted in campaign
        * Multiple IOCs identified and verified
        • Campaign shows election interference patterns
        1. Strategic implications for national security
        2. Immediate response required
        """
        
        bullet_points = intelligence_analyst._extract_bullet_points(test_text)
        
        assert len(bullet_points) >= 4
        assert 'Confirmed APT29 attribution with high confidence' in bullet_points
        assert 'Government infrastructure targeted in campaign' in bullet_points
        assert 'Multiple IOCs identified and verified' in bullet_points
    
    def test_threat_level_extraction(self, intelligence_analyst):
        """Test threat level extraction from text"""
        
        assert intelligence_analyst._extract_threat_level("Threat Level: Critical") == "Critical"
        assert intelligence_analyst._extract_threat_level("High threat assessment") == "High" 
        assert intelligence_analyst._extract_threat_level("Medium risk identified") == "Medium"
        assert intelligence_analyst._extract_threat_level("Low priority concern") == "Low"
        assert intelligence_analyst._extract_threat_level("Unknown assessment") == "Unknown"
    
    def test_confidence_score_extraction(self, intelligence_analyst):
        """Test confidence score extraction from text"""
        
        assert intelligence_analyst._extract_confidence_score("High confidence assessment") == 0.8
        assert intelligence_analyst._extract_confidence_score("Medium confidence level") == 0.6
        assert intelligence_analyst._extract_confidence_score("Low confidence analysis") == 0.4
        assert intelligence_analyst._extract_confidence_score("No confidence indicators") == 0.5
    
    def test_entity_formatting_for_prompts(self, intelligence_analyst, sample_extracted_content):
        """Test entity formatting for AI prompt inclusion"""
        
        entities = sample_extracted_content['entities']
        formatted = intelligence_analyst._format_entities(entities)
        
        assert 'APT29' in formatted
        assert 'threat_actor' in formatted
        assert 'Confidence:' in formatted
        assert '0.95' in formatted
    
    def test_analysis_result_serialization(self, intelligence_analyst):
        """Test analysis result to dictionary conversion"""
        
        result = intelligence_analyst.create_analysis_result(789)
        result.summary = "Test analysis summary"
        result.key_findings = ["Finding 1", "Finding 2"]
        result.recommendations = ["Recommendation 1"]
        result.confidence_score = 0.75
        result.mark_completed(2.5)
        
        result_dict = result.to_dict()
        
        assert result_dict['specialist_type'] == 'intelligence-analyst'
        assert result_dict['issue_number'] == 789
        assert result_dict['summary'] == "Test analysis summary"
        assert result_dict['key_findings'] == ["Finding 1", "Finding 2"]
        assert result_dict['confidence_score'] == 0.75
        assert result_dict['status'] == 'completed'
        assert result_dict['processing_time_seconds'] == 2.5