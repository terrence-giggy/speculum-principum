---
name: "Base Deliverable Template"
description: "Foundation template for all deliverable documents with standard structure"
type: "base"
version: "1.0"
author: "System"
variables:
  issue.number: "GitHub issue number"
  issue.title: "GitHub issue title"
  issue.body: "GitHub issue description"
  issue.labels: "List of GitHub issue labels"
  issue.author: "GitHub issue author"
  issue.created_at: "Issue creation timestamp"
  issue.url: "GitHub issue URL"
  deliverable.name: "Deliverable identifier"
  deliverable.title: "Deliverable display title"
  deliverable.description: "Deliverable description"
  deliverable.type: "Deliverable type"
  deliverable.format: "Output format"
  workflow.name: "Workflow name"
  workflow.description: "Workflow description"
  timestamp: "Generation timestamp"
  processing_id: "Unique processing identifier"
sections:
  - "header"
  - "overview"
  - "context"
  - "content"
  - "summary"
  - "footer"
---

{% section header %}
# {{ deliverable.title }}

**Issue**: #{{ issue.number }} - {{ issue.title }}  
**Generated**: {{ timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') }}  
**Workflow**: {{ workflow.name }}  
**Processing ID**: {{ processing_id }}

---
{% endsection %}

{% section overview %}
## Overview

{{ deliverable.description }}

{% if workflow.description %}
### Workflow Context

{{ workflow.description }}
{% endif %}

### Document Information

- **Type**: {{ deliverable.type }}
- **Format**: {{ deliverable.format }}
- **Generated**: {{ date }} {{ time }}
{% endsection %}

{% section context %}
## Issue Context

### Issue Details

- **Number**: #{{ issue.number }}
- **Title**: {{ issue.title }}
- **Author**: {{ issue.author or 'Unknown' }}
- **Created**: {{ issue.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if issue.created_at else 'Unknown' }}
- **URL**: {{ issue.url or 'Not available' }}

{% if issue.labels %}
### Labels

{% for label in issue.labels %}
- `{{ label }}`
{% endfor %}
{% endif %}

### Issue Description

{{ issue.body or 'No description provided.' }}
{% endsection %}

{% section content %}
## Content

*This section contains the main deliverable content. It should be overridden by specific templates or provided through sections.*

{% if sections.main_content %}
{{ sections.main_content }}
{% else %}
### Analysis Required

This deliverable requires detailed analysis based on:

1. **Issue Requirements**: Understanding the specific needs outlined in the issue
2. **Workflow Specifications**: Following the defined workflow process
3. **Context Analysis**: Considering the broader project context
4. **Deliverable Goals**: Meeting the specific objectives of this deliverable type

*[Content generation would be handled by AI integration or manual input]*
{% endif %}
{% endsection %}

{% section summary %}
## Summary

{% if sections.summary %}
{{ sections.summary }}
{% else %}
### Key Points

- Deliverable generated successfully for issue #{{ issue.number }}
- Workflow: {{ workflow.name }}
- Type: {{ deliverable.type }}
- Format: {{ deliverable.format }}

### Next Steps

1. Review generated content for accuracy and completeness
2. Validate against issue requirements
3. Update or enhance content as needed
4. Mark deliverable as complete when satisfied

{% if deliverable.required %}
**Note**: This is a required deliverable for the workflow.
{% else %}
**Note**: This is an optional deliverable for the workflow.
{% endif %}
{% endif %}
{% endsection %}

{% section footer %}
---

## Document Metadata

| Field | Value |
|-------|-------|
| Generated | {{ timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') }} |
| Issue | #{{ issue.number }} |
| Workflow | {{ workflow.name }} |
| Deliverable | {{ deliverable.name }} |
| Version | {{ deliverable.metadata.version or '1.0' }} |
| Processing ID | {{ processing_id }} |

{% if deliverable.metadata.tags %}
### Tags

{% for tag in deliverable.metadata.tags %}
- {{ tag }}
{% endfor %}
{% endif %}

*Generated automatically by Speculum Principum Issue Processor*
{% endsection %}