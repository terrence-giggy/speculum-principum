"""
Tests for AI Content Extraction Integration (Task 1.3)

Tests for integration of ContentExtractionAgent with IssueProcessor workflow.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from pathlib import Path

from src.core.issue_processor import IssueProcessor, GitHubIntegratedIssueProcessor, IssueData, ProcessingResult, IssueProcessingStatus
from src.agents.content_extraction_agent import (
    ContentExtractionAgent, StructuredContent, Entity, 
    Relationship, ExtractionResult
)
from src.utils.config_manager import AIConfig


class TestContentExtractionIntegration:
    """Test integration of content extraction with issue processing"""
    
    @pytest.fixture
    def mock_ai_config(self):
        """Mock AI configuration"""
        config = Mock(spec=AIConfig)
        config.enabled = True
        config.models.content_extraction = "gpt-4o"
        config.settings.timeout_seconds = 30
        config.settings.retry_count = 3
        config.settings.enable_logging = True
        config.confidence_thresholds.entity_extraction = 0.7
        return config
    
    @pytest.fixture
    def sample_issue_data(self):
        """Sample issue data for testing"""
        return IssueData(
            number=123,
            title="Security Analysis: Suspicious Domain Activity",
            body="Analysis of suspicious domain activity detected in network traffic. The domain evil.example.com has been seen communicating with internal systems.",
            labels=['site-monitor', 'security', 'intelligence'],
            assignees=['github-copilot[bot]'],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            url="https://github.com/test/repo/issues/123"
        )
    
    @pytest.fixture
    def mock_extracted_content(self):
        """Mock extracted structured content"""
        return StructuredContent(
            summary="Security analysis of suspicious domain evil.example.com",
            entities=[
                Entity(name="evil.example.com", type="domain", confidence=0.9),
                Entity(name="network traffic", type="technology", confidence=0.8)
            ],
            relationships=[
                Relationship(
                    entity1="evil.example.com", 
                    entity2="internal systems", 
                    relationship="communicates_with", 
                    confidence=0.85
                )
            ],
            events=[],
            indicators=[],
            key_topics=["domain analysis", "network security"],
            urgency_level="medium",
            content_type="security",
            confidence_score=0.85,
            extraction_timestamp=datetime.utcnow().isoformat()
        )
    
    @patch('src.core.issue_processor.DeliverableGenerator')
    @patch('src.core.issue_processor.WorkflowMatcher')
    @patch('src.core.issue_processor.ConfigManager')
    def test_content_extraction_integration_enabled(self, mock_config_manager, mock_workflow_matcher, 
                                                   mock_deliverable_generator, mock_ai_config, 
                                                   sample_issue_data, mock_extracted_content, tmp_path):
        """Test that content extraction is properly integrated when AI is enabled"""
        
        # Setup mocks
        mock_config = Mock()
        mock_config.ai = mock_ai_config
        mock_config.agent.workflow_directory = "docs/workflow/deliverables"
        mock_config.agent.template_directory = None
        mock_config.agent.output_directory = str(tmp_path)
        mock_config.agent.username = "test-agent"
        mock_config.agent.processing.default_timeout_minutes = 5
        mock_config.agent.git = None
        
        mock_config_manager.load_config_with_env_substitution.return_value = mock_config
        
        # Mock workflow matcher
        mock_workflow = Mock()
        mock_workflow.name = "security_analysis"
        mock_workflow.deliverables = [{"name": "analysis", "template": "basic"}]
        mock_workflow.output = {"folder_structure": "issue_{issue_number}", "file_pattern": "{deliverable_name}.md"}
        
        mock_workflow_matcher.return_value.get_best_workflow_match.return_value = (mock_workflow, "Found workflow")
        
        # Mock deliverable generator
        mock_deliverable_generator.return_value.generate_deliverable.return_value = "Generated content with AI data"
        
        with patch('src.agents.content_extraction_agent.ContentExtractionAgent') as mock_extraction_agent_class:
            # Mock content extraction agent
            mock_extraction_agent = Mock()
            mock_extraction_result = ExtractionResult(
                success=True,
                structured_content=mock_extracted_content,
                processing_time_ms=1500,
                ai_response_metadata={"model": "gpt-4o", "usage": {"tokens": 150}}
            )
            mock_extraction_agent.extract_content.return_value = mock_extraction_result
            mock_extraction_agent_class.return_value = mock_extraction_agent
            
            with patch('src.core.issue_processor.GitHubIssueCreator'):
                # Initialize processor
                processor = GitHubIntegratedIssueProcessor(
                    github_token="test-token",
                    repository="test/repo",
                    config_path="test_config.yaml",
                    output_base_dir=tmp_path
                )
                
                # Manually set the content extraction agent to our mock
                processor.content_extraction_agent = mock_extraction_agent
                
                # Verify AI extraction is enabled
                assert processor.enable_ai_extraction == True
            
            # Mock the _extract_issue_content to return our mock content
            with patch.object(processor, '_extract_issue_content') as mock_extract:
                mock_extract.return_value = mock_extracted_content
                
                # Process the issue
                result = processor.process_issue(sample_issue_data)
        
        # Verify results
        assert result.status == IssueProcessingStatus.COMPLETED
        assert result.workflow_name == "security_analysis"
        
        # Verify content extraction was called
        mock_extract.assert_called_once_with(sample_issue_data)
        
        # Verify deliverable generator received the extracted content
        mock_deliverable_generator.return_value.generate_deliverable.assert_called_once()
        call_args = mock_deliverable_generator.return_value.generate_deliverable.call_args
        additional_context = call_args.kwargs['additional_context']
        assert 'extracted_content' in additional_context
        assert additional_context['extracted_content'] == mock_extracted_content
    
    @patch('src.core.issue_processor.DeliverableGenerator')
    @patch('src.core.issue_processor.WorkflowMatcher')
    @patch('src.core.issue_processor.ConfigManager')
    def test_content_extraction_disabled(self, mock_config_manager, mock_workflow_matcher, 
                                        mock_deliverable_generator, sample_issue_data, tmp_path):
        """Test that processing works normally when AI content extraction is disabled"""
        
        # Setup mocks with AI disabled
        mock_config = Mock()
        mock_config.ai = None  # AI disabled
        mock_config.agent.workflow_directory = "docs/workflow/deliverables"
        mock_config.agent.template_directory = None
        mock_config.agent.output_directory = str(tmp_path)
        mock_config.agent.username = "test-agent"
        mock_config.agent.processing.default_timeout_minutes = 5
        mock_config.agent.git = None
        
        mock_config_manager.load_config_with_env_substitution.return_value = mock_config
        
        # Mock workflow matcher
        mock_workflow = Mock()
        mock_workflow.name = "basic_workflow"
        mock_workflow.deliverables = [{"name": "report", "template": "basic"}]
        mock_workflow.output = {"folder_structure": "issue_{issue_number}", "file_pattern": "{deliverable_name}.md"}
        
        mock_workflow_matcher.return_value.get_best_workflow_match.return_value = (mock_workflow, "Found workflow")
        
        # Mock deliverable generator
        mock_deliverable_generator.return_value.generate_deliverable.return_value = "Generated content without AI"
        
        # Initialize processor
        processor = IssueProcessor(
            config_path="test_config.yaml",
            output_base_dir=tmp_path,
            enable_git=False
        )
        
        # Verify AI extraction is disabled
        assert processor.enable_ai_extraction == False
        assert processor.content_extraction_agent is None
        
        # Process the issue
        result = processor.process_issue(sample_issue_data)
        
        # Verify results
        assert result.status == IssueProcessingStatus.COMPLETED
        assert result.workflow_name == "basic_workflow"
        
        # Verify deliverable generator was called without extracted content
        mock_deliverable_generator.return_value.generate_deliverable.assert_called_once()
        call_args = mock_deliverable_generator.return_value.generate_deliverable.call_args
        additional_context = call_args.kwargs['additional_context']
        assert 'extracted_content' not in additional_context or additional_context.get('extracted_content') is None
    
    @patch('src.core.issue_processor.DeliverableGenerator')
    @patch('src.core.issue_processor.WorkflowMatcher')
    @patch('src.core.issue_processor.ConfigManager')
    def test_content_extraction_failure_recovery(self, mock_config_manager, mock_workflow_matcher, 
                                                mock_deliverable_generator, mock_ai_config, 
                                                sample_issue_data, tmp_path):
        """Test that processing continues when content extraction fails"""
        
        # Setup mocks
        mock_config = Mock()
        mock_config.ai = mock_ai_config
        mock_config.agent.workflow_directory = "docs/workflow/deliverables"
        mock_config.agent.template_directory = None
        mock_config.agent.output_directory = str(tmp_path)
        mock_config.agent.username = "test-agent"
        mock_config.agent.processing.default_timeout_minutes = 5
        mock_config.agent.git = None
        
        mock_config_manager.load_config_with_env_substitution.return_value = mock_config
        
        # Mock workflow matcher
        mock_workflow = Mock()
        mock_workflow.name = "fallback_workflow"
        mock_workflow.deliverables = [{"name": "report", "template": "basic"}]
        mock_workflow.output = {"folder_structure": "issue_{issue_number}", "file_pattern": "{deliverable_name}.md"}
        
        mock_workflow_matcher.return_value.get_best_workflow_match.return_value = (mock_workflow, "Found workflow")
        
        # Mock deliverable generator
        mock_deliverable_generator.return_value.generate_deliverable.return_value = "Generated content after extraction failure"
        
        with patch('src.core.issue_processor.GitHubIssueCreator'):
            # Initialize processor
            processor = GitHubIntegratedIssueProcessor(
                github_token="test-token",
                repository="test/repo",
                config_path="test_config.yaml",
                output_base_dir=tmp_path
            )
            
            # Mock content extraction to fail
            with patch.object(processor, '_extract_issue_content') as mock_extract:
                mock_extract.side_effect = Exception("AI service unavailable")
                
                # Process the issue
                result = processor.process_issue(sample_issue_data)
        
            # Verify processing continued despite extraction failure
            assert result.status == IssueProcessingStatus.COMPLETED
            assert result.workflow_name == "fallback_workflow"
            
            # Verify extraction was attempted
            mock_extract.assert_called_once_with(sample_issue_data)
            
            # Verify deliverable generator was called without extracted content (fallback)
            mock_deliverable_generator.return_value.generate_deliverable.assert_called_once()
            call_args = mock_deliverable_generator.return_value.generate_deliverable.call_args
            additional_context = call_args.kwargs['additional_context']
            assert 'extracted_content' not in additional_context or additional_context.get('extracted_content') is None
    
    def test_extract_issue_content_conversion(self, mock_ai_config, sample_issue_data, mock_extracted_content):
        """Test that _extract_issue_content properly converts IssueData to expected format"""
        
        with patch('src.core.issue_processor.ConfigManager') as mock_config_manager:
            mock_config = Mock()
            mock_config.ai = mock_ai_config
            mock_config.agent.workflow_directory = "docs/workflow/deliverables"
            mock_config.agent.template_directory = None
            mock_config.agent.output_directory = "/tmp"
            mock_config.agent.username = "test-agent"
            mock_config.agent.processing.default_timeout_minutes = 5
            mock_config.agent.git = None
            
            mock_config_manager.load_config_with_env_substitution.return_value = mock_config
            
            with patch('src.core.issue_processor.DeliverableGenerator'), \
                 patch('src.core.issue_processor.WorkflowMatcher'):
                
                # Initialize processor
                processor = IssueProcessor(
                    config_path="test_config.yaml",
                    enable_git=False
                )
                
                # Mock content extraction agent
                mock_agent = Mock()
                mock_extraction_result = ExtractionResult(
                    success=True,
                    structured_content=mock_extracted_content
                )
                mock_agent.extract_content.return_value = mock_extraction_result
                processor.content_extraction_agent = mock_agent
                
                # Call extraction method
                result = processor._extract_issue_content(sample_issue_data)
                
                # Verify the result
                assert result == mock_extracted_content
                
                # Verify agent was called with properly formatted issue dict
                mock_agent.extract_content.assert_called_once()
                call_args = mock_agent.extract_content.call_args[0][0]
                
                assert call_args['number'] == 123
                assert call_args['title'] == "Security Analysis: Suspicious Domain Activity"
                assert isinstance(call_args['labels'], list)
                assert call_args['labels'][0]['name'] == 'site-monitor'
                assert isinstance(call_args['assignees'], list)
                assert call_args['assignees'][0]['login'] == 'github-copilot[bot]'