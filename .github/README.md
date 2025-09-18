# GitHub Actions Setup for Speculum Principis

This directory contains the GitHub Actions workflow for automatically running the Speculum Principis content monitoring agent.

## Overview

The workflow runs the agent every 6 hours to:
- Monitor configured content sources
- Analyze content for relevance
- Store findings in a persistent database
- Cache dependencies for faster execution

## Files

### `.github/workflows/content-monitoring.yml`
Main workflow that:
- ✅ **Caches Python dependencies** - Speeds up subsequent runs
- ✅ **Caches ML models** - Avoids re-downloading large models
- ✅ **Artifact persistence** - Maintains database state between runs
- ✅ **Fallback demo mode** - Works even if heavy dependencies fail
- ✅ **Comprehensive reporting** - Provides execution summaries

### `requirements-github.txt`
Lightweight dependencies optimized for GitHub Actions:
- Avoids NumPy 2.x compatibility issues
- Includes only essential packages
- Faster installation times

### `github_actions_demo.py`
Standalone demo script that:
- Works without heavy ML dependencies
- Simulates realistic content processing
- Maintains database persistence
- Perfect for testing and CI/CD

### `.env.github`
Environment configuration template for GitHub Actions.

## Configuration

### Environment Variables

Set these in your repository's GitHub Actions secrets/variables:

```bash
# Analysis Configuration
RELEVANCE_THRESHOLD=0.6        # Content relevance threshold (0-1)
LOG_LEVEL=INFO                 # Logging level
DATABASE_URL=sqlite:///speculum_data.db

# Source Configuration (optional)
RSS_SOURCES=https://example.com/feed1.rss,https://example.com/feed2.rss
```

### Workflow Triggers

The workflow runs on:
- **Schedule**: Every 6 hours (`0 */6 * * *`)
- **Manual**: Via workflow_dispatch
- **Push**: To main branch (for testing)
- **Pull Request**: For validation

## Features

### 🚀 **Optimized Performance**
- **Dependency Caching**: Python packages cached between runs
- **ML Model Caching**: Hugging Face models and NLTK data cached
- **System Dependencies**: APT packages cached
- **Smart Cache Keys**: Based on requirements.txt hash

### 💾 **Database Persistence**
- **Artifact Storage**: Database stored as GitHub artifact
- **30-day Retention**: Artifacts kept for 30 days
- **Automatic Recovery**: Downloads previous database on each run
- **Size Tracking**: Monitors database growth

### 🛡️ **Robust Execution**
- **Fallback Modes**: Demo mode if dependencies fail
- **Error Handling**: Comprehensive error capture
- **Timeout Protection**: 30-minute execution limit
- **Failure Artifacts**: Logs uploaded on failures

### 📊 **Comprehensive Reporting**
- **Execution Summary**: Results in workflow summary
- **Statistics Display**: Content analyzed, subjects found
- **Database Status**: Size, growth, persistence
- **Error Details**: Failed steps and reasons

## Usage

### 1. **Enable Workflow**
```bash
# Repository Settings > Actions > General
# Enable "Allow GitHub Actions to create and approve pull requests"
```

### 2. **Configure Secrets** (optional)
```bash
# Repository Settings > Secrets and Variables > Actions
OPENAI_API_KEY=your_api_key_here
NEWS_API_KEY=your_news_api_key
```

### 3. **Customize Sources**
Edit `github_actions_demo.py` to add your content sources:
```python
sources = {
    "your_source": [
        MockContentItem(
            "Your Content Title",
            "Content text to analyze",
            "https://example.com/article",
            "your_source"
        )
    ]
}
```

### 4. **Manual Trigger**
```bash
# GitHub Repository > Actions > Content Monitoring > Run workflow
```

## Monitoring

### Workflow Status
- **Green**: Successful execution
- **Red**: Failed execution 
- **Yellow**: In progress

### Artifacts
- `speculum-database`: Current database state
- `monitoring-logs-{run_id}`: Failure logs (if errors)

### Summary Reports
Each run creates a summary showing:
- Execution status
- Content items found
- Database statistics
- Next run schedule

## Troubleshooting

### Common Issues

#### 1. **Dependency Conflicts**
```bash
# Solution: Uses lightweight requirements-github.txt
# Falls back to demo mode if needed
```

#### 2. **Database Too Large**
```bash
# GitHub artifact limit: 10GB
# Monitor database size in reports
# Implement cleanup if needed
```

#### 3. **Execution Timeout**
```bash
# Current limit: 30 minutes
# Optimize source count/processing
# Consider splitting into multiple workflows
```

#### 4. **Missing Artifacts**
```bash
# Artifacts expire after 30 days
# Workflow creates new database if missing
# No data loss, just starts fresh
```

### Debug Mode

Enable debug logging:
```yaml
# Manual trigger with DEBUG log level
# Or set in workflow env vars
LOG_LEVEL: DEBUG
```

## Customization

### Adding Sources
1. **RSS Feeds**: Add URLs to RSS_SOURCES environment variable
2. **Custom Sources**: Modify `MockSourceManager` in demo script
3. **Real Sources**: Update main application source configuration

### Changing Schedule
```yaml
# .github/workflows/content-monitoring.yml
schedule:
  - cron: '0 */3 * * *'  # Every 3 hours
  # - cron: '0 9 * * 1'  # Weekly on Monday at 9 AM
```

### Database Options
1. **SQLite** (default): Uses artifacts for persistence
2. **External DB**: Set DATABASE_URL to PostgreSQL/MySQL
3. **Cloud Storage**: Implement custom storage in workflow

## Security

### Best Practices
- ✅ API keys stored in GitHub Secrets
- ✅ No sensitive data in logs
- ✅ Limited execution time
- ✅ Artifact encryption by GitHub

### Access Control
- Workflow runs with repository permissions
- No external network access required for demo mode
- ML model downloads cached securely

## Cost Optimization

### GitHub Actions Minutes
- **Free tier**: 2,000 minutes/month
- **Estimated usage**: ~30 minutes/day (4 runs × 7.5 min avg)
- **Monthly usage**: ~900 minutes (well within limits)

### Storage
- **Artifacts**: Minimal cost for database storage
- **Cache**: Free for public repositories

## Performance Metrics

### Typical Execution Times
- **Cold start**: 8-12 minutes (no cache)
- **Warm start**: 3-5 minutes (with cache)
- **Demo mode**: 30-60 seconds

### Resource Usage
- **Memory**: ~2GB peak
- **CPU**: 2 cores
- **Storage**: <100MB artifacts
- **Network**: Minimal (cached dependencies)

## Migration

### From Continuous Deployment
```bash
# Old: Long-running server
docker run speculum-principis start

# New: Scheduled executions
# Handled automatically by GitHub Actions
```

### Database Migration
```bash
# Export existing data
python -m speculum_principis.cli export --format json > data.json

# Import to new system
# Upload as artifact or configure external database
```

## Support

For issues with:
- **Workflow failures**: Check Actions logs
- **Configuration**: Review environment variables
- **Performance**: Monitor execution times
- **Database**: Check artifact sizes

See main project README for application-specific support.