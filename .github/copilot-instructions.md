# Copilot Instructions for Speculum Principum

## Architecture & Core Flow
Two-tier system: **Site Monitoring** (Google Search API → deduplication → GitHub issues) + **Issue Processing** (workflow-driven document generation)

**Core modules**:
- `src/core/site_monitor.py` - Site monitoring orchestration
- `src/core/issue_processor.py` - Automated workflow processing
- `src/workflow/workflow_matcher.py` - Workflow discovery and matching
- `src/workflow/deliverable_generator.py` - Template-based document generation
- `src/storage/git_manager.py` - Git operations for branch/commit management
- `src/clients/search_client.py` - Google API + rate limiting
- `src/core/deduplication.py` - SHA256 content hashing in `processed_urls.json`
- `src/utils/config_manager.py` - YAML with `${ENV_VAR}` substitution

**Site monitoring flow**: `search_all_sites()` → `_filter_new_results()` → `_create_individual_issues()` → `_mark_results_processed()`

**Issue processing flow**: Label detection → Workflow matching → Agent assignment → Document generation → Git commits

## Key Commands

**Site monitoring**: `python main.py monitor --config config.yaml --no-individual-issues`
**Issue processing**: `python main.py process-issues --issue 123 --dry-run`
**Status/validation**: `python main.py status`, `pytest tests/ -v`

## Code Quality Standards

**Testing**: Use centralized fixtures from `tests/conftest.py`. Mock GitHub API and workflows. Validate with `ConfigValidator.validate_config_file()`.

**Naming**: `create_*` factories, `get_*` status/info, `_private_method` helpers, `handle_*_command` for CLI.

**Error handling**: Google API rate limiting via `daily_query_limit`, GitHub retry logic, workflow validation, git conflict resolution.

**Configuration**: All configs use `${VAR_NAME}` substitution. Required: `GITHUB_TOKEN`, `GOOGLE_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID`. Workflows in `docs/workflow/deliverables/`.

## Essential Patterns

**Deduplication**: Content hash = `sha256(normalized_url + title.lower())[:16]`. JSON storage with retention policies.

**Workflow system**: YAML definitions with `trigger_labels`, template-based deliverables, Git branch per issue.

**Safe testing**: Always use `--dry-run` and `--no-individual-issues` to avoid API/Git changes.

**VS Code integration**: Use F5 debug configs and tasks. Virtual environment at `.venv/bin/python`.