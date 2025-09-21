#!/usr/bin/env python3
"""
Speculum Principum - A Python app that runs operations via GitHub Actions
Main entry point for the application with site monitoring capabilities
"""

import os
import sys
import argparse
from dotenv import load_dotenv

from src.github_operations import GitHubIssueCreator
from src.site_monitor import create_monitor_service_from_config


def main():
    """Main entry point for the application"""
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Speculum Principum - GitHub Operations & Site Monitoring')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Legacy issue creation command
    issue_parser = subparsers.add_parser('create-issue', help='Create a GitHub issue')
    issue_parser.add_argument('--title', required=True, help='Issue title')
    issue_parser.add_argument('--body', help='Issue body/description')
    issue_parser.add_argument('--labels', nargs='*', help='Issue labels')
    issue_parser.add_argument('--assignees', nargs='*', help='Issue assignees')
    
    # Site monitoring commands
    monitor_parser = subparsers.add_parser('monitor', help='Run site monitoring')
    monitor_parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    monitor_parser.add_argument('--no-individual-issues', action='store_true',
                               help='Skip creating individual issues for each search result')
    
    setup_parser = subparsers.add_parser('setup', help='Set up repository for monitoring')
    setup_parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    
    status_parser = subparsers.add_parser('status', help='Show monitoring status')
    status_parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old monitoring data')
    cleanup_parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    cleanup_parser.add_argument('--days-old', type=int, default=7, help='Days old threshold')
    cleanup_parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    
    args = parser.parse_args()
    
    # If no command specified, show help
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Get required environment variables
    github_token = os.getenv('GITHUB_TOKEN')
    repo_name = os.getenv('GITHUB_REPOSITORY')
    
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)
        
    if not repo_name and args.command != 'create-issue':
        print("Error: GITHUB_REPOSITORY environment variable is required for monitoring commands", file=sys.stderr)
        sys.exit(1)
    
    try:
        if args.command == 'create-issue':
            # Legacy issue creation
            if not repo_name:
                print("Error: GITHUB_REPOSITORY environment variable is required", file=sys.stderr)
                sys.exit(1)
                
            creator = GitHubIssueCreator(github_token, repo_name)
            issue = creator.create_issue(
                title=args.title,
                body=args.body or "",
                labels=args.labels or [],
                assignees=args.assignees or []
            )
            print(f"Successfully created issue #{issue.number}: {issue.title}")
            print(f"URL: {issue.html_url}")
        
        elif args.command == 'monitor':
            # Site monitoring
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
        
        elif args.command == 'setup':
            # Repository setup
            if not os.path.exists(args.config):
                print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
                sys.exit(1)
            
            service = create_monitor_service_from_config(args.config, github_token)
            service.setup_repository()
            print("✅ Repository setup completed")
        
        elif args.command == 'status':
            # Show status
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
        
        elif args.command == 'cleanup':
            # Cleanup old data
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
    
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()