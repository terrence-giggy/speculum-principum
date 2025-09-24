"""
Simple smoke tests to validate basic functionality
"""

import pytest
import tempfile
import os
from pathlib import Path


class TestBasicImports:
    """Test that core modules can be imported"""
    
    def test_core_imports(self):
        """Test importing core modules"""
        try:
            import src.site_monitor
            import src.search_client
            import src.config_manager
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import core modules: {e}")


class TestBasicFunctionality:
    """Test basic functionality works"""
    
    def test_search_result_creation(self):
        """Test creating search results"""
        from src.search_client import SearchResult
        
        result = SearchResult("Test", "https://test.com", "Snippet")
        assert result.title == "Test"
        assert result.link == "https://test.com"
    
    def test_config_basic_structure(self):
        """Test config can be created"""
        from src.config_manager import MonitorConfig, SiteConfig, GitHubConfig, SearchConfig
        
        config = MonitorConfig(
            sites=[SiteConfig(name="test", url="test.com")],
            github=GitHubConfig(repository="test/repo"),
            search=SearchConfig(api_key="test-key", search_engine_id="test-engine", daily_query_limit=100),
            storage_path="test.json"
        )
        
        assert config is not None
        assert len(config.sites) == 1
