"""
Google Custom Search Client
Handles search operations with date filtering, rate limiting, and result parsing
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from urllib.parse import urlparse, urljoin
import time
import re

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import GoogleAuthError

from .config_manager import SiteConfig, SearchConfig


logger = logging.getLogger(__name__)


class SearchResult:
    """Represents a single search result"""
    
    def __init__(self, title: str, link: str, snippet: str, display_link: str = None, 
                 formatted_url: str = None, cache_id: str = None):
        self.title = title
        self.link = link
        self.snippet = snippet
        self.display_link = display_link or link
        self.formatted_url = formatted_url or link
        self.cache_id = cache_id
        self.discovered_at = datetime.utcnow()
    
    def __str__(self):
        return f"SearchResult(title='{self.title[:50]}...', link='{self.link}')"
    
    def __repr__(self):
        return self.__str__()
    



class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, daily_limit: int):
        self.daily_limit = daily_limit
        self.calls_today = 0
        self.last_reset = datetime.utcnow().date()
        self.last_call_time = 0
        self.min_interval = 1.0  # Minimum seconds between calls
    
    def can_make_request(self) -> bool:
        """Check if we can make another request"""
        today = datetime.utcnow().date()
        
        # Reset counter if it's a new day
        if today > self.last_reset:
            self.calls_today = 0
            self.last_reset = today
        
        return self.calls_today < self.daily_limit
    
    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_interval:
            wait_time = self.min_interval - time_since_last_call
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
    
    def record_request(self) -> None:
        """Record that a request was made"""
        self.calls_today += 1
        self.last_call_time = time.time()
        logger.debug(f"API calls made today: {self.calls_today}/{self.daily_limit}")


class GoogleCustomSearchClient:
    """Client for Google Custom Search API with monitoring-specific features"""
    
    def __init__(self, search_config: SearchConfig):
        self.config = search_config
        self.rate_limiter = RateLimiter(search_config.daily_query_limit)
        
        try:
            self.service = build('customsearch', 'v1', developerKey=search_config.api_key)
        except GoogleAuthError as e:
            raise ValueError(f"Failed to initialize Google Custom Search API: {e}") from e
        
        logger.info(f"Initialized Google Custom Search client with engine ID: {search_config.search_engine_id}")
    
    def search_site_for_updates(self, site_config: SiteConfig) -> List[SearchResult]:
        """
        Search a specific site for recent updates
        
        Args:
            site_config: Configuration for the site to search
            
        Returns:
            List of SearchResult objects
            
        Raises:
            RuntimeError: If the search fails or rate limit is exceeded
        """
        if not self.rate_limiter.can_make_request():
            raise RuntimeError(f"Daily API rate limit ({self.config.daily_query_limit}) exceeded")
        
        # Build search query
        query = self._build_search_query(site_config)
        
        logger.info(f"Searching site '{site_config.name}' with query: {query}")
        
        try:
            self.rate_limiter.wait_if_needed()
            
            # Build search parameters
            search_params = {
                'q': query,
                'cx': self.config.search_engine_id,
                'num': min(site_config.max_results, self.config.results_per_query),
                'dateRestrict': f'd{self.config.date_range_days}',
                # 'sort': 'date',  # This is affecting results, removed for now
                'safe': 'off',
                'fields': 'items,searchInformation,queries'
            }
            
            # Execute search
            result = self.service.cse().list(**search_params).execute()
            self.rate_limiter.record_request()

            logger.info(f"---")
            logger.info(f"Raw API response: {result}")
            logger.info(f"---")
            
            # Parse results
            search_results = self._parse_search_results(result, site_config)
            
            logger.info(f"Found {len(search_results)} results for site '{site_config.name}'")
            return search_results
            
        except HttpError as e:
            logger.error(f"Google Search API error for site '{site_config.name}': {e}")
            raise RuntimeError(f"Search API error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error searching site '{site_config.name}': {e}")
            raise RuntimeError(f"Unexpected search error: {e}") from e
    
    def _build_search_query(self, site_config: SiteConfig) -> str:
        """Build search query for a site"""
        query_parts = [f"site:{site_config.url}"]
        
        # Add keywords if specified
        if site_config.keywords:
            keywords_query = " OR ".join(f'"{keyword}"' for keyword in site_config.keywords)
            query_parts.append(f"({keywords_query})")
        
        # Add custom search terms
        if site_config.custom_search_terms:
            terms_query = " OR ".join(f'"{term}"' for term in site_config.custom_search_terms)
            query_parts.append(f"({terms_query})")
        
        # Add path restrictions
        if site_config.search_paths:
            path_queries = []
            for path in site_config.search_paths:
                # Ensure path starts with /
                if not path.startswith('/'):
                    path = '/' + path
                path_queries.append(f"inurl:{path}")
            query_parts.append(f"({' OR '.join(path_queries)})")
        
        # Add path exclusions
        if site_config.exclude_paths:
            for exclude_path in site_config.exclude_paths:
                if not exclude_path.startswith('/'):
                    exclude_path = '/' + exclude_path
                query_parts.append(f"-inurl:{exclude_path}")
        
        return " ".join(query_parts)
    
    def _parse_search_results(self, api_response: Dict[str, Any], site_config: SiteConfig) -> List[SearchResult]:
        """Parse Google Search API response into SearchResult objects"""
        results = []
        
        items = api_response.get('items', [])
        total_results = api_response.get('searchInformation', {}).get('totalResults', '0')
        
        logger.debug(f"API returned {len(items)} items out of {total_results} total results")
        
        for item in items:
            try:
                result = SearchResult(
                    title=item.get('title', 'No Title'),
                    link=item.get('link', ''),
                    snippet=item.get('snippet', ''),
                    display_link=item.get('displayLink'),
                    formatted_url=item.get('formattedUrl'),
                    cache_id=item.get('cacheId')
                )
                
                # Validate the result
                if self._is_valid_result(result, site_config):
                    results.append(result)
                else:
                    logger.debug(f"Filtered out invalid result: {result.link}")
                    
            except Exception as e:
                logger.warning(f"Error parsing search result item: {e}")
                continue
        
        return results
    
    def _is_valid_result(self, result: SearchResult, site_config: SiteConfig) -> bool:
        """Validate if a search result should be included"""
        if not result.link:
            return False
        
        try:
            parsed_url = urlparse(result.link)
            
            # Handle site_config.url which may or may not have a scheme
            site_url = site_config.url
            if not site_url.startswith(('http://', 'https://')):
                site_url = 'https://' + site_url
            parsed_site = urlparse(site_url)
            
            # Extract domain names for comparison
            result_domain = parsed_url.netloc.lower()
            target_domain = parsed_site.netloc.lower()
            
            # Remove 'www.' prefix for comparison
            if result_domain.startswith('www.'):
                result_domain = result_domain[4:]
            if target_domain.startswith('www.'):
                target_domain = target_domain[4:]
            
            # Check if the URL is from the correct domain
            if target_domain != result_domain:
                logger.debug(f"Result domain '{result_domain}' doesn't match target '{target_domain}': {result.link}")
                return False
            
            # Check exclude paths
            for exclude_path in site_config.exclude_paths:
                if exclude_path in parsed_url.path:
                    logger.debug(f"Result matches exclude path '{exclude_path}': {result.link}")
                    return False
            
            # If search paths are specified, ensure the URL matches at least one
            if site_config.search_paths:
                path_matches = any(
                    search_path in parsed_url.path 
                    for search_path in site_config.search_paths
                )
                if not path_matches:
                    logger.debug(f"Result doesn't match any search path: {result.link}")
                    return False
            
            logger.debug(f"Result validated successfully: {result.link}")
            return True
            
        except Exception as e:
            logger.warning(f"Error validating result URL '{result.link}': {e}")
            return False
    
    def search_all_sites(self, sites: List[SiteConfig]) -> Dict[str, List[SearchResult]]:
        """
        Search all configured sites for updates
        
        Args:
            sites: List of site configurations to search
            
        Returns:
            Dictionary mapping site names to their search results
            
        Raises:
            RuntimeError: If rate limit is exceeded before all sites are searched
        """
        all_results = {}
        
        logger.info(f"Starting search across {len(sites)} sites")
        
        for i, site in enumerate(sites, 1):
            if not self.rate_limiter.can_make_request():
                remaining_sites = len(sites) - i + 1
                logger.warning(f"Rate limit reached. Skipping {remaining_sites} remaining sites.")
                break
            
            try:
                results = self.search_site_for_updates(site)
                all_results[site.name] = results
                
                logger.info(f"Completed search {i}/{len(sites)}: {site.name} ({len(results)} results)")
                
                # Add small delay between site searches to be respectful
                if i < len(sites):  # Don't sleep after the last search
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Failed to search site '{site.name}': {e}")
                all_results[site.name] = []
        
        total_results = sum(len(results) for results in all_results.values())
        logger.info(f"Search completed. Total results: {total_results}")
        
        return all_results
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        return {
            'calls_made_today': self.rate_limiter.calls_today,
            'daily_limit': self.rate_limiter.daily_limit,
            'calls_remaining': self.rate_limiter.daily_limit - self.rate_limiter.calls_today,
            'reset_date': self.rate_limiter.last_reset.isoformat()
        }


def normalize_url(url: str) -> str:
    """
    Normalize URL for comparison and deduplication
    
    Args:
        url: Raw URL to normalize
        
    Returns:
        Normalized URL string
    """
    try:
        parsed = urlparse(url.lower())
        
        # Check if this is actually a valid URL (has scheme and netloc, or at least netloc)
        if not parsed.netloc and not parsed.scheme:
            # This is likely not a valid URL, just return lowercase
            return url.lower()
        
        # Remove common tracking parameters
        tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 
                          'fbclid', 'gclid', 'ref', 'source']
        
        # Rebuild URL without tracking parameters
        scheme = parsed.scheme or 'https'
        netloc = parsed.netloc
        path = parsed.path.rstrip('/')  # Remove trailing slash
        
        # Parse and filter query parameters
        if parsed.query:
            from urllib.parse import parse_qs, urlencode
            params = parse_qs(parsed.query)
            filtered_params = {k: v for k, v in params.items() if k not in tracking_params}
            query = urlencode(filtered_params, doseq=True) if filtered_params else ''
        else:
            query = ''
        
        fragment = ''  # Ignore fragments for normalization
        
        from urllib.parse import urlunparse
        normalized = urlunparse((scheme, netloc, path, '', query, fragment))
        
        return normalized
        
    except Exception as e:
        logger.warning(f"Error normalizing URL '{url}': {e}")
        return url.lower()  # Fallback to simple lowercase


def create_search_summary(results: Dict[str, List[SearchResult]]) -> Dict[str, Any]:
    """
    Create a summary of search results across all sites
    
    Args:
        results: Dictionary mapping site names to search results
        
    Returns:
        Summary dictionary with statistics and highlights
    """
    total_results = sum(len(site_results) for site_results in results.values())
    sites_with_results = len([name for name, site_results in results.items() if site_results])
    
    # Find most common keywords in titles and snippets
    all_text = []
    for site_results in results.values():
        for result in site_results:
            all_text.extend([result.title, result.snippet])
    
    # Simple keyword extraction (you could use more sophisticated NLP here)
    word_counts = {}
    for text in all_text:
        if text:
            words = re.findall(r'\b\w+\b', text.lower())
            for word in words:
                if len(word) > 3:  # Skip short words
                    word_counts[word] = word_counts.get(word, 0) + 1
    
    # Get top keywords
    top_keywords = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'total_results': total_results,
        'sites_searched': len(results),
        'sites_with_results': sites_with_results,
        'top_keywords': [{'word': word, 'count': count} for word, count in top_keywords],
        'search_timestamp': datetime.utcnow().isoformat(),
        'sites_summary': {
            name: {
                'result_count': len(site_results),
                'has_results': len(site_results) > 0
            }
            for name, site_results in results.items()
        }
    }