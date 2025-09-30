# {{ deliverable_spec.title }}

**Issue**: #{{ issue_data.number }} - {{ issue_data.title }}  
**Generated**: {{ timestamp }}  
**Workflow**: {{ workflow_info.name }}  

## Executive Summary

This intelligence summary has been enhanced with AI-extracted structured content from issue #{{ issue_data.number }}.

### Issue Overview
- **Title**: {{ issue_data.title }}
- **Labels**: {{ issue_data.labels | join(", ") }}
- **Created**: {{ issue_data.created_at.strftime('%Y-%m-%d %H:%M UTC') }}
{% if issue_data.assignees -%}
- **Assignees**: {{ issue_data.assignees | join(", ") }}
{% endif %}

### Content Summary
{{ issue_data.body[:500] }}{% if issue_data.body|length > 500 %}...{% endif %}

## AI-Extracted Structured Content

{% if additional_context.extracted_content -%}
{% set extracted = additional_context.extracted_content -%}

### Content Analysis
- **Content Type**: {{ extracted.content_type | title }}
- **Urgency Level**: {{ extracted.urgency_level | title }}
- **Confidence Score**: {{ "%.2f" | format(extracted.confidence_score) }}
- **Key Topics**: {{ extracted.key_topics | join(", ") }}

### Extracted Entities ({{ extracted.entities | length }})
{% if extracted.entities -%}
| Name | Type | Confidence | Context |
|------|------|------------|---------|
{% for entity in extracted.entities -%}
| {{ entity.name }} | {{ entity.type | title }} | {{ "%.2f" | format(entity.confidence) }} | {{ entity.context or "N/A" }} |
{% endfor %}
{% else -%}
*No entities extracted from the content.*
{% endif %}

### Key Relationships ({{ extracted.relationships | length }})
{% if extracted.relationships -%}
{% for relationship in extracted.relationships -%}
- **{{ relationship.entity1 }}** {{ relationship.relationship }} **{{ relationship.entity2 }}** (Confidence: {{ "%.2f" | format(relationship.confidence) }})
  {% if relationship.context -%}
  - Context: {{ relationship.context }}
  {% endif %}
{% endfor %}
{% else -%}
*No relationships identified in the content.*
{% endif %}

### Intelligence Indicators ({{ extracted.indicators | length }})
{% if extracted.indicators -%}
| Type | Value | Confidence | Description |
|------|-------|------------|-------------|
{% for indicator in extracted.indicators -%}
| {{ indicator.type }} | `{{ indicator.value }}` | {{ "%.2f" | format(indicator.confidence) }} | {{ indicator.description or "N/A" }} |
{% endfor %}
{% else -%}
*No intelligence indicators detected.*
{% endif %}

### Timeline Events ({{ extracted.events | length }})
{% if extracted.events -%}
{% for event in extracted.events -%}
- **{{ event.description }}**
  {% if event.timestamp -%}
  - Time: {{ event.timestamp }}
  {% endif %}
  {% if event.entities_involved -%}
  - Entities: {{ event.entities_involved | join(", ") }}
  {% endif %}
  - Confidence: {{ "%.2f" | format(event.confidence) }}
{% endfor %}
{% else -%}
*No timeline events extracted.*
{% endif %}

## Intelligence Assessment

### Summary of Findings
Based on the AI-extracted content analysis:

- **{{ extracted.entities | length }}** entities were identified with an average confidence of {{ "%.2f" | format((extracted.entities | map(attribute='confidence') | sum) / (extracted.entities | length)) if extracted.entities else "N/A" }}
- **{{ extracted.relationships | length }}** relationships were mapped between entities
- **{{ extracted.indicators | length }}** intelligence indicators were detected
- Content classified as **{{ extracted.content_type | title }}** with **{{ extracted.urgency_level | title }}** urgency

### Key Intelligence Points
{% for topic in extracted.key_topics -%}
- {{ topic | title }}
{% endfor %}

{% else -%}

## Content Analysis

*This analysis was generated without AI content extraction. The structured content extraction feature may be disabled or unavailable.*

### Manual Analysis Required
Please review the issue content manually for:
- Key entities (domains, IPs, organizations, persons)
- Relationships between identified entities  
- Intelligence indicators (IOCs, TTPs, behaviors)
- Timeline of events
- Critical intelligence points

{% endif %}

## Recommendations

{% if additional_context.extracted_content -%}
{% set extracted = additional_context.extracted_content -%}
Based on the AI-extracted analysis:

1. **Priority Assessment**: {{ extracted.urgency_level | title }} priority based on content analysis
2. **Entity Investigation**: Focus investigation on the {{ extracted.entities | length }} identified entities
{% if extracted.indicators -%}
3. **Indicator Monitoring**: Monitor {{ extracted.indicators | length }} detected intelligence indicators
{% endif %}
{% if extracted.relationships -%}
4. **Relationship Analysis**: Investigate {{ extracted.relationships | length }} mapped relationships for additional intelligence
{% endif %}

{% else -%}
1. **Manual Review Required**: Conduct thorough manual analysis of issue content
2. **Entity Identification**: Identify and catalog all relevant entities mentioned
3. **Relationship Mapping**: Map relationships between identified entities
4. **Indicator Extraction**: Extract all possible intelligence indicators
{% endif %}

## Next Steps

- [ ] Validate extracted entities and relationships
- [ ] Cross-reference indicators with existing intelligence
- [ ] Conduct deeper analysis on high-confidence findings
- [ ] Update relevant intelligence databases
- [ ] Consider workflow assignment to appropriate specialists

---

*Generated by Speculum Principum AI-Enhanced Intelligence Analysis*  
*Extraction Timestamp: {% if additional_context.extracted_content %}{{ additional_context.extracted_content.extraction_timestamp }}{% else %}N/A{% endif %}*