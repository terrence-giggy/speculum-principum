# Workflow Definitions Documentation

This directory contains workflow definitions for the automated issue processing agent. Each workflow defines how GitHub issues with specific labels should be processed and what deliverables should be generated.

## Workflow File Format

Workflow definitions are YAML files that specify:

- **Trigger conditions** - What labels activate this workflow
- **Output structure** - Where and how files are organized
- **Deliverable specifications** - What documents to generate
- **Processing configuration** - Timeouts, validation rules, etc.

## Workflow Schema

```yaml
name: "Workflow Name"
description: "Brief description of workflow purpose"
version: "1.0.0"

# Labels that trigger this workflow (in addition to 'site-monitor')
trigger_labels:
  - "label1"
  - "label2"

# Output configuration
output:
  folder_structure: "study/{issue_number}-workflow-type"
  file_pattern: "{deliverable_name}.md"
  branch_pattern: "workflow-type/issue-{issue_number}"

# Required deliverables
deliverables:
  - name: "deliverable-name"
    title: "Human Readable Title"
    description: "What this deliverable contains"
    template: "template_file.md"
    required: true|false
    order: 1

# Processing configuration
processing:
  timeout: 60  # minutes
  require_review: true|false
  auto_pr: true|false
  context:
    focus_areas: []
    custom_settings: "value"

# Validation rules
validation:
  min_word_count: 100
  required_sections: []
  checks: []
```

## Available Variables

The following variables can be used in patterns:

- `{issue_number}` - GitHub issue number
- `{title_slug}` - Issue title converted to URL-friendly slug
- `{date}` - Current date in YYYY-MM-DD format
- `{deliverable_name}` - Name of the specific deliverable
- `{workflow_name}` - Name of the workflow being executed

## Trigger Label Logic

1. All workflows require the `site-monitor` label to be processed
2. Additional `trigger_labels` refine which workflow is selected
3. If multiple workflows match, the agent will request clarification
4. If no specific workflow matches (only `site-monitor`), the agent will list available options

## Deliverable Templates

Templates referenced in the `template` field should be placed in the `templates/` directory at the project root. Templates use Markdown format with variable substitution.

## Processing Flow

1. **Issue Detection** - Agent scans for issues with `site-monitor` label
2. **Workflow Matching** - Finds appropriate workflow based on labels
3. **Assignment** - Agent assigns itself to the issue
4. **Generation** - Creates deliverables per workflow specification
5. **Git Operations** - Creates branch and commits generated files
6. **Completion** - Updates issue with results and removes assignment

## Example Workflows

### Research Analysis
- **Triggers**: `research`, `analysis`, `deep-dive`
- **Purpose**: Comprehensive research documents
- **Deliverables**: Overview, background, methodology, findings, recommendations

### Technical Review
- **Triggers**: `technical-review`, `code-review`, `architecture`
- **Purpose**: Technical assessment and recommendations
- **Deliverables**: Architecture analysis, security assessment, performance review

## Creating New Workflows

1. Create a new YAML file in this directory
2. Follow the schema documented above
3. Define unique trigger labels to avoid conflicts
4. Specify required deliverables with clear descriptions
5. Set appropriate processing timeouts and validation rules
6. Test with a sample issue before deploying

## Best Practices

- Use descriptive trigger labels that clearly indicate workflow purpose
- Keep deliverable names URL-friendly (lowercase, hyphens, no spaces)
- Set realistic timeouts based on workflow complexity
- Include validation rules to ensure quality output
- Document any special requirements in the workflow description

## Troubleshooting

- **Multiple workflows match**: Add more specific labels to disambiguate
- **No workflow matches**: Ensure `site-monitor` label is present and check trigger labels
- **Validation failures**: Review min_word_count and required_sections settings
- **Timeout issues**: Increase processing timeout or simplify deliverables

## Integration

These workflows integrate with:
- `src/workflow_matcher.py` - Workflow discovery and matching
- `src/issue_processor.py` - Issue processing orchestration
- `src/deliverable_generator.py` - Document generation
- `main.py process-issues` - Command-line interface