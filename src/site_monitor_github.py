"""
Enhanced GitHub Operations for Site Monitoring
Extends the existing GitHub operations with monitoring-specific functionality
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from github import Github
from github.GithubException import GithubException

from .github_issue_creator import GitHubIssueCreator
from .search_client import SearchResult
from .deduplication import ProcessedEntry


logger = logging.getLogger(__name__)


class SiteMonitorIssueCreator(GitHubIssueCreator):
    """Extended GitHub issue creator for site monitoring"""
    

    
    def create_individual_result_issue(self, site_name: str, result: SearchResult, 
                                      labels: Optional[List[str]] = None) -> Any:
        """
        Create a GitHub issue for a single search result
        
        Args:
            site_name: Name of the monitored site
            result: Single SearchResult object
            labels: Additional labels to apply
            
        Returns:
            Created GitHub issue object
        """
        # Build issue title - limit to reasonable length
        title_content = result.title[:100] if len(result.title) <= 100 else result.title[:97] + "..."
        title = f"📄 {site_name}: {title_content}"
        
        # Build issue body
        body = self._build_individual_result_body(site_name, result)
        
        # Combine default and custom labels
        default_labels = ['site-monitor', 'automated', 'documentation']
        all_labels = list(set(default_labels + (labels or [])))
        
        # Create the issue
        issue = self.create_issue(
            title=title,
            body=body,
            labels=all_labels
        )
        
        logger.info(f"Created individual result issue #{issue.number} for {site_name}")
        return issue
    
    

    
    def _build_individual_result_body(self, site_name: str, result: SearchResult) -> str:
        """Build the body content for an individual search result issue"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        
        body = f"""# New Update Found on {site_name}

🔍 **Search Result** | 📅 **Date**: {timestamp}

## 📄 {result.title}

**🔗 URL**: {result.link}

**📝 Snippet**: {result.snippet}

---
*This issue was automatically created by the Site Monitor service for a single search result.*
"""
        
        return body


    

    
    def close_old_monitoring_issues(self, days_old: int = 7, 
                                  dry_run: bool = True) -> List[int]:
        """
        Close old site monitoring issues
        
        Args:
            days_old: Close issues older than this many days
            dry_run: If True, only return issue numbers that would be closed
            
        Returns:
            List of issue numbers that were (or would be) closed
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        closed_issues = []
        
        try:
            # Search for open site monitoring issues
            query = 'is:issue is:open label:site-monitor'
            issues = self.repo.get_issues(state='open', labels=['site-monitor'])
            
            for issue in issues:
                # Skip if issue is newer than cutoff
                if issue.created_at.replace(tzinfo=None) > cutoff_date:
                    continue
                
                if not dry_run:
                    # Add closing comment
                    close_comment = f"""## 🔒 Auto-closing Issue

This site monitoring issue is being automatically closed as it's older than {days_old} days.

**Closed at**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---
*This issue was automatically closed by the Site Monitor service.*
"""
                    issue.create_comment(close_comment)
                    issue.edit(state='closed')
                    
                    logger.info(f"Closed old monitoring issue #{issue.number}")
                
                closed_issues.append(issue.number)
            
            if dry_run and closed_issues:
                logger.info(f"Dry run: would close {len(closed_issues)} old issues")
            elif closed_issues:
                logger.info(f"Closed {len(closed_issues)} old monitoring issues")
            
            return closed_issues
            
        except GithubException as e:
            logger.error(f"Failed to close old monitoring issues: {e}")
            raise



def create_site_monitoring_labels(github_client: GitHubIssueCreator, 
                                 labels_config: Optional[List[Dict[str, str]]] = None) -> List[str]:
    """
    Create labels for site monitoring if they don't exist
    
    Args:
        github_client: GitHubIssueCreator instance
        labels_config: List of label configurations with 'name', 'color', 'description'
        
    Returns:
        List of created label names
    """
    if labels_config is None:
        labels_config = [
            {
                'name': 'site-monitor',
                'color': '0E8A16',  # Green
                'description': 'Automated site monitoring results'
            },
            {
                'name': 'daily-summary',
                'color': '1D76DB',  # Blue
                'description': 'Daily monitoring summary'
            },
            {
                'name': 'automated',
                'color': '5319E7',  # Purple
                'description': 'Automatically generated content'
            },
            {
                'name': 'documentation',
                'color': 'FEF2C0',  # Light yellow
                'description': 'Documentation related updates'
            }
        ]
    
    created_labels = []
    
    try:
        # Get existing labels
        existing_labels = {label.name for label in github_client.repo.get_labels()}
        
        for label_config in labels_config:
            label_name = label_config['name']
            
            if label_name not in existing_labels:
                github_client.repo.create_label(
                    name=label_name,
                    color=label_config['color'],
                    description=label_config.get('description', '')
                )
                created_labels.append(label_name)
                logger.info(f"Created label: {label_name}")
            else:
                logger.debug(f"Label already exists: {label_name}")
        
        return created_labels
        
    except GithubException as e:
        logger.error(f"Failed to create labels: {e}")
        raise