#!/usr/bin/env python3
"""
Simple demonstration of Speculum Principis functionality without heavy ML dependencies.

This script shows the core functionality working with mocked analysis components.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from speculum_principis.utils.config import Config
from speculum_principis.monitoring.sources import ContentItem, RSSSource
from speculum_principis.analysis.processor import AnalysisResult


class MockContentProcessor:
    """Mock content processor for demonstration."""
    
    def __init__(self, config):
        self.config = config
    
    async def analyze_content(self, content_items, source_name):
        """Mock analysis that returns simple results."""
        results = []
        for item in content_items:
            # Simple mock analysis
            score = 0.8 if any(term in item.content.lower() for term in 
                              ['research', 'ai', 'technology', 'science']) else 0.3
            
            if score >= self.config.relevance_threshold:
                result = AnalysisResult(
                    content_item=item,
                    relevance_score=score,
                    subjects=['AI Research', 'Technology'],
                    keywords=['research', 'technology', 'science'],
                    topics=['Tech trends'],
                    entities=[],
                    summary=f"Mock analysis of: {item.title[:50]}...",
                    metadata={'mock': True}
                )
                results.append(result)
        return results


class MockDatabaseManager:
    """Mock database manager for demonstration."""
    
    def __init__(self, config):
        self.config = config
        self.stored_items = []
    
    async def initialize(self):
        """Mock initialization."""
        print("Mock database initialized")
    
    async def store_content(self, analysis_result):
        """Mock storage."""
        self.stored_items.append(analysis_result)
        print(f"Stored: {analysis_result.content_item.title[:50]}... (score: {analysis_result.relevance_score:.2f})")


async def demo_basic_functionality():
    """Demonstrate basic system functionality."""
    print("=== Speculum Principis Demonstration ===\n")
    
    # Create configuration
    config = Config()
    config.relevance_threshold = 0.5
    print(f"Configuration loaded: {config}")
    print()
    
    # Create mock components
    processor = MockContentProcessor(config)
    db_manager = MockDatabaseManager(config)
    
    await db_manager.initialize()
    print()
    
    # Create sample content
    sample_content = [
        ContentItem(
            title="New AI Research Breakthrough in Machine Learning",
            content="Scientists have developed a revolutionary new approach to artificial intelligence that shows promising results in machine learning applications.",
            url="https://example.com/ai-research",
            source="tech_news",
            published_date=datetime.now(),
            metadata={}
        ),
        ContentItem(
            title="Local Weather Update",
            content="Today will be sunny with temperatures reaching 75 degrees.",
            url="https://example.com/weather",
            source="weather_news",
            published_date=datetime.now(),
            metadata={}
        ),
        ContentItem(
            title="Quantum Computing Advances",
            content="Recent research in quantum computing has shown significant progress in error correction and stability.",
            url="https://example.com/quantum",
            source="science_news",
            published_date=datetime.now(),
            metadata={}
        )
    ]
    
    print("Sample content created:")
    for item in sample_content:
        print(f"  - {item.title}")
    print()
    
    # Process content
    print("Analyzing content...")
    results = await processor.analyze_content(sample_content, "demo_source")
    print(f"Analysis complete. {len(results)} relevant items found.")
    print()
    
    # Store results
    print("Storing relevant content:")
    for result in results:
        await db_manager.store_content(result)
    
    print()
    print("=== Demo Complete ===")
    print(f"Total items processed: {len(sample_content)}")
    print(f"Relevant items found: {len(results)}")
    print(f"Items stored: {len(db_manager.stored_items)}")
    
    # Show stored results
    if db_manager.stored_items:
        print("\nStored items details:")
        for item in db_manager.stored_items:
            print(f"  Title: {item.content_item.title}")
            print(f"  Score: {item.relevance_score:.2f}")
            print(f"  Subjects: {', '.join(item.subjects)}")
            print(f"  Keywords: {', '.join(item.keywords)}")
            print()


async def demo_rss_fetching():
    """Demonstrate RSS fetching (if network is available)."""
    print("=== RSS Fetching Demo ===\n")
    
    config = Config()
    
    # Try to fetch from a simple RSS feed
    try:
        print("Testing RSS feed fetching...")
        rss_source = RSSSource("test_feed", "https://rss.cnn.com/rss/edition.rss", config)
        
        # This might fail due to network restrictions, but shows the structure
        content = await rss_source.fetch_content()
        print(f"Successfully fetched {len(content)} items from RSS feed")
        
        if content:
            print("Sample item:")
            item = content[0]
            print(f"  Title: {item.title[:80]}...")
            print(f"  Source: {item.source}")
            print(f"  URL: {item.url}")
            print(f"  Content length: {len(item.content)}")
        
    except Exception as e:
        print(f"RSS fetching failed (expected in sandbox): {e}")
        print("This is normal in a restricted environment.")
    
    print()


if __name__ == "__main__":
    print("Starting Speculum Principis demonstration...\n")
    
    try:
        # Run basic functionality demo
        asyncio.run(demo_basic_functionality())
        
        print("\n" + "="*50 + "\n")
        
        # Try RSS demo
        asyncio.run(demo_rss_fetching())
        
        print("Demonstration completed successfully!")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()