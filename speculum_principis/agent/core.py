"""
Core agent implementation for Speculum Principis.

This module contains the main agent class that orchestrates the monitoring,
analysis, and storage of internet content for identifying study subjects.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..monitoring.sources import SourceManager
from ..analysis.processor import ContentProcessor
from ..storage.database import DatabaseManager
from ..utils.config import Config


@dataclass
class MonitoringResult:
    """Result from a monitoring cycle."""
    sources_checked: int
    content_items_found: int
    relevant_subjects: int
    errors: List[str]
    timestamp: datetime


class SpeculumAgent:
    """
    Main agent class that coordinates monitoring, analysis, and storage.
    
    The agent runs a single monitoring cycle per execution, checking various 
    internet sources for new content, analyzing it for relevance to study subjects, 
    and storing interesting findings.
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize the agent with configuration."""
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.source_manager = SourceManager(self.config)
        self.content_processor = ContentProcessor(self.config)
        self.db_manager = DatabaseManager(self.config)
        
        # State tracking
        self.last_run = None
        self.is_running = False
        self.start_time = None
        self.stats = {
            "total_runs": 0,
            "total_content_analyzed": 0,
            "total_subjects_found": 0,
            "errors": 0
        }

    async def run_once(self):
        """Run a single monitoring cycle and exit."""
        self.logger.info("Starting Speculum Principis agent (single run)...")
        
        # Set running state
        self.is_running = True
        if not self.start_time:
            self.start_time = datetime.now()
        
        # Initialize database
        await self.db_manager.initialize()
        
        # Run single monitoring cycle
        try:
            result = await self._run_monitoring_cycle()
            self._update_stats(result)
            self.last_run = datetime.now()
            
            self.logger.info(
                f"Monitoring cycle completed: {result.content_items_found} items found, "
                f"{result.relevant_subjects} relevant subjects identified"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
            self.stats["errors"] += 1
            raise
        finally:
            # Reset running state
            self.is_running = False

    async def _run_monitoring_cycle(self) -> MonitoringResult:
        """Run a single monitoring cycle."""
        self.logger.debug("Starting monitoring cycle...")
        
        errors = []
        content_items = []
        
        try:
            # Fetch content from all sources
            sources_data = await self.source_manager.fetch_all_sources()
            
            # Process each source's content
            for source_name, source_content in sources_data.items():
                try:
                    # Analyze content for relevant subjects
                    analysis_results = await self.content_processor.analyze_content(
                        source_content, source_name
                    )
                    content_items.extend(analysis_results)
                    
                except Exception as e:
                    error_msg = f"Error processing source {source_name}: {e}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            # Store results
            relevant_subjects = 0
            for item in content_items:
                if item.relevance_score >= self.config.relevance_threshold:
                    await self.db_manager.store_content(item)
                    relevant_subjects += 1
            
            return MonitoringResult(
                sources_checked=len(sources_data),
                content_items_found=len(content_items),
                relevant_subjects=relevant_subjects,
                errors=errors,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            error_msg = f"Critical error in monitoring cycle: {e}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            
            return MonitoringResult(
                sources_checked=0,
                content_items_found=0,
                relevant_subjects=0,
                errors=errors,
                timestamp=datetime.now()
            )

    def _update_stats(self, result: MonitoringResult):
        """Update agent statistics."""
        self.stats["total_runs"] += 1
        self.stats["total_content_analyzed"] += result.content_items_found
        self.stats["total_subjects_found"] += result.relevant_subjects
        if result.errors:
            self.stats["errors"] += len(result.errors)

    async def get_recent_subjects(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recently discovered subjects."""
        since_date = datetime.now() - timedelta(days=days)
        return await self.db_manager.get_subjects_since(since_date)

    async def search_subjects(self, query: str) -> List[Dict[str, Any]]:
        """Search for subjects matching a query."""
        return await self.db_manager.search_subjects(query)

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        uptime_minutes = 0
        if self.start_time:
            uptime_minutes = (datetime.now() - self.start_time).total_seconds() / 60
            
        return {
            **self.stats,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "is_running": self.is_running,
            "uptime_minutes": uptime_minutes,
        }