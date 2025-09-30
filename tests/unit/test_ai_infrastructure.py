"""
Tests for AI Client Infrastructure (Task 1.2)

Tests for GitHub Models client, AI prompt builder, and content extraction agent.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.clients.github_models_client import GitHubModelsClient, AIResponse, RateLimitInfo
from src.utils.ai_prompt_builder import (
    AIPromptBuilder, IssueContent, ExtractionFocus, 
    SpecialistType, PromptType, WorkflowInfo
)
from src.agents.content_extraction_agent import (
    ContentExtractionAgent, StructuredContent, Entity, 
    Relationship, Event, Indicator, ExtractionResult
)
from src.utils.config_manager import AIConfig, AIModelConfig, AISettingsConfig


class TestGitHubModelsClient:
    """Test GitHub Models API client"""
    
    def test_client_initialization(self):
        """Test client initialization with default parameters"""
        client = GitHubModelsClient(
            github_token="test-token",
            model="gpt-4o"
        )
        
        assert client.token == "test-token"
        assert client.model == "gpt-4o"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert "Authorization" in client.headers
    
    def test_client_initialization_with_custom_params(self):
        """Test client initialization with custom parameters"""
        client = GitHubModelsClient(
            github_token="test-token",
            model="gpt-4o-mini",
            timeout=60,
            max_retries=5,
            enable_logging=False
        )
        
        assert client.model == "gpt-4o-mini"
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.enable_logging is False
    
    def test_client_validation_errors(self):
        """Test client validation with invalid parameters"""
        with pytest.raises(ValueError, match="GitHub token is required"):
            GitHubModelsClient(github_token="", model="gpt-4o")
        
        with pytest.raises(ValueError, match="Model name is required"):
            GitHubModelsClient(github_token="test-token", model="")
        
        with pytest.raises(ValueError, match="Max retries must be non-negative"):
            GitHubModelsClient(github_token="test-token", model="gpt-4o", max_retries=-1)
    
    @patch('requests.post')
    def test_successful_chat_completion(self, mock_post):
        """Test successful chat completion request"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Test response"},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 50}
        }
        mock_post.return_value = mock_response
        
        client = GitHubModelsClient("test-token", "gpt-4o")
        messages = [{"role": "user", "content": "Hello"}]
        
        result = client.chat_completion(messages)
        
        assert isinstance(result, AIResponse)
        assert result.content == "Test response"
        assert result.model == "gpt-4o"
        assert result.finish_reason == "stop"
        assert result.usage == {"total_tokens": 50}
    
    @patch('requests.post')
    def test_simple_completion(self, mock_post):
        """Test simple completion with system message"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Simple response"}}]
        }
        mock_post.return_value = mock_response
        
        client = GitHubModelsClient("test-token", "gpt-4o")
        
        result = client.simple_completion(
            prompt="Test prompt",
            system_message="You are a helpful assistant",
            max_tokens=100
        )
        
        assert result.content == "Simple response"
        
        # Verify the request was made correctly
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        assert len(payload['messages']) == 2
        assert payload['messages'][0]['role'] == 'system'
        assert payload['messages'][1]['role'] == 'user'
        assert payload['max_tokens'] == 100
    
    def test_chat_completion_validation(self):
        """Test chat completion parameter validation"""
        client = GitHubModelsClient("test-token", "gpt-4o")
        
        # Test empty messages
        with pytest.raises(ValueError, match="Messages list cannot be empty"):
            client.chat_completion([])
        
        # Test invalid message format
        with pytest.raises(ValueError, match="All messages must have 'role' and 'content' fields"):
            client.chat_completion([{"role": "user"}])  # Missing content
        
        # Test invalid temperature
        with pytest.raises(ValueError, match="Temperature must be between 0 and 1"):
            client.chat_completion([{"role": "user", "content": "test"}], temperature=1.5)
    
    @patch('requests.post')
    def test_rate_limiting_handling(self, mock_post):
        """Test rate limiting response handling"""
        # Mock rate limited response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '5'}
        mock_post.return_value = mock_response
        
        client = GitHubModelsClient("test-token", "gpt-4o", max_retries=0)
        
        with pytest.raises(Exception):
            client.chat_completion([{"role": "user", "content": "test"}])
    
    def test_rate_limit_tracking(self):
        """Test rate limit status tracking"""
        client = GitHubModelsClient("test-token", "gpt-4o")
        
        # Initial state
        status = client.get_rate_limit_status()
        assert status["request_count"] == 0
        assert status["requests_remaining"] == 50
        
        # After updating
        client._update_rate_limit()
        status = client.get_rate_limit_status()
        assert status["request_count"] == 1
        assert status["requests_remaining"] == 49


class TestAIPromptBuilder:
    """Test AI prompt builder functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.builder = AIPromptBuilder()
        self.sample_issue = IssueContent(
            title="Test Security Issue",
            body="This issue discusses potential security vulnerabilities in the target organization.",
            labels=["security", "intelligence"],
            number=123,
            assignee="github-copilot[bot]"
        )
    
    def test_content_extraction_prompt(self):
        """Test content extraction prompt generation"""
        focus = ExtractionFocus(
            entities=True,
            relationships=True,
            events=False
        )
        
        prompt = self.builder.build_content_extraction_prompt(
            issue=self.sample_issue,
            focus=focus,
            specialist_context="Security analysis context"
        )
        
        assert "system" in prompt
        assert "user" in prompt
        assert "Security analysis context" in prompt["system"]
        assert "Test Security Issue" in prompt["user"]
        assert "entities" in prompt["system"].lower()
        assert "relationships" in prompt["system"].lower()
        
    def test_workflow_assignment_prompt(self):
        """Test workflow assignment prompt generation"""
        workflows = [
            WorkflowInfo(
                name="security-analysis",
                description="Security threat analysis",
                trigger_labels=["security", "threat"],
                deliverables=["threat-assessment", "security-report"],
                specialist_type="threat-hunter"
            )
        ]
        
        prompt = self.builder.build_workflow_assignment_prompt(
            issue=self.sample_issue,
            available_workflows=workflows,
            confidence_threshold=0.8
        )
        
        assert "workflow_name1" in prompt["system"]
        assert "security-analysis" in prompt["user"]
        assert "Security threat analysis" in prompt["user"]
        assert "0.8" in prompt["system"]
    
    def test_specialist_analysis_prompt(self):
        """Test specialist analysis prompt generation"""
        extracted_content = {
            "entities": {"organizations": ["Target Corp"]},
            "key_topics": ["security", "vulnerability"]
        }
        
        prompt = self.builder.build_specialist_analysis_prompt(
            issue=self.sample_issue,
            specialist_type=SpecialistType.THREAT_HUNTER,
            extracted_content=extracted_content,
            analysis_focus=["IOCs", "TTPs"]
        )
        
        assert "Threat Hunter" in prompt["system"]
        assert "IOCs, TTPs" in prompt["system"]
        assert "Target Corp" in prompt["user"]
        assert "Test Security Issue" in prompt["user"]
    
    def test_document_generation_prompt(self):
        """Test document generation prompt generation"""
        extracted_data = {
            "summary": "Security analysis of target organization",
            "entities": ["Target Corp", "Security Team"],
            "key_topics": ["vulnerability", "assessment"]
        }
        
        specialist_analysis = {
            "threat_level": "medium",
            "key_findings": ["Vulnerable systems identified"]
        }
        
        prompt = self.builder.build_document_generation_prompt(
            template_name="threat-assessment",
            extracted_data=extracted_data,
            specialist_analysis=specialist_analysis,
            target_audience="security analyst"
        )
        
        assert "threat-assessment" in prompt["system"]
        assert "security analyst" in prompt["system"]
        assert "Security analysis of target organization" in prompt["user"]
        assert "medium" in prompt["user"]
    
    def test_entity_extraction_prompt(self):
        """Test entity extraction prompt generation"""
        content = "Microsoft Corporation is located in Redmond, Washington. The CEO is Satya Nadella."
        entity_types = ["people", "organizations", "locations"]
        
        prompt = self.builder.build_entity_extraction_prompt(
            content=content,
            entity_types=entity_types
        )
        
        assert "people, organizations, locations" in prompt["system"]
        assert "Microsoft Corporation" in prompt["user"]
        assert "Satya Nadella" in prompt["user"]
    
    def test_validation_prompt(self):
        """Test validation prompt generation"""
        original_content = "Test content with entities and relationships"
        extracted_data = {
            "entities": ["Entity1", "Entity2"],
            "relationships": [{"entity1": "Entity1", "entity2": "Entity2"}]
        }
        
        prompt = self.builder.build_validation_prompt(
            original_content=original_content,
            extracted_data=extracted_data
        )
        
        assert "accuracy of extracted entities" in prompt["system"]
        assert "Test content with entities" in prompt["user"]
        assert "Entity1" in prompt["user"]


class TestContentExtractionAgent:
    """Test content extraction agent functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create mock AI config
        self.ai_config = AIConfig(
            enabled=True,
            models=AIModelConfig(content_extraction="gpt-4o"),
            settings=AISettingsConfig(temperature=0.3, max_tokens=1000)
        )
        
        # Mock GitHub Models client
        self.mock_client = Mock(spec=GitHubModelsClient)
        
    @patch('src.agents.content_extraction_agent.GitHubModelsClient')
    def test_agent_initialization(self, mock_client_class):
        """Test content extraction agent initialization"""
        mock_client_class.return_value = self.mock_client
        
        agent = ContentExtractionAgent(
            github_token="test-token",
            ai_config=self.ai_config
        )
        
        assert agent.ai_config == self.ai_config
        assert agent.confidence_threshold == 0.7  # Default value
        mock_client_class.assert_called_once()
    
    @patch('src.agents.content_extraction_agent.GitHubModelsClient')
    def test_successful_content_extraction(self, mock_client_class):
        """Test successful content extraction from issue"""
        # Setup mocks
        mock_client_class.return_value = self.mock_client
        
        # Mock AI response
        mock_ai_response = AIResponse(
            content=json.dumps({
                "summary": "Test summary",
                "entities": {
                    "organizations": ["Test Corp"],
                    "people": ["John Doe"]
                },
                "relationships": [{
                    "entity1": "John Doe",
                    "entity2": "Test Corp",
                    "relationship": "works for",
                    "confidence": 0.9
                }],
                "events": [{
                    "description": "Security incident",
                    "timestamp": "2024-01-01",
                    "confidence": 0.8
                }],
                "indicators": [{
                    "type": "IOC",
                    "value": "malicious.domain.com",
                    "confidence": 0.9
                }],
                "key_topics": ["security", "incident"],
                "urgency_level": "high",
                "content_type": "security",
                "confidence_score": 0.85
            }),
            model="gpt-4o"
        )
        self.mock_client.chat_completion.return_value = mock_ai_response
        
        # Test issue data
        issue_data = {
            "title": "Security Incident Report",
            "body": "Details about the security incident at Test Corp involving John Doe",
            "labels": [{"name": "security"}, {"name": "urgent"}],
            "number": 456,
            "assignee": {"login": "github-copilot[bot]"}
        }
        
        agent = ContentExtractionAgent("test-token", self.ai_config)
        agent.ai_client = self.mock_client
        
        result = agent.extract_content(issue_data)
        
        assert result.success is True
        assert result.structured_content is not None
        
        content = result.structured_content
        assert content.summary == "Test summary"
        assert len(content.entities) == 2
        assert len(content.relationships) == 1
        assert len(content.events) == 1
        assert len(content.indicators) == 1
        assert content.urgency_level == "high"
        assert content.confidence_score == 0.85
    
    @patch('src.agents.content_extraction_agent.GitHubModelsClient')
    def test_extraction_with_focus(self, mock_client_class):
        """Test content extraction with specific focus areas"""
        mock_client_class.return_value = self.mock_client
        
        focus = ExtractionFocus(
            entities=True,
            relationships=False,
            events=True,
            indicators=True
        )
        
        agent = ContentExtractionAgent("test-token", self.ai_config)
        agent.ai_client = self.mock_client
        
        # Mock minimal response
        mock_ai_response = AIResponse(
            content=json.dumps({
                "summary": "Focused extraction",
                "entities": {"organizations": ["Test Corp"]},
                "relationships": [],
                "events": [],
                "indicators": [],
                "key_topics": [],
                "urgency_level": "medium",
                "content_type": "research",
                "confidence_score": 0.7
            }),
            model="gpt-4o"
        )
        self.mock_client.chat_completion.return_value = mock_ai_response
        
        issue_data = {
            "title": "Test Issue",
            "body": "Test content",
            "labels": [],
            "number": 1
        }
        
        result = agent.extract_content(issue_data, extraction_focus=focus)
        
        assert result.success is True
        assert result.structured_content is not None
        assert result.structured_content.summary == "Focused extraction"
    
    @patch('src.agents.content_extraction_agent.GitHubModelsClient')
    def test_extraction_error_handling(self, mock_client_class):
        """Test error handling in content extraction"""
        mock_client_class.return_value = self.mock_client
        
        # Mock AI client to raise exception
        self.mock_client.chat_completion.side_effect = Exception("AI service error")
        
        agent = ContentExtractionAgent("test-token", self.ai_config)
        agent.ai_client = self.mock_client
        
        issue_data = {
            "title": "Test Issue",
            "body": "Test content",
            "labels": [],
            "number": 1
        }
        
        result = agent.extract_content(issue_data)
        
        assert result.success is False
        assert result.error_message == "AI service error"
        assert result.structured_content is None
    
    @patch('src.agents.content_extraction_agent.GitHubModelsClient')
    def test_entity_extraction_only(self, mock_client_class):
        """Test entity-only extraction functionality"""
        mock_client_class.return_value = self.mock_client
        
        # Mock AI response for entity extraction
        mock_ai_response = AIResponse(
            content=json.dumps({
                "entities": {
                    "people": ["Alice Smith", "Bob Johnson"],
                    "organizations": ["Acme Corp"]
                },
                "confidence_scores": {
                    "Alice Smith": 0.9,
                    "Bob Johnson": 0.8,
                    "Acme Corp": 0.95
                }
            }),
            model="gpt-4o"
        )
        self.mock_client.chat_completion.return_value = mock_ai_response
        
        agent = ContentExtractionAgent("test-token", self.ai_config)
        agent.ai_client = self.mock_client
        
        result = agent.extract_entities_only(
            content="Alice Smith and Bob Johnson work at Acme Corp.",
            entity_types=["people", "organizations"]
        )
        
        assert result.success is True
        assert result.structured_content is not None
        assert len(result.structured_content.entities) == 3
        
        # Check entity details
        entities_by_name = {e.name: e for e in result.structured_content.entities}
        assert "Alice Smith" in entities_by_name
        assert entities_by_name["Alice Smith"].confidence == 0.9
        assert entities_by_name["Acme Corp"].type == "organizations"
    
    @patch('src.agents.content_extraction_agent.GitHubModelsClient')
    def test_validation_functionality(self, mock_client_class):
        """Test content validation functionality"""
        mock_client_class.return_value = self.mock_client
        
        # Mock validation response
        mock_ai_response = AIResponse(
            content=json.dumps({
                "validation_results": {
                    "accuracy_score": 0.9,
                    "completeness_score": 0.8,
                    "consistency_score": 0.95,
                    "overall_quality": 0.88
                },
                "issues_found": [],
                "recommendations": [],
                "validated": True
            }),
            model="gpt-4o"
        )
        self.mock_client.chat_completion.return_value = mock_ai_response
        
        agent = ContentExtractionAgent("test-token", self.ai_config)
        agent.ai_client = self.mock_client
        
        # Create sample extracted content
        extracted_content = StructuredContent(
            summary="Test content",
            entities=[Entity(name="Test Corp", type="organization", confidence=0.9)],
            relationships=[],
            events=[],
            indicators=[],
            key_topics=["test"],
            urgency_level="medium",
            content_type="research",
            confidence_score=0.8,
            extraction_timestamp=datetime.utcnow().isoformat()
        )
        
        validation_result = agent.validate_extraction(
            original_content="Test Corp is a technology company.",
            extracted_data=extracted_content
        )
        
        assert validation_result["validated"] is True
        assert validation_result["validation_results"]["overall_quality"] == 0.88
    
    @patch('src.agents.content_extraction_agent.GitHubModelsClient')
    def test_health_check(self, mock_client_class):
        """Test agent health check functionality"""
        # Set up the mock client properly before agent creation
        self.mock_client.model = "gpt-4o"
        self.mock_client.health_check.return_value = {
            "status": "healthy",
            "model": "gpt-4o",
            "response_time_ms": 150
        }
        mock_client_class.return_value = self.mock_client
        
        agent = ContentExtractionAgent("test-token", self.ai_config)
        
        health = agent.health_check()
        
        assert health["status"] == "healthy"
        assert health["agent_type"] == "ContentExtractionAgent"
        assert "ai_client_status" in health
        assert "configuration" in health
    
    @patch('src.agents.content_extraction_agent.GitHubModelsClient')
    def test_statistics(self, mock_client_class):
        """Test extraction statistics functionality"""
        mock_client_class.return_value = self.mock_client
        self.mock_client.model = "gpt-4o"
        self.mock_client.get_rate_limit_status.return_value = {
            "request_count": 5,
            "requests_remaining": 45
        }
        
        agent = ContentExtractionAgent("test-token", self.ai_config)
        agent.ai_client = self.mock_client
        
        stats = agent.get_extraction_statistics()
        
        assert stats["agent_type"] == "ContentExtractionAgent"
        assert stats["ai_model"] == "gpt-4o"
        assert stats["confidence_threshold"] == 0.7
        assert "rate_limit_status" in stats