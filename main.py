#!/usr/bin/env python3
"""
Speculum Principum - A Python app that runs operations via GitHub Actions
Main entry point for the application with site monitoring capabilities
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

from src.clients.github_issue_creator import GitHubIssueCreator
from src.core.batch_processor import BatchMetrics
from src.core.issue_processor import (
    GitHubIntegratedIssueProcessor, 
    IssueProcessingStatus, 
    ProcessingResult
)
from src.core.processing_orchestrator import ProcessingOrchestrator
from src.core.site_monitor import create_monitor_service_from_config
from src.agents.ai_workflow_assignment_agent import AIWorkflowAssignmentAgent
from src.utils.cli_helpers import (
    ConfigValidator, 
    ProgressReporter, 
    IssueResultFormatter,
    BatchProcessor, 
    safe_execute_cli_command, 
    CliResult
)
from src.utils.specialist_config_cli import (
    setup_specialist_config_parser,
    handle_specialist_config_command
)
from src.utils.logging_config import setup_logging


def setup_argument_parser() -> argparse.ArgumentParser:
    """
    Set up the command-line argument parser with all subcommands.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description='Speculum Principum - GitHub Operations & Site Monitoring',
        prog='speculum-principum'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Legacy issue creation command
    setup_create_issue_parser(subparsers)
    
    # Site monitoring commands
    setup_monitor_parser(subparsers)
    setup_setup_parser(subparsers)
    setup_status_parser(subparsers)
    setup_cleanup_parser(subparsers)
    
    # Issue processing commands
    setup_process_issues_parser(subparsers)
    setup_process_copilot_issues_parser(subparsers)
    setup_assign_workflows_parser(subparsers)
    
    # Specialist workflow configuration commands
    setup_specialist_config_parser(subparsers)
    
    return parser


def setup_create_issue_parser(subparsers) -> None:
    """Set up create-issue command parser."""
    issue_parser = subparsers.add_parser(
        'create-issue', 
        help='Create a GitHub issue'
    )
    issue_parser.add_argument('--title', required=True, help='Issue title')
    issue_parser.add_argument('--body', help='Issue body/description')
    issue_parser.add_argument('--labels', nargs='*', help='Issue labels')
    issue_parser.add_argument('--assignees', nargs='*', help='Issue assignees')


def setup_monitor_parser(subparsers) -> None:
    """Set up monitor command parser."""
    monitor_parser = subparsers.add_parser(
        'monitor', 
        help='Run site monitoring'
    )
    monitor_parser.add_argument(
        '--config', 
        default='config.yaml', 
        help='Configuration file path'
    )
    monitor_parser.add_argument(
        '--no-individual-issues', 
        action='store_true',
        help='Skip creating individual issues for each search result'
    )


def setup_setup_parser(subparsers) -> None:
    """Set up setup command parser."""
    setup_parser = subparsers.add_parser(
        'setup', 
        help='Set up repository for monitoring'
    )
    setup_parser.add_argument(
        '--config', 
        default='config.yaml', 
        help='Configuration file path'
    )


def setup_status_parser(subparsers) -> None:
    """Set up status command parser."""
    status_parser = subparsers.add_parser(
        'status', 
        help='Show monitoring status'
    )
    status_parser.add_argument(
        '--config', 
        default='config.yaml', 
        help='Configuration file path'
    )


def setup_cleanup_parser(subparsers) -> None:
    """Set up cleanup command parser."""
    cleanup_parser = subparsers.add_parser(
        'cleanup', 
        help='Clean up old monitoring data'
    )
    cleanup_parser.add_argument(
        '--config', 
        default='config.yaml', 
        help='Configuration file path'
    )
    cleanup_parser.add_argument(
        '--days-old', 
        type=int, 
        default=7, 
        help='Days old threshold'
    )
    cleanup_parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Dry run mode'
    )


def setup_process_issues_parser(subparsers) -> None:
    """Set up process-issues command parser."""
    process_parser = subparsers.add_parser(
        'process-issues', 
        help='Process issues with automated workflows'
    )
    process_parser.add_argument(
        '--config', 
        default='config.yaml', 
        help='Configuration file path'
    )
    process_parser.add_argument(
        '--issue', 
        type=int, 
        help='Process specific issue number'
    )
    process_parser.add_argument(
        '--batch-size', 
        type=int, 
        default=10, 
        help='Maximum issues to process in batch mode'
    )
    process_parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Show what would be processed without making changes'
    )
    process_parser.add_argument(
        '--force-clarification', 
        action='store_true', 
        help='Force clarification requests even for apparent matches'
    )
    process_parser.add_argument(
        '--assignee-filter', 
        help='Only process issues assigned to specific user'
    )
    process_parser.add_argument(
        '--label-filter', 
        nargs='*', 
        help='Additional labels to filter issues (beyond site-monitor)'
    )
    process_parser.add_argument(
        '--verbose', '-v', 
        action='store_true', 
        help='Show detailed progress information'
    )
    process_parser.add_argument(
        '--continue-on-error', 
        action='store_true', 
        help='Continue batch processing even if individual issues fail'
    )
    process_parser.add_argument(
        '--from-monitor', 
        action='store_true', 
        help='Use site monitor to find and process unprocessed issues'
    )
    process_parser.add_argument(
        '--find-issues-only', 
        action='store_true', 
        help='Find and output site-monitor issues without processing (for CI/CD)'
    )



def setup_process_copilot_issues_parser(subparsers) -> None:
    """Set up process-copilot-issues command parser."""
    copilot_parser = subparsers.add_parser(
        'process-copilot-issues', 
        help='Process issues assigned to GitHub Copilot for AI analysis'
    )
    copilot_parser.add_argument(
        '--config', 
        default='config.yaml', 
        help='Configuration file path'
    )
    copilot_parser.add_argument(
        '--specialist-filter', 
        choices=['intelligence-analyst', 'osint-researcher', 'target-profiler', 'business-analyst'],
        help='Filter by specialist type'
    )
    copilot_parser.add_argument(
        '--batch-size', 
        type=int, 
        default=5, 
        help='Maximum issues to process in batch mode'
    )
    copilot_parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Show what would be processed without making changes'
    )
    copilot_parser.add_argument(
        '--verbose', '-v', 
        action='store_true', 
        help='Show detailed progress information'
    )
    copilot_parser.add_argument(
        '--continue-on-error', 
        action='store_true', 
        help='Continue processing even if individual issues fail'
    )


def setup_assign_workflows_parser(subparsers) -> None:
    """Set up assign-workflows command parser."""
    assign_parser = subparsers.add_parser(
        'assign-workflows', 
        help='Assign workflows to unassigned site-monitor issues using AI analysis'
    )
    assign_parser.add_argument(
        '--config', 
        default='config.yaml', 
        help='Configuration file path'
    )
    assign_parser.add_argument(
        '--limit', 
        type=int, 
        default=20, 
        help='Maximum issues to process'
    )
    assign_parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Show what would be done without making changes'
    )
    assign_parser.add_argument(
        '--verbose', '-v', 
        action='store_true', 
        help='Show detailed progress information'
    )
    assign_parser.add_argument(
        '--statistics', 
        action='store_true', 
        help='Show workflow assignment statistics'
    )
    assign_parser.add_argument(
        '--disable-ai', 
        action='store_true', 
        help='Disable AI analysis and use label-based matching only (fallback mode)'
    )


def validate_environment() -> tuple[str, str]:
    """
    Validate required environment variables.
    
    Returns:
        Tuple of (github_token, repo_name)
        
    Raises:
        SystemExit: If required environment variables are missing
    """
    github_token = os.getenv('GITHUB_TOKEN')
    repo_name = os.getenv('GITHUB_REPOSITORY')
    
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)
        
    if not repo_name:
        print("Error: GITHUB_REPOSITORY environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    return github_token, repo_name


def handle_create_issue_command(args, github_token: str, repo_name: str) -> None:
    """Handle create-issue command."""
    creator = GitHubIssueCreator(github_token, repo_name)
    issue = creator.create_issue(
        title=args.title,
        body=args.body or "",
        labels=args.labels or [],
        assignees=args.assignees or []
    )
    print(f"Successfully created issue #{issue.number}: {issue.title}")
    print(f"URL: {issue.html_url}")


def handle_monitor_command(args, github_token: str) -> None:
    """Handle monitor command."""
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    
    service = create_monitor_service_from_config(args.config, github_token)
    results = service.run_monitoring_cycle(
        create_individual_issues=not args.no_individual_issues
    )
    
    if results['success']:
        print(f"✅ Monitoring completed successfully")
        print(f"📊 Found {results['new_results_found']} new results")
        print(f"📝 Created {results['individual_issues_created']} individual issues")
    else:
        print(f"❌ Monitoring failed: {results['error']}", file=sys.stderr)
        sys.exit(1)


def handle_setup_command(args, github_token: str) -> None:
    """Handle setup command."""
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    
    service = create_monitor_service_from_config(args.config, github_token)
    service.setup_repository()
    print("✅ Repository setup completed")


def handle_status_command(args, github_token: str) -> None:
    """Handle status command."""
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    
    service = create_monitor_service_from_config(args.config, github_token)
    status = service.get_monitoring_status()
    print(f"📊 Site Monitor Status")
    print(f"Repository: {status['repository']}")
    print(f"Sites configured: {status['sites_configured']}")
    rate_status = status['rate_limit_status']
    print(f"Rate limit: {rate_status['calls_remaining']}/{rate_status['daily_limit']} calls remaining")
    dedup_stats = status['deduplication_stats']
    print(f"Processed entries: {dedup_stats['total_entries']}")


def handle_cleanup_command(args, github_token: str) -> None:
    """Handle cleanup command."""
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    
    service = create_monitor_service_from_config(args.config, github_token)
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
        print(f"❌ Cleanup failed: {results['error']}", file=sys.stderr)
        sys.exit(1)


def handle_process_issues_command(args, github_token: str, repo_name: str) -> None:
    """Handle process-issues command."""
    
    def process_issues_command() -> CliResult:
        # Validate configuration and environment
        config_result = ConfigValidator.validate_config_file(args.config)
        if not config_result.success:
            return config_result
        
        env_result = ConfigValidator.validate_environment()
        if not env_result.success:
            return env_result
        
        # Initialize components
        reporter = ProgressReporter(args.verbose)
        
        try:
            # Create processor
            processor = GitHubIntegratedIssueProcessor(
                github_token=github_token,
                repository=repo_name,
                config_path=args.config
            )
            
            # Create orchestrator for batch operations
            orchestrator = ProcessingOrchestrator(processor)
            
            # Validate workflow directory from config
            config = processor.config
            workflow_dir = getattr(config, 'workflow_directory', 'docs/workflow/deliverables')
            
            workflow_result = ConfigValidator.validate_workflow_directory(workflow_dir)
            if not workflow_result.success:
                return workflow_result
            
            if args.verbose:
                reporter.show_info(f"Using workflow directory: {workflow_dir}")
                if workflow_result.data:
                    reporter.show_info(f"Found {workflow_result.data['workflow_count']} workflow(s)")
            
            
            # Handle find-issues-only mode (for CI/CD integration)
            if args.find_issues_only:
                reporter.start_operation("Finding site-monitor issues")
                
                try:
                    from src.core.batch_processor import BatchProcessor
                    
                    # Create a batch processor just for finding issues
                    batch_processor = BatchProcessor(processor, processor.github, config=None)
                    
                    # Build filters
                    filters = {}
                    if args.assignee_filter:
                        filters['assignee'] = args.assignee_filter
                    if args.label_filter:
                        filters['additional_labels'] = args.label_filter
                    
                    # Find issues
                    issue_numbers = batch_processor._find_site_monitor_issues(filters)
                    
                    if not issue_numbers:
                        reporter.complete_operation(True)
                        return CliResult(
                            success=True,
                            message="[]",  # Empty JSON array for no issues
                            data={'issues': [], 'count': 0}
                        )
                    
                    # Get detailed issue information
                    issues_data = []
                    for issue_number in issue_numbers[:args.batch_size]:
                        try:
                            issue_data = processor.github.get_issue_data(issue_number)
                            issues_data.append({
                                'number': issue_number,
                                'title': issue_data.get('title', ''),
                                'labels': issue_data.get('labels', [])
                            })
                        except Exception as e:
                            reporter.show_info(f"Warning: Could not get data for issue #{issue_number}: {e}")
                    
                    reporter.complete_operation(True)
                    
                    # Output JSON for CI/CD consumption
                    import json
                    issues_json = json.dumps(issues_data)
                    
                    return CliResult(
                        success=True,
                        message=issues_json,
                        data={'issues': issues_data, 'count': len(issues_data)}
                    )
                    
                except Exception as e:
                    reporter.complete_operation(False)
                    return CliResult(
                        success=False,
                        message=f"❌ Failed to find issues: {str(e)}",
                        error_code=1
                    )
            
            # Process issues (single or batch)
            if args.issue:
                # Single issue processing using batch processor for consistency
                reporter.start_operation(f"Processing issue #{args.issue}")
                
                # Check if issue has site-monitor label first
                if not args.dry_run:
                    try:
                        issue_data_dict = processor.github.get_issue_data(args.issue)
                        labels = issue_data_dict.get('labels', [])
                        
                        if 'site-monitor' not in labels:
                            reporter.complete_operation(False)
                            return CliResult(
                                success=False,
                                message=f"❌ Issue #{args.issue} does not have the 'site-monitor' label",
                                error_code=1
                            )
                    except Exception as e:
                        reporter.complete_operation(False)
                        return CliResult(
                            success=False,
                            message=f"❌ Could not retrieve issue #{args.issue}: {str(e)}",
                            error_code=1
                        )
                
                # Process using batch processor
                issue_numbers = [args.issue]
                batch_metrics, batch_results = orchestrator.process_batch(
                    issue_numbers=issue_numbers,
                    batch_size=1,
                    dry_run=args.dry_run
                )
                
                reporter.complete_operation(len(batch_results) > 0 and batch_results[0].status not in [IssueProcessingStatus.ERROR])
                
                # Format single result
                if batch_results:
                    result = batch_results[0]
                    formatted_result = IssueResultFormatter.format_single_result({
                        'status': result.status.value,
                        'issue': result.issue_number,
                        'workflow': result.workflow_name,
                        'files_created': result.created_files or [],
                        'error': result.error_message,
                        'clarification': result.clarification_needed
                    })
                    
                    return CliResult(
                        success=result.status not in [IssueProcessingStatus.ERROR],
                        message=formatted_result,
                        data={
                            'issue_number': result.issue_number,
                            'status': result.status.value,
                            'workflow_name': result.workflow_name,
                            'created_files': result.created_files,
                            'error_message': result.error_message
                        }
                    )
                else:
                    return CliResult(
                        success=False,
                        message=f"❌ No result returned for issue #{args.issue}",
                        error_code=1
                    )
            
            else:
                # Batch processing using the new BatchProcessor
                reporter.start_operation("Starting batch processing")
                
                try:
                    # Determine processing mode
                    if args.issue:
                        # Process specific issue using batch processor for consistency
                        issue_numbers = [args.issue]
                        batch_metrics, batch_results = orchestrator.process_batch(
                            issue_numbers=issue_numbers,
                            batch_size=1,
                            dry_run=args.dry_run
                        )
                    elif args.from_monitor:
                        # Use site monitor to find unprocessed issues
                        
                        reporter.show_info("🔍 Using site monitor to find unprocessed issues...")
                        
                        # Create site monitor service
                        monitor_service = create_monitor_service_from_config(args.config, github_token)
                        
                        # Process existing issues using site monitor integration
                        monitor_result = monitor_service.process_existing_issues(
                            limit=args.batch_size,
                            force_reprocess=False
                        )
                        
                        if monitor_result['success']:
                            # Convert monitor results to expected format
                            
                            batch_results = []
                            for result in monitor_result['processed_issues']:
                                status = IssueProcessingStatus.COMPLETED if result['status'] == 'completed' else IssueProcessingStatus.ERROR
                                batch_results.append(ProcessingResult(
                                    issue_number=result['issue_number'],
                                    status=status,
                                    workflow_name=result['workflow'],
                                    created_files=result['deliverables'],
                                    error_message=result['error']
                                ))
                            
                            # Create metrics
                            
                            total_found = monitor_result['total_found']
                            successful = monitor_result['successful_processes']
                            
                            batch_metrics = BatchMetrics(
                                total_issues=total_found,
                                processed_count=len(batch_results),
                                success_count=successful,
                                error_count=len(batch_results) - successful,
                                start_time=datetime.now(),
                                end_time=datetime.now()
                            )
                        else:
                            return CliResult(
                                success=False,
                                message=f"❌ Site monitor failed to find issues: {monitor_result['error']}",
                                error_code=1
                            )
                    else:
                        # Process all site-monitor issues using standard method
                        batch_metrics, batch_results = orchestrator.process_all_site_monitor_issues(
                            batch_size=args.batch_size,
                            dry_run=args.dry_run,
                            assignee_filter=args.assignee_filter,
                            additional_labels=args.label_filter
                        )
                    
                    reporter.complete_operation(True, f"Batch processing complete")
                    
                    # Format batch results
                    if args.verbose:
                        reporter.show_info(
                            f"Processed {batch_metrics.processed_count}/{batch_metrics.total_issues} issues"
                        )
                        reporter.show_info(f"Success rate: {batch_metrics.success_rate:.1f}%")
                        reporter.show_info(f"Duration: {batch_metrics.duration_seconds:.1f}s")
                    
                    # Convert results for formatting
                    results = []
                    for result in batch_results:
                        results.append({
                            'status': result.status.value,
                            'issue': result.issue_number,
                            'workflow': result.workflow_name,
                            'files_created': result.created_files or [],
                            'error': result.error_message,
                            'clarification': result.clarification_needed
                        })
                    
                    # Format batch results
                    formatted_results = IssueResultFormatter.format_batch_results(results)
                    
                    # Check for errors
                    error_count = batch_metrics.error_count
                    success = error_count == 0 or args.continue_on_error
                    
                    return CliResult(
                        success=success,
                        message=formatted_results,
                        data={
                            'results': results, 
                            'error_count': error_count,
                            'metrics': batch_metrics
                        }
                    )
                    
                except Exception as e:
                    return CliResult(
                        success=False,
                        message=f"Failed to retrieve issues: {str(e)}",
                        error_code=1
                    )
        
        except Exception as e:
            return CliResult(
                success=False,
                message=f"Issue processing failed: {str(e)}",
                error_code=1
            )
    
    # Execute the command safely
    exit_code = safe_execute_cli_command(process_issues_command)
    if exit_code != 0:
        sys.exit(exit_code)


def handle_process_copilot_issues_command(args, github_token: str, repo_name: str) -> None:
    """Handle process-copilot-issues command."""
    
    def process_copilot_issues_command() -> CliResult:
        # Validate configuration and environment
        config_result = ConfigValidator.validate_config_file(args.config)
        if not config_result.success:
            return config_result
        
        env_result = ConfigValidator.validate_environment()
        if not env_result.success:
            return env_result
        
        # Initialize components
        reporter = ProgressReporter(args.verbose)
        
        try:
            # Create processor
            processor = GitHubIntegratedIssueProcessor(
                github_token=github_token,
                repository=repo_name,
                config_path=args.config
            )
            
            # Create batch processor
            from src.core.batch_processor import BatchProcessor
            batch_processor = BatchProcessor(processor, processor.github, config=None)
            
            # Validate workflow directory from config
            config = processor.config
            workflow_dir = getattr(config, 'workflow_directory', 'docs/workflow/deliverables')
            
            workflow_result = ConfigValidator.validate_workflow_directory(workflow_dir)
            if not workflow_result.success:
                return workflow_result
            
            if args.verbose:
                reporter.show_info(f"Using workflow directory: {workflow_dir}")
                if workflow_result.data:
                    reporter.show_info(f"Found {workflow_result.data['workflow_count']} workflow(s)")
            
            # Find Copilot-assigned issues
            reporter.start_operation("Finding Copilot-assigned issues")
            
            try:
                copilot_issues = processor.get_copilot_assigned_issues()
                
                if not copilot_issues:
                    reporter.complete_operation(True)
                    return CliResult(
                        success=True,
                        message="✅ No Copilot-assigned issues found for processing",
                        data={'issues': [], 'count': 0}
                    )
                
                # Apply specialist filter if provided
                if args.specialist_filter:
                    original_count = len(copilot_issues)
                    copilot_issues = [
                        issue for issue in copilot_issues
                        if args.specialist_filter in issue.get('labels', [])
                        or any(args.specialist_filter.replace('-', '_') in label.replace('-', '_')
                               for label in issue.get('labels', []))
                    ]
                    
                    if args.verbose:
                        reporter.show_info(f"Filtered from {original_count} to {len(copilot_issues)} issues for specialist: {args.specialist_filter}")
                
                if not copilot_issues:
                    filter_msg = f" for specialist '{args.specialist_filter}'" if args.specialist_filter else ""
                    reporter.complete_operation(True)
                    return CliResult(
                        success=True,
                        message=f"✅ No Copilot-assigned issues found{filter_msg}",
                        data={'issues': [], 'count': 0}
                    )
                
                # Limit issues processed
                limited_issues = copilot_issues[:args.batch_size]
                
                if args.verbose:
                    reporter.show_info(f"Processing {len(limited_issues)} Copilot-assigned issues")
                    for issue in limited_issues:
                        reporter.show_info(f"  - Issue #{issue['number']}: {issue['title']}")
                
                reporter.complete_operation(True)
                
                # Process issues using batch processor
                if args.dry_run:
                    reporter.start_operation("Dry run - showing what would be processed")
                else:
                    reporter.start_operation(f"Processing {len(limited_issues)} Copilot-assigned issues")
                
                batch_metrics, batch_results = batch_processor.process_copilot_assigned_issues(
                    specialist_filter=args.specialist_filter,
                    dry_run=args.dry_run
                )
                
                reporter.complete_operation(batch_metrics.error_count == 0)
                
                # Format results
                results = [
                    {
                        'status': result.status.value,
                        'issue': result.issue_number,
                        'workflow': result.workflow_name,
                        'files_created': result.created_files or [],
                        'error': result.error_message,
                        'clarification': result.clarification_needed
                    }
                    for result in batch_results
                ]
                
                # Format batch results
                formatted_results = IssueResultFormatter.format_batch_results(results)
                
                # Check for errors
                error_count = batch_metrics.error_count
                success = error_count == 0 or args.continue_on_error
                
                return CliResult(
                    success=success,
                    message=formatted_results,
                    data={
                        'results': results,
                        'error_count': error_count,
                        'metrics': batch_metrics,
                        'specialist_filter': args.specialist_filter
                    }
                )
                
            except Exception as e:
                reporter.complete_operation(False)
                return CliResult(
                    success=False,
                    message=f"❌ Failed to process Copilot-assigned issues: {str(e)}",
                    error_code=1
                )
        
        except Exception as e:
            return CliResult(
                success=False,
                message=f"Copilot issue processing failed: {str(e)}",
                error_code=1
            )
    
    # Execute the command safely
    exit_code = safe_execute_cli_command(process_copilot_issues_command)
    if exit_code != 0:
        sys.exit(exit_code)


def handle_assign_workflows_command(args, github_token: str, repo_name: str) -> None:
    """Handle assign-workflows command."""
    
    def assign_workflows_command() -> CliResult:
        # Validate configuration and environment
        config_result = ConfigValidator.validate_config_file(args.config)
        if not config_result.success:
            return config_result
        
        try:
            # Determine whether to disable AI based on arguments and configuration
            disable_ai = args.disable_ai
            
            # Load AI configuration from file
            ai_enabled = True  # Default to enabled
            try:
                from src.utils.config_manager import ConfigManager
                config = ConfigManager.load_config(args.config)
                ai_config = getattr(config, 'ai', None)
                if ai_config and not ai_config.enabled:
                    ai_enabled = False
                if disable_ai:
                    ai_enabled = False
            except Exception:
                ai_enabled = True  # Default to enabled if config fails
            
            # Initialize the AI workflow assignment agent
            agent = AIWorkflowAssignmentAgent(
                github_token=github_token,
                repo_name=repo_name,
                config_path=args.config,
                enable_ai=ai_enabled
            )
            
            agent_type = "AI-enhanced" if ai_enabled else "Label-based (fallback)"
            
            reporter = ProgressReporter(verbose=args.verbose)
            
            if args.statistics:
                # Show statistics instead of processing
                reporter.start_operation("Fetching assignment statistics")
                stats = agent.get_assignment_statistics()
                
                if 'error' in stats:
                    return CliResult(
                        success=False,
                        message=f"❌ Failed to get statistics: {stats['error']}",
                        error_code=1
                    )
                
                # Format statistics output
                stats_lines = [
                    f"📊 **Workflow Assignment Statistics**",
                    f"🤖 **Agent Type:** {agent_type}",
                    f"",
                    f"**Issues Overview:**",
                    f"  Total site-monitor issues: {stats['total_site_monitor_issues']}",
                    f"  Unassigned issues: {stats['unassigned']}",
                    f"  Assigned issues: {stats['assigned']}",
                    f"  Need clarification: {stats['needs_clarification']}",
                ]
                
                if stats.get('needs_review', 0) > 0:
                    stats_lines.append(f"  Need review: {stats['needs_review']}")
                
                stats_lines.extend([
                    f"  Feature labeled: {stats['feature_labeled']}",
                    f""
                ])
                
                if stats['workflow_breakdown']:
                    stats_lines.extend([
                        f"**Workflow Breakdown:**"
                    ])
                    for workflow, count in sorted(stats['workflow_breakdown'].items()):
                        stats_lines.append(f"  {workflow}: {count}")
                    stats_lines.append("")
                
                if stats['label_distribution']:
                    stats_lines.extend([
                        f"**Label Distribution (Top 10):**"
                    ])
                    sorted_labels = sorted(stats['label_distribution'].items(), key=lambda x: x[1], reverse=True)
                    for label, count in sorted_labels[:10]:
                        stats_lines.append(f"  {label}: {count}")
                
                return CliResult(
                    success=True,
                    message="\n".join(stats_lines),
                    data=stats
                )
            
            else:
                # Process issues for workflow assignment
                reporter.start_operation(f"Processing workflow assignments (limit: {args.limit}, dry_run: {args.dry_run})")
                
                result = agent.process_issues_batch(
                    limit=args.limit,
                    dry_run=args.dry_run
                )
                
                if 'error' in result:
                    return CliResult(
                        success=False,
                        message=f"❌ Processing failed: {result['error']}",
                        error_code=1
                    )
                
                # Format results
                total = result['total_issues']
                processed = result['processed']
                duration = result['duration_seconds']
                stats = result['statistics']
                
                result_lines = [
                    f"✅ **Workflow Assignment Complete**",
                    f"🤖 **Agent Type:** {agent_type}",
                    f"",
                    f"**Summary:**",
                    f"  Processed: {processed}/{total} issues in {duration:.1f}s",
                    f""
                ]
                
                # Add statistics breakdown
                if stats:
                    result_lines.extend([
                        f"**Actions Taken:**"
                    ])
                    for action, count in stats.items():
                        if count > 0:
                            action_name = action.replace('_', ' ').title()
                            result_lines.append(f"  {action_name}: {count}")
                
                # Add details if verbose
                if args.verbose and result['results']:
                    result_lines.extend([
                        f"",
                        f"**Issue Details:**"
                    ])
                    for issue_result in result['results']:
                        # All results are now from AI agent (dictionary format)
                        action = issue_result.get('action_taken', 'unknown').replace('_', ' ').title()
                        result_lines.append(f"  Issue #{issue_result['issue_number']}: {action}")
                        if issue_result.get('assigned_workflow'):
                            result_lines.append(f"    Workflow: {issue_result['assigned_workflow']}")
                        if issue_result.get('labels_added'):
                            result_lines.append(f"    Labels added: {', '.join(issue_result['labels_added'])}")
                        if issue_result.get('message'):
                            result_lines.append(f"    Note: {issue_result['message']}")
                        # Add AI-specific information
                        if ai_enabled and 'ai_analysis' in issue_result:
                            ai_analysis = issue_result['ai_analysis']
                            if ai_analysis.get('summary'):
                                result_lines.append(f"    AI Summary: {ai_analysis['summary']}")
                            if ai_analysis.get('content_type'):
                                result_lines.append(f"    Content Type: {ai_analysis['content_type']}")
                            if ai_analysis.get('urgency_level'):
                                result_lines.append(f"    Urgency: {ai_analysis['urgency_level']}")
                
                if args.dry_run:
                    result_lines.insert(2, f"🧪 **DRY RUN** - No changes were made")
                
                success = processed > 0 or total == 0
                return CliResult(
                    success=success,
                    message="\n".join(result_lines),
                    data=result
                )
                
        except Exception as e:
            return CliResult(
                success=False,
                message=f"Workflow assignment failed: {str(e)}",
                error_code=1
            )
    
    # Execute the command safely
    exit_code = safe_execute_cli_command(assign_workflows_command)
    if exit_code != 0:
        sys.exit(exit_code)


def main():
    """Main entry point for the application."""
    load_dotenv()
    
    # Set up argument parser
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # If no command specified, show help
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Set up logging configuration
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', None)
    enable_console = not os.getenv('GITHUB_ACTIONS', '').lower() == 'true'  # Disable console in GitHub Actions
    
    try:
        setup_logging(
            log_level=log_level,
            log_file=log_file,
            enable_console=enable_console
        )
    except Exception as e:
        print(f"Warning: Failed to set up logging: {e}", file=sys.stderr)
        # Continue without proper logging rather than failing
    
    # Validate environment
    github_token, repo_name = validate_environment()
    
    try:
        # Route to appropriate command handler
        if args.command == 'create-issue':
            handle_create_issue_command(args, github_token, repo_name)
        elif args.command == 'monitor':
            handle_monitor_command(args, github_token)
        elif args.command == 'setup':
            handle_setup_command(args, github_token)
        elif args.command == 'status':
            handle_status_command(args, github_token)
        elif args.command == 'cleanup':
            handle_cleanup_command(args, github_token)
        elif args.command == 'process-issues':
            handle_process_issues_command(args, github_token, repo_name)
        elif args.command == 'process-copilot-issues':
            handle_process_copilot_issues_command(args, github_token, repo_name)
        elif args.command == 'assign-workflows':
            handle_assign_workflows_command(args, github_token, repo_name)
        elif args.command == 'specialist-config':
            exit_code = handle_specialist_config_command(args)
            sys.exit(exit_code)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            parser.print_help()
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()