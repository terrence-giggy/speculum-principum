"""
Error Handler

This module provides centralized error handling, recovery strategies, and retry
logic for issue processing operations.
"""

import functools
import logging
import time
from typing import Dict, Any, Optional, Callable, Type, Tuple
from datetime import datetime

from .logging_config import get_logger, log_exception, log_retry_attempt
from ..storage.issue_state_manager import IssueStateManager, IssueProcessingStatus


class ErrorHandler:
    """
    Centralized error handling and recovery for issue processing.
    
    This class provides:
    - Retry decorators with exponential backoff
    - Error recovery strategies
    - Fallback workflow execution
    - Error classification and reporting
    """
    
    def __init__(self, 
                 state_manager: IssueStateManager,
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0):
        """
        Initialize the error handler.
        
        Args:
            state_manager: Issue state manager for tracking failures
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
        """
        self.logger = get_logger(__name__)
        self.state_manager = state_manager
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def retry_on_exception(self,
                          exceptions: Tuple[Type[Exception], ...] = (Exception,),
                          max_retries: Optional[int] = None,
                          base_delay: Optional[float] = None) -> Callable:
        """
        Decorator to retry function calls on specific exceptions.
        
        Args:
            exceptions: Tuple of exception types to retry on
            max_retries: Override default max retries
            base_delay: Override default base delay
            
        Returns:
            Decorated function with retry logic
        """
        retry_count = max_retries if max_retries is not None else self.max_retries
        delay = base_delay if base_delay is not None else self.base_delay
        
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(retry_count + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        
                        if attempt == retry_count:
                            # Final attempt failed
                            log_exception(self.logger, f"All retry attempts failed for {func.__name__}", e)
                            raise
                        
                        # Calculate delay with exponential backoff
                        retry_delay = min(delay * (2 ** attempt), self.max_delay)
                        log_retry_attempt(self.logger, func.__name__, attempt + 1, retry_count, retry_delay)
                        time.sleep(retry_delay)
                    except Exception as e:
                        # Non-retryable exception
                        log_exception(self.logger, f"Non-retryable exception in {func.__name__}", e)
                        raise
                
                # This should never be reached, but just in case
                if last_exception:
                    raise last_exception
                    
            return wrapper
        return decorator

    def handle_processing_error(self, 
                              issue_number: int,
                              error: Exception,
                              error_code: Optional[str] = None,
                              recoverable: bool = False) -> Dict[str, Any]:
        """
        Handle a processing error by logging and updating state.
        
        Args:
            issue_number: Issue number that failed
            error: The exception that occurred
            error_code: Optional error code for categorization
            recoverable: Whether the error might be recoverable
            
        Returns:
            Error details dictionary
        """
        error_message = str(error)
        self.logger.error(f"Processing error for issue #{issue_number}: {error_message}")
        log_exception(self.logger, f"Issue #{issue_number} processing failed", error)
        
        # Update issue status to error
        self.state_manager.mark_issue_error(
            issue_number=issue_number,
            error_message=error_message,
            error_code=error_code
        )
        
        error_details = {
            'error_type': type(error).__name__,
            'error_message': error_message,
            'error_code': error_code,
            'recoverable': recoverable,
            'timestamp': datetime.now().isoformat()
        }
        
        # Log additional context if available
        if hasattr(error, 'issue_number'):
            error_details['original_issue_number'] = getattr(error, 'issue_number', None)
        if hasattr(error, 'error_code'):
            error_details['original_error_code'] = getattr(error, 'error_code', None)
            
        return error_details

    def execute_with_fallback(self, 
                            primary_func: Callable,
                            fallback_func: Optional[Callable] = None,
                            issue_number: Optional[int] = None,
                            *args, **kwargs) -> Tuple[Any, bool]:
        """
        Execute a function with fallback strategy if it fails.
        
        Args:
            primary_func: Primary function to execute
            fallback_func: Fallback function to execute on failure
            issue_number: Issue number for error tracking
            *args, **kwargs: Arguments to pass to both functions
            
        Returns:
            Tuple of (result, used_fallback)
        """
        try:
            result = primary_func(*args, **kwargs)
            return result, False
        except Exception as e:
            self.logger.warning(f"Primary function failed: {e}")
            
            if fallback_func is None:
                # No fallback available, re-raise
                if issue_number:
                    self.handle_processing_error(
                        issue_number=issue_number,
                        error=e,
                        error_code="NO_FALLBACK"
                    )
                raise
            
            try:
                self.logger.info("Attempting fallback strategy")
                result = fallback_func(*args, **kwargs)
                
                if issue_number:
                    self.logger.info(f"Fallback successful for issue #{issue_number}")
                
                return result, True
            except Exception as fallback_error:
                self.logger.error(f"Fallback also failed: {fallback_error}")
                
                if issue_number:
                    # Log both failures
                    combined_error = f"Primary: {e}; Fallback: {fallback_error}"
                    self.handle_processing_error(
                        issue_number=issue_number,
                        error=Exception(combined_error),
                        error_code="BOTH_FAILED"
                    )
                raise fallback_error

    def classify_error(self, error: Exception) -> Dict[str, Any]:
        """
        Classify an error to determine handling strategy.
        
        Args:
            error: Exception to classify
            
        Returns:
            Error classification information
        """
        classification = {
            'error_type': type(error).__name__,
            'severity': 'medium',
            'category': 'unknown',
            'recoverable': False,
            'retry_recommended': False,
            'user_actionable': False
        }
        
        error_message = str(error).lower()
        error_type = type(error).__name__
        
        # Network/connectivity errors
        if any(keyword in error_message for keyword in ['timeout', 'connection', 'network', 'unreachable']):
            classification.update({
                'category': 'network',
                'recoverable': True,
                'retry_recommended': True,
                'severity': 'low'
            })
        
        # Configuration errors
        elif any(keyword in error_message for keyword in ['config', 'not found', 'missing', 'invalid']):
            classification.update({
                'category': 'configuration',
                'recoverable': False,
                'user_actionable': True,
                'severity': 'high'
            })
        
        # Permission errors
        elif any(keyword in error_message for keyword in ['permission', 'access', 'forbidden', 'unauthorized']):
            classification.update({
                'category': 'permission',
                'recoverable': False,
                'user_actionable': True,
                'severity': 'high'
            })
        
        # Resource errors
        elif any(keyword in error_message for keyword in ['memory', 'disk', 'space', 'resource']):
            classification.update({
                'category': 'resource',
                'recoverable': True,
                'retry_recommended': False,  # Usually need manual intervention
                'user_actionable': True,
                'severity': 'high'
            })
        
        # Validation errors
        elif any(keyword in error_message for keyword in ['validation', 'invalid', 'malformed', 'corrupt']):
            classification.update({
                'category': 'validation',
                'recoverable': False,
                'user_actionable': True,
                'severity': 'medium'
            })
        
        # Workflow/processing errors
        elif 'workflow' in error_message or error_type.endswith('WorkflowError'):
            classification.update({
                'category': 'workflow',
                'recoverable': True,
                'retry_recommended': True,
                'severity': 'medium'
            })
        
        # Timeout errors
        elif 'timeout' in error_message or error_type.endswith('TimeoutError'):
            classification.update({
                'category': 'timeout',
                'recoverable': True,
                'retry_recommended': True,
                'severity': 'low'
            })
        
        # GitHub API errors
        elif any(keyword in error_message for keyword in ['github', 'api', 'rate limit']):
            classification.update({
                'category': 'github_api',
                'recoverable': True,
                'retry_recommended': True,
                'severity': 'low' if 'rate limit' in error_message else 'medium'
            })
        
        return classification

    def create_error_report(self, 
                          issue_number: int,
                          error: Exception,
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a comprehensive error report.
        
        Args:
            issue_number: Issue number where error occurred
            error: The exception that occurred
            context: Additional context information
            
        Returns:
            Comprehensive error report
        """
        classification = self.classify_error(error)
        
        report = {
            'issue_number': issue_number,
            'timestamp': datetime.now().isoformat(),
            'error': {
                'message': str(error),
                'type': type(error).__name__,
                'classification': classification
            },
            'recovery_suggestions': self._get_recovery_suggestions(classification),
            'context': context or {}
        }
        
        # Add error attributes if available
        if hasattr(error, 'error_code'):
            error_code = getattr(error, 'error_code', None)
            if error_code:
                report['error']['code'] = error_code
        if hasattr(error, '__traceback__'):
            # Don't include full traceback in report, but note it's available
            report['error']['has_traceback'] = True
        
        return report

    def _get_recovery_suggestions(self, classification: Dict[str, Any]) -> list:
        """Get recovery suggestions based on error classification."""
        suggestions = []
        
        category = classification.get('category', 'unknown')
        
        if category == 'network':
            suggestions.extend([
                "Check network connectivity",
                "Verify external service availability",
                "Retry the operation after a short delay"
            ])
        elif category == 'configuration':
            suggestions.extend([
                "Verify configuration file syntax and values",
                "Check that all required environment variables are set",
                "Ensure file paths exist and are accessible"
            ])
        elif category == 'permission':
            suggestions.extend([
                "Check file and directory permissions",
                "Verify API credentials and tokens",
                "Ensure the user has necessary access rights"
            ])
        elif category == 'resource':
            suggestions.extend([
                "Check available disk space",
                "Monitor memory usage",
                "Clean up temporary files if needed"
            ])
        elif category == 'workflow':
            suggestions.extend([
                "Verify workflow definition files",
                "Check workflow template syntax",
                "Ensure required workflow dependencies are available"
            ])
        elif category == 'github_api':
            suggestions.extend([
                "Check GitHub API rate limits",
                "Verify GitHub token permissions",
                "Wait before retrying API calls"
            ])
        else:
            suggestions.extend([
                "Check application logs for more details",
                "Verify input data format and content",
                "Consider retrying the operation"
            ])
        
        if classification.get('retry_recommended', False):
            suggestions.insert(0, "This error may be transient - retry is recommended")
        
        return suggestions