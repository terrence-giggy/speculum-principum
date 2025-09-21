"""
Configuration Management Module
Handles loading and validation of YAML configuration files for site monitoring
"""

import yaml
import os
from typing import Dict, List, Optional, Any
from jsonschema import validate, ValidationError
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SiteConfig:
    """Configuration for a single monitored site"""
    url: str
    name: str
    keywords: List[str] = None
    max_results: int = 10
    search_paths: List[str] = None
    exclude_paths: List[str] = None
    custom_search_terms: List[str] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        if self.keywords is None:
            self.keywords = []
        if self.search_paths is None:
            self.search_paths = []
        if self.exclude_paths is None:
            self.exclude_paths = []
        if self.custom_search_terms is None:
            self.custom_search_terms = []


@dataclass
class GitHubConfig:
    """GitHub repository configuration"""
    repository: str
    issue_labels: List[str] = None
    default_assignees: List[str] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        if self.issue_labels is None:
            self.issue_labels = ["site-monitor", "automated"]
        if self.default_assignees is None:
            self.default_assignees = []


@dataclass
class SearchConfig:
    """Google Custom Search configuration"""
    api_key: str
    search_engine_id: str
    daily_query_limit: int = 90  # Leave buffer from 100 daily limit
    results_per_query: int = 10
    date_range_days: int = 1  # Search for results in last N days
    
    def __post_init__(self):
        """Validate search configuration"""
        if self.daily_query_limit > 100:
            raise ValueError("Daily query limit cannot exceed 100 (Google free tier limit)")
        if self.results_per_query > 10:
            raise ValueError("Results per query cannot exceed 10 (Google API limit)")


@dataclass
class MonitorConfig:
    """Complete monitoring configuration"""
    sites: List[SiteConfig]
    github: GitHubConfig
    search: SearchConfig
    storage_path: str = "processed_urls.json"
    log_level: str = "INFO"


class ConfigLoader:
    """Loads and validates monitoring configuration from YAML files"""
    
    # JSON Schema for configuration validation
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["sites", "github", "search"],
        "properties": {
            "sites": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["url", "name"],
                    "properties": {
                        "url": {"type": "string", "format": "uri"},
                        "name": {"type": "string", "minLength": 1},
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "max_results": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10
                        },
                        "search_paths": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "exclude_paths": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "custom_search_terms": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "additionalProperties": False
                }
            },
            "github": {
                "type": "object",
                "required": ["repository"],
                "properties": {
                    "repository": {"type": "string", "pattern": r"^[^/]+/[^/]+$"},
                    "issue_labels": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "default_assignees": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "additionalProperties": False
            },
            "search": {
                "type": "object",
                "required": ["api_key", "search_engine_id"],
                "properties": {
                    "api_key": {"type": "string", "minLength": 1},
                    "search_engine_id": {"type": "string", "minLength": 1},
                    "daily_query_limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100
                    },
                    "results_per_query": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10
                    },
                    "date_range_days": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 30
                    }
                },
                "additionalProperties": False
            },
            "storage_path": {"type": "string"},
            "log_level": {
                "type": "string",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            }
        },
        "additionalProperties": False
    }
    
    @classmethod
    def load_config(cls, config_path: str) -> MonitorConfig:
        """
        Load and validate configuration from YAML file
        
        Args:
            config_path: Path to the YAML configuration file
            
        Returns:
            MonitorConfig object with loaded configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
            ValidationError: If configuration doesn't match schema
            ValueError: If configuration values are invalid
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}") from e
        
        # Validate against schema
        try:
            validate(instance=config_data, schema=cls.CONFIG_SCHEMA)
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e.message}") from e
        
        # Convert to dataclass objects
        return cls._build_config(config_data)
    
    @classmethod
    def _build_config(cls, config_data: Dict[str, Any]) -> MonitorConfig:
        """Build MonitorConfig object from validated configuration data"""
        
        # Build site configurations
        sites = []
        for site_data in config_data['sites']:
            site = SiteConfig(
                url=site_data['url'],
                name=site_data['name'],
                keywords=site_data.get('keywords', []),
                max_results=site_data.get('max_results', 10),
                search_paths=site_data.get('search_paths', []),
                exclude_paths=site_data.get('exclude_paths', []),
                custom_search_terms=site_data.get('custom_search_terms', [])
            )
            sites.append(site)
        
        # Build GitHub configuration
        github_data = config_data['github']
        github = GitHubConfig(
            repository=github_data['repository'],
            issue_labels=github_data.get('issue_labels', ["site-monitor", "automated"]),
            default_assignees=github_data.get('default_assignees', [])
        )
        
        # Build search configuration
        search_data = config_data['search']
        search = SearchConfig(
            api_key=search_data['api_key'],
            search_engine_id=search_data['search_engine_id'],
            daily_query_limit=search_data.get('daily_query_limit', 90),
            results_per_query=search_data.get('results_per_query', 10),
            date_range_days=search_data.get('date_range_days', 1)
        )
        
        return MonitorConfig(
            sites=sites,
            github=github,
            search=search,
            storage_path=config_data.get('storage_path', 'processed_urls.json'),
            log_level=config_data.get('log_level', 'INFO')
        )
    



def load_config_with_env_substitution(config_path: str) -> MonitorConfig:
    """
    Load configuration with environment variable substitution
    
    This function allows configuration values to reference environment variables
    using the format: ${ENV_VAR_NAME} or ${ENV_VAR_NAME:default_value}
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        MonitorConfig object with environment variables substituted
    """
    import re
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Read raw YAML content
    with open(config_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Pattern to match ${VAR_NAME} or ${VAR_NAME:default_value}
    env_pattern = re.compile(r'\$\{([^}:]+)(?::([^}]*))?\}')
    
    def replace_env_var(match):
        var_name = match.group(1)
        default_value = match.group(2) if match.group(2) is not None else ''
        return os.getenv(var_name, default_value)
    
    # Substitute environment variables
    content = env_pattern.sub(replace_env_var, content)
    
    # Parse the substituted YAML
    try:
        config_data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML after environment substitution: {e}") from e
    
    # Validate and build config
    try:
        validate(instance=config_data, schema=ConfigLoader.CONFIG_SCHEMA)
    except ValidationError as e:
        raise ValueError(f"Configuration validation failed: {e.message}") from e
    
    return ConfigLoader._build_config(config_data)