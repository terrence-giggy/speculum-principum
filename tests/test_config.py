"""Tests for configuration management."""

import pytest
import os
import tempfile
from speculum_principis.utils.config import Config


class TestConfig:
    """Test cases for configuration management."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.database_url == "sqlite:///speculum_principis.db"
        assert config.monitor_interval == 60
        assert config.max_concurrent_requests == 10
        assert config.min_content_length == 100
        assert config.relevance_threshold == 0.7
        assert config.log_level == "INFO"

    def test_config_from_env(self):
        """Test loading configuration from environment variables."""
        # Set environment variables
        env_vars = {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "MONITOR_INTERVAL_MINUTES": "30",
            "MAX_CONCURRENT_REQUESTS": "5",
            "MIN_CONTENT_LENGTH": "200",
            "RELEVANCE_THRESHOLD": "0.8",
            "LOG_LEVEL": "DEBUG"
        }
        
        # Temporarily set environment variables
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.getenv(key)
            os.environ[key] = value
        
        try:
            config = Config.from_env()
            
            assert config.database_url == "postgresql://test:test@localhost/test"
            assert config.monitor_interval == 30
            assert config.max_concurrent_requests == 5
            assert config.min_content_length == 200
            assert config.relevance_threshold == 0.8
            assert config.log_level == "DEBUG"
            
        finally:
            # Restore original environment
            for key in env_vars:
                if original_env[key] is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_env[key]

    def test_config_from_env_file(self):
        """Test loading configuration from .env file."""
        env_content = """
DATABASE_URL=sqlite:///test.db
MONITOR_INTERVAL_MINUTES=45
RELEVANCE_THRESHOLD=0.6
LOG_LEVEL=WARNING
        """.strip()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_file = f.name
        
        try:
            config = Config.from_env(env_file)
            
            assert config.database_url == "sqlite:///test.db"
            assert config.monitor_interval == 45
            assert config.relevance_threshold == 0.6
            assert config.log_level == "WARNING"
            
        finally:
            os.unlink(env_file)

    def test_config_validation_valid(self):
        """Test configuration validation with valid values."""
        config = Config()
        assert config.validate() is True

    def test_config_validation_invalid_interval(self):
        """Test configuration validation with invalid monitor interval."""
        config = Config()
        config.monitor_interval = 0  # Invalid
        
        assert config.validate() is False

    def test_config_validation_invalid_threshold(self):
        """Test configuration validation with invalid relevance threshold."""
        config = Config()
        config.relevance_threshold = 1.5  # Invalid (> 1.0)
        
        assert config.validate() is False

    def test_config_validation_invalid_requests(self):
        """Test configuration validation with invalid max requests."""
        config = Config()
        config.max_concurrent_requests = 0  # Invalid
        
        assert config.validate() is False

    def test_config_str_representation(self):
        """Test string representation of config."""
        config = Config()
        config_str = str(config)
        
        assert "Config(" in config_str
        assert "database_url=" in config_str
        assert "monitor_interval=" in config_str
        # Should not contain sensitive data
        assert "api_key" not in config_str.lower()

    def test_invalid_env_values(self):
        """Test handling of invalid environment variable values."""
        # Set invalid environment variables
        env_vars = {
            "MONITOR_INTERVAL_MINUTES": "invalid",
            "RELEVANCE_THRESHOLD": "not_a_number",
            "MAX_CONCURRENT_REQUESTS": "negative"
        }
        
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.getenv(key)
            os.environ[key] = value
        
        try:
            config = Config.from_env()
            
            # Should fall back to defaults for invalid values
            assert config.monitor_interval == 60  # default
            assert config.relevance_threshold == 0.7  # default
            assert config.max_concurrent_requests == 10  # default
            
        finally:
            # Restore original environment
            for key in env_vars:
                if original_env[key] is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_env[key]