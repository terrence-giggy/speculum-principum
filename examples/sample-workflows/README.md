# Sample Workflows

This directory contains example workflow definitions that demonstrate different use cases and features of the Issue Processor system. These workflows can be used as templates for creating your own custom workflows.

## Available Examples

### Basic Workflows
- **`simple-research.yaml`** - Basic research workflow for general questions
- **`quick-analysis.yaml`** - Fast-turnaround analysis for urgent issues
- **`documentation-review.yaml`** - Documentation review and improvement workflow

### Technical Workflows
- **`security-assessment.yaml`** - Comprehensive security analysis and threat modeling
- **`code-review.yaml`** - Code quality and architecture review
- **`performance-analysis.yaml`** - Performance evaluation and optimization recommendations

### Specialized Workflows
- **`compliance-audit.yaml`** - Compliance verification and audit workflow
- **`risk-assessment.yaml`** - Risk analysis and mitigation planning
- **`competitive-analysis.yaml`** - Market and competitive research workflow

### Advanced Examples
- **`multi-stage-research.yaml`** - Complex workflow with dependencies and stages
- **`conditional-workflow.yaml`** - Adaptive workflow based on issue characteristics
- **`integration-example.yaml`** - Workflow with external system integrations

## Usage Instructions

### 1. Copy and Customize
```bash
# Copy an example workflow
cp examples/sample-workflows/security-assessment.yaml docs/workflow/deliverables/my-security-workflow.yaml

# Edit the workflow to match your needs
nano docs/workflow/deliverables/my-security-workflow.yaml
```

### 2. Validate Your Workflow
```bash
# Check if your workflow is valid
python main.py validate-workflows --file docs/workflow/deliverables/my-security-workflow.yaml
```

### 3. Test the Workflow
```bash
# Test workflow matching
python main.py test-workflow-match --labels "security,web-application,site-monitor"

# Dry run with a test issue
python main.py process-issues --issue 123 --dry-run
```

## Customization Guidelines

### Modifying Trigger Labels
Update the `trigger_labels` section to match your organization's labeling conventions:

```yaml
trigger_labels:
  - "your-primary-label"
  - "your-secondary-label"
  - "specific-use-case"
```

### Adapting Output Structure
Customize the `output` section to match your preferred file organization:

```yaml
output:
  folder_structure: "reports/{date}/{issue_number}"
  file_naming: "{workflow_name}_{deliverable_name}.md"
  branch_naming: "analysis-{issue_number}"
```

### Customizing Deliverables
Modify the `deliverables` section to generate the documents you need:

```yaml
deliverables:
  - name: "executive_summary"
    template: "custom_summary.md"
    required: true
    description: "High-level overview for leadership"
```

## Contributing

If you create useful workflow examples, consider contributing them back to this collection:

1. Place your workflow in this directory
2. Update this README with a description
3. Submit a pull request

## Support

For questions about creating or customizing workflows:
- Review the [Workflow Creation Guide](../../docs/workflow-creation-guide.md)
- Check the [Issue Processor Documentation](../../docs/issue-processor.md)
- Open an issue for additional support