"""
Configuration management for Speculum Principis.

This module handles loading and managing configuration from environment
variables and configuration files.
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration settings for the agent."""
    
    # Database configuration
    database_url: str = "sqlite:///speculum_principis.db"
    
    # API Keys
    openai_api_key: Optional[str] = None
    news_api_key: Optional[str] = None
    
    # Monitoring configuration
    monitor_interval: int = 60  # minutes
    max_concurrent_requests: int = 10
    request_delay: float = 1.0  # seconds
    source_timeout: int = 30  # seconds
    
    # Content filtering
    min_content_length: int = 100
    max_items_per_source: int = 50
    relevance_threshold: float = 0.7
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/speculum.log"
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "Config":
        """Load configuration from environment variables."""
        # Load from .env file if specified
        if env_file and os.path.exists(env_file):
            load_dotenv(env_file)
        elif os.path.exists(".env"):
            load_dotenv(".env")
        
        config = cls()
        
        # Database configuration
        if db_url := os.getenv("DATABASE_URL"):
            config.database_url = db_url
        
        # API Keys
        config.openai_api_key = os.getenv("OPENAI_API_KEY")
        config.news_api_key = os.getenv("NEWS_API_KEY")
        
        # Monitoring configuration
        if monitor_interval := os.getenv("MONITOR_INTERVAL_MINUTES"):
            try:
                config.monitor_interval = int(monitor_interval)
            except ValueError:
                logging.warning(f"Invalid MONITOR_INTERVAL_MINUTES: {monitor_interval}")
        
        if max_requests := os.getenv("MAX_CONCURRENT_REQUESTS"):
            try:
                config.max_concurrent_requests = int(max_requests)
            except ValueError:
                logging.warning(f"Invalid MAX_CONCURRENT_REQUESTS: {max_requests}")
        
        if request_delay := os.getenv("REQUEST_DELAY_SECONDS"):
            try:
                config.request_delay = float(request_delay)
            except ValueError:
                logging.warning(f"Invalid REQUEST_DELAY_SECONDS: {request_delay}")
        
        # Content filtering
        if min_length := os.getenv("MIN_CONTENT_LENGTH"):
            try:
                config.min_content_length = int(min_length)
            except ValueError:
                logging.warning(f"Invalid MIN_CONTENT_LENGTH: {min_length}")
        
        if threshold := os.getenv("RELEVANCE_THRESHOLD"):
            try:
                config.relevance_threshold = float(threshold)
            except ValueError:
                logging.warning(f"Invalid RELEVANCE_THRESHOLD: {threshold}")
        
        # Logging
        if log_level := os.getenv("LOG_LEVEL"):
            config.log_level = log_level.upper()
        
        if log_file := os.getenv("LOG_FILE"):
            config.log_file = log_file
        
        return config
    
    def setup_logging(self):
        """Setup logging configuration."""
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        
        # Set specific log levels for external libraries
        logging.getLogger('aiohttp').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        errors = []
        
        # Validate ranges
        if not 1 <= self.monitor_interval <= 1440:  # 1 minute to 24 hours
            errors.append("monitor_interval must be between 1 and 1440 minutes")
        
        if not 1 <= self.max_concurrent_requests <= 100:
            errors.append("max_concurrent_requests must be between 1 and 100")
        
        if not 0.1 <= self.request_delay <= 60:
            errors.append("request_delay must be between 0.1 and 60 seconds")
        
        if not 10 <= self.min_content_length <= 10000:
            errors.append("min_content_length must be between 10 and 10000 characters")
        
        if not 0.0 <= self.relevance_threshold <= 1.0:
            errors.append("relevance_threshold must be between 0.0 and 1.0")
        
        if not 1 <= self.max_items_per_source <= 1000:
            errors.append("max_items_per_source must be between 1 and 1000")
        
        # Log errors
        if errors:
            logging.error("Configuration validation errors:")
            for error in errors:
                logging.error(f"  - {error}")
            return False
        
        return True
    
    def __str__(self) -> str:
        """String representation of config (excluding sensitive data)."""
        return (
            f"Config("
            f"database_url={self.database_url}, "
            f"monitor_interval={self.monitor_interval}, "
            f"max_concurrent_requests={self.max_concurrent_requests}, "
            f"relevance_threshold={self.relevance_threshold}, "
            f"log_level={self.log_level}"
            f")"
        )