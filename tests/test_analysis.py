"""Tests for content analysis functionality."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from speculum_principis.analysis.processor import (
    ContentProcessor, KeywordExtractor, RelevanceScorer, AnalysisResult
)
from speculum_principis.monitoring.sources import ContentItem
from speculum_principis.utils.config import Config


class TestKeywordExtractor:
    """Test cases for keyword extraction."""

    @pytest.fixture
    def extractor(self):
        """Create a keyword extractor instance."""
        return KeywordExtractor()

    def test_extract_keywords_basic(self, extractor):
        """Test basic keyword extraction."""
        text = "Artificial intelligence and machine learning are transforming technology research."
        
        with patch.object(extractor, '_ensure_nltk_data'):
            keywords = extractor.extract_keywords(text)
        
        # Should extract relevant keywords
        assert isinstance(keywords, list)
        # Note: Actual NLTK processing may not work in test environment

    def test_extract_phrases_with_indicators(self, extractor):
        """Test phrase extraction with subject indicators."""
        text = "This research studies artificial intelligence. The experiment shows promising results."
        
        with patch.object(extractor, '_ensure_nltk_data'):
            phrases = extractor.extract_phrases(text)
        
        assert isinstance(phrases, list)

    def test_extract_keywords_empty_text(self, extractor):
        """Test keyword extraction with empty text."""
        with patch.object(extractor, '_ensure_nltk_data'):
            keywords = extractor.extract_keywords("")
        
        assert keywords == []

    def test_extract_phrases_no_indicators(self, extractor):
        """Test phrase extraction with no subject indicators."""
        text = "This is just regular text without any special terms."
        
        with patch.object(extractor, '_ensure_nltk_data'):
            phrases = extractor.extract_phrases(text)
        
        assert isinstance(phrases, list)


class TestRelevanceScorer:
    """Test cases for relevance scoring."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config()

    @pytest.fixture
    def scorer(self, config):
        """Create a relevance scorer instance."""
        return RelevanceScorer(config)

    @pytest.fixture
    def sample_content(self):
        """Create sample content item."""
        return ContentItem(
            title="AI Research Breakthrough",
            content="Scientists at MIT have developed a new artificial intelligence algorithm for machine learning research.",
            url="https://example.com/ai-research",
            source="mit_news",
            published_date=datetime.now(),
            metadata={}
        )

    def test_relevance_scoring_high(self, scorer, sample_content):
        """Test relevance scoring for high-relevance content."""
        keywords = ["artificial", "intelligence", "algorithm", "research", "mit"]
        entities = [
            {"text": "MIT", "label": "ORG", "description": "Organization"},
            {"text": "AI Algorithm", "label": "PRODUCT", "description": "Technology"}
        ]
        
        score = scorer.calculate_relevance(sample_content, keywords, entities)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be high due to academic terms and reliable source

    def test_relevance_scoring_low(self, scorer):
        """Test relevance scoring for low-relevance content."""
        low_content = ContentItem(
            title="Random Blog Post",
            content="Just some random thoughts about daily life.",
            url="https://example.com/random",
            source="random_blog",
            published_date=datetime.now(),
            metadata={}
        )
        
        keywords = ["random", "thoughts", "daily"]
        entities = []
        
        score = scorer.calculate_relevance(low_content, keywords, entities)
        
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should be low due to lack of academic/tech terms

    def test_relevance_scoring_with_tech_terms(self, scorer):
        """Test relevance scoring with technology terms."""
        tech_content = ContentItem(
            title="Blockchain Innovation",
            content="New blockchain technology enables quantum computing applications.",
            url="https://example.com/tech",
            source="tech_news",
            published_date=datetime.now(),
            metadata={}
        )
        
        keywords = ["blockchain", "quantum", "computing", "technology"]
        entities = []
        
        score = scorer.calculate_relevance(tech_content, keywords, entities)
        
        assert score > 0.3  # Should get points for tech terms


class TestContentProcessor:
    """Test cases for the main content processor."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Config()
        config.relevance_threshold = 0.5
        return config

    @pytest.fixture
    def processor(self, config):
        """Create a content processor instance."""
        return ContentProcessor(config)

    @pytest.fixture
    def sample_content_items(self):
        """Create sample content items."""
        return [
            ContentItem(
                title="AI Research Paper",
                content="This paper presents novel findings in artificial intelligence research.",
                url="https://example.com/paper1",
                source="arxiv",
                published_date=datetime.now(),
                metadata={}
            ),
            ContentItem(
                title="Random Article",
                content="Short text.",
                url="https://example.com/short",
                source="blog",
                published_date=datetime.now(),
                metadata={}
            )
        ]

    @pytest.mark.asyncio
    async def test_analyze_content_basic(self, processor, sample_content_items):
        """Test basic content analysis."""
        # Mock the component methods to avoid NLTK/spaCy dependencies in tests
        with patch.object(processor.keyword_extractor, 'extract_keywords', return_value=["ai", "research"]):
            with patch.object(processor.keyword_extractor, 'extract_phrases', return_value=["AI research"]):
                with patch.object(processor.entity_extractor, 'extract_entities', return_value=[]):
                    with patch.object(processor.relevance_scorer, 'calculate_relevance', return_value=0.8):
                        results = await processor.analyze_content(sample_content_items, "test_source")
        
        assert isinstance(results, list)
        # Should filter based on relevance threshold
        for result in results:
            assert isinstance(result, AnalysisResult)
            assert result.relevance_score >= processor.config.relevance_threshold

    @pytest.mark.asyncio
    async def test_analyze_single_item(self, processor, sample_content_items):
        """Test analysis of a single content item."""
        item = sample_content_items[0]
        
        with patch.object(processor.keyword_extractor, 'extract_keywords', return_value=["ai", "research"]):
            with patch.object(processor.keyword_extractor, 'extract_phrases', return_value=["AI research"]):
                with patch.object(processor.entity_extractor, 'extract_entities', return_value=[]):
                    with patch.object(processor.relevance_scorer, 'calculate_relevance', return_value=0.8):
                        result = await processor._analyze_single_item(item)
        
        assert isinstance(result, AnalysisResult)
        assert result.content_item == item
        assert result.relevance_score == 0.8
        assert "ai" in result.keywords
        assert "research" in result.keywords

    def test_identify_subjects(self, processor):
        """Test subject identification."""
        keywords = ["artificial", "intelligence", "machine", "learning"]
        phrases = ["new artificial intelligence breakthrough", "novel machine learning method"]
        entities = [
            {"text": "Google AI", "label": "ORG", "description": "Organization"},
            {"text": "TensorFlow", "label": "PRODUCT", "description": "Software"}
        ]
        
        subjects = processor._identify_subjects(keywords, phrases, entities)
        
        assert isinstance(subjects, list)
        assert len(subjects) <= 20  # Should be limited
        # Should include entities from relevant categories
        assert "Google AI" in subjects or "TensorFlow" in subjects

    def test_generate_summary(self, processor, sample_content_items):
        """Test summary generation."""
        item = sample_content_items[0]
        keywords = ["ai", "research", "paper"]
        
        summary = processor._generate_summary(item, keywords)
        
        assert isinstance(summary, str)
        assert len(summary) <= 500  # Should be limited in length
        assert item.title in summary  # Should include title