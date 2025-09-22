"""
Logging Configuration Module

Provides centralized logging configuration for the Speculum Principum application.
Supports different log levels, formatters, and output destinations for different
components of the system.

This module ensures consistent logging across all components while providing
flexibility for different deployment scenarios (development, testing, production).
"""

import logging
import logging.handlers
import sys
import os
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime


class SpeculumLoggerConfig:
    """
    Centralized logging configuration for Speculum Principum.
    
    Provides methods to configure logging for different components with
    appropriate handlers, formatters, and log levels.
    """
    
    # Default log format for different scenarios
    DETAILED_FORMAT = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "[%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"
    )
    
    SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    
    CONSOLE_FORMAT = "%(levelname)-8s %(name)-20s %(message)s"
    
    # Component-specific log levels
    DEFAULT_LEVELS = {
        'src.site_monitor': logging.INFO,
        'src.issue_processor': logging.INFO,
        'src.workflow_matcher': logging.INFO,
        'src.github_issue_creator': logging.INFO,
        'src.deliverable_generator': logging.INFO,
        'src.git_manager': logging.INFO,
        'src.search_client': logging.WARNING,
        'urllib3': logging.WARNING,
        'github': logging.WARNING,
        'requests': logging.WARNING,
    }
    
    def __init__(
        self,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        enable_console: bool = True,
        enable_file_rotation: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        Initialize logging configuration.
        
        Args:
            log_level: Global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (if None, uses default based on environment)
            enable_console: Whether to enable console logging
            enable_file_rotation: Whether to use rotating file handler
            max_file_size: Maximum size for each log file before rotation
            backup_count: Number of backup files to keep
        """
        self.log_level = getattr(logging, log_level.upper())
        self.log_file = log_file or self._get_default_log_file()
        self.enable_console = enable_console
        self.enable_file_rotation = enable_file_rotation
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        
        self._configured = False
        self._handlers: Dict[str, logging.Handler] = {}
    
    def _get_default_log_file(self) -> str:
        """
        Determine default log file path based on environment.
        
        Returns:
            Path to the default log file
        """
        if os.getenv('GITHUB_ACTIONS'):
            # In GitHub Actions, log to a temporary file
            return '/tmp/speculum-principum.log'
        else:
            # Local development/production
            return 'site_monitor.log'
    
    def configure_logging(self) -> None:
        """
        Configure the root logger and component-specific loggers.
        
        This method sets up all handlers, formatters, and log levels
        for the entire application.
        """
        if self._configured:
            return
        
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Set root logger level
        root_logger.setLevel(logging.DEBUG)
        
        # Create handlers
        self._create_console_handler()
        self._create_file_handler()
        
        # Configure component-specific loggers
        self._configure_component_loggers()
        
        # Add a startup message
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured - Level: {logging.getLevelName(self.log_level)}")
        if self.log_file:
            logger.info(f"Log file: {self.log_file}")
        
        self._configured = True
    
    def _create_console_handler(self) -> None:
        """Create and configure console handler."""
        if not self.enable_console:
            return
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        
        # Use simpler format for console output
        console_formatter = logging.Formatter(
            self.CONSOLE_FORMAT,
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        logging.getLogger().addHandler(console_handler)
        self._handlers['console'] = console_handler
    
    def _create_file_handler(self) -> None:
        """Create and configure file handler."""
        if not self.log_file:
            return
        
        # Ensure log directory exists
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.enable_file_rotation:
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
        else:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        
        file_handler.setLevel(logging.DEBUG)
        
        # Use detailed format for file output
        file_formatter = logging.Formatter(
            self.DETAILED_FORMAT,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        logging.getLogger().addHandler(file_handler)
        self._handlers['file'] = file_handler
    
    def _configure_component_loggers(self) -> None:
        """Configure loggers for specific components."""
        for logger_name, level in self.DEFAULT_LEVELS.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger for a specific component.
        
        Args:
            name: Logger name (typically __name__ from the calling module)
            
        Returns:
            Configured logger instance
        """
        if not self._configured:
            self.configure_logging()
        
        return logging.getLogger(name)
    
    def set_component_level(self, component: str, level: str) -> None:
        """
        Set log level for a specific component.
        
        Args:
            component: Component name (e.g., 'src.issue_processor')
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        log_level = getattr(logging, level.upper())
        logger = logging.getLogger(component)
        logger.setLevel(log_level)
    
    def add_file_handler(self, filename: str, level: str = "DEBUG") -> None:
        """
        Add an additional file handler for specific logging needs.
        
        Args:
            filename: Path to the log file
            level: Log level for this handler
        """
        handler = logging.FileHandler(filename, encoding='utf-8')
        handler.setLevel(getattr(logging, level.upper()))
        
        formatter = logging.Formatter(
            self.DETAILED_FORMAT,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logging.getLogger().addHandler(handler)
        self._handlers[f'file_{filename}'] = handler
    
    def get_handler(self, handler_name: str) -> Optional[logging.Handler]:
        """
        Get a specific handler by name.
        
        Args:
            handler_name: Name of the handler ('console', 'file', etc.)
            
        Returns:
            Handler instance or None if not found
        """
        return self._handlers.get(handler_name)
    
    def log_system_info(self) -> None:
        """Log system information for debugging purposes."""
        logger = self.get_logger(__name__)
        
        logger.info("=== System Information ===")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Process ID: {os.getpid()}")
        
        # Environment information
        github_actions = os.getenv('GITHUB_ACTIONS', 'false')
        logger.info(f"GitHub Actions: {github_actions}")
        
        if github_actions == 'true':
            logger.info(f"GitHub Workflow: {os.getenv('GITHUB_WORKFLOW', 'unknown')}")
            logger.info(f"GitHub Actor: {os.getenv('GITHUB_ACTOR', 'unknown')}")
        
        logger.info("=== Configuration Complete ===")


class LoggerContextManager:
    """
    Context manager for temporary logging configuration changes.
    
    Useful for testing or temporary debugging scenarios where you need
    to change logging configuration temporarily.
    """
    
    def __init__(self, logger_name: str, level: str):
        """
        Initialize context manager.
        
        Args:
            logger_name: Name of the logger to modify
            level: Temporary log level to set
        """
        self.logger_name = logger_name
        self.new_level = getattr(logging, level.upper())
        self.original_level = None
    
    def __enter__(self):
        """Enter context and set temporary log level."""
        logger = logging.getLogger(self.logger_name)
        self.original_level = logger.level
        logger.setLevel(self.new_level)
        return logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original log level."""
        if self.original_level is not None:
            logger = logging.getLogger(self.logger_name)
            logger.setLevel(self.original_level)


# Global logger configuration instance
_global_config: Optional[SpeculumLoggerConfig] = None


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    **kwargs
) -> SpeculumLoggerConfig:
    """
    Set up global logging configuration.
    
    Args:
        log_level: Global log level
        log_file: Path to log file
        enable_console: Whether to enable console logging
        **kwargs: Additional arguments for SpeculumLoggerConfig
        
    Returns:
        Configured SpeculumLoggerConfig instance
    """
    global _global_config
    
    _global_config = SpeculumLoggerConfig(
        log_level=log_level,
        log_file=log_file,
        enable_console=enable_console,
        **kwargs
    )
    
    _global_config.configure_logging()
    return _global_config


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the global configuration.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    global _global_config
    
    if _global_config is None:
        _global_config = setup_logging()
    
    return _global_config.get_logger(name)


def with_logging_context(logger_name: str, level: str):
    """
    Decorator for temporary logging level changes.
    
    Args:
        logger_name: Name of the logger to modify
        level: Temporary log level
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with LoggerContextManager(logger_name, level):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience function for common error logging patterns
def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    """
    Log an exception with consistent formatting.
    
    Args:
        logger: Logger instance to use
        message: Context message describing what was happening
        exc: Exception that occurred
    """
    logger.error(f"{message}: {type(exc).__name__}: {exc}", exc_info=True)


def log_retry_attempt(logger: logging.Logger, operation: str, attempt: int, max_attempts: int, error: Exception) -> None:
    """
    Log a retry attempt with consistent formatting.
    
    Args:
        logger: Logger instance to use
        operation: Description of the operation being retried
        attempt: Current attempt number
        max_attempts: Maximum number of attempts
        error: Error that caused the retry
    """
    logger.warning(f"Retry {attempt}/{max_attempts} for {operation}: {type(error).__name__}: {error}")