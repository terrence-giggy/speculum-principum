"""
Batch processing module for handling multiple issues efficiently.

This module provides the BatchProcessor class which coordinates the processing
of multiple GitHub issues in batches, with proper error handling, progress tracking,
and rate limiting to avoid overwhelming the GitHub API.

The BatchProcessor handles:
- Issue filtering and prioritization
- Batch size management and queue processing
- Error recovery and retry logic
- Progress reporting and statistics
- Rate limiting to respect API quotas

Key features:
- Configurable batch sizes for memory management
- Parallel processing with controlled concurrency
- Comprehensive error handling with retry strategies
- Detailed progress reporting and metrics
- Integration with existing issue processor infrastructure
"""

import logging
import time
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json

from .issue_processor import IssueProcessor, IssueProcessingStatus, ProcessingResult, IssueData
from ..clients.github_issue_creator import GitHubIssueCreator
from ..utils.config_manager import ConfigManager


@dataclass
class BatchConfig:
    """Configuration for batch processing operations."""
    max_batch_size: int = 10
    max_concurrent_workers: int = 3
    retry_count: int = 2
    retry_delay_seconds: float = 1.0
    rate_limit_delay: float = 0.5
    timeout_seconds: int = 300
    stop_on_first_error: bool = False
    include_assigned: bool = False
    priority_labels: List[str] = field(default_factory=lambda: ['urgent', 'high-priority'])


@dataclass
class BatchMetrics:
    """Metrics and statistics for batch processing operations."""
    total_issues: int = 0
    processed_count: int = 0
    success_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    clarification_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_times: List[float] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Calculate total processing duration."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def average_processing_time(self) -> float:
        """Calculate average processing time per issue."""
        if self.processing_times:
            return sum(self.processing_times) / len(self.processing_times)
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.processed_count > 0:
            return (self.success_count / self.processed_count) * 100
        return 0.0


class BatchProgressReporter:
    """Progress reporting for batch operations."""
    
    def __init__(self, verbose: bool = False, progress_callback: Optional[Callable] = None):
        """
        Initialize progress reporter.
        
        Args:
            verbose: Enable verbose logging output
            progress_callback: Optional callback function for progress updates
        """
        self.verbose = verbose
        self.progress_callback = progress_callback
        self.logger = logging.getLogger(__name__)
    
    def report_start(self, total_issues: int, batch_size: int) -> None:
        """Report batch processing start."""
        if self.verbose:
            self.logger.info(f"Starting batch processing: {total_issues} issues, batch size {batch_size}")
        
        if self.progress_callback:
            self.progress_callback({
                'type': 'start',
                'total_issues': total_issues,
                'batch_size': batch_size
            })
    
    def report_batch_start(self, batch_number: int, batch_size: int) -> None:
        """Report start of a specific batch."""
        if self.verbose:
            self.logger.info(f"Processing batch {batch_number}: {batch_size} issues")
        
        if self.progress_callback:
            self.progress_callback({
                'type': 'batch_start',
                'batch_number': batch_number,
                'batch_size': batch_size
            })
    
    def report_issue_complete(self, issue_number: int, status: str, processing_time: float) -> None:
        """Report completion of single issue."""
        if self.verbose:
            self.logger.info(f"Issue #{issue_number}: {status} ({processing_time:.2f}s)")
        
        if self.progress_callback:
            self.progress_callback({
                'type': 'issue_complete',
                'issue_number': issue_number,
                'status': status,
                'processing_time': processing_time
            })
    
    def report_batch_complete(self, batch_number: int, metrics: BatchMetrics) -> None:
        """Report completion of a batch."""
        if self.verbose:
            self.logger.info(
                f"Batch {batch_number} complete: "
                f"{metrics.success_count} success, "
                f"{metrics.error_count} errors, "
                f"{metrics.skipped_count} skipped"
            )
        
        if self.progress_callback:
            self.progress_callback({
                'type': 'batch_complete',
                'batch_number': batch_number,
                'metrics': metrics
            })
    
    def report_final_summary(self, metrics: BatchMetrics) -> None:
        """Report final processing summary."""
        message = (
            f"Batch processing complete: {metrics.processed_count}/{metrics.total_issues} processed, "
            f"Success rate: {metrics.success_rate:.1f}%, "
            f"Duration: {metrics.duration_seconds:.1f}s"
        )
        
        if self.verbose:
            self.logger.info(message)
            self.logger.info(f"Average processing time: {metrics.average_processing_time:.2f}s")
        
        if self.progress_callback:
            self.progress_callback({
                'type': 'summary',
                'metrics': metrics,
                'message': message
            })


class BatchProcessor:
    """
    Batch processor for handling multiple GitHub issues efficiently.
    
    This class coordinates the processing of multiple issues with proper
    error handling, progress tracking, and rate limiting. It integrates
    with the existing IssueProcessor infrastructure while adding batch-specific
    capabilities like parallel processing and queue management.
    """
    
    def __init__(self, 
                 issue_processor: IssueProcessor,
                 github_client: GitHubIssueCreator,
                 config: Optional[BatchConfig] = None,
                 progress_reporter: Optional[BatchProgressReporter] = None):
        """
        Initialize batch processor.
        
        Args:
            issue_processor: Core issue processor instance
            github_client: GitHub API client for issue queries
            config: Batch processing configuration
            progress_reporter: Progress reporting handler
        """
        self.issue_processor = issue_processor
        self.github_client = github_client
        self.config = config or BatchConfig()
        self.progress_reporter = progress_reporter or BatchProgressReporter()
        self.logger = logging.getLogger(__name__)
        
        # State tracking
        self._processing_state: Dict[str, Any] = {}
        self._cancelled = False
    
    def process_site_monitor_issues(self, 
                                   filters: Optional[Dict[str, Any]] = None,
                                   dry_run: bool = False) -> Tuple[BatchMetrics, List[ProcessingResult]]:
        """
        Process all issues with site-monitor label.
        
        Args:
            filters: Additional filters for issue selection
            dry_run: If True, only analyze what would be processed
            
        Returns:
            Tuple of (batch metrics, list of processing results)
        """
        # Find all site-monitor issues
        issues = self._find_site_monitor_issues(filters or {})
        
        if not issues:
            self.logger.info("No site-monitor issues found for processing")
            return BatchMetrics(), []
        
        return self.process_issues(issues, dry_run=dry_run)
    
    def process_issues(self, 
                      issue_numbers: List[int],
                      dry_run: bool = False) -> Tuple[BatchMetrics, List[ProcessingResult]]:
        """
        Process a specific list of issues in batches.
        
        Args:
            issue_numbers: List of issue numbers to process
            dry_run: If True, only analyze what would be processed
            
        Returns:
            Tuple of (batch metrics, list of processing results)
        """
        if not issue_numbers:
            return BatchMetrics(), []
        
        # Initialize metrics and state
        metrics = BatchMetrics(
            total_issues=len(issue_numbers),
            start_time=datetime.now(timezone.utc)
        )
        
        all_results = []
        self._cancelled = False
        
        # Report processing start
        self.progress_reporter.report_start(
            total_issues=len(issue_numbers),
            batch_size=self.config.max_batch_size
        )
        
        try:
            # Process in batches
            for batch_number, batch_issues in enumerate(self._create_batches(issue_numbers), 1):
                if self._cancelled:
                    self.logger.info("Batch processing cancelled")
                    break
                
                self.progress_reporter.report_batch_start(batch_number, len(batch_issues))
                
                # Process current batch
                batch_results = self._process_batch(batch_issues, dry_run)
                all_results.extend(batch_results)
                
                # Update metrics
                self._update_metrics_from_batch(metrics, batch_results)
                
                # Report batch completion
                self.progress_reporter.report_batch_complete(batch_number, metrics)
                
                # Rate limiting between batches
                if batch_number < len(list(self._create_batches(issue_numbers))):
                    time.sleep(self.config.rate_limit_delay)
                
                # Stop on first error if configured
                if (self.config.stop_on_first_error and 
                    any(r.status == IssueProcessingStatus.ERROR for r in batch_results)):
                    self.logger.warning("Stopping batch processing due to error")
                    break
        
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            raise
        finally:
            metrics.end_time = datetime.now(timezone.utc)
            self.progress_reporter.report_final_summary(metrics)
        
        return metrics, all_results
    
    def cancel_processing(self) -> None:
        """Cancel ongoing batch processing."""
        self._cancelled = True
        self.logger.info("Batch processing cancellation requested")
    
    def _find_site_monitor_issues(self, filters: Dict[str, Any]) -> List[int]:
        """
        Find all issues with site-monitor label that match filters.
        
        Args:
            filters: Filter criteria for issue selection
            
        Returns:
            List of issue numbers matching criteria
        """
        try:
            # Query GitHub for site-monitor issues
            query_parts = ['label:site-monitor', 'state:open']
            
            # Add assignee filter if specified
            if filters.get('assignee'):
                if filters['assignee'] == 'none':
                    query_parts.append('no:assignee')
                else:
                    query_parts.append(f'assignee:{filters["assignee"]}')
            elif not self.config.include_assigned:
                # By default, skip assigned issues to avoid conflicts
                query_parts.append('no:assignee')
            
            # Add additional label filters
            if filters.get('additional_labels'):
                for label in filters['additional_labels']:
                    query_parts.append(f'label:{label}')
            
            # Execute search using get_issues_with_labels
            issues = self.github_client.get_issues_with_labels(['site-monitor'], state='open')
            
            # Filter based on assignee criteria
            filtered_issues = []
            for issue in issues:
                # Check assignee filter
                if filters.get('assignee'):
                    if filters['assignee'] == 'none':
                        if issue.assignee is not None:
                            continue
                    else:
                        if not issue.assignee or issue.assignee.login != filters['assignee']:
                            continue
                elif not self.config.include_assigned:
                    # By default, skip assigned issues to avoid conflicts
                    if issue.assignee is not None:
                        continue
                
                # Check additional label filters
                if filters.get('additional_labels'):
                    issue_labels = [label.name for label in issue.labels]
                    if not any(label in issue_labels for label in filters['additional_labels']):
                        continue
                
                filtered_issues.append(issue)
            
            # Extract issue numbers
            issue_numbers = [issue.number for issue in filtered_issues]
            
            # Apply priority sorting if configured
            if self.config.priority_labels:
                issue_numbers = self._sort_by_priority(issue_numbers, filtered_issues)
            
            self.logger.info(f"Found {len(issue_numbers)} site-monitor issues for processing")
            return issue_numbers
        
        except Exception as e:
            self.logger.error(f"Failed to find site-monitor issues: {e}")
            return []
    
    def _sort_by_priority(self, issue_numbers: List[int], issues: List[Any]) -> List[int]:
        """Sort issues by priority labels."""
        def get_priority_score(issue: Any) -> int:
            labels = [label.name for label in issue.labels]
            for i, priority_label in enumerate(self.config.priority_labels):
                if priority_label in labels:
                    return len(self.config.priority_labels) - i
            return 0
        
        # Create mapping for sorting
        issue_priority_map = {
            issue.number: get_priority_score(issue) 
            for issue in issues
        }
        
        # Sort by priority (highest first), then by issue number (lowest first)
        return sorted(issue_numbers, 
                     key=lambda n: (-issue_priority_map.get(n, 0), n))
    
    def _create_batches(self, issue_numbers: List[int]) -> List[List[int]]:
        """Split issue numbers into processing batches."""
        batch_size = self.config.max_batch_size
        return [
            issue_numbers[i:i + batch_size] 
            for i in range(0, len(issue_numbers), batch_size)
        ]
    
    def _process_batch(self, 
                      issue_numbers: List[int], 
                      dry_run: bool = False) -> List[ProcessingResult]:
        """
        Process a single batch of issues.
        
        Args:
            issue_numbers: Issues to process in this batch
            dry_run: If True, only analyze what would be processed
            
        Returns:
            List of processing results for the batch
        """
        batch_results = []
        
        # Use thread pool for parallel processing
        max_workers = min(self.config.max_concurrent_workers, len(issue_numbers))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all issues for processing
            future_to_issue = {
                executor.submit(self._process_single_issue_with_retry, issue_number, dry_run): issue_number
                for issue_number in issue_numbers
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_issue):
                issue_number = future_to_issue[future]
                start_time = time.time()
                
                try:
                    result = future.result(timeout=self.config.timeout_seconds)
                    processing_time = time.time() - start_time
                    
                    # Report progress
                    self.progress_reporter.report_issue_complete(
                        issue_number, result.status.value, processing_time
                    )
                    
                    batch_results.append(result)
                
                except Exception as e:
                    processing_time = time.time() - start_time
                    error_result = ProcessingResult(
                        issue_number=issue_number,
                        status=IssueProcessingStatus.ERROR,
                        error_message=f"Batch processing failed: {str(e)}",
                        processing_time_seconds=processing_time
                    )
                    
                    self.progress_reporter.report_issue_complete(
                        issue_number, error_result.status.value, processing_time
                    )
                    
                    batch_results.append(error_result)
                    self.logger.error(f"Failed to process issue #{issue_number}: {e}")
        
        return batch_results
    
    def _process_single_issue_with_retry(self, 
                                        issue_number: int, 
                                        dry_run: bool = False) -> ProcessingResult:
        """
        Process a single issue with retry logic.
        
        Args:
            issue_number: Issue number to process
            dry_run: If True, only analyze what would be processed
            
        Returns:
            Processing result for the issue
        """
        last_exception = None
        
        for attempt in range(self.config.retry_count + 1):
            try:
                if dry_run:
                    # For dry run, get issue data and analyze what would happen
                    issue_data_dict = self.github_client.get_issue_data(issue_number)
                    issue_data = IssueData(
                        number=issue_number,
                        title=issue_data_dict.get('title', ''),
                        body=issue_data_dict.get('body', ''),
                        labels=issue_data_dict.get('labels', []),
                        assignees=issue_data_dict.get('assignees', []),
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                        url=issue_data_dict.get('url', '')
                    )
                    # Return analysis result (similar to processing but without side effects)
                    return ProcessingResult(
                        issue_number=issue_number,
                        status=IssueProcessingStatus.PENDING,
                        processing_time_seconds=0.0
                    )
                else:
                    # Get issue data and process
                    issue_data_dict = self.github_client.get_issue_data(issue_number)
                    issue_data = IssueData(
                        number=issue_number,
                        title=issue_data_dict.get('title', ''),
                        body=issue_data_dict.get('body', ''),
                        labels=issue_data_dict.get('labels', []),
                        assignees=issue_data_dict.get('assignees', []),
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                        url=issue_data_dict.get('url', '')
                    )
                    return self.issue_processor.process_issue(issue_data)
            
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.retry_count:
                    self.logger.warning(
                        f"Issue #{issue_number} processing failed (attempt {attempt + 1}), "
                        f"retrying in {self.config.retry_delay_seconds}s: {e}"
                    )
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    self.logger.error(
                        f"Issue #{issue_number} processing failed after {self.config.retry_count + 1} attempts: {e}"
                    )
        
        # All retries failed
        return ProcessingResult(
            issue_number=issue_number,
            status=IssueProcessingStatus.ERROR,
            error_message=f"Failed after {self.config.retry_count + 1} attempts: {str(last_exception)}",
            processing_time_seconds=0.0
        )
    
    def _update_metrics_from_batch(self, 
                                  metrics: BatchMetrics, 
                                  batch_results: List[ProcessingResult]) -> None:
        """Update overall metrics with batch results."""
        for result in batch_results:
            metrics.processed_count += 1
            if result.processing_time_seconds:
                metrics.processing_times.append(result.processing_time_seconds)
            
            if result.status == IssueProcessingStatus.COMPLETED:
                metrics.success_count += 1
            elif result.status == IssueProcessingStatus.ERROR:
                metrics.error_count += 1
            elif result.status == IssueProcessingStatus.NEEDS_CLARIFICATION:
                metrics.clarification_count += 1
            else:
                metrics.skipped_count += 1
    
    def get_processing_state(self) -> Dict[str, Any]:
        """Get current processing state for monitoring."""
        return self._processing_state.copy()
    
    def save_batch_results(self, 
                          results: List[ProcessingResult], 
                          output_path: str) -> None:
        """Save batch processing results to file."""
        try:
            results_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_issues': len(results),
                'results': [
                    {
                        'issue_number': r.issue_number,
                        'status': r.status.value,
                        'error_message': r.error_message,
                        'clarification_needed': r.clarification_needed,
                        'processing_time_seconds': r.processing_time_seconds,
                        'created_files': r.created_files or [],
                        'workflow_name': r.workflow_name
                    }
                    for r in results
                ]
            }
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(results_data, f, indent=2)
            
            self.logger.info(f"Batch results saved to {output_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to save batch results: {e}")