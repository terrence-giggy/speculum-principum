#!/usr/bin/env python3
"""
Speculum Principum - A Python app that runs operations via GitHub Actions
Main entry point for the application
"""

import os
import sys
import argparse
from dotenv import load_dotenv

from src.github_operations import GitHubIssueCreator


def main():
    """Main entry point for the application"""
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Speculum Principum - GitHub Operations via Actions')
    parser.add_argument('operation', choices=['create-issue'], help='Operation to perform')
    parser.add_argument('--title', required=True, help='Issue title')
    parser.add_argument('--body', help='Issue body/description')
    parser.add_argument('--labels', nargs='*', help='Issue labels')
    parser.add_argument('--assignees', nargs='*', help='Issue assignees')
    
    args = parser.parse_args()
    
    # Get required environment variables
    github_token = os.getenv('GITHUB_TOKEN')
    repo_name = os.getenv('GITHUB_REPOSITORY')
    
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)
        
    if not repo_name:
        print("Error: GITHUB_REPOSITORY environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    try:
        if args.operation == 'create-issue':
            creator = GitHubIssueCreator(github_token, repo_name)
            issue = creator.create_issue(
                title=args.title,
                body=args.body or "",
                labels=args.labels or [],
                assignees=args.assignees or []
            )
            print(f"Successfully created issue #{issue.number}: {issue.title}")
            print(f"URL: {issue.html_url}")
    
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()