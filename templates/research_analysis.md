---
name: "Research Analysis Template"
description: "Specialized template for research analysis deliverables"
type: "document"
extends: "base_deliverable"
version: "1.0"
author: "Research Team"
variables:
  research.scope: "Research scope definition"
  research.methodology: "Research methodology description"
  research.timeline: "Research timeline"
  research.questions: "Primary research questions"
  research.objectives: "Research objectives"
  sources.primary: "Primary source materials"
  sources.secondary: "Secondary source materials"
  findings.summary: "Summary of key findings"
  findings.detailed: "Detailed findings"
  recommendations.immediate: "Immediate action recommendations"
  recommendations.longterm: "Long-term recommendations"
sections:
  - "executive_summary"
  - "research_scope"
  - "methodology"
  - "timeline"
  - "literature_review"
  - "findings"
  - "analysis"
  - "recommendations"
  - "limitations"
  - "next_steps"
  - "references"
---

{% section content %}
## Research Analysis

### Executive Summary

{% if sections.executive_summary %}
{{ sections.executive_summary }}
{% else %}
This research analysis addresses the topic outlined in issue #{{ issue.number }}: "{{ issue.title }}". The analysis provides a comprehensive examination of the subject matter, including background research, current state assessment, and actionable recommendations.

**Key Findings:**
- [To be populated based on research results]

**Primary Recommendations:**
- [To be populated based on analysis]

**Timeline:** {{ research.timeline or 'To be determined' }}
{% endif %}

### Research Scope and Objectives

{% if sections.research_scope %}
{{ sections.research_scope }}
{% else %}
#### Primary Research Questions

Based on the issue description and requirements, this research addresses:

1. **Context Understanding**: What is the current state of the topic area?
2. **Problem Analysis**: What specific challenges or opportunities exist?
3. **Solution Investigation**: What approaches or solutions are available?
4. **Impact Assessment**: What are the potential outcomes of different approaches?

#### Research Objectives

- Provide comprehensive background analysis
- Identify key stakeholders and considerations
- Evaluate available options and approaches
- Develop actionable recommendations
- Establish framework for decision-making

#### Scope Boundaries

**In Scope:**
- [Define what will be researched]

**Out of Scope:**
- [Define what will not be covered]

**Assumptions:**
- [List key assumptions made during research]
{% endif %}

### Methodology

{% if sections.methodology %}
{{ sections.methodology }}
{% else %}
#### Research Approach

This analysis follows a structured methodology:

1. **Literature Review**: Comprehensive review of existing knowledge and documentation
2. **Stakeholder Analysis**: Identification and consideration of key stakeholders
3. **Current State Assessment**: Evaluation of present conditions and constraints
4. **Gap Analysis**: Identification of knowledge or capability gaps
5. **Option Evaluation**: Assessment of potential approaches or solutions
6. **Recommendation Development**: Formulation of actionable next steps

#### Data Sources

**Primary Sources:**
- Issue description and comments
- Direct stakeholder input
- System documentation
- Performance data

**Secondary Sources:**
- Industry best practices
- Academic research
- Case studies
- Technical documentation

#### Analysis Framework

The research utilizes the following analytical frameworks:
- [Specify frameworks used, e.g., SWOT, stakeholder analysis, etc.]
{% endif %}

### Timeline and Milestones

{% if sections.timeline %}
{{ sections.timeline }}
{% else %}
#### Research Timeline

| Phase | Description | Duration | Deliverables |
|-------|-------------|----------|--------------|
| Phase 1 | Background Research | Days 1-2 | Literature review, context analysis |
| Phase 2 | Data Collection | Days 3-4 | Stakeholder input, current state assessment |
| Phase 3 | Analysis | Days 5-6 | Gap analysis, option evaluation |
| Phase 4 | Synthesis | Days 7-8 | Recommendations, documentation |

#### Key Milestones

- **Background Complete**: Comprehensive understanding of topic area
- **Data Collected**: All relevant information gathered
- **Analysis Complete**: Thorough evaluation of options
- **Recommendations Ready**: Actionable next steps defined
{% endif %}

### Literature Review and Background

{% if sections.literature_review %}
{{ sections.literature_review }}
{% else %}
#### Existing Knowledge

*[This section would contain a comprehensive review of existing documentation, research, and knowledge related to the topic]*

#### Current State Analysis

*[Analysis of the present situation, including strengths, weaknesses, opportunities, and constraints]*

#### Stakeholder Perspectives

*[Summary of relevant stakeholder viewpoints and considerations]*

#### Industry Context

*[Relevant industry trends, best practices, and benchmarks]*
{% endif %}

### Key Findings

{% if sections.findings %}
{{ sections.findings }}
{% else %}
#### Primary Findings

*[Detailed presentation of research findings organized by theme or importance]*

1. **Finding 1**: [Description and supporting evidence]
2. **Finding 2**: [Description and supporting evidence]
3. **Finding 3**: [Description and supporting evidence]

#### Supporting Evidence

*[Additional data, quotes, or documentation that supports the findings]*

#### Implications

*[Analysis of what the findings mean for the issue at hand]*
{% endif %}

### Analysis and Interpretation

{% if sections.analysis %}
{{ sections.analysis }}
{% else %}
#### Critical Analysis

*[Deep analysis of the findings, including patterns, relationships, and insights]*

#### Risk Assessment

**Identified Risks:**
- [Risk 1]: [Description and mitigation]
- [Risk 2]: [Description and mitigation]

**Risk Mitigation Strategies:**
- [Strategy 1]
- [Strategy 2]

#### Opportunity Analysis

**Key Opportunities:**
- [Opportunity 1]: [Description and potential impact]
- [Opportunity 2]: [Description and potential impact]

#### Trade-offs and Considerations

*[Analysis of trade-offs between different approaches or decisions]*
{% endif %}

### Recommendations

{% if sections.recommendations %}
{{ sections.recommendations }}
{% else %}
#### Immediate Actions (Next 30 days)

1. **[Action 1]**: [Description, rationale, and expected outcome]
2. **[Action 2]**: [Description, rationale, and expected outcome]
3. **[Action 3]**: [Description, rationale, and expected outcome]

#### Short-term Actions (1-3 months)

1. **[Action 1]**: [Description and strategic importance]
2. **[Action 2]**: [Description and strategic importance]

#### Long-term Strategic Actions (3+ months)

1. **[Strategy 1]**: [Description and long-term impact]
2. **[Strategy 2]**: [Description and long-term impact]

#### Implementation Priorities

| Priority | Action | Timeline | Resources Required |
|----------|--------|----------|-------------------|
| High | [Action] | [Timeline] | [Resources] |
| Medium | [Action] | [Timeline] | [Resources] |
| Low | [Action] | [Timeline] | [Resources] |
{% endif %}

### Limitations and Considerations

{% if sections.limitations %}
{{ sections.limitations }}
{% else %}
#### Research Limitations

- **Data Availability**: [Description of any data limitations]
- **Time Constraints**: [Impact of timeline on depth of analysis]
- **Scope Boundaries**: [Areas not covered and why]
- **Assumption Dependencies**: [Key assumptions that may affect conclusions]

#### Validity Considerations

- **Source Reliability**: [Assessment of source quality and reliability]
- **Methodology Constraints**: [Limitations of chosen research approach]
- **Bias Potential**: [Potential sources of bias and mitigation efforts]

#### Future Research Needs

*[Areas where additional research would be valuable]*
{% endif %}

### Next Steps and Follow-up

{% if sections.next_steps %}
{{ sections.next_steps }}
{% else %}
#### Immediate Next Steps

1. **Review and Validation**: Stakeholder review of findings and recommendations
2. **Decision Making**: Select preferred approach based on analysis
3. **Planning**: Develop detailed implementation plan
4. **Resource Allocation**: Identify and secure necessary resources

#### Success Metrics

- [Metric 1]: [Description and measurement approach]
- [Metric 2]: [Description and measurement approach]
- [Metric 3]: [Description and measurement approach]

#### Follow-up Timeline

| Timeframe | Activity | Responsible Party |
|-----------|----------|-------------------|
| 1 week | Review completion | [Stakeholder] |
| 2 weeks | Decision finalization | [Decision maker] |
| 1 month | Implementation start | [Implementation team] |
| 3 months | Progress review | [Review team] |

#### Monitoring and Evaluation

*[Framework for ongoing monitoring of implementation and outcomes]*
{% endif %}

### References and Sources

{% if sections.references %}
{{ sections.references }}
{% else %}
#### Primary Sources

1. GitHub Issue #{{ issue.number }}: {{ issue.title }}
   - URL: {{ issue.url }}
   - Created: {{ issue.created_at.strftime('%Y-%m-%d') if issue.created_at else 'Unknown' }}

{% if sources.primary %}
{% for source in sources.primary %}
2. {{ source }}
{% endfor %}
{% endif %}

#### Secondary Sources

{% if sources.secondary %}
{% for source in sources.secondary %}
- {{ source }}
{% endfor %}
{% else %}
*[Additional sources would be listed here as they are identified and consulted]*
{% endif %}

#### Additional Resources

*[Links to related documentation, tools, or resources that may be useful for implementation]*
{% endif %}
{% endsection %}