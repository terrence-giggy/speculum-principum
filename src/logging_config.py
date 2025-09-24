"""
Logging Configuration Module

Provides centralized logging configuration for the Speculum Principum application.
This simplified version maintains all the functionality while removing unused complexity.
"""

import logging
import logging.handlers
import sys
import os
from typing import Optional
from pathlib import Path


# Default log formats
DETAILED_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - "
    "[%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"
)

SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

CONSOLE_FORMAT = "%(levelname)-8s %(name)-20s %(message)s"

# Component-specific log levels
DEFAULT_COMPONENT_LEVELS = {
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

# Global state to track if logging has been configured
_logging_configured = False


def _get_default_log_file() -> str:
    """Determine default log file path based on environment."""
    if os.getenv('GITHUB_ACTIONS'):
        return '/tmp/speculum-principum.log'
    else:
        return 'site_monitor.log'


def _create_console_handler(log_level: int) -> Optional[logging.Handler]:
    """Create and configure console handler."""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    console_formatter = logging.Formatter(
        CONSOLE_FORMAT,
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    return console_handler


def _create_file_handler(log_file: str, enable_rotation: bool = True) -> Optional[logging.Handler]:
    """Create and configure file handler."""
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    if enable_rotation:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
    else:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
    
    file_handler.setLevel(logging.DEBUG)
    
    file_formatter = logging.Formatter(
        DETAILED_FORMAT,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    return file_handler


def _configure_component_loggers() -> None:
    """Configure loggers for specific components."""
    for logger_name, level in DEFAULT_COMPONENT_LEVELS.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file_rotation: bool = True
) -> bool:
    """
    Set up global logging configuration.
    
    Args:
        log_level: Global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (if None, uses default based on environment)
        enable_console: Whether to enable console logging
        enable_file_rotation: Whether to use rotating file handler
        
    Returns:
        True if logging was successfully configured
    """
    global _logging_configured
    
    if _logging_configured:
        return True
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root logger level
    root_logger.setLevel(logging.DEBUG)
    
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create console handler if requested
    if enable_console:
        console_handler = _create_console_handler(numeric_level)
        if console_handler:
            root_logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if log_file:
        file_handler = _create_file_handler(log_file, enable_file_rotation)
        if file_handler:
            root_logger.addHandler(file_handler)
    elif log_file is None:
        # Use default log file
        default_file = _get_default_log_file()
        file_handler = _create_file_handler(default_file, enable_file_rotation)
        if file_handler:
            root_logger.addHandler(file_handler)
    
    # Configure component-specific loggers
    _configure_component_loggers()
    
    # Add a startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {logging.getLevelName(numeric_level)}")
    if log_file or log_file is None:
        actual_log_file = log_file or _get_default_log_file()
        logger.info(f"Log file: {actual_log_file}")
    
    _logging_configured = True
    return True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the global configuration.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    global _logging_configured
    
    if not _logging_configured:
        setup_logging()
    
    return logging.getLogger(name)


def set_component_level(component: str, level: str) -> None:
    """
    Set logging level for a specific component.
    
    Args:
        component: Component name (logger name)
        level: Log level to set (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger(component)
    logger.setLevel(log_level)


class LoggerContextManager:
    """Context manager for temporary logger level changes."""
    
    def __init__(self, logger_name: str, level: str):
        """
        Initialize context manager.
        
        Args:
            logger_name: Name of the logger to modify
            level: Temporary log level
        """
        self.logger_name = logger_name
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.original_level = None
    
    def __enter__(self):
        """Enter context and set temporary log level."""
        logger = logging.getLogger(self.logger_name)
        self.original_level = logger.level
        logger.setLevel(self.level)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original log level."""
        if self.original_level is not None:
            logger = logging.getLogger(self.logger_name)
            logger.setLevel(self.original_level)


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
