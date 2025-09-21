# Copilot Instructions for Speculum Principum

## Architecture & Core Flow
Site monitoring service: Google Search API → deduplication → GitHub issues

**Layer separation**:
- `site_monitor.py` - orchestration
- `search_client.py` - Google API + rate limiting  
- `deduplication.py` - SHA256 content hashing in `processed_urls.json`
- `site_monitor_github.py` - issue creation with templates
- `config_manager.py` - YAML with `${ENV_VAR}` substitution

**Critical flow**: `search_all_sites()` → `_filter_new_results()` → `_create_individual_issues()` → `_mark_results_processed()`

## Code Quality Standards

**Testing**: Use centralized fixtures from `tests/conftest.py`. Mock GitHub API with `mock_github_issue`. Validate configs with `MonitorConfig.load_config()`.

**Naming**: `create_*` factories, `get_*` status/info, `_private_method` helpers.

**Error handling**: Google API rate limiting via `daily_query_limit`, GitHub retry logic, JSON corruption handling in `DeduplicationManager`.

**Configuration**: All configs use `${VAR_NAME}` substitution. Required: `GITHUB_TOKEN`, `GOOGLE_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID`.

## Essential Patterns

**Deduplication**: Content hash = `sha256(normalized_url + title.lower())[:16]`. Storage in JSON with retention policies.

**Safe testing**: Always use `--no-individual-issues --no-summary-issue` to avoid API spam.

**Two-tier GitHub ops**: Basic `GitHubIssueCreator` + specialized `SiteMonitorIssueCreator` for domain logic.

**Development flow**: `python main.py setup` → `python main.py status` → `pytest tests/test_site_monitor.py -v`