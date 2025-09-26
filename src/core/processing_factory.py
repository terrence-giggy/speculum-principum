"""
Factory for creating processing components without circular dependencies.

This module provides factory functions that create and configure
processing components in the correct order, eliminating circular imports.
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


class ProcessingFactory:
    """
    Factory for creating processing components.
    
    This factory manages the creation and configuration of issue processors
    and batch processors without introducing circular dependencies.
    """
    
    @staticmethod
    def create_github_integrated_processor(
        github_token: str,
        repository: str,
        config_path: str = "config.yaml",
        workflow_dir: Optional[str] = None,
        output_base_dir: Optional[str] = None
    ):
        """
        Create a GitHub-integrated issue processor.
        
        Args:
            github_token: GitHub personal access token
            repository: Repository name in format 'owner/repo'
            config_path: Path to configuration file
            workflow_dir: Override for workflow directory path
            output_base_dir: Override for output base directory
            
        Returns:
            GitHubIntegratedIssueProcessor instance
        """
        from .issue_processor import GitHubIntegratedIssueProcessor
        return GitHubIntegratedIssueProcessor(
            github_token=github_token,
            repository=repository,
            config_path=config_path,
            workflow_dir=workflow_dir,
            output_base_dir=output_base_dir
        )
    
    @staticmethod
    def create_batch_processor(
        issue_processor,
        github_client,
        batch_size: int = 10,
        max_workers: int = 3,
        include_assigned: bool = False,
        verbose: bool = True
    ):
        """
        Create a batch processor with the given configuration.
        
        Args:
            issue_processor: Issue processor instance
            github_client: GitHub client instance
            batch_size: Maximum issues per batch
            max_workers: Maximum concurrent workers
            include_assigned: Whether to include assigned issues
            verbose: Enable verbose progress reporting
            
        Returns:
            Configured BatchProcessor instance
        """
        from .batch_processor import BatchProcessor, BatchConfig, BatchProgressReporter
        
        # Configure batch processing
        batch_config = BatchConfig(
            max_batch_size=batch_size,
            max_concurrent_workers=min(max_workers, batch_size),
            include_assigned=include_assigned
        )
        
        # Create progress reporter
        progress_reporter = BatchProgressReporter(verbose=verbose)
        
        # Create and return batch processor
        return BatchProcessor(
            issue_processor=issue_processor,
            github_client=github_client,
            config=batch_config,
            progress_reporter=progress_reporter
        )
    
    @staticmethod
    def create_complete_processing_system(
        github_token: str,
        repository: str,
        config_path: str = "config.yaml",
        workflow_dir: Optional[str] = None,
        output_base_dir: Optional[str] = None,
        batch_size: int = 10,
        max_workers: int = 3
    ):
        """
        Create a complete processing system with both issue and batch processors.
        
        Args:
            github_token: GitHub personal access token
            repository: Repository name in format 'owner/repo'
            config_path: Path to configuration file
            workflow_dir: Override for workflow directory path
            output_base_dir: Override for output base directory
            batch_size: Maximum issues per batch
            max_workers: Maximum concurrent workers
            
        Returns:
            Tuple of (issue_processor, batch_processor)
        """
        # Create issue processor first
        issue_processor = ProcessingFactory.create_github_integrated_processor(
            github_token=github_token,
            repository=repository,
            config_path=config_path,
            workflow_dir=workflow_dir,
            output_base_dir=output_base_dir
        )
        
        # Create batch processor using the issue processor
        batch_processor = ProcessingFactory.create_batch_processor(
            issue_processor=issue_processor,
            github_client=issue_processor.github,
            batch_size=batch_size,
            max_workers=max_workers
        )
        
        return issue_processor, batch_processor