# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automating various operations in the Speculum Principum project.

## Overview

The project includes several automated workflows:

- **`process-issues.yml`** - Automated issue processing with workflow-based deliverable generation
- **`site-monitoring.yml`** - Scheduled site monitoring operations
- **`test.yml`** - Continuous integration testing
- **`setup-monitoring.yml`** - Initial repository setup
- **`scheduled-operations.yml`** - Periodic maintenance tasks
- **`weekly-cleanup.yml`** - Weekly cleanup operations

## Issue Processing Workflow (`process-issues.yml`)

### Purpose

Automatically processes GitHub issues labeled with `site-monitor` by:

1. Matching issues to appropriate workflows from `docs/workflow/deliverables/`
2. Generating structured research documents based on workflow specifications
3. Committing generated content to the repository
4. Managing issue assignment and status updates

### Triggers

The workflow is triggered by:

- **Issue Events**: When issues are labeled or assigned
- **Manual Dispatch**: For testing or processing specific issues

### Workflow Jobs

#### 1. `check-issues`

Discovers and validates issues that need processing:

- Filters for open issues with `site-monitor` label
- Excludes issues already assigned to `github-actions[bot]`
- Outputs a list of issues for parallel processing
- Uses fallback logic if helper scripts are unavailable

#### 2. `process-issues`

Processes each issue in parallel:

- Assigns issue to `github-actions[bot]` during processing
- Runs the issue processor with appropriate workflow matching
- Generates deliverables based on matched workflow specifications
- Handles both dry-run and live processing modes

#### 3. `summary`

Provides processing results and summary:

- Reports success/failure status for all issues
- Generates workflow summary for GitHub Actions UI
- Provides links to detailed logs for troubleshooting

### Required Secrets

Configure these secrets in your repository settings (`Settings > Secrets and variables > Actions`):

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `GITHUB_TOKEN` | GitHub authentication token | ✅ Auto-provided |
| `GOOGLE_API_KEY` | Google Custom Search API key | ✅ |
| `GOOGLE_SEARCH_ENGINE_ID` | Google Custom Search Engine ID | ✅ |

**Note**: `GITHUB_TOKEN` is automatically provided by GitHub Actions and doesn't need manual configuration.

### Manual Workflow Dispatch

You can manually trigger the workflow with custom parameters:

1. Go to **Actions** tab in your repository
2. Select **Process Issues with Automated Workflows**
3. Click **Run workflow**
4. Configure options:
   - **Issue number**: Process a specific issue (optional)
   - **Dry run**: Test without making changes (default: true)

### Configuration

The workflow uses the same `config.yaml` file as the local application. Ensure your configuration includes:

```yaml
# Agent configuration for GitHub Actions
agent:
  username: "github-actions[bot]"
  processing_timeout: 300
  max_batch_size: 10

# Workflow configuration
workflows:
  directory: "docs/workflow/deliverables"
  cache_enabled: true

# Output configuration
output:
  base_directory: "study"
  create_branches: false  # GitHub Actions commits to main
```

### Workflow Processing Logic

1. **Issue Discovery**: Finds issues with `site-monitor` label
2. **Workflow Matching**: Matches issues to workflows based on additional labels
3. **Assignment**: Assigns issues to `github-actions[bot]` during processing
4. **Generation**: Creates deliverables according to workflow specifications
5. **Commit**: Commits generated content with descriptive commit messages
6. **Cleanup**: Removes assignment and updates issue status

### Output Structure

Generated deliverables are committed to the repository following the structure defined in the matched workflow:

```
study/
  {issue_number}/
    analysis.md
    research.md
    summary.md
    ...
```

### Error Handling

The workflow includes comprehensive error handling:

- **Graceful Degradation**: Falls back to manual processing if automation fails
- **Parallel Processing**: Failures in one issue don't affect others
- **Detailed Logging**: Comprehensive logs for troubleshooting
- **Status Reporting**: Clear success/failure indicators

### Troubleshooting

#### Common Issues

**1. "No issues found to process"**
- Verify issues have the `site-monitor` label
- Check that issues aren't already assigned to `github-actions[bot]`
- Ensure issues are in "open" state

**2. "Workflow matching failed"**
- Verify workflow definitions exist in `docs/workflow/deliverables/`
- Check that workflows have proper YAML front matter with `trigger_labels`
- Review issue labels to ensure they match workflow trigger conditions

**3. "Permission denied" errors**
- Verify `GITHUB_TOKEN` has sufficient permissions
- Check repository settings for Actions permissions
- Ensure branch protection rules allow automated commits

**4. "API rate limit exceeded"**
- Monitor Google API usage quotas
- Consider implementing request batching for large issue volumes
- Review `daily_query_limit` in configuration

#### Debugging Steps

1. **Check workflow logs**:
   - Go to Actions tab > Select failed workflow run
   - Review individual job logs for detailed error messages

2. **Test locally**:
   ```bash
   python main.py process-issues --issue {number} --dry-run
   ```

3. **Validate configuration**:
   ```bash
   python main.py status --config config.yaml
   ```

4. **Manual workflow trigger**:
   - Use manual dispatch with dry-run enabled
   - Process single issues first before batch operations

### Best Practices

#### Security

- Never commit secrets to the repository
- Use GitHub secrets for all sensitive configuration
- Regularly rotate API keys and tokens
- Review workflow permissions periodically

#### Performance

- Process issues in small batches to avoid API rate limits
- Use parallel processing judiciously (max 3 concurrent jobs)
- Implement caching for workflow definitions
- Monitor resource usage and adjust timeouts as needed

#### Maintenance

- Regularly review and update workflow definitions
- Monitor processing success rates and adjust error handling
- Keep dependencies updated in `requirements.txt`
- Document any custom workflow additions

### Integration with Existing Workflows

The issue processing workflow integrates seamlessly with existing automation:

- **Site Monitoring**: Issues created by site monitoring automatically trigger processing
- **Manual Issues**: Manually created issues with appropriate labels are also processed
- **Batch Operations**: Supports both individual and batch processing modes
- **Cleanup**: Integrates with existing cleanup workflows for maintenance

### Workflow Customization

To customize the workflow behavior:

1. **Modify triggers**: Edit the `on:` section to change when the workflow runs
2. **Adjust parallelism**: Change `max-parallel` in the strategy matrix
3. **Update timeouts**: Modify timeout values in individual steps
4. **Add custom steps**: Insert additional processing steps as needed

### Monitoring and Metrics

The workflow provides several monitoring capabilities:

- **GitHub Actions UI**: Visual workflow status and history
- **Step summaries**: Detailed processing results
- **Commit messages**: Clear traceability of automated changes
- **Issue comments**: Status updates and clarification requests

For additional monitoring, consider integrating with external tools or implementing custom webhook notifications.