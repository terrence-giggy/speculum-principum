#!/usr/bin/env python3
"""
GitHub Actions compatible demo runner for Speculum Principis.

This script runs the agent with mock components to demonstrate functionality
without requiring heavy ML dependencies.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta

# Add the project to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Standalone configuration class (avoiding imports)
class Config:
    """Standalone configuration for GitHub Actions demo."""
    
    def __init__(self):
        self.relevance_threshold = float(os.getenv('RELEVANCE_THRESHOLD', 0.6))
        self.monitor_interval = int(os.getenv('MONITOR_INTERVAL', 360))
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///speculum_data.db')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.max_concurrent_requests = int(os.getenv('MAX_CONCURRENT_REQUESTS', 10))
        self.request_delay = float(os.getenv('REQUEST_DELAY', 1.0))
        self.source_timeout = int(os.getenv('SOURCE_TIMEOUT', 30))
        self.min_content_length = int(os.getenv('MIN_CONTENT_LENGTH', 100))
        self.max_items_per_source = int(os.getenv('MAX_ITEMS_PER_SOURCE', 50))
        
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    def validate(self):
        """Validate configuration."""
        if self.relevance_threshold < 0 or self.relevance_threshold > 1:
            print("❌ Invalid relevance threshold (must be 0-1)")
            return False
        return True
        
    def __str__(self):
        return f"Config(threshold={self.relevance_threshold}, db={self.database_url})"


class MockAnalysisResult:
    def __init__(self, content_item, relevance_score=0.8):
        self.content_item = content_item
        self.relevance_score = relevance_score
        self.subjects = ['AI Research', 'Technology', 'Science']
        self.keywords = ['research', 'technology', 'science', 'ai']
        self.entities = []
        self.summary = f"Analysis of: {content_item.title[:50]}..."
        self.metadata = {'source': content_item.source, 'processed_at': datetime.now().isoformat()}


class MockContentItem:
    def __init__(self, title, content, url, source):
        self.title = title
        self.content = content
        self.url = url
        self.source = source
        self.published_date = datetime.now()
        self.metadata = {}


class MockSourceManager:
    def __init__(self, config):
        self.config = config
        
    async def fetch_all_sources(self):
        """Simulate fetching from multiple sources."""
        # Simulate realistic content discovery
        sources = {
            "tech_news": [
                MockContentItem(
                    "Breakthrough in AI Research Methodology",
                    "Researchers have developed new techniques for improving artificial intelligence research methodologies, focusing on more efficient training processes.",
                    "https://example.com/ai-research-breakthrough",
                    "tech_news"
                ),
                MockContentItem(
                    "Quantum Computing Advances in Error Correction",
                    "Latest developments in quantum computing show significant progress in error correction algorithms and quantum state preservation.",
                    "https://example.com/quantum-advances",
                    "tech_news"
                ),
                MockContentItem(
                    "New Programming Language for Machine Learning",
                    "A new programming language designed specifically for machine learning applications has been released, promising better performance.",
                    "https://example.com/new-ml-language",
                    "tech_news"
                )
            ],
            "science_feed": [
                MockContentItem(
                    "Climate Science Modeling Improvements",
                    "Scientists have developed improved climate models that provide more accurate predictions for regional weather patterns.",
                    "https://example.com/climate-modeling",
                    "science_feed"
                ),
                MockContentItem(
                    "Neuroscience Research on Learning",
                    "New neuroscience research reveals insights into how the brain processes and retains information during learning.",
                    "https://example.com/neuroscience-learning",
                    "science_feed"
                )
            ],
            "research_papers": [
                MockContentItem(
                    "Novel Approach to Data Analysis",
                    "Researchers propose a novel statistical approach to analyzing large datasets with improved accuracy and efficiency.",
                    "https://example.com/data-analysis-research",
                    "research_papers"
                )
            ]
        }
        
        print(f"📡 Fetched content from {len(sources)} sources:")
        for source, items in sources.items():
            print(f"  - {source}: {len(items)} items")
            
        return sources


class MockContentProcessor:
    def __init__(self, config):
        self.config = config
        
    async def analyze_content(self, content_items, source_name):
        """Mock content analysis with realistic scoring."""
        results = []
        
        for item in content_items:
            # Simulate content analysis
            score = self._calculate_mock_score(item)
            
            if score >= self.config.relevance_threshold:
                result = MockAnalysisResult(item, score)
                results.append(result)
                
        print(f"🔍 Analyzed {len(content_items)} items from {source_name}, {len(results)} relevant")
        return results
    
    def _calculate_mock_score(self, item):
        """Calculate a realistic relevance score."""
        # Higher scores for research-related content
        research_terms = ['research', 'study', 'analysis', 'methodology', 'breakthrough']
        tech_terms = ['ai', 'technology', 'computing', 'algorithm', 'programming']
        science_terms = ['science', 'scientific', 'neuroscience', 'climate', 'data']
        
        content_lower = (item.title + " " + item.content).lower()
        
        score = 0.3  # Base score
        
        # Boost for research terms
        research_matches = sum(1 for term in research_terms if term in content_lower)
        score += research_matches * 0.15
        
        # Boost for tech terms
        tech_matches = sum(1 for term in tech_terms if term in content_lower)
        score += tech_matches * 0.12
        
        # Boost for science terms
        science_matches = sum(1 for term in science_terms if term in content_lower)
        score += science_matches * 0.10
        
        # Cap at 0.95
        return min(0.95, score)


class MockDatabaseManager:
    def __init__(self, config):
        self.config = config
        self.stored_items = []
        self.db_file = config.database_url.replace('sqlite:///', '')
        
    async def initialize(self):
        """Mock database initialization."""
        if os.path.exists(self.db_file):
            # Simulate loading existing data
            size = os.path.getsize(self.db_file)
            print(f"💾 Database initialized: {self.db_file} ({size} bytes)")
        else:
            print(f"💾 Database initialized: {self.db_file} (new)")
            # Create empty database file
            with open(self.db_file, 'w') as f:
                f.write("")
                
    async def store_content(self, analysis_result):
        """Mock content storage."""
        self.stored_items.append(analysis_result)
        
        # Append to database file to simulate persistence
        with open(self.db_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()},{analysis_result.content_item.title},{analysis_result.relevance_score}\n")
            
        print(f"💾 Stored: {analysis_result.content_item.title[:60]}... (score: {analysis_result.relevance_score:.2f})")


class MonitoringResult:
    def __init__(self, sources_checked, content_items_found, relevant_subjects, errors):
        self.sources_checked = sources_checked
        self.content_items_found = content_items_found
        self.relevant_subjects = relevant_subjects
        self.errors = errors
        self.timestamp = datetime.now()


class SpeculumAgent:
    """GitHub Actions compatible Speculum Agent with mock components."""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.source_manager = MockSourceManager(self.config)
        self.content_processor = MockContentProcessor(self.config)
        self.db_manager = MockDatabaseManager(self.config)
        
        self.last_run = None
        self.stats = {
            "total_runs": 0,
            "total_content_analyzed": 0,
            "total_subjects_found": 0,
            "errors": 0
        }

    async def run_once(self):
        """Run a single monitoring cycle and exit."""
        print("🚀 Starting Speculum Principis agent (GitHub Actions mode)...")
        print(f"📋 Configuration: {self.config}")
        
        # Initialize database
        await self.db_manager.initialize()
        
        try:
            result = await self._run_monitoring_cycle()
            self._update_stats(result)
            self.last_run = datetime.now()
            
            print(f"\n✅ Monitoring cycle completed:")
            print(f"   📊 Sources checked: {result.sources_checked}")
            print(f"   📄 Content items found: {result.content_items_found}")
            print(f"   🎯 Relevant subjects: {result.relevant_subjects}")
            
            if result.errors:
                print(f"   ⚠️  Errors: {len(result.errors)}")
                
            return result
            
        except Exception as e:
            print(f"❌ Error in monitoring cycle: {e}")
            self.stats["errors"] += 1
            raise

    async def _run_monitoring_cycle(self):
        """Run a single monitoring cycle."""
        errors = []
        content_items = []
        
        try:
            # Fetch content from all sources
            sources_data = await self.source_manager.fetch_all_sources()
            
            # Process each source's content
            for source_name, source_content in sources_data.items():
                try:
                    analysis_results = await self.content_processor.analyze_content(
                        source_content, source_name
                    )
                    content_items.extend(analysis_results)
                    
                except Exception as e:
                    error_msg = f"Error processing source {source_name}: {e}"
                    print(f"⚠️  {error_msg}")
                    errors.append(error_msg)
            
            # Store relevant results
            relevant_subjects = 0
            for item in content_items:
                if item.relevance_score >= self.config.relevance_threshold:
                    await self.db_manager.store_content(item)
                    relevant_subjects += 1
            
            return MonitoringResult(
                sources_checked=len(sources_data),
                content_items_found=len(content_items),
                relevant_subjects=relevant_subjects,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"Critical error in monitoring cycle: {e}"
            print(f"❌ {error_msg}")
            errors.append(error_msg)
            
            return MonitoringResult(
                sources_checked=0,
                content_items_found=0,
                relevant_subjects=0,
                errors=errors
            )

    def _update_stats(self, result):
        """Update agent statistics."""
        self.stats["total_runs"] += 1
        self.stats["total_content_analyzed"] += result.content_items_found
        self.stats["total_subjects_found"] += result.relevant_subjects
        if result.errors:
            self.stats["errors"] += len(result.errors)

    def get_stats(self):
        """Get agent statistics."""
        return {
            **self.stats,
            "last_run": self.last_run.isoformat() if self.last_run else None,
        }


async def main():
    """Main execution function for GitHub Actions."""
    print("🎬 Speculum Principis - GitHub Actions Demo Mode")
    print("=" * 50)
    
    # Create configuration
    config = Config()
    config.setup_logging()
    
    if not config.validate():
        print("❌ Configuration validation failed")
        sys.exit(1)
    
    # Create and run agent
    agent = SpeculumAgent(config)
    
    try:
        result = await agent.run_once()
        
        # Show final statistics
        stats = agent.get_stats()
        print(f"\n📈 Final Statistics:")
        print(f"   Total runs: {stats['total_runs']}")
        print(f"   Content analyzed: {stats['total_content_analyzed']}")
        print(f"   Subjects found: {stats['total_subjects_found']}")
        print(f"   Errors: {stats['errors']}")
        print(f"   Last run: {stats['last_run']}")
        
        # Check database
        if os.path.exists(agent.db_manager.db_file):
            size = os.path.getsize(agent.db_manager.db_file)
            print(f"   Database size: {size} bytes")
        
        print(f"\n🎯 Stored {len(agent.db_manager.stored_items)} relevant items")
        
        if agent.db_manager.stored_items:
            print("📝 Top items:")
            for i, item in enumerate(agent.db_manager.stored_items[:3], 1):
                print(f"   {i}. {item.content_item.title[:70]}... (score: {item.relevance_score:.2f})")
        
        print("\n✅ Demo completed successfully!")
        
        # Set GitHub Actions outputs
        if os.getenv('GITHUB_ACTIONS'):
            print(f"::set-output name=items_found::{result.content_items_found}")
            print(f"::set-output name=relevant_subjects::{result.relevant_subjects}")
            print(f"::set-output name=database_size::{os.path.getsize(agent.db_manager.db_file) if os.path.exists(agent.db_manager.db_file) else 0}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())