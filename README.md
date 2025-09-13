# Speculum Principis

A Python-based generative agent that monitors public internet material for new and evolving study subjects. The agent continuously scans various sources like RSS feeds, academic publications, news sites, and social media to identify emerging topics and research areas.

## Features

- **Multi-Source Monitoring**: Monitors RSS feeds, web pages, academic sources, and news outlets
- **Intelligent Analysis**: Uses NLP and machine learning to identify relevant study subjects
- **Continuous Operation**: Runs as a daemon with configurable monitoring intervals
- **Subject Tracking**: Maintains a database of discovered subjects with relevance scoring
- **Search & Discovery**: Search for subjects and view discovery trends
- **Extensible Architecture**: Easy to add new sources and analysis methods
- **CLI Interface**: Command-line tools for interaction and management

## Installation

1. Clone the repository:
```bash
git clone https://github.com/terrence-giggy/speculum-principis.git
cd speculum-principis
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package:
```bash
pip install -e .
```

4. Download required NLP models:
```bash
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('averaged_perceptron_tagger')"
```

## Configuration

Copy the example configuration file and customize it:
```bash
cp .env.example .env
```

Key configuration options:
- `DATABASE_URL`: Database connection string (default: SQLite)
- `MONITOR_INTERVAL_MINUTES`: How often to check sources (default: 60)
- `RELEVANCE_THRESHOLD`: Minimum score for storing subjects (default: 0.7)
- `LOG_LEVEL`: Logging verbosity (default: INFO)

## Usage

### Start the Monitoring Agent

Start continuous monitoring:
```bash
speculum start
```

### View Recent Subjects

List subjects discovered in the last 7 days:
```bash
speculum subjects
```

List subjects from the last 30 days:
```bash
speculum subjects --days 30
```

### Search for Subjects

Search for subjects containing specific terms:
```bash
speculum search "artificial intelligence"
speculum search "climate change"
```

### View Statistics

Show agent and database statistics:
```bash
speculum stats
```

### Add New Sources

Add an RSS feed:
```bash
speculum add-source --source-type rss --name "AI News" --url "https://example.com/ai-feed.xml"
```

Add a web scraping source:
```bash
speculum add-source --source-type web --name "Tech Blog" --url "https://example.com/blog" --selector ".article-title"
```

### Test the System

Run a single monitoring cycle for testing:
```bash
speculum test
```

## Default Sources

The agent comes pre-configured with several high-quality sources:

**Academic & Research:**
- arXiv Computer Science papers
- Nature News
- Science Daily
- MIT News
- Stanford News

**Technology:**
- Hacker News
- TechCrunch
- Ars Technica

**Discussion:**
- Reddit Science (via web scraping)

## Architecture

The system consists of several key components:

### Agent Core (`speculum_principis.agent.core`)
- Main orchestration logic
- Monitoring loop management
- Statistics tracking

### Source Management (`speculum_principis.monitoring.sources`)
- RSS feed parsing
- Web scraping
- Concurrent source fetching
- Rate limiting and error handling

### Content Analysis (`speculum_principis.analysis.processor`)
- NLP-based keyword extraction
- Named entity recognition
- Relevance scoring
- Subject identification

### Data Storage (`speculum_principis.storage.database`)
- SQLAlchemy-based persistence
- Content and subject tracking
- Search functionality
- Statistics aggregation

### Configuration (`speculum_principis.utils.config`)
- Environment-based configuration
- Validation and logging setup

## Subject Detection

The agent uses several techniques to identify relevant study subjects:

1. **Keyword Analysis**: Extracts important terms using NLTK
2. **Entity Recognition**: Identifies organizations, products, and concepts using spaCy
3. **Relevance Scoring**: Combines multiple factors:
   - Academic terminology presence
   - Technology indicators
   - Source reliability
   - Content freshness
   - Keyword diversity

4. **Subject Extraction**: Identifies potential research areas from:
   - High-frequency keywords
   - Named entities
   - Phrases containing novelty indicators

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Code Formatting

```bash
black speculum_principis/
flake8 speculum_principis/
```

### Type Checking

```bash
mypy speculum_principis/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Roadmap

- [ ] Integration with academic APIs (PubMed, Google Scholar)
- [ ] Social media monitoring (Twitter, LinkedIn)
- [ ] Advanced ML models for better subject classification
- [ ] Web dashboard for visualization
- [ ] Export functionality (CSV, JSON, API)
- [ ] Clustering and trend analysis
- [ ] Automated report generation
- [ ] Integration with research tools (Zotero, Mendeley)

## Support

For questions and support, please open an issue on GitHub.