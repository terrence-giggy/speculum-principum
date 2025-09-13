"""
Source management for monitoring various internet sources.

This module handles the collection of content from different sources like
RSS feeds, news APIs, academic sources, and social media.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import aiohttp
import feedparser
from bs4 import BeautifulSoup

from ..utils.config import Config


@dataclass
class ContentItem:
    """Represents a piece of content from a source."""
    title: str
    content: str
    url: str
    source: str
    published_date: Optional[datetime]
    metadata: Dict[str, Any]


class RSSSource:
    """Handler for RSS feed sources."""
    
    def __init__(self, name: str, url: str, config: Config):
        self.name = name
        self.url = url
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{name}")

    async def fetch_content(self) -> List[ContentItem]:
        """Fetch content from RSS feed."""
        try:
            # Use feedparser to parse RSS
            feed = feedparser.parse(self.url)
            items = []
            
            for entry in feed.entries[:self.config.max_items_per_source]:
                # Extract content
                content = getattr(entry, 'content', [])
                if content and hasattr(content[0], 'value'):
                    text_content = content[0].value
                else:
                    text_content = getattr(entry, 'summary', '')
                
                # Clean HTML
                soup = BeautifulSoup(text_content, 'html.parser')
                clean_content = soup.get_text().strip()
                
                if len(clean_content) < self.config.min_content_length:
                    continue
                
                # Parse published date
                published_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_date = datetime(*entry.published_parsed[:6])
                
                item = ContentItem(
                    title=getattr(entry, 'title', ''),
                    content=clean_content,
                    url=getattr(entry, 'link', ''),
                    source=self.name,
                    published_date=published_date,
                    metadata={
                        'feed_title': feed.feed.get('title', ''),
                        'feed_description': feed.feed.get('description', ''),
                        'tags': [tag.term for tag in getattr(entry, 'tags', [])]
                    }
                )
                items.append(item)
            
            self.logger.info(f"Fetched {len(items)} items from {self.name}")
            return items
            
        except Exception as e:
            self.logger.error(f"Error fetching RSS feed {self.name}: {e}")
            return []


class WebScrapingSource:
    """Handler for web scraping sources."""
    
    def __init__(self, name: str, url: str, selector: str, config: Config):
        self.name = name
        self.url = url
        self.selector = selector
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{name}")

    async def fetch_content(self) -> List[ContentItem]:
        """Fetch content by scraping web pages."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as response:
                    if response.status != 200:
                        self.logger.error(f"HTTP {response.status} for {self.url}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    items = []
                    elements = soup.select(self.selector)
                    
                    for element in elements[:self.config.max_items_per_source]:
                        title = element.get('title', '') or element.text[:100]
                        content = element.get_text().strip()
                        
                        if len(content) < self.config.min_content_length:
                            continue
                        
                        # Try to find a link
                        link_elem = element.find('a')
                        url = link_elem.get('href', self.url) if link_elem else self.url
                        
                        # Make relative URLs absolute
                        if url.startswith('/'):
                            base_url = f"{response.url.scheme}://{response.url.host}"
                            url = base_url + url
                        
                        item = ContentItem(
                            title=title,
                            content=content,
                            url=url,
                            source=self.name,
                            published_date=datetime.now(),
                            metadata={
                                'scraped_from': self.url,
                                'selector': self.selector
                            }
                        )
                        items.append(item)
                    
                    self.logger.info(f"Scraped {len(items)} items from {self.name}")
                    return items
                    
        except Exception as e:
            self.logger.error(f"Error scraping {self.name}: {e}")
            return []


class SourceManager:
    """Manages all content sources and coordinates fetching."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.sources = self._initialize_sources()

    def _initialize_sources(self) -> List[Any]:
        """Initialize default sources for monitoring."""
        sources = []
        
        # Academic/Research RSS feeds
        sources.extend([
            RSSSource("arxiv_cs", "http://rss.arxiv.org/rss/cs", self.config),
            RSSSource("nature_news", "https://www.nature.com/nature.rss", self.config),
            RSSSource("science_daily", "https://www.sciencedaily.com/rss/all.xml", self.config),
        ])
        
        # Technology news feeds
        sources.extend([
            RSSSource("hacker_news", "https://hnrss.org/frontpage", self.config),
            RSSSource("tech_crunch", "https://techcrunch.com/feed/", self.config),
            RSSSource("ars_technica", "https://feeds.arstechnica.com/arstechnica/index", self.config),
        ])
        
        # Research and education feeds
        sources.extend([
            RSSSource("mit_news", "https://news.mit.edu/rss/feed", self.config),
            RSSSource("stanford_news", "https://news.stanford.edu/feed/", self.config),
        ])
        
        # Add web scraping sources for sites without RSS
        sources.extend([
            WebScrapingSource(
                "reddit_science", 
                "https://old.reddit.com/r/science/",
                ".thing .title a.title",
                self.config
            ),
        ])
        
        return sources

    def add_rss_source(self, name: str, url: str):
        """Add a new RSS source."""
        source = RSSSource(name, url, self.config)
        self.sources.append(source)
        self.logger.info(f"Added RSS source: {name}")

    def add_web_source(self, name: str, url: str, selector: str):
        """Add a new web scraping source."""
        source = WebScrapingSource(name, url, selector, self.config)
        self.sources.append(source)
        self.logger.info(f"Added web scraping source: {name}")

    async def fetch_all_sources(self) -> Dict[str, List[ContentItem]]:
        """Fetch content from all configured sources."""
        self.logger.info(f"Fetching content from {len(self.sources)} sources...")
        
        # Create tasks for all sources
        tasks = []
        for source in self.sources:
            task = asyncio.create_task(source.fetch_content())
            tasks.append((source.name, task))
        
        # Gather results with timeout
        results = {}
        for source_name, task in tasks:
            try:
                content = await asyncio.wait_for(task, timeout=self.config.source_timeout)
                results[source_name] = content
            except asyncio.TimeoutError:
                self.logger.warning(f"Source {source_name} timed out")
                results[source_name] = []
            except Exception as e:
                self.logger.error(f"Error fetching from {source_name}: {e}")
                results[source_name] = []
        
        total_items = sum(len(items) for items in results.values())
        self.logger.info(f"Fetched {total_items} total items from all sources")
        
        return results

    def get_source_names(self) -> List[str]:
        """Get list of all configured source names."""
        return [source.name for source in self.sources]