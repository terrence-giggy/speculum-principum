"""
Content analysis and processing for identifying study subjects.

This module uses NLP and machine learning techniques to analyze content
and identify emerging or evolving study subjects.
"""

import logging
import re
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

# NLP imports
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tag import pos_tag
import spacy

from ..monitoring.sources import ContentItem
from ..utils.config import Config


@dataclass
class AnalysisResult:
    """Result of content analysis."""
    content_item: ContentItem
    relevance_score: float
    subjects: List[str]
    keywords: List[str]
    topics: List[str]
    entities: List[Dict[str, str]]
    summary: str
    metadata: Dict[str, Any]


class KeywordExtractor:
    """Extracts important keywords and phrases from text."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.KeywordExtractor")
        self._ensure_nltk_data()
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Subject-related keywords that indicate relevance
        self.subject_indicators = {
            'research', 'study', 'analysis', 'investigation', 'experiment',
            'theory', 'method', 'approach', 'technique', 'framework',
            'model', 'algorithm', 'dataset', 'findings', 'results',
            'discovery', 'breakthrough', 'innovation', 'development',
            'artificial intelligence', 'machine learning', 'deep learning',
            'neural networks', 'natural language processing', 'computer vision',
            'data science', 'big data', 'analytics', 'statistics',
            'quantum computing', 'blockchain', 'cryptocurrency',
            'biotechnology', 'genetics', 'genomics', 'medicine',
            'climate change', 'sustainability', 'renewable energy',
            'space exploration', 'astronomy', 'physics', 'chemistry',
            'psychology', 'sociology', 'economics', 'politics'
        }

    def _ensure_nltk_data(self):
        """Ensure required NLTK data is downloaded."""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
            nltk.data.find('corpora/wordnet')
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)

    def extract_keywords(self, text: str, max_keywords: int = 20) -> List[str]:
        """Extract important keywords from text."""
        try:
            # Tokenize and clean
            tokens = word_tokenize(text.lower())
            
            # Remove stopwords and non-alphabetic tokens
            filtered_tokens = [
                self.lemmatizer.lemmatize(token)
                for token in tokens
                if token.isalpha() and 
                token not in self.stop_words and 
                len(token) > 2
            ]
            
            # Get POS tags to focus on nouns and adjectives
            pos_tags = pos_tag(filtered_tokens)
            keywords = [
                word for word, pos in pos_tags
                if pos.startswith(('NN', 'JJ', 'VB'))
            ]
            
            # Count frequency
            keyword_freq = {}
            for keyword in keywords:
                keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
            
            # Sort by frequency
            sorted_keywords = sorted(
                keyword_freq.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            return [keyword for keyword, freq in sorted_keywords[:max_keywords]]
            
        except Exception as e:
            self.logger.error(f"Error extracting keywords: {e}")
            return []

    def extract_phrases(self, text: str, max_phrases: int = 10) -> List[str]:
        """Extract important phrases from text."""
        try:
            sentences = sent_tokenize(text)
            phrases = []
            
            # Look for phrases containing subject indicators
            for sentence in sentences:
                sentence_lower = sentence.lower()
                for indicator in self.subject_indicators:
                    if indicator in sentence_lower:
                        # Extract the sentence as a potential phrase
                        clean_sentence = re.sub(r'[^\w\s]', '', sentence).strip()
                        if len(clean_sentence) > 10 and len(clean_sentence) < 200:
                            phrases.append(clean_sentence)
                        break
            
            return phrases[:max_phrases]
            
        except Exception as e:
            self.logger.error(f"Error extracting phrases: {e}")
            return []


class EntityExtractor:
    """Extracts named entities from text using spaCy."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.EntityExtractor")
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None

    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """Extract named entities from text."""
        if not self.nlp:
            return []
        
        try:
            doc = self.nlp(text)
            entities = []
            
            for ent in doc.ents:
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'description': spacy.explain(ent.label_) or ent.label_
                })
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
            return []


class RelevanceScorer:
    """Scores content relevance for study subject identification."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.RelevanceScorer")
        
        # Academic and research indicators
        self.academic_terms = {
            'research', 'study', 'analysis', 'experiment', 'survey',
            'method', 'methodology', 'approach', 'technique', 'algorithm',
            'theory', 'hypothesis', 'findings', 'results', 'conclusion',
            'peer-reviewed', 'publication', 'journal', 'conference',
            'university', 'institute', 'laboratory', 'academic'
        }
        
        # Technology and innovation indicators
        self.tech_terms = {
            'artificial intelligence', 'ai', 'machine learning', 'ml',
            'deep learning', 'neural network', 'nlp', 'computer vision',
            'data science', 'big data', 'algorithm', 'automation',
            'blockchain', 'quantum', 'biotechnology', 'nanotechnology',
            'innovation', 'breakthrough', 'advancement', 'development'
        }

    def calculate_relevance(self, content_item: ContentItem, keywords: List[str], 
                          entities: List[Dict[str, str]]) -> float:
        """Calculate relevance score for content."""
        try:
            score = 0.0
            text = (content_item.title + " " + content_item.content).lower()
            
            # Base score from content length (longer content may be more substantial)
            if len(content_item.content) > self.config.min_content_length:
                score += 0.1
            
            # Academic terms boost
            academic_matches = sum(1 for term in self.academic_terms if term in text)
            score += min(academic_matches * 0.1, 0.3)
            
            # Technology terms boost
            tech_matches = sum(1 for term in self.tech_terms if term in text)
            score += min(tech_matches * 0.1, 0.3)
            
            # Keyword diversity (more diverse keywords = higher score)
            if keywords:
                unique_keywords = set(keywords)
                score += min(len(unique_keywords) * 0.02, 0.2)
            
            # Entity types (organizations, technologies, etc.)
            relevant_entity_types = {'ORG', 'PRODUCT', 'EVENT', 'WORK_OF_ART'}
            entity_score = sum(
                0.05 for entity in entities 
                if entity['label'] in relevant_entity_types
            )
            score += min(entity_score, 0.2)
            
            # Source reliability (academic sources get higher scores)
            source_name = content_item.source.lower()
            if any(term in source_name for term in ['arxiv', 'nature', 'science', 'mit', 'stanford']):
                score += 0.2
            elif any(term in source_name for term in ['tech', 'research', 'academic']):
                score += 0.1
            
            # Recent content bonus
            if content_item.published_date:
                days_old = (datetime.now() - content_item.published_date).days
                if days_old <= 7:
                    score += 0.1
                elif days_old <= 30:
                    score += 0.05
            
            return min(score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating relevance: {e}")
            return 0.0


class ContentProcessor:
    """Main content processor that orchestrates analysis."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.keyword_extractor = KeywordExtractor()
        self.entity_extractor = EntityExtractor()
        self.relevance_scorer = RelevanceScorer(config)

    async def analyze_content(self, content_items: List[ContentItem], 
                            source_name: str) -> List[AnalysisResult]:
        """Analyze a list of content items."""
        self.logger.debug(f"Analyzing {len(content_items)} items from {source_name}")
        
        results = []
        for item in content_items:
            try:
                result = await self._analyze_single_item(item)
                if result.relevance_score >= self.config.relevance_threshold:
                    results.append(result)
            except Exception as e:
                self.logger.error(f"Error analyzing item {item.title[:50]}...: {e}")
        
        self.logger.info(f"Found {len(results)} relevant items from {source_name}")
        return results

    async def _analyze_single_item(self, item: ContentItem) -> AnalysisResult:
        """Analyze a single content item."""
        text = item.title + " " + item.content
        
        # Extract keywords and phrases
        keywords = self.keyword_extractor.extract_keywords(text)
        phrases = self.keyword_extractor.extract_phrases(text)
        
        # Extract entities
        entities = self.entity_extractor.extract_entities(text)
        
        # Calculate relevance score
        relevance_score = self.relevance_scorer.calculate_relevance(item, keywords, entities)
        
        # Identify potential subjects
        subjects = self._identify_subjects(keywords, phrases, entities)
        
        # Generate summary
        summary = self._generate_summary(item, keywords)
        
        return AnalysisResult(
            content_item=item,
            relevance_score=relevance_score,
            subjects=subjects,
            keywords=keywords,
            topics=phrases,
            entities=entities,
            summary=summary,
            metadata={
                'analysis_timestamp': datetime.now().isoformat(),
                'keyword_count': len(keywords),
                'entity_count': len(entities),
                'phrase_count': len(phrases)
            }
        )

    def _identify_subjects(self, keywords: List[str], phrases: List[str], 
                          entities: List[Dict[str, str]]) -> List[str]:
        """Identify potential study subjects from analysis."""
        subjects = set()
        
        # Keywords that could be subjects
        for keyword in keywords[:10]:  # Top 10 keywords
            if len(keyword) > 3:  # Filter short words
                subjects.add(keyword.title())
        
        # Entities that could be subjects (organizations, products, etc.)
        for entity in entities:
            if entity['label'] in ['ORG', 'PRODUCT', 'EVENT', 'WORK_OF_ART']:
                subjects.add(entity['text'])
        
        # Extract subjects from phrases
        for phrase in phrases:
            # Look for phrases that might indicate new subjects
            if any(indicator in phrase.lower() for indicator in ['new', 'novel', 'emerging', 'breakthrough']):
                # Extract key terms from the phrase
                words = phrase.split()
                for i, word in enumerate(words):
                    if word.lower() in ['new', 'novel', 'emerging'] and i + 1 < len(words):
                        potential_subject = ' '.join(words[i+1:i+3])
                        subjects.add(potential_subject.title())
        
        return list(subjects)[:20]  # Limit to top 20 subjects

    def _generate_summary(self, item: ContentItem, keywords: List[str]) -> str:
        """Generate a brief summary of the content."""
        # Simple extractive summary using first sentence and key info
        sentences = item.content.split('.')[:3]
        summary_parts = []
        
        # Add title
        summary_parts.append(f"Title: {item.title}")
        
        # Add first sentence
        if sentences:
            summary_parts.append(sentences[0].strip() + ".")
        
        # Add key keywords
        if keywords:
            summary_parts.append(f"Key terms: {', '.join(keywords[:5])}")
        
        return " ".join(summary_parts)[:500]  # Limit to 500 characters