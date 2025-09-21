"""
Enhanced GitHub Operations for Site Monitoring
Extends the existing GitHub operations with monitoring-specific functionality
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from github import Github
from github.GithubException import GithubException

from .github_operations import GitHubIssueCreator
from .search_client import SearchResult
from .deduplication import ProcessedEntry


logger = logging.getLogger(__name__)


class SiteMonitorIssueCreator(GitHubIssueCreator):
    """Extended GitHub issue creator for site monitoring"""
    
    def create_site_update_issue(self, site_name: str, results: List[SearchResult], 
                               labels: Optional[List[str]] = None) -> Any:
        """
        Create a GitHub issue for site updates
        
        Args:
            site_name: Name of the monitored site
            results: List of SearchResult objects found
            labels: Additional labels to apply
            
        Returns:
            Created GitHub issue object
        """
        if not results:
            raise ValueError("Cannot create issue with no results")
        
        # Build issue title
        if len(results) == 1:
            title = f"📄 New update found on {site_name}: {results[0].title[:80]}..."
        else:
            title = f"📄 {len(results)} new updates found on {site_name}"
        
        # Build issue body
        body = self._build_issue_body(site_name, results)
        
        # Combine default and custom labels
        default_labels = ['site-monitor', 'automated', 'documentation']
        all_labels = list(set(default_labels + (labels or [])))
        
        # Create the issue
        issue = self.create_issue(
            title=title,
            body=body,
            labels=all_labels
        )
        
        logger.info(f"Created site monitoring issue #{issue.number} for {site_name}")
        return issue
    
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
    
    def create_daily_summary_issue(self, all_results: Dict[str, List[SearchResult]], 
                                 search_summary: Dict[str, Any],
                                 labels: Optional[List[str]] = None) -> Any:
        """
        Create a daily summary issue with all site monitoring results
        
        Args:
            all_results: Dictionary mapping site names to search results
            search_summary: Summary statistics from search operations
            labels: Additional labels to apply
            
        Returns:
            Created GitHub issue object
        """
        today = datetime.utcnow().strftime('%Y-%m-%d')
        total_results = sum(len(results) for results in all_results.values())
        
        # Build title
        if total_results == 0:
            title = f"📊 Daily Site Monitor Summary - {today} (No updates found)"
        else:
            title = f"📊 Daily Site Monitor Summary - {today} ({total_results} updates found)"
        
        # Build body
        body = self._build_daily_summary_body(all_results, search_summary, today)
        
        # Labels
        default_labels = ['site-monitor', 'daily-summary', 'automated']
        all_labels = list(set(default_labels + (labels or [])))
        
        # Create the issue
        issue = self.create_issue(
            title=title,
            body=body,
            labels=all_labels
        )
        
        logger.info(f"Created daily summary issue #{issue.number}")
        return issue
    
    def _build_issue_body(self, site_name: str, results: List[SearchResult]) -> str:
        """Build the body content for a site update issue"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        
        body = f"""# New Updates Found on {site_name}

🔍 **Monitoring Results** | 📅 **Date**: {timestamp}

Found {len(results)} new update(s) on **{site_name}**:

"""
        
        for i, result in enumerate(results, 1):
            # Truncate long titles and snippets
            title = result.title if len(result.title) <= 100 else result.title[:97] + "..."
            snippet = result.snippet if len(result.snippet) <= 200 else result.snippet[:197] + "..."
            
            body += f"""## {i}. {title}

**🔗 URL**: {result.link}

**📝 Snippet**: {snippet}

---

"""
        
        body += f"""
## 🤖 Automation Details

- **Monitor**: Site Update Detection
- **Search Engine**: Google Custom Search API
- **Detection Time**: {timestamp}
- **Total Results**: {len(results)}

<details>
<summary>📋 Click to view technical details</summary>

### Search Metadata
- **Site Name**: {site_name}
- **Results Found**: {len(results)}
- **Search Timestamp**: {timestamp}

### Individual Results
"""
        
        for i, result in enumerate(results, 1):
            body += f"""
**Result {i}:**
- Title: `{result.title}`
- URL: `{result.link}`
- Display Link: `{result.display_link or 'N/A'}`
- Cache ID: `{result.cache_id or 'N/A'}`
"""
        
        body += """
</details>

---
*This issue was automatically created by the Site Monitor service.*
"""
        
        return body
    
    def _build_individual_result_body(self, site_name: str, result: SearchResult) -> str:
        """Build the body content for an individual search result issue"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        
        # Truncate long snippet for summary section
        snippet_preview = result.snippet if len(result.snippet) <= 200 else result.snippet[:197] + "..."
        
        body = f"""# New Update Found on {site_name}

🔍 **Search Result** | 📅 **Date**: {timestamp}

## 📄 {result.title}

**🔗 URL**: {result.link}

**📝 Snippet**: {snippet_preview}

---

## 🤖 Automation Details

- **Monitor**: Site Update Detection
- **Search Engine**: Google Custom Search API
- **Detection Time**: {timestamp}
- **Site Name**: {site_name}

<details>
<summary>📋 Click to view technical details</summary>

### Search Result Metadata
- **Title**: `{result.title}`
- **URL**: `{result.link}`
- **Display Link**: `{result.display_link or 'N/A'}`
- **Cache ID**: `{result.cache_id or 'N/A'}`
- **Discovered At**: {result.discovered_at.strftime('%Y-%m-%d %H:%M UTC')}

### Full Snippet
```
{result.snippet}
```

</details>

---
*This issue was automatically created by the Site Monitor service for a single search result.*
"""
        
        return body

    def _build_daily_summary_body(self, all_results: Dict[str, List[SearchResult]], 
                                search_summary: Dict[str, Any], date: str) -> str:
        """Build the body content for a daily summary issue"""
        
        body = f"""# Daily Site Monitoring Summary - {date}

🔍 **Monitoring Overview** | 📊 **Summary Statistics**

"""
        
        # Add summary statistics
        total_results = search_summary.get('total_results', 0)
        sites_searched = search_summary.get('sites_searched', 0)
        sites_with_results = search_summary.get('sites_with_results', 0)
        
        body += f"""## 📈 Summary Statistics

| Metric | Value |
|--------|-------|
| **Sites Monitored** | {sites_searched} |
| **Sites with Updates** | {sites_with_results} |
| **Total Updates Found** | {total_results} |
| **Success Rate** | {(sites_with_results/sites_searched*100):.1f}% |

"""
        
        # Add per-site breakdown
        if total_results > 0:
            body += """## 🏠 Per-Site Breakdown

"""
            for site_name, results in all_results.items():
                if results:
                    body += f"""### {site_name} ({len(results)} updates)

"""
                    for i, result in enumerate(results[:3], 1):  # Show max 3 results per site
                        title = result.title if len(result.title) <= 80 else result.title[:77] + "..."
                        body += f"**{i}.** [{title}]({result.link})\n"
                    
                    if len(results) > 3:
                        body += f"*... and {len(results) - 3} more updates*\n"
                    
                    body += "\n"
                else:
                    body += f"### {site_name}\n🔍 No updates found\n\n"
        else:
            body += """## 🔍 No Updates Found

No new updates were detected on any monitored sites today.

"""
        
        # Add trending keywords if available
        top_keywords = search_summary.get('top_keywords', [])
        if top_keywords:
            body += """## 🏷️ Trending Keywords

"""
            for keyword_data in top_keywords[:10]:
                word = keyword_data['word']
                count = keyword_data['count']
                body += f"- **{word}** ({count} mentions)\n"
            body += "\n"
        
        # Add technical details
        body += f"""## 🤖 Technical Details

<details>
<summary>📋 Click to view monitoring details</summary>

### Search Configuration
- **Date Range**: Last {search_summary.get('date_range_days', 1)} day(s)
- **API Calls Made**: {search_summary.get('api_calls_made', 'N/A')}
- **Search Timestamp**: {search_summary.get('search_timestamp', 'N/A')}

### Site Summary
"""
        
        sites_summary = search_summary.get('sites_summary', {})
        for site_name, site_info in sites_summary.items():
            result_count = site_info.get('result_count', 0)
            body += f"- **{site_name}**: {result_count} results\n"
        
        body += """
</details>

---
*This summary was automatically generated by the Site Monitor service.*
"""
        
        return body
    
    def update_issue_with_processing_results(self, issue_number: int, 
                                           processed_entries: List[ProcessedEntry]) -> None:
        """
        Update an existing issue with processing results
        
        Args:
            issue_number: GitHub issue number to update
            processed_entries: List of ProcessedEntry objects that were processed
        """
        try:
            issue = self.repo.get_issue(issue_number)
            
            # Build comment with processing results
            comment_body = f"""## 🔄 Processing Complete

This issue has been processed and the following entries have been recorded:

"""
            
            for entry in processed_entries:
                status = "✅ Tracked" if entry.issue_number else "📝 Recorded"
                comment_body += f"- {status} [{entry.title[:60]}...]({entry.url})\n"
            
            comment_body += f"""
**Processing Summary:**
- **Total Entries**: {len(processed_entries)}
- **Processed At**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

---
*This comment was automatically added by the Site Monitor service.*
"""
            
            # Add comment to issue
            issue.create_comment(comment_body)
            
            logger.info(f"Updated issue #{issue_number} with processing results")
            
        except GithubException as e:
            logger.error(f"Failed to update issue #{issue_number}: {e}")
            raise
    
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


def format_search_results_as_markdown(results: List[SearchResult], 
                                    site_name: Optional[str] = None) -> str:
    """
    Format search results as markdown for use in issues or comments
    
    Args:
        results: List of SearchResult objects
        site_name: Optional site name to include in formatting
        
    Returns:
        Formatted markdown string
    """
    if not results:
        return "*No results found.*"
    
    header = f"## Search Results"
    if site_name:
        header += f" for {site_name}"
    header += f" ({len(results)} found)\n\n"
    
    markdown = header
    
    for i, result in enumerate(results, 1):
        title = result.title if len(result.title) <= 100 else result.title[:97] + "..."
        snippet = result.snippet if len(result.snippet) <= 150 else result.snippet[:147] + "..."
        
        markdown += f"""### {i}. {title}

**🔗 Link**: [{result.display_link}]({result.link})

**📝 Snippet**: {snippet}

---

"""
    
    return markdown


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