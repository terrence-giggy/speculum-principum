"""
Database management for storing and retrieving analyzed content.

This module handles persistence of content items, analysis results,
and discovered subjects using SQLAlchemy ORM.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import asyncio

from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from ..analysis.processor import AnalysisResult
from ..utils.config import Config

Base = declarative_base()


class ContentRecord(Base):
    """Database model for content items."""
    __tablename__ = 'content'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    source = Column(String(100), nullable=False)
    published_date = Column(DateTime)
    discovered_date = Column(DateTime, default=datetime.utcnow)
    relevance_score = Column(Float, nullable=False)
    keywords = Column(JSON)
    subjects = Column(JSON)
    entities = Column(JSON)
    summary = Column(Text)
    item_metadata = Column(JSON)


class SubjectRecord(Base):
    """Database model for discovered subjects."""
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    occurrence_count = Column(Integer, default=1)
    relevance_score = Column(Float, default=0.0)
    sources = Column(JSON)  # List of sources where this subject was found
    keywords = Column(JSON)  # Associated keywords
    subject_metadata = Column(JSON)


class DatabaseManager:
    """Manages database operations for the agent."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self.engine = None
        self.session_factory = None
        self._initialized = False

    async def initialize(self):
        """Initialize database connection and create tables."""
        if self._initialized:
            return
        
        try:
            # Create database engine
            if self.config.database_url.startswith('sqlite'):
                # For SQLite, use regular engine (async SQLite is complex)
                self.engine = create_engine(
                    self.config.database_url,
                    echo=False
                )
                self.session_factory = sessionmaker(bind=self.engine)
            else:
                # For other databases, use async engine
                self.engine = create_async_engine(
                    self.config.database_url,
                    echo=False
                )
                self.session_factory = async_sessionmaker(bind=self.engine)
            
            # Create tables
            if self.config.database_url.startswith('sqlite'):
                Base.metadata.create_all(self.engine)
            else:
                async with self.engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            
            self._initialized = True
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise

    async def store_content(self, analysis_result: AnalysisResult):
        """Store analyzed content in the database."""
        try:
            if self.config.database_url.startswith('sqlite'):
                await self._store_content_sync(analysis_result)
            else:
                await self._store_content_async(analysis_result)
                
        except Exception as e:
            self.logger.error(f"Error storing content: {e}")

    async def _store_content_sync(self, analysis_result: AnalysisResult):
        """Store content using synchronous session (for SQLite)."""
        session = self.session_factory()
        try:
            item = analysis_result.content_item
            
            # Check if content already exists
            existing = session.query(ContentRecord).filter_by(url=item.url).first()
            if existing:
                self.logger.debug(f"Content already exists: {item.url}")
                return
            
            # Create content record
            content_record = ContentRecord(
                title=item.title,
                content=item.content,
                url=item.url,
                source=item.source,
                published_date=item.published_date,
                relevance_score=analysis_result.relevance_score,
                keywords=analysis_result.keywords,
                subjects=analysis_result.subjects,
                entities=[
                    {'text': e['text'], 'label': e['label'], 'description': e.get('description', '')}
                    for e in analysis_result.entities
                ],
                summary=analysis_result.summary,
                metadata=analysis_result.metadata
            )
            
            session.add(content_record)
            session.commit()
            
            # Update subject records
            await self._update_subjects_sync(session, analysis_result)
            
            self.logger.debug(f"Stored content: {item.title[:50]}...")
            
        finally:
            session.close()

    async def _store_content_async(self, analysis_result: AnalysisResult):
        """Store content using async session."""
        async with self.session_factory() as session:
            item = analysis_result.content_item
            
            # Check if content already exists
            result = await session.execute(
                session.query(ContentRecord).filter_by(url=item.url)
            )
            existing = result.first()
            if existing:
                self.logger.debug(f"Content already exists: {item.url}")
                return
            
            # Create content record
            content_record = ContentRecord(
                title=item.title,
                content=item.content,
                url=item.url,
                source=item.source,
                published_date=item.published_date,
                relevance_score=analysis_result.relevance_score,
                keywords=analysis_result.keywords,
                subjects=analysis_result.subjects,
                entities=[
                    {'text': e['text'], 'label': e['label'], 'description': e.get('description', '')}
                    for e in analysis_result.entities
                ],
                summary=analysis_result.summary,
                metadata=analysis_result.metadata
            )
            
            session.add(content_record)
            await session.commit()
            
            # Update subject records
            await self._update_subjects_async(session, analysis_result)

    async def _update_subjects_sync(self, session: Session, analysis_result: AnalysisResult):
        """Update subject records synchronously."""
        for subject_name in analysis_result.subjects:
            if not subject_name.strip():
                continue
                
            # Check if subject exists
            subject = session.query(SubjectRecord).filter_by(name=subject_name).first()
            
            if subject:
                # Update existing subject
                subject.last_seen = datetime.utcnow()
                subject.occurrence_count += 1
                subject.relevance_score = max(subject.relevance_score, analysis_result.relevance_score)
                
                # Update sources list
                sources = subject.sources or []
                if analysis_result.content_item.source not in sources:
                    sources.append(analysis_result.content_item.source)
                    subject.sources = sources
                
                # Update keywords
                keywords = set(subject.keywords or [])
                keywords.update(analysis_result.keywords[:5])  # Add top 5 keywords
                subject.keywords = list(keywords)[:20]  # Keep top 20
                
            else:
                # Create new subject
                subject = SubjectRecord(
                    name=subject_name,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    occurrence_count=1,
                    relevance_score=analysis_result.relevance_score,
                    sources=[analysis_result.content_item.source],
                    keywords=analysis_result.keywords[:10],
                    subject_metadata={}
                )
                session.add(subject)
        
        session.commit()

    async def _update_subjects_async(self, session: AsyncSession, analysis_result: AnalysisResult):
        """Update subject records asynchronously."""
        for subject_name in analysis_result.subjects:
            if not subject_name.strip():
                continue
                
            # Check if subject exists
            result = await session.execute(
                session.query(SubjectRecord).filter_by(name=subject_name)
            )
            subject = result.first()
            
            if subject:
                # Update existing subject
                subject.last_seen = datetime.utcnow()
                subject.occurrence_count += 1
                subject.relevance_score = max(subject.relevance_score, analysis_result.relevance_score)
                
                # Update sources list
                sources = subject.sources or []
                if analysis_result.content_item.source not in sources:
                    sources.append(analysis_result.content_item.source)
                    subject.sources = sources
                
                # Update keywords
                keywords = set(subject.keywords or [])
                keywords.update(analysis_result.keywords[:5])
                subject.keywords = list(keywords)[:20]
                
            else:
                # Create new subject
                subject = SubjectRecord(
                    name=subject_name,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    occurrence_count=1,
                    relevance_score=analysis_result.relevance_score,
                    sources=[analysis_result.content_item.source],
                    keywords=analysis_result.keywords[:10],
                    subject_metadata={}
                )
                session.add(subject)
        
        await session.commit()

    async def get_subjects_since(self, since_date: datetime) -> List[Dict[str, Any]]:
        """Get subjects discovered since a given date."""
        try:
            if self.config.database_url.startswith('sqlite'):
                return await self._get_subjects_since_sync(since_date)
            else:
                return await self._get_subjects_since_async(since_date)
        except Exception as e:
            self.logger.error(f"Error getting subjects: {e}")
            return []

    async def _get_subjects_since_sync(self, since_date: datetime) -> List[Dict[str, Any]]:
        """Get subjects using synchronous session."""
        session = self.session_factory()
        try:
            subjects = session.query(SubjectRecord).filter(
                SubjectRecord.first_seen >= since_date
            ).order_by(SubjectRecord.relevance_score.desc()).all()
            
            return [
                {
                    'name': s.name,
                    'first_seen': s.first_seen.isoformat(),
                    'last_seen': s.last_seen.isoformat(),
                    'occurrence_count': s.occurrence_count,
                    'relevance_score': s.relevance_score,
                    'sources': s.sources or [],
                    'keywords': s.keywords or []
                }
                for s in subjects
            ]
        finally:
            session.close()

    async def _get_subjects_since_async(self, since_date: datetime) -> List[Dict[str, Any]]:
        """Get subjects using async session."""
        async with self.session_factory() as session:
            result = await session.execute(
                session.query(SubjectRecord).filter(
                    SubjectRecord.first_seen >= since_date
                ).order_by(SubjectRecord.relevance_score.desc())
            )
            subjects = result.all()
            
            return [
                {
                    'name': s.name,
                    'first_seen': s.first_seen.isoformat(),
                    'last_seen': s.last_seen.isoformat(),
                    'occurrence_count': s.occurrence_count,
                    'relevance_score': s.relevance_score,
                    'sources': s.sources or [],
                    'keywords': s.keywords or []
                }
                for s in subjects
            ]

    async def search_subjects(self, query: str) -> List[Dict[str, Any]]:
        """Search for subjects matching a query."""
        try:
            if self.config.database_url.startswith('sqlite'):
                return await self._search_subjects_sync(query)
            else:
                return await self._search_subjects_async(query)
        except Exception as e:
            self.logger.error(f"Error searching subjects: {e}")
            return []

    async def _search_subjects_sync(self, query: str) -> List[Dict[str, Any]]:
        """Search subjects using synchronous session."""
        session = self.session_factory()
        try:
            subjects = session.query(SubjectRecord).filter(
                SubjectRecord.name.contains(query)
            ).order_by(SubjectRecord.relevance_score.desc()).limit(50).all()
            
            return [
                {
                    'name': s.name,
                    'first_seen': s.first_seen.isoformat(),
                    'last_seen': s.last_seen.isoformat(),
                    'occurrence_count': s.occurrence_count,
                    'relevance_score': s.relevance_score,
                    'sources': s.sources or [],
                    'keywords': s.keywords or []
                }
                for s in subjects
            ]
        finally:
            session.close()

    async def _search_subjects_async(self, query: str) -> List[Dict[str, Any]]:
        """Search subjects using async session."""
        async with self.session_factory() as session:
            result = await session.execute(
                session.query(SubjectRecord).filter(
                    SubjectRecord.name.contains(query)
                ).order_by(SubjectRecord.relevance_score.desc()).limit(50)
            )
            subjects = result.all()
            
            return [
                {
                    'name': s.name,
                    'first_seen': s.first_seen.isoformat(),
                    'last_seen': s.last_seen.isoformat(),
                    'occurrence_count': s.occurrence_count,
                    'relevance_score': s.relevance_score,
                    'sources': s.sources or [],
                    'keywords': s.keywords or []
                }
                for s in subjects
            ]

    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            if self.config.database_url.startswith('sqlite'):
                return await self._get_stats_sync()
            else:
                return await self._get_stats_async()
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {}

    async def _get_stats_sync(self) -> Dict[str, Any]:
        """Get stats using synchronous session."""
        session = self.session_factory()
        try:
            content_count = session.query(ContentRecord).count()
            subject_count = session.query(SubjectRecord).count()
            
            # Get recent activity
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_content = session.query(ContentRecord).filter(
                ContentRecord.discovered_date >= week_ago
            ).count()
            recent_subjects = session.query(SubjectRecord).filter(
                SubjectRecord.first_seen >= week_ago
            ).count()
            
            return {
                'total_content_items': content_count,
                'total_subjects': subject_count,
                'recent_content_items': recent_content,
                'recent_subjects': recent_subjects
            }
        finally:
            session.close()

    async def _get_stats_async(self) -> Dict[str, Any]:
        """Get stats using async session."""
        async with self.session_factory() as session:
            content_result = await session.execute(session.query(ContentRecord).count())
            content_count = content_result.scalar()
            
            subject_result = await session.execute(session.query(SubjectRecord).count())
            subject_count = subject_result.scalar()
            
            # Get recent activity
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_content_result = await session.execute(
                session.query(ContentRecord).filter(
                    ContentRecord.discovered_date >= week_ago
                ).count()
            )
            recent_content = recent_content_result.scalar()
            
            recent_subjects_result = await session.execute(
                session.query(SubjectRecord).filter(
                    SubjectRecord.first_seen >= week_ago
                ).count()
            )
            recent_subjects = recent_subjects_result.scalar()
            
            return {
                'total_content_items': content_count,
                'total_subjects': subject_count,
                'recent_content_items': recent_content,
                'recent_subjects': recent_subjects
            }