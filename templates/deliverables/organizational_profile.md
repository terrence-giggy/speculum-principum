# Organizational Profile Report

**Issue**: #{{ issue.number }} - {{ issue.title }}  
**Generated**: {{ timestamp }}  
**Specialist**: Target Profiler Agent  
**Confidence**: {{ analysis_result.confidence_score | round(2) }}

---

## Executive Summary

{{ ai_content.executive_summary | default("*AI-generated executive summary not available*") }}

### Key Organizations Identified
{% for org in analysis_result.entities_analyzed %}
- {{ org }}
{% endfor %}

### Critical Findings
{% for finding in analysis_result.key_findings %}
- {{ finding }}
{% endfor %}

---

## Organizational Structure

### Primary Organizations
{% if analysis_result.entities_analyzed %}
{% for organization in analysis_result.entities_analyzed[:5] %}
**{{ organization }}**
- Type: Organization/Entity
- Context: Identified in source intelligence
{% endfor %}
{% else %}
*No primary organizations explicitly identified*
{% endif %}

### Organizational Hierarchy
{{ ai_content.organizational_hierarchy | default("*Organizational hierarchy analysis not available - recommend further investigation*") }}

### Business Units and Divisions  
{{ ai_content.business_units | default("*Business unit structure requires additional analysis*") }}

---

## Key Personnel

### Executive Leadership
{{ ai_content.executive_leadership | default("*Executive leadership analysis not available*") }}

### Decision Makers and Influencers
{{ ai_content.decision_makers | default("*Decision maker identification requires further investigation*") }}

### Personnel Networks
{% if analysis_result.relationships_identified %}
{% for relationship in analysis_result.relationships_identified %}
- {{ relationship }}
{% endfor %}
{% else %}
*Personnel relationship mapping requires additional analysis*
{% endif %}

---

## Stakeholder Analysis

### Internal Stakeholders
{{ ai_content.internal_stakeholders | default("*Internal stakeholder analysis not available*") }}

### External Stakeholders  
{{ ai_content.external_stakeholders | default("*External stakeholder analysis not available*") }}

### Stakeholder Influence Mapping
{{ ai_content.stakeholder_influence | default("*Stakeholder influence analysis requires further investigation*") }}

---

## Business Intelligence

### Financial Analysis
{% if analysis_result.specialist_notes.financial_indicators %}
**Financial Indicators Identified:**
{% for indicator in analysis_result.specialist_notes.financial_indicators %}
- {{ indicator | title }}
{% endfor %}
{% else %}
*No significant financial indicators identified in available intelligence*
{% endif %}

### Market Position
{{ ai_content.market_position | default("*Market positioning analysis not available*") }}

### Competitive Landscape
{{ ai_content.competitive_analysis | default("*Competitive landscape analysis requires additional research*") }}

### Strategic Partnerships
{{ ai_content.strategic_partnerships | default("*Strategic partnership analysis not available*") }}

---

## Risk Assessment

{% if analysis_result.risk_assessment %}
### Organizational Risk Factors
**Risk Level**: {{ analysis_result.risk_assessment.organizational_risk | default("Unknown") | title }}

{{ ai_content.organizational_risks | default("*Organizational risk analysis not available*") }}

### Leadership Risks
**Risk Level**: {{ analysis_result.risk_assessment.leadership_risk | default("Unknown") | title }}

{{ ai_content.leadership_risks | default("*Leadership risk analysis not available*") }}

### Competitive Risks  
**Risk Level**: {{ analysis_result.risk_assessment.competitive_risk | default("Unknown") | title }}

{{ ai_content.competitive_risks | default("*Competitive risk analysis not available*") }}

{% else %}
### Risk Assessment
*Comprehensive risk assessment requires additional analysis with enhanced intelligence collection*
{% endif %}

---

## Strategic Recommendations

### Immediate Actions
{% for recommendation in analysis_result.recommendations[:3] %}
{{ loop.index }}. {{ recommendation }}
{% endfor %}

### Strategic Intelligence Collection
{{ ai_content.collection_recommendations | default("**Recommended Intelligence Gaps to Address:**
- Organizational chart and reporting relationships
- Financial performance and funding sources
- Key decision-making processes and authorities
- Strategic partnerships and vendor relationships
- Competitive positioning and market dynamics") }}

### Follow-up Analysis
{{ ai_content.followup_analysis | default("**Additional Analysis Recommended:**
- Deep dive into executive leadership backgrounds
- Financial analysis and business model assessment
- Competitive intelligence and market positioning
- Stakeholder influence and decision-making processes") }}

---

## Methodology and Confidence

### Analysis Approach
- **Specialist Type**: Target Profiler Agent
- **Analysis Method**: {{ analysis_result.specialist_notes.analysis_type | default("Pattern-based analysis") | title }}
- **Processing Time**: {{ analysis_result.processing_time_seconds | default("N/A") }} seconds
{% if analysis_result.specialist_notes.model_used %}
- **AI Model Used**: {{ analysis_result.specialist_notes.model_used }}
{% endif %}

### Confidence Assessment
- **Overall Confidence**: {{ (analysis_result.confidence_score * 100) | round(1) }}%
- **Stakeholder Count**: {{ analysis_result.specialist_notes.stakeholder_count | default(0) }}
- **Organizational Levels**: {{ analysis_result.specialist_notes.organizational_levels | default(1) }}

### Data Quality and Limitations
{% if analysis_result.confidence_score >= 0.8 %}
**High Confidence**: Analysis based on substantial organizational intelligence with clear indicators.
{% elif analysis_result.confidence_score >= 0.6 %}
**Medium Confidence**: Analysis contains reliable organizational indicators but may benefit from additional intelligence collection.
{% else %}
**Lower Confidence**: Analysis based on limited organizational intelligence. Additional research strongly recommended.
{% endif %}

---

## Technical Details

**Issue Labels**: {{ issue.labels | map(attribute='name') | join(', ') }}  
**Analysis ID**: {{ analysis_result.analysis_id }}  
**Generated**: {{ analysis_result.created_at.strftime('%Y-%m-%d %H:%M:%S') }} UTC  
**Status**: {{ analysis_result.status.value | title }}

### Source Intelligence Summary
**Title**: {{ issue.title }}  
**Content Length**: {{ issue.body | length }} characters  
**Key Terms Density**: {{ analysis_result.specialist_notes.organizations_found | default(0) }} organizations, {{ analysis_result.specialist_notes.personnel_found | default(0) }} personnel

---

*This organizational profile was generated by the Speculum Principum Target Profiler Agent. Classification and distribution should follow organizational security policies.*