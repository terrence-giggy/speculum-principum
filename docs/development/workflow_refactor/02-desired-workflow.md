# Desired Workflow Design

## Vision Statement

A fully automated, AI-enhanced pipeline that discovers content, intelligently assigns specialist workflows, generates comprehensive guidance, and seamlessly hands off to Copilot for document creation—all without manual intervention.

## Target Workflow Architecture

### Unified Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AUTOMATED PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────┘

Stage 1: DISCOVERY                    Labels: [site-monitor]
┌─────────────────────────────────────────────────────────────┐
│  Site Monitoring (Operations -1)                            │
│  • Google Search API discovers new content                  │
│  • Content deduplication (SHA256 hashing)                   │
│  • Create issue with site-monitor label                     │
│  • Trigger: Daily schedule OR manual dispatch               │
└────────────────────┬────────────────────────────────────────┘
                     │ Automatic trigger via label event
                     ▼
Stage 2: ANALYSIS                     Labels: [site-monitor, analyzing]
┌─────────────────────────────────────────────────────────────┐
│  AI Workflow Assignment (Operations -2)                     │
│  • Detect new site-monitor issues                           │
│  • GitHub Models API semantic analysis                      │
│  • Multi-factor confidence scoring                          │
│  • Assign specialist labels                                 │
│  • Remove site-monitor, add specialist label                │
│  • Trigger: Label event (site-monitor added)                │
└────────────────────┬────────────────────────────────────────┘
                     │ Automatic trigger via label assignment
                     ▼
Stage 3: PREPARATION                  Labels: [specialist-type, processing]
┌─────────────────────────────────────────────────────────────┐
│  Unified Issue Processing (NEW Operations -3)               │
│  • Detect specialist-labeled issues                         │
│  • Generate specialist-specific guidance/prompts            │
│  • Create structured issue body with requirements           │
│  • Assign to github-copilot[bot]                           │
│  • Add copilot-assigned label                              │
│  • Remove processing label                                  │
│  • Trigger: Label event (specialist label added)            │
└────────────────────┬────────────────────────────────────────┘
                     │ Issue assigned to Copilot
                     ▼
Stage 4: EXECUTION                    Labels: [copilot-assigned]
┌─────────────────────────────────────────────────────────────┐
│  Copilot Processing (Copilot handles)                       │
│  • Read specialist guidance from issue body                 │
│  • Generate required deliverables                           │
│  • Create feature branch                                    │
│  • Commit documents                                         │
│  • Create PR with deliverables                             │
│  • Update issue with PR link                               │
└────────────────────┬────────────────────────────────────────┘
                     │ PR created
                     ▼
Stage 5: COMPLETION                   Labels: [completed]
┌─────────────────────────────────────────────────────────────┐
│  Automatic Cleanup (NEW)                                    │
│  • Detect PR merge event                                    │
│  • Remove all workflow labels                               │
│  • Add completed label                                      │
│  • Close original issue                                     │
│  • Archive in processed state                               │
└─────────────────────────────────────────────────────────────┘
```

## Label State Machine

### State Transitions

```
[Initial] → [site-monitor] → [analyzing] → [specialist-type] → 
[processing] → [copilot-assigned] → [completed]
```

### Label Definitions

| Label | Stage | Purpose | Auto-Added | Auto-Removed |
|-------|-------|---------|------------|--------------|
| `site-monitor` | Discovery | Marks new discoveries | ✅ Monitoring | ✅ After analysis |
| `analyzing` | Analysis | Temp state during AI analysis | ✅ Workflow assignment | ✅ After assignment |
| `intelligence-analyst` | Assignment | Specialist type assigned | ✅ AI assignment | ✅ After completion |
| `osint-researcher` | Assignment | Specialist type assigned | ✅ AI assignment | ✅ After completion |
| `target-profiler` | Assignment | Specialist type assigned | ✅ AI assignment | ✅ After completion |
| `processing` | Preparation | Temp state during guidance gen | ✅ Issue processor | ✅ After Copilot assignment |
| `copilot-assigned` | Execution | Ready for Copilot processing | ✅ Issue processor | ✅ After completion |
| `urgent` | Modifier | Priority processing | ❌ Manual only | ❌ Manual |
| `completed` | Final | Processing complete | ✅ PR merge event | ❌ Never |

### Label Lifecycle Rules

1. **Mutual Exclusivity**: Only one stage label at a time (site-monitor OR specialist OR copilot-assigned)
2. **Temporary Labels**: `analyzing` and `processing` are short-lived, removed after stage completion
3. **Specialist Persistence**: Specialist labels persist until completion for reference
4. **Priority Override**: `urgent` label bypasses normal flow for immediate processing

## Unified Processing Command

### New Command: `process-pipeline`

Replaces both `process-issues` and `process-copilot-issues` with intelligent stage detection.

#### Command Signature
```bash
python main.py process-pipeline \
  --config config.yaml \
  --stage [auto|analysis|preparation|all] \
  --batch-size 10 \
  --priority [normal|urgent] \
  --dry-run
```

#### Stage Detection Logic

```python
def determine_processing_stage(issue):
    """Intelligently determine what stage to process"""
    
    labels = [label.name for label in issue.labels]
    
    # Stage 2: Analysis (site-monitor → specialist)
    if 'site-monitor' in labels and not any(specialist in labels):
        return 'analysis'
    
    # Stage 3: Preparation (specialist → copilot)
    if any(specialist in labels) and 'copilot-assigned' not in labels:
        return 'preparation'
    
    # Already processed
    if 'copilot-assigned' in labels or 'completed' in labels:
        return 'skip'
    
    return 'unknown'
```

#### Processing Logic by Stage

**Stage 2: Analysis**
```python
def process_analysis_stage(issue):
    # Add analyzing label
    issue.add_to_labels('analyzing')
    
    # AI-powered workflow assignment
    assignment = ai_workflow_agent.analyze_content(issue)
    
    # Assign specialist labels
    for specialist in assignment.specialists:
        issue.add_to_labels(specialist.label)
    
    # Remove discovery labels
    issue.remove_from_labels('site-monitor', 'analyzing')
    
    # Trigger next stage via label event
    return assignment
```

**Stage 3: Preparation**
```python
def process_preparation_stage(issue):
    # Add processing label
    issue.add_to_labels('processing')
    
    # Get specialist configuration
    specialists = specialist_config.find_matching_specialists(issue)
    
    # Generate specialist guidance
    guidance = generate_specialist_guidance(issue, specialists)
    
    # Update issue body with guidance
    issue.edit(body=f"{issue.body}\n\n{guidance}")
    
    # Assign to Copilot
    issue.add_to_assignees('github-copilot[bot]')
    issue.add_to_labels('copilot-assigned')
    
    # Remove temporary label
    issue.remove_from_labels('processing')
    
    return guidance
```

## GitHub Actions Integration

### Workflow: `ops-unified-pipeline.yml`

```yaml
name: Operations - Unified Pipeline

on:
  issues:
    types: [opened, labeled, assigned]
  
  schedule:
    - cron: '0 */2 * * *'  # Every 2 hours
  
  workflow_dispatch:
    inputs:
      stage:
        description: 'Pipeline stage to run'
        type: choice
        options: ['auto', 'analysis', 'preparation', 'all']
        default: 'auto'

jobs:
  detect-stage:
    name: Detect Processing Stage
    runs-on: ubuntu-latest
    outputs:
      stage: ${{ steps.detect.outputs.stage }}
      should_process: ${{ steps.detect.outputs.should_process }}
    
    steps:
      - name: Detect required stage
        id: detect
        run: |
          # Determine if this issue needs processing
          # Output stage (analysis/preparation/skip)
  
  process-analysis:
    name: AI Workflow Assignment
    needs: detect-stage
    if: needs.detect-stage.outputs.stage == 'analysis'
    runs-on: ubuntu-latest
    
    steps:
      - name: Run analysis stage
        run: |
          python main.py process-pipeline \
            --stage analysis \
            --issue ${{ github.event.issue.number }}
  
  process-preparation:
    name: Specialist Guidance Generation
    needs: detect-stage
    if: needs.detect-stage.outputs.stage == 'preparation'
    runs-on: ubuntu-latest
    
    steps:
      - name: Run preparation stage
        run: |
          python main.py process-pipeline \
            --stage preparation \
            --issue ${{ github.event.issue.number }}
```

## Specialist Guidance Structure

### Issue Body Template (After Preparation)

```markdown
# [Original Issue Title]

## 🎯 Target Information
[Original discovery information]

---

## 🤖 Copilot Processing Instructions

**Assigned Specialists**: Intelligence Analyst, OSINT Researcher

### Intelligence Analyst Requirements

**Deliverable**: `docs/intelligence/[target-name]-intelligence-report.md`

**Analysis Framework**:
1. Executive Summary
2. Threat Assessment
3. Attribution Analysis
4. Recommendations

**Content Requirements**:
- Analyze provided source material for intelligence indicators
- Cross-reference with known threat patterns
- Assess credibility and reliability of information
- Provide actionable intelligence recommendations

**Template**: Use `templates/specialists/intelligence-analyst/report.md`

---

### OSINT Researcher Requirements

**Deliverable**: `docs/osint/[target-name]-osint-profile.md`

**Investigation Framework**:
1. Digital Footprint Analysis
2. Social Media Presence
3. Infrastructure Mapping
4. Timeline Construction

**Data Points Required**:
- Domain registration details
- Social media accounts
- Public records
- Technical infrastructure

**Template**: Use `templates/specialists/osint-researcher/profile.md`

---

## 📋 Checklist

- [ ] Generate intelligence report using analyst framework
- [ ] Create OSINT profile with required data points
- [ ] Create feature branch: `specialist/multi/issue-[N]`
- [ ] Commit deliverables to branch
- [ ] Create PR linking to this issue
- [ ] Update this issue with PR link

---

*This issue is ready for Copilot processing. The specialist guidance above provides requirements and templates.*
```

## Backward Compatibility

### Deprecated Commands (Transition Period)

During migration, old commands will still work but show warnings:

```bash
$ python main.py process-issues --config config.yaml

⚠️  WARNING: 'process-issues' is deprecated and will be removed in v2.0
   Use 'process-pipeline --stage preparation' instead
   
   This command will continue to work but may not include latest features.
   
   Migration guide: docs/development/workflow-refactor/05-migration-strategy.md

[Continues with old behavior...]
```

### Gradual Migration Path

1. **Week 1-2**: Deploy `process-pipeline` alongside old commands
2. **Week 3-4**: Update GitHub Actions to use new command
3. **Week 5-6**: Add deprecation warnings to old commands
4. **Week 7-8**: Monitor usage, assist with migrations
5. **Week 9+**: Remove old commands, full cutover

## Success Metrics

### Pipeline Efficiency
- **End-to-End Time**: < 15 minutes from discovery to Copilot assignment
- **Manual Interventions**: 0 (fully automated)
- **Label Accuracy**: > 95% correct specialist assignments

### System Health
- **Pipeline Completion Rate**: > 90% of issues reach Copilot
- **Error Recovery**: Automatic retry on transient failures
- **Cost per Issue**: < $0.10 in API costs

### User Experience
- **Command Clarity**: Single entry point for all processing
- **Label Understanding**: Clear state transitions visible to users
- **Documentation Coverage**: 100% of workflow states documented

---

**Next**: See `03-technical-architecture.md` for implementation details
