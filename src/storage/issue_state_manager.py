"""
Issue State Manager

This module handles the persistent state management for issue processing,
including tracking processing status, managing timeouts, and maintaining
processing history.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

from ..utils.logging_config import get_logger, log_exception


class IssueProcessingStatus(Enum):
    """Status of issue processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class IssueStateManager:
    """
    Manages persistent state for issue processing operations.
    
    This class handles:
    - Loading and saving processing state to disk
    - Validating state structure and cleaning up corrupted data
    - Tracking processing status and metadata for each issue
    - Managing processing timeouts
    """
    
    def __init__(self, 
                 output_dir: Path,
                 enable_state_saving: bool = True,
                 processing_timeout: int = 300):
        """
        Initialize the issue state manager.
        
        Args:
            output_dir: Directory where state file will be stored
            enable_state_saving: Whether to enable persistent state saving
            processing_timeout: Timeout in seconds for processing operations
        """
        self.logger = get_logger(__name__)
        self.output_dir = output_dir
        self.enable_state_saving = enable_state_saving
        self.processing_timeout = processing_timeout
        self._processing_state: Dict[str, Dict[str, Any]] = {}
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing state
        self._load_processing_state()
    
    @property
    def state_file_path(self) -> Path:
        """Get the path to the state file."""
        return self.output_dir / '.processing_state.json'
    
    def _load_processing_state(self) -> None:
        """Load processing state from persistent storage with error handling."""
        if not self.enable_state_saving:
            self._processing_state = {}
            return
            
        state_file = self.state_file_path
        try:
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    self._processing_state = json.load(f)
                self.logger.info(f"Loaded processing state for {len(self._processing_state)} issues")
                
                # Validate loaded state structure
                self._validate_processing_state()
            else:
                self.logger.info("No existing processing state file found, starting fresh")
                self._processing_state = {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Corrupted processing state file, starting fresh: {e}")
            self._processing_state = {}
            # Backup the corrupted file
            try:
                backup_file = state_file.with_suffix(f'.backup.{int(datetime.now().timestamp())}')
                state_file.rename(backup_file)
                self.logger.info(f"Corrupted state file backed up to: {backup_file}")
            except Exception as backup_error:
                self.logger.warning(f"Failed to backup corrupted state file: {backup_error}")
        except Exception as e:
            log_exception(self.logger, "Failed to load processing state", e)
            self._processing_state = {}

    def _validate_processing_state(self) -> None:
        """Validate the structure of loaded processing state."""
        if not isinstance(self._processing_state, dict):
            self.logger.warning("Invalid processing state format, resetting")
            self._processing_state = {}
            return
        
        # Clean up invalid entries
        valid_statuses = {status.value for status in IssueProcessingStatus}
        cleaned_count = 0
        
        for issue_id, state in list(self._processing_state.items()):
            if not isinstance(state, dict) or 'status' not in state:
                del self._processing_state[issue_id]
                cleaned_count += 1
            elif state['status'] not in valid_statuses:
                self.logger.warning(f"Invalid status '{state['status']}' for issue {issue_id}, removing entry")
                del self._processing_state[issue_id]
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} invalid state entries")
            self._save_processing_state()

    def _save_processing_state(self) -> None:
        """Save processing state to persistent storage with error handling."""
        if not self.enable_state_saving:
            return
            
        try:
            state_file = self.state_file_path
            # Write to a temporary file first, then move it to avoid corruption
            temp_file = state_file.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._processing_state, f, indent=2, ensure_ascii=False)
            
            # Atomic move
            temp_file.replace(state_file)
            self.logger.debug(f"Saved processing state for {len(self._processing_state)} issues")
            
        except Exception as e:
            log_exception(self.logger, "Failed to save processing state", e)

    def get_issue_status(self, issue_number: int) -> IssueProcessingStatus:
        """Get current processing status for an issue."""
        issue_key = str(issue_number)
        state = self._processing_state.get(issue_key, {})
        status_value = state.get('status', IssueProcessingStatus.PENDING.value)
        
        try:
            return IssueProcessingStatus(status_value)
        except ValueError:
            # Invalid status value, reset to pending
            self.logger.warning(f"Invalid status '{status_value}' for issue #{issue_number}, resetting to pending")
            return IssueProcessingStatus.PENDING

    def update_issue_status(self, 
                           issue_number: int, 
                           status: IssueProcessingStatus,
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """Update processing status for an issue."""
        issue_key = str(issue_number)
        current_state = self._processing_state.get(issue_key, {})
        
        updated_state = {
            **current_state,
            'status': status.value,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        if metadata:
            updated_state.update(metadata)
        
        self._processing_state[issue_key] = updated_state
        self._save_processing_state()
        
        self.logger.debug(f"Updated issue #{issue_number} status to {status.value}")

    def get_issue_metadata(self, issue_number: int) -> Dict[str, Any]:
        """Get metadata for an issue."""
        issue_key = str(issue_number)
        return self._processing_state.get(issue_key, {}).copy()

    def check_processing_timeout(self, issue_number: int, start_time: datetime) -> None:
        """
        Check if processing has exceeded the timeout limit.
        
        Args:
            issue_number: Issue number to check
            start_time: When processing started
            
        Raises:
            ProcessingTimeoutError: If processing has timed out
        """
        from ..core.issue_processor import ProcessingTimeoutError  # Import here to avoid circular imports
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        if elapsed_time > self.processing_timeout:
            error_msg = f"Processing timeout ({self.processing_timeout}s) exceeded for issue #{issue_number}"
            self.logger.error(error_msg)
            
            # Update status to timeout
            self.update_issue_status(issue_number, IssueProcessingStatus.TIMEOUT, {
                'timeout_at': datetime.now(timezone.utc).isoformat(),
                'elapsed_seconds': elapsed_time
            })
            
            raise ProcessingTimeoutError(error_msg, issue_number=issue_number)

    def mark_issue_completed(self, 
                           issue_number: int, 
                           deliverables: Optional[list] = None,
                           processing_time: Optional[float] = None) -> None:
        """Mark an issue as completed with optional metadata."""
        metadata = {
            'completed_at': datetime.now(timezone.utc).isoformat()
        }
        
        if deliverables:
            metadata['deliverables'] = deliverables
        
        if processing_time:
            metadata['processing_time_seconds'] = processing_time
        
        self.update_issue_status(issue_number, IssueProcessingStatus.COMPLETED, metadata)

    def mark_issue_error(self, 
                        issue_number: int, 
                        error_message: str,
                        error_code: Optional[str] = None) -> None:
        """Mark an issue as having an error."""
        metadata = {
            'error_at': datetime.now(timezone.utc).isoformat(),
            'error_message': error_message
        }
        
        if error_code:
            metadata['error_code'] = error_code
        
        self.update_issue_status(issue_number, IssueProcessingStatus.ERROR, metadata)

    def get_all_issues_with_status(self, status: IssueProcessingStatus) -> Dict[str, Dict[str, Any]]:
        """Get all issues with a specific status."""
        return {
            issue_id: state 
            for issue_id, state in self._processing_state.items()
            if state.get('status') == status.value
        }

    def cleanup_old_state(self, days_old: int = 30) -> int:
        """
        Clean up state entries older than specified days.
        
        Args:
            days_old: Number of days after which to remove completed/error states
            
        Returns:
            Number of entries removed
        """
        if not self.enable_state_saving:
            return 0
        
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        removed_count = 0
        
        # Only clean up completed or error states
        cleanable_statuses = {
            IssueProcessingStatus.COMPLETED.value,
            IssueProcessingStatus.ERROR.value,
            IssueProcessingStatus.TIMEOUT.value
        }
        
        for issue_id, state in list(self._processing_state.items()):
            if state.get('status') not in cleanable_statuses:
                continue
                
            # Check if state has an update timestamp
            updated_at_str = state.get('updated_at') or state.get('completed_at') or state.get('error_at')
            if not updated_at_str:
                continue
                
            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                if updated_at < cutoff_date:
                    del self._processing_state[issue_id]
                    removed_count += 1
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Invalid timestamp for issue {issue_id}: {e}")
                continue
        
        if removed_count > 0:
            self._save_processing_state()
            self.logger.info(f"Cleaned up {removed_count} old state entries")
        
        return removed_count