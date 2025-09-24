"""
Site Monitor Service
Main orchestration service that combines search, deduplication, and GitHub operations
"""

import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from ..utils.config_manager import MonitorConfig, load_config_with_env_substitution
from ..clients.search_client import GoogleCustomSearchClient, SearchResult, create_search_summary
from .deduplication import DeduplicationManager, ProcessedEntry
from ..clients.github_issue_creator import GitHubIssueCreator

# Import issue processor only when needed to avoid circular dependencies
try:
    from .issue_processor import IssueProcessor
    ISSUE_PROCESSOR_AVAILABLE = True
except ImportError:
    ISSUE_PROCESSOR_AVAILABLE = False


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('site_monitor.log')
    ]
)

logger = logging.getLogger(__name__)


class SiteMonitorService:
    """Main service for monitoring sites and creating GitHub issues"""
    
    def __init__(self, config: MonitorConfig, github_token: str):
        self.config = config
        self.github_token = github_token
        
        # Initialize components
        self.search_client = GoogleCustomSearchClient(config.search)
        self.dedup_manager = DeduplicationManager(
            storage_path=config.storage_path,
            retention_days=30
        )
        self.github_client = GitHubIssueCreator(
            token=github_token,
            repository=config.github.repository
        )
        
        # Initialize issue processor if available and enabled
        self.issue_processor = None
        if (ISSUE_PROCESSOR_AVAILABLE and 
            hasattr(config, 'agent') and 
            getattr(config.agent, 'enabled', False)):
            try:
                self.issue_processor = IssueProcessor(
                    config_path=getattr(config, 'config_path', 'config.yaml'),
                    workflow_dir=getattr(config.agent, 'workflow_dir', None),
                    output_base_dir=getattr(config.agent, 'output_dir', None),
                    enable_git=getattr(config.agent, 'enable_git', True)
                )
                logger.info("Issue processor initialized and enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize issue processor: {e}")
                self.issue_processor = None
        
        # Set logging level
        logging.getLogger().setLevel(getattr(logging, config.log_level))
        logger.info(f"Initialized SiteMonitorService for repository: {config.github.repository}")
    
    def run_monitoring_cycle(self, create_individual_issues: bool = True) -> Dict[str, Any]:
        """
        Run a complete monitoring cycle
        
        Args:
            create_individual_issues: Whether to create individual issues for each result
            
        Returns:
            Dictionary with monitoring results and statistics
        """
        logger.info("Starting site monitoring cycle")
        cycle_start = datetime.utcnow()
        
        try:
            # Step 1: Search all sites
            logger.info("Step 1: Searching all configured sites")
            all_search_results = self.search_client.search_all_sites(self.config.sites)
            
            # Step 2: Filter out already processed results
            logger.info("Step 2: Filtering out already processed results")
            new_results = self._filter_new_results(all_search_results)
            
            # Step 3: Create individual issues for sites with new results
            individual_issues = []
            if create_individual_issues:
                logger.info("Step 3: Creating individual GitHub issues")
                individual_issues = self._create_individual_issues(new_results)
            
            # Step 4: Mark results as processed
            logger.info("Step 4: Marking results as processed")
            processed_entries = self._mark_results_processed(new_results, individual_issues)
            
            # Step 5: Save deduplication data
            logger.info("Step 5: Saving deduplication data")
            self.dedup_manager.save_processed_entries()
            
            # Step 6: Process issues with agent workflows (if enabled)
            issue_processing_results = []
            if individual_issues and self.issue_processor:
                logger.info("Step 6: Processing issues with automated workflows")
                issue_processing_results = self._process_created_issues(individual_issues)
            
            # Calculate cycle statistics
            cycle_end = datetime.utcnow()
            cycle_duration = (cycle_end - cycle_start).total_seconds()
            
            total_new_results = sum(len(results) for results in new_results.values())
            
            results = {
                'success': True,
                'cycle_start': cycle_start.isoformat(),
                'cycle_end': cycle_end.isoformat(),
                'cycle_duration_seconds': cycle_duration,
                'sites_monitored': len(self.config.sites),
                'total_search_results': sum(len(results) for results in all_search_results.values()),
                'new_results_found': total_new_results,
                'individual_issues_created': len(individual_issues),
                'individual_issue_numbers': [issue.number for issue in individual_issues],
                'issue_processing_results': issue_processing_results,
                'rate_limit_status': self.search_client.get_rate_limit_status(),
                'deduplication_stats': self.dedup_manager.get_processed_stats(),
                'error': None
            }
            
            logger.info(f"Monitoring cycle completed successfully in {cycle_duration:.2f} seconds")
            logger.info(f"Found {total_new_results} new results across {len(self.config.sites)} sites")
            
            return results
            
        except Exception as e:
            logger.error(f"Monitoring cycle failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'cycle_start': cycle_start.isoformat(),
                'cycle_end': datetime.utcnow().isoformat()
            }
    
    def _filter_new_results(self, all_results: Dict[str, List[SearchResult]]) -> Dict[str, List[SearchResult]]:
        """Filter search results to only include new/unprocessed ones"""
        new_results = {}
        
        for site_name, results in all_results.items():
            if results:
                filtered_results = self.dedup_manager.filter_new_results(results, site_name)
                new_results[site_name] = filtered_results
            else:
                new_results[site_name] = []
        
        return new_results
    
    def _create_individual_issues(self, new_results: Dict[str, List[SearchResult]]) -> List[Any]:
        """Create individual GitHub issues for each search result"""
        issues = []
        
        for site_name, results in new_results.items():
            if not results:
                continue
            
            for result in results:
                try:
                    issue = self.github_client.create_individual_result_issue(
                        site_name=site_name,
                        result=result,
                        labels=self.config.github.issue_labels
                    )
                    issues.append(issue)
                    logger.info(f"Created issue #{issue.number} for {site_name}: {result.title[:50]}...")
                    
                except Exception as e:
                    logger.error(f"Failed to create issue for result from {site_name}: {e}")
                    continue
        
        return issues
    
    def _mark_results_processed(self, new_results: Dict[str, List[SearchResult]], 
                              individual_issues: List[Any]) -> List[ProcessedEntry]:
        """Mark search results as processed in the deduplication system"""
        processed_entries = []
        
        # Create a flat list of (site_name, result) tuples in the same order as issues
        result_pairs = []
        for site_name, results in new_results.items():
            for result in results:
                result_pairs.append((site_name, result))
        
        # Now each issue corresponds to one result in the same order
        for i, issue in enumerate(individual_issues):
            if i < len(result_pairs):
                site_name, result = result_pairs[i]
                entry = self.dedup_manager.mark_result_processed(
                    result=result,
                    site_name=site_name,
                    issue_number=issue.number
                )
                processed_entries.append(entry)
        
        # Handle any remaining results that didn't get issues (due to errors)
        for i in range(len(individual_issues), len(result_pairs)):
            site_name, result = result_pairs[i]
            entry = self.dedup_manager.mark_result_processed(
                result=result,
                site_name=site_name,
                issue_number=None  # No issue was created
            )
            processed_entries.append(entry)
        
        return processed_entries
    
    def _process_created_issues(self, individual_issues: List[Any]) -> List[Dict[str, Any]]:
        """
        Process newly created issues with the issue processor agent.
        
        Args:
            individual_issues: List of GitHub issue objects to process
            
        Returns:
            List of processing results for each issue
        """
        processing_results = []
        
        if not self.issue_processor:
            logger.debug("Issue processor not available, skipping issue processing")
            return processing_results
        
        for issue in individual_issues:
            try:
                logger.info(f"Processing issue #{issue.number} with automated workflow")
                
                # Process the issue using the issue processor
                result = self.issue_processor.process_issue(issue.number)
                processing_results.append({
                    'issue_number': issue.number,
                    'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
                    'workflow': result.workflow_name or 'none',
                    'deliverables': result.created_files or [],
                    'error': result.error_message
                })
                
                # Add small delay between processing to avoid overwhelming the system
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to process issue #{issue.number}: {e}")
                processing_results.append({
                    'issue_number': issue.number,
                    'status': 'error',
                    'workflow': 'none',
                    'deliverables': [],
                    'error': str(e)
                })
        
        successful_processes = sum(1 for r in processing_results if r['status'] not in ['error', 'failed'])
        logger.info(f"Issue processing completed: {successful_processes}/{len(individual_issues)} issues processed successfully")
        
        return processing_results
    
    def setup_repository(self) -> None:
        """Set up the repository with necessary labels and configuration"""
        logger.info("Setting up repository for site monitoring")
        
        try:
            # Create monitoring labels
            created_labels = self.github_client.create_monitoring_labels()
            if created_labels:
                logger.info(f"Created labels: {', '.join(created_labels)}")
            else:
                logger.info("All required labels already exist")
            
        except Exception as e:
            logger.error(f"Failed to set up repository: {e}")
            raise
    
    def cleanup_old_data(self, days_old: int = 7, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up old monitoring data and issues"""
        logger.info(f"Cleaning up data older than {days_old} days (dry_run={dry_run})")
        
        try:
            # Clean up old deduplication entries
            original_entries = len(self.dedup_manager.processed_entries)
            self.dedup_manager.cleanup_storage()
            remaining_entries = len(self.dedup_manager.processed_entries)
            removed_entries = original_entries - remaining_entries
            
            # Clean up old GitHub issues
            closed_issues = self.github_client.close_old_monitoring_issues(
                days_old=days_old,
                dry_run=dry_run
            )
            
            cleanup_results = {
                'success': True,
                'removed_dedup_entries': removed_entries,
                'closed_issues': len(closed_issues),
                'closed_issue_numbers': closed_issues,
                'dry_run': dry_run
            }
            
            logger.info(f"Cleanup completed: removed {removed_entries} entries, closed {len(closed_issues)} issues")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status and statistics"""
        return {
            'repository': self.config.github.repository,
            'sites_configured': len(self.config.sites),
            'site_names': [site.name for site in self.config.sites],
            'rate_limit_status': self.search_client.get_rate_limit_status(),
            'deduplication_stats': self.dedup_manager.get_processed_stats(),
            'config': {
                'daily_query_limit': self.config.search.daily_query_limit,
                'results_per_query': self.config.search.results_per_query,
                'date_range_days': self.config.search.date_range_days,
                'storage_path': self.config.storage_path,
                'log_level': self.config.log_level
            }
        }
    
    def process_existing_issues(self, limit: Optional[int] = None, 
                              force_reprocess: bool = False) -> Dict[str, Any]:
        """
        Scan for and process existing site-monitor labeled issues.
        
        Args:
            limit: Maximum number of issues to process (None for all)
            force_reprocess: Whether to reprocess already assigned issues
            
        Returns:
            Dictionary with processing results and statistics
        """
        if not self.issue_processor:
            return {
                'success': False,
                'error': 'Issue processor not available or not enabled',
                'processed_issues': []
            }
        
        try:
            logger.info("Scanning for existing site-monitor issues to process")
            
            # Get site-monitor labeled issues from GitHub
            unprocessed_issues = self.github_client.get_unprocessed_monitoring_issues(
                limit=limit,
                force_reprocess=force_reprocess
            )
            
            if not unprocessed_issues:
                logger.info("No unprocessed site-monitor issues found")
                return {
                    'success': True,
                    'processed_issues': [],
                    'message': 'No unprocessed issues found'
                }
            
            logger.info(f"Found {len(unprocessed_issues)} unprocessed issues")
            
            # Process each issue
            processing_results = []
            for issue in unprocessed_issues:
                try:
                    logger.info(f"Processing existing issue #{issue.number}")
                    
                    result = self.issue_processor.process_issue(issue.number)
                    processing_results.append({
                        'issue_number': issue.number,
                        'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
                        'workflow': result.workflow_name or 'none',
                        'deliverables': result.created_files or [],
                        'error': result.error_message
                    })
                    
                    # Brief delay between issues
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Failed to process existing issue #{issue.number}: {e}")
                    processing_results.append({
                        'issue_number': issue.number,
                        'status': 'error',
                        'workflow': 'none',
                        'deliverables': [],
                        'error': str(e)
                    })
            
            successful_processes = sum(1 for r in processing_results if r['status'] not in ['error', 'failed'])
            logger.info(f"Existing issue processing completed: {successful_processes}/{len(unprocessed_issues)} issues processed successfully")
            
            return {
                'success': True,
                'processed_issues': processing_results,
                'total_found': len(unprocessed_issues),
                'successful_processes': successful_processes
            }
            
        except Exception as e:
            logger.error(f"Failed to process existing issues: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_issues': []
            }


def create_monitor_service_from_config(config_path: str, github_token: str) -> SiteMonitorService:
    """
    Create a SiteMonitorService instance from configuration file
    
    Args:
        config_path: Path to YAML configuration file
        github_token: GitHub personal access token
        
    Returns:
        Configured SiteMonitorService instance
    """
    config = load_config_with_env_substitution(config_path)
    return SiteMonitorService(config, github_token)


def main():
    """Main entry point for the site monitoring service"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Site Monitor Service')
    parser.add_argument('command', choices=['monitor', 'setup', 'cleanup', 'status'], 
                       help='Command to execute')
    parser.add_argument('--config', default='config.yaml', 
                       help='Path to configuration file')
    parser.add_argument('--github-token', 
                       help='GitHub token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Dry run mode (for cleanup command)')
    parser.add_argument('--days-old', type=int, default=7,
                       help='Days old threshold for cleanup (default: 7)')
    parser.add_argument('--no-individual-issues', action='store_true',
                       help='Skip creating individual issues (monitor command)')
    
    args = parser.parse_args()
    
    # Get GitHub token
    github_token = args.github_token or os.getenv('GITHUB_TOKEN')
    if not github_token:
        logger.error("GitHub token required. Use --github-token or set GITHUB_TOKEN environment variable.")
        sys.exit(1)
    
    # Check if config file exists
    if not os.path.exists(args.config):
        logger.error(f"Configuration file not found: {args.config}")
        sys.exit(1)
    
    try:
        # Create service instance
        service = create_monitor_service_from_config(args.config, github_token)
        
        if args.command == 'monitor':
            # Run monitoring cycle
            results = service.run_monitoring_cycle(
                create_individual_issues=not args.no_individual_issues
            )
            
            if results['success']:
                print(f"✅ Monitoring completed successfully")
                print(f"📊 Found {results['new_results_found']} new results")
                print(f"📝 Created {results['individual_issues_created']} individual issues")
            else:
                print(f"❌ Monitoring failed: {results['error']}")
                sys.exit(1)
        
        elif args.command == 'setup':
            # Set up repository
            service.setup_repository()
            print("✅ Repository setup completed")
        
        elif args.command == 'cleanup':
            # Clean up old data
            results = service.cleanup_old_data(
                days_old=args.days_old,
                dry_run=args.dry_run
            )
            
            if results['success']:
                if args.dry_run:
                    print(f"🔍 Dry run: would remove {results['removed_dedup_entries']} entries and close {results['closed_issues']} issues")
                else:
                    print(f"🧹 Cleanup completed: removed {results['removed_dedup_entries']} entries and closed {results['closed_issues']} issues")
            else:
                print(f"❌ Cleanup failed: {results['error']}")
                sys.exit(1)
        
        elif args.command == 'status':
            # Show monitoring status
            status = service.get_monitoring_status()
            print(f"📊 Site Monitor Status")
            print(f"Repository: {status['repository']}")
            print(f"Sites configured: {status['sites_configured']}")
            print(f"Rate limit: {status['rate_limit_status']['calls_remaining']}/{status['rate_limit_status']['daily_limit']} calls remaining")
            print(f"Processed entries: {status['deduplication_stats']['total_entries']}")
    
    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()