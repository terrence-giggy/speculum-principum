"""
Test suite for OSINT Researcher Specialist Agent

Comprehensive tests for the OSINT researcher agent functionality including
issue compatibility, priority calculation, analysis capabilities, and both
AI-powered and fallback analysis methods.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from typing import Dict, Any

from src.agents.specialist_agents.osint_researcher import OSINTResearcherAgent
from src.agents.specialist_agents import SpecialistType, AnalysisResult, AnalysisStatus
from src.clients.github_models_client import AIResponse


class TestOSINTResearcherAgent:
    """Test cases for OSINT Researcher Agent"""

    @pytest.fixture
    def osint_agent(self):
        """Create OSINT researcher agent for testing"""
        agent = OSINTResearcherAgent()
        agent.ai_client = Mock()
        return agent

    @pytest.fixture
    def sample_osint_issue(self):
        """Sample GitHub issue with OSINT-relevant content"""
        return {
            'number': 123,
            'title': 'OSINT Research on Target Organization',
            'body': 'Need to conduct digital footprint analysis and verify information about example.com domain and associated social media accounts. Cross-reference with public records.',
            'labels': [{'name': 'osint'}, {'name': 'reconnaissance'}, {'name': 'verification'}],
            'assignees': [{'login': 'github-copilot[bot]'}],
            'created_at': '2024-01-01T10:00:00Z',
            'updated_at': '2024-01-01T12:00:00Z',
            'url': 'https://github.com/test/repo/issues/123'
        }

    @pytest.fixture
    def sample_structured_content(self):
        """Sample structured content for OSINT analysis"""
        return {
            'entities': {
                'domain': [
                    {'name': 'example.com', 'confidence': 0.9, 'type': 'domain'},
                    {'name': 'subdomain.example.com', 'confidence': 0.8, 'type': 'domain'}
                ],
                'organization': [
                    {'name': 'Example Corp', 'confidence': 0.7, 'type': 'organization'}
                ],
                'person': [
                    {'name': 'John Doe', 'confidence': 0.6, 'type': 'person'}
                ],
                'technology': [
                    {'name': 'Apache Web Server', 'confidence': 0.8, 'type': 'technology'}
                ]
            },
            'relationships': [
                {
                    'entity1': 'Example Corp',
                    'entity2': 'example.com',
                    'relationship': 'owns',
                    'confidence': 0.9
                }
            ],
            'events': [
                {
                    'description': 'Domain registration',
                    'timestamp': '2020-01-01',
                    'entities_involved': ['example.com'],
                    'confidence': 0.8
                }
            ],
            'indicators': [
                {
                    'type': 'domain',
                    'value': 'example.com',
                    'description': 'Target domain for analysis',
                    'confidence': 0.9
                }
            ]
        }

    def test_specialist_properties(self, osint_agent):
        """Test basic specialist properties and configuration"""
        assert osint_agent.specialist_type == SpecialistType.OSINT_RESEARCHER
        assert 'osint' in osint_agent.supported_labels
        assert 'reconnaissance' in osint_agent.supported_labels
        assert 'verification' in osint_agent.supported_labels
        assert 'digital-footprint' in osint_agent.supported_labels
        assert 'content_extraction' in osint_agent.required_capabilities

    def test_issue_compatibility_with_osint_labels(self, osint_agent, sample_osint_issue):
        """Test issue compatibility detection with OSINT labels"""
        assert osint_agent.validate_issue_compatibility(sample_osint_issue) is True

    def test_issue_compatibility_with_osint_keywords(self, osint_agent):
        """Test issue compatibility with OSINT keywords in content"""
        issue = {
            'title': 'Domain investigation needed',
            'body': 'Please verify the whois information and conduct reconnaissance on the target website',
            'labels': []
        }
        assert osint_agent.validate_issue_compatibility(issue) is True

    def test_issue_compatibility_rejection(self, osint_agent):
        """Test rejection of non-OSINT issues"""
        non_osint_issue = {
            'title': 'Bug fix needed',
            'body': 'The application crashes when clicking submit button',
            'labels': [{'name': 'bug'}, {'name': 'frontend'}]
        }
        assert osint_agent.validate_issue_compatibility(non_osint_issue) is False

    def test_priority_score_calculation(self, osint_agent, sample_osint_issue):
        """Test priority score calculation based on OSINT relevance"""
        score = osint_agent.calculate_priority_score(sample_osint_issue)
        assert 0.5 <= score <= 1.0  # Should be high priority for OSINT content

    def test_priority_score_with_keywords(self, osint_agent):
        """Test priority calculation with keyword-rich content"""
        high_keyword_issue = {
            'title': 'Digital footprint analysis',
            'body': 'Verify domain information, check social media, validate public records, cross-reference sources',
            'labels': [{'name': 'osint'}]
        }
        score = osint_agent.calculate_priority_score(high_keyword_issue)
        assert score >= 0.4  # Should have decent priority

    def test_ai_analysis_success(self, osint_agent, sample_structured_content, sample_osint_issue):
        """Test successful AI-powered OSINT analysis"""
        # Mock successful AI response
        mock_response = Mock()
        mock_response.content = '{"findings": {"digital_footprint": {"assessment": "Strong online presence", "opportunities": ["domain analysis", "social media"]}, "source_verification": {"reliability": "Medium", "credibility_factors": ["public records available"]}, "research_gaps": {"missing_info": ["contact details"], "collection_opportunities": ["whois lookup"]}, "verification_status": {"verified_info": ["domain ownership"], "requires_verification": ["personnel info"]}}, "recommendations": {"immediate_actions": ["conduct domain analysis"], "research_techniques": ["WHOIS lookup", "social media search"], "collection_targets": ["example.com"], "verification_steps": ["cross-reference public records"]}, "confidence_assessment": {"overall": 0.8, "source_reliability": 0.7, "information_completeness": 0.6, "verification_confidence": 0.7}, "intelligence_gaps": ["missing contact information"], "analysis_report": "Comprehensive OSINT analysis completed"}'
        
        osint_agent.ai_client.chat_completion.return_value = mock_response

        result = osint_agent.analyze_issue(sample_osint_issue, sample_structured_content)

        assert isinstance(result, AnalysisResult)
        assert result.specialist_type == SpecialistType.OSINT_RESEARCHER
        assert result.status == AnalysisStatus.COMPLETED
        assert len(result.key_findings) >= 1
        assert len(result.recommendations) > 0
        assert result.specialist_notes['processing_method'] == 'ai_enhanced'

    def test_fallback_analysis(self, osint_agent, sample_structured_content, sample_osint_issue):
        """Test fallback analysis when AI is unavailable"""
        # Disable AI client to trigger fallback
        osint_agent.ai_client = None

        result = osint_agent.analyze_issue(sample_osint_issue, sample_structured_content)

        assert isinstance(result, AnalysisResult)
        assert result.specialist_type == SpecialistType.OSINT_RESEARCHER
        assert result.status == AnalysisStatus.COMPLETED
        assert result.specialist_notes['processing_method'] == 'fallback_analysis'
        assert len(result.key_findings) >= 1
        assert len(result.recommendations) > 0
        assert 'OSINT Research Analysis Report' in result.specialist_notes['osint_analysis']['analysis_report']

    def test_ai_analysis_failure_handling(self, osint_agent, sample_structured_content, sample_osint_issue):
        """Test handling of AI analysis failures"""
        # Mock AI client failure
        osint_agent.ai_client.chat_completion.side_effect = Exception("API Error")

        result = osint_agent.analyze_issue(sample_osint_issue, sample_structured_content)

        # AI failure should fall back to rule-based analysis, not completely fail
        assert isinstance(result, AnalysisResult)
        assert result.status == AnalysisStatus.COMPLETED  # Falls back to rule-based
        assert result.specialist_notes['processing_method'] == 'fallback_analysis'

    def test_osint_researcher_persona(self, osint_agent):
        """Test OSINT researcher persona generation"""
        persona = osint_agent._get_osint_researcher_persona()
        assert 'OSINT researcher' in persona
        assert 'verification' in persona
        assert 'Digital footprint' in persona  # Capital D to match the actual text
        assert 'research practices' in persona

    def test_analysis_prompt_building(self, osint_agent, sample_structured_content, sample_osint_issue):
        """Test OSINT analysis prompt construction"""
        prompt = osint_agent._build_osint_analysis_prompt(sample_structured_content, sample_osint_issue)
        assert 'DIGITAL FOOTPRINT ASSESSMENT' in prompt
        assert 'SOURCE VERIFICATION' in prompt
        assert 'RESEARCH GAP ANALYSIS' in prompt
        assert 'VERIFICATION RECOMMENDATIONS' in prompt
        assert 'example.com' in prompt  # Should include entity data

    def test_fallback_analysis_components(self, osint_agent, sample_structured_content, sample_osint_issue):
        """Test individual components of fallback analysis"""
        analysis = osint_agent._perform_fallback_osint_analysis(sample_structured_content, sample_osint_issue)
        
        # Check structure
        assert 'findings' in analysis
        assert 'recommendations' in analysis
        assert 'confidence_assessment' in analysis
        assert 'intelligence_gaps' in analysis
        assert 'analysis_report' in analysis

        # Check findings structure
        findings = analysis['findings']
        assert 'digital_footprint' in findings
        assert 'source_verification' in findings
        assert 'research_gaps' in findings
        assert 'verification_status' in findings

        # Check recommendations
        recommendations = analysis['recommendations']
        assert 'immediate_actions' in recommendations
        assert 'research_techniques' in recommendations
        assert len(recommendations['research_techniques']) > 0

    def test_digital_entity_identification(self, osint_agent, sample_structured_content, sample_osint_issue):
        """Test identification of digital entities for OSINT analysis"""
        analysis = osint_agent._perform_fallback_osint_analysis(sample_structured_content, sample_osint_issue)
        
        # Should identify domain entities
        opportunities = analysis['findings']['digital_footprint']['opportunities']
        assert any('example.com' in str(opp) for opp in opportunities)

    def test_verification_target_identification(self, osint_agent, sample_structured_content, sample_osint_issue):
        """Test identification of entities requiring verification"""
        # Add low-confidence entity that should require verification
        sample_structured_content['entities']['person'][0]['confidence'] = 0.5
        
        analysis = osint_agent._perform_fallback_osint_analysis(sample_structured_content, sample_osint_issue)
        verification_targets = analysis['findings']['verification_status']['requires_verification']
        
        assert len(verification_targets) > 0
        assert 'John Doe' in verification_targets

    def test_intelligence_gap_detection(self, osint_agent, sample_osint_issue):
        """Test detection of intelligence gaps in structured content"""
        # Create content with missing entity types
        minimal_content = {
            'entities': {'domain': [{'name': 'example.com', 'confidence': 0.9}]},
            'relationships': [],
            'indicators': []
        }
        
        analysis = osint_agent._perform_fallback_osint_analysis(minimal_content, sample_osint_issue)
        gaps = analysis['intelligence_gaps']
        
        assert any('personnel' in gap.lower() for gap in gaps)
        assert any('organizational' in gap.lower() for gap in gaps)
        assert any('geographical' in gap.lower() for gap in gaps)

    def test_analysis_report_generation(self, osint_agent, sample_structured_content, sample_osint_issue):
        """Test generation of comprehensive OSINT analysis report"""
        analysis = osint_agent._perform_fallback_osint_analysis(sample_structured_content, sample_osint_issue)
        report = analysis['analysis_report']
        
        assert '# OSINT Research Analysis Report' in report
        assert 'Digital Footprint Assessment' in report
        assert 'Verification Requirements' in report
        assert 'Recommended OSINT Collection' in report
        assert 'Confidence Assessment' in report

    def test_response_parsing_json(self, osint_agent):
        """Test parsing of valid JSON response from AI"""
        json_response = '{"findings": {"test": "data"}, "recommendations": {"actions": []}, "confidence_assessment": {"overall": 0.8}, "intelligence_gaps": [], "analysis_report": "test report"}'
        
        parsed = osint_agent._parse_osint_analysis_response(json_response)
        
        assert parsed is not None
        assert 'findings' in parsed
        assert parsed['findings']['test'] == 'data'

    def test_response_parsing_text_fallback(self, osint_agent):
        """Test fallback parsing for non-JSON responses"""
        text_response = "This is a text response from AI analysis"
        
        parsed = osint_agent._parse_osint_analysis_response(text_response)
        
        assert parsed is not None
        assert 'findings' in parsed
        assert 'analysis_report' in parsed
        assert parsed['analysis_report'] == text_response

    def test_confidence_assessment_structure(self, osint_agent, sample_structured_content, sample_osint_issue):
        """Test structure and values of confidence assessment"""
        analysis = osint_agent._perform_fallback_osint_analysis(sample_structured_content, sample_osint_issue)
        confidence = analysis['confidence_assessment']
        
        required_keys = ['overall', 'source_reliability', 'information_completeness', 'verification_confidence']
        for key in required_keys:
            assert key in confidence
            assert 0.0 <= confidence[key] <= 1.0

    def test_supported_labels_completeness(self, osint_agent):
        """Test that all expected OSINT-related labels are supported"""
        expected_labels = [
            'osint', 'reconnaissance', 'digital-footprint', 'verification',
            'source-analysis', 'investigation', 'research'
        ]
        
        supported = osint_agent.supported_labels
        for label in expected_labels:
            assert label in supported

    def test_required_capabilities_completeness(self, osint_agent):
        """Test that all required OSINT capabilities are declared"""
        expected_capabilities = [
            'content_extraction', 'source_verification', 'digital_footprint_analysis',
            'research_gap_identification', 'cross_referencing', 'information_validation'
        ]
        
        required = osint_agent.required_capabilities
        for capability in expected_capabilities:
            assert capability in required