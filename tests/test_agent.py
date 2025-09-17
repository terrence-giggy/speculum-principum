"""Tests for the core agent functionality."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from speculum_principis.agent.core import SpeculumAgent, MonitoringResult
from speculum_principis.utils.config import Config
from speculum_principis.monitoring.sources import ContentItem
from speculum_principis.analysis.processor import AnalysisResult


class TestSpeculumAgent:
    """Test cases for the main agent class."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = Config()
        config.database_url = "sqlite:///:memory:"
        config.monitor_interval = 1  # 1 minute for testing
        config.relevance_threshold = 0.5
        config.log_level = "DEBUG"
        return config

    @pytest.fixture
    def agent(self, config):
        """Create a test agent instance."""
        return SpeculumAgent(config)

    def test_agent_initialization(self, agent, config):
        """Test that agent initializes correctly."""
        assert agent.config == config
        assert not agent.is_running
        assert agent.last_run is None
        assert agent.stats["total_runs"] == 0

    @pytest.mark.asyncio
    async def test_monitoring_cycle_basic(self, agent):
        """Test a basic monitoring cycle."""
        # Mock dependencies
        agent.source_manager = Mock()
        agent.content_processor = Mock()
        agent.db_manager = Mock()
        
        # Mock source data
        test_content = [
            ContentItem(
                title="Test Article",
                content="This is a test article about artificial intelligence research.",
                url="https://example.com/test",
                source="test_source",
                published_date=datetime.now(),
                metadata={}
            )
        ]
        
        agent.source_manager.fetch_all_sources = AsyncMock(return_value={
            "test_source": test_content
        })
        
        # Mock analysis results
        test_analysis = AnalysisResult(
            content_item=test_content[0],
            relevance_score=0.8,
            subjects=["Artificial Intelligence", "Research"],
            keywords=["ai", "research", "test"],
            topics=["AI research trends"],
            entities=[{"text": "AI", "label": "PRODUCT", "description": "Technology"}],
            summary="Test article about AI research",
            metadata={}
        )
        
        agent.content_processor.analyze_content = AsyncMock(return_value=[test_analysis])
        agent.db_manager.store_content = AsyncMock()
        
        # Run monitoring cycle
        result = await agent._run_monitoring_cycle()
        
        # Verify results
        assert isinstance(result, MonitoringResult)
        assert result.sources_checked == 1
        assert result.content_items_found == 1
        assert result.relevant_subjects == 1
        assert len(result.errors) == 0
        
        # Verify mocks were called
        agent.source_manager.fetch_all_sources.assert_called_once()
        agent.content_processor.analyze_content.assert_called_once()
        agent.db_manager.store_content.assert_called_once_with(test_analysis)

    def test_stats_update(self, agent):
        """Test statistics updating."""
        result = MonitoringResult(
            sources_checked=5,
            content_items_found=10,
            relevant_subjects=3,
            errors=[],
            timestamp=datetime.now()
        )
        
        agent._update_stats(result)
        
        assert agent.stats["total_runs"] == 1
        assert agent.stats["total_content_analyzed"] == 10
        assert agent.stats["total_subjects_found"] == 3
        assert agent.stats["errors"] == 0

    def test_stats_with_errors(self, agent):
        """Test statistics with errors."""
        result = MonitoringResult(
            sources_checked=2,
            content_items_found=5,
            relevant_subjects=1,
            errors=["Error 1", "Error 2"],
            timestamp=datetime.now()
        )
        
        agent._update_stats(result)
        
        assert agent.stats["total_runs"] == 1
        assert agent.stats["errors"] == 2

    def test_get_stats(self, agent):
        """Test getting agent statistics."""
        # Set some initial stats
        agent.stats["total_runs"] = 5
        agent.stats["total_content_analyzed"] = 50
        agent.is_running = True
        agent.last_run = datetime.now()
        
        stats = agent.get_stats()
        
        assert stats["total_runs"] == 5
        assert stats["total_content_analyzed"] == 50
        assert stats["is_running"] is True
        assert "last_run" in stats
        assert "uptime_minutes" in stats