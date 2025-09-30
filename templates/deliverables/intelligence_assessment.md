# Intelligence Assessment Report

**Issue #{{ issue.number }}**: {{ issue.title }}  
**Generated**: {{ current_date }}  
**Analyst**: AI Intelligence Analyst  
**Classification**: UNCLASSIFIED//FOR OFFICIAL USE ONLY

---

## EXECUTIVE SUMMARY

{% if additional_context.specialist_analysis %}
{{ additional_context.specialist_analysis.summary }}

**Key Assessment**: {{ additional_context.specialist_analysis.risk_assessment.threat_level }} threat level with {{ additional_context.specialist_analysis.risk_assessment.impact_level }} potential impact.
{% else %}
Intelligence analysis requested for issue {{ issue.number }}: {{ issue.title }}
{% endif %}

---

## THREAT ASSESSMENT

{% if additional_context.specialist_analysis and additional_context.specialist_analysis.risk_assessment %}
### Threat Level: {{ additional_context.specialist_analysis.risk_assessment.threat_level }}

{{ additional_context.specialist_analysis.risk_assessment.threat_assessment }}

### Impact Level: {{ additional_context.specialist_analysis.risk_assessment.impact_level }}

{{ additional_context.specialist_analysis.risk_assessment.risk_evaluation }}

{% if additional_context.specialist_analysis.risk_assessment.strategic_implications %}
### Strategic Implications

{{ additional_context.specialist_analysis.risk_assessment.strategic_implications }}
{% endif %}
{% else %}
**Content for Analysis:**
```
{{ issue.body }}
```
{% endif %}

---

## KEY FINDINGS

{% if additional_context.specialist_analysis and additional_context.specialist_analysis.key_findings %}
{% for finding in additional_context.specialist_analysis.key_findings %}
- {{ finding }}
{% endfor %}
{% else %}
- Analysis pending - requires intelligence specialist review
- Initial assessment based on issue content and labels
{% endif %}

---

## RECOMMENDATIONS

{% if additional_context.specialist_analysis and additional_context.specialist_analysis.recommendations %}
### Immediate Actions
{% for recommendation in additional_context.specialist_analysis.recommendations %}
- {{ recommendation }}
{% endfor %}
{% else %}
- Conduct detailed threat analysis
- Review intelligence sources and collection requirements
- Coordinate with relevant stakeholders for strategic response
{% endif %}

---

## INTELLIGENCE DETAILS

### Extracted Entities
{% if additional_context.extracted_content and additional_context.extracted_content.entities %}
| Entity | Type | Confidence |
|--------|------|------------|
{% for entity in additional_context.extracted_content.entities %}
| {{ entity.name }} | {{ entity.type }} | {{ "%.2f"|format(entity.confidence) }} |
{% endfor %}
{% else %}
No structured entities extracted from source material.
{% endif %}

### Identified Relationships
{% if additional_context.extracted_content and additional_context.extracted_content.relationships %}
{% for relationship in additional_context.extracted_content.relationships %}
- **{{ relationship.source }}** --{{ relationship.type }}--> **{{ relationship.target }}** (Confidence: {{ "%.2f"|format(relationship.confidence) }})
{% endfor %}
{% else %}
No structured relationships identified.
{% endif %}

### Timeline and Events
{% if additional_context.extracted_content and additional_context.extracted_content.events %}
{% for event in additional_context.extracted_content.events %}
- **{{ event.timestamp }}**: {{ event.description }} ({{ event.type }})
{% endfor %}
{% else %}
No timeline events extracted.
{% endif %}

### Technical Indicators
{% if additional_context.extracted_content and additional_context.extracted_content.indicators %}
| Indicator | Type | Confidence |
|-----------|------|------------|
{% for indicator in additional_context.extracted_content.indicators %}
| `{{ indicator.value }}` | {{ indicator.type }} | {{ "%.2f"|format(indicator.confidence) }} |
{% endfor %}
{% else %}
No technical indicators identified.
{% endif %}

---

## CONFIDENCE ASSESSMENT

{% if additional_context.specialist_analysis %}
**Analysis Confidence**: {{ "%.0f"|format(additional_context.specialist_analysis.confidence_score * 100) }}%

**Methodology**: {% if additional_context.specialist_analysis.specialist_notes.analysis_type == 'ai_powered' %}AI-Enhanced Analysis{% else %}Rule-Based Analysis{% endif %}

{% if additional_context.specialist_analysis.specialist_notes.analysis_type == 'ai_powered' %}
**AI Model**: {{ additional_context.specialist_analysis.specialist_notes.model_used }}
{% endif %}

{% if additional_context.specialist_analysis.processing_time_seconds %}
**Processing Time**: {{ "%.2f"|format(additional_context.specialist_analysis.processing_time_seconds) }} seconds
{% endif %}
{% else %}
**Analysis Confidence**: Preliminary assessment pending specialist review
{% endif %}

---

## COLLECTION REQUIREMENTS

- [ ] Validate threat actor attribution through additional sources
- [ ] Confirm technical indicators through threat intelligence feeds  
- [ ] Assess broader campaign context and related activities
- [ ] Coordinate with cybersecurity teams for defensive measures

---

## DISTRIBUTION

- **Primary**: Issue stakeholders and assigned personnel
- **Secondary**: Security operations and threat intelligence teams  
- **Coordination**: Strategic planning and risk management

---

**Report Generated**: {{ current_date }}  
**Next Review**: As required based on threat development  
**Contact**: GitHub Issue #{{ issue.number }} for questions and updates

*This assessment is based on available information at time of generation. Confidence levels and recommendations may change as additional intelligence becomes available.*