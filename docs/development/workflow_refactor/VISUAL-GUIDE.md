# Workflow Transformation - Visual Guide

## Current State vs. Desired State

### BEFORE: Fragmented Three-Stage Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                   STAGE 1: SITE MONITORING                          │
│  Command: python main.py monitor --config config.yaml              │
│  Workflow: ops-site-monitoring.yml                                  │
│  Output: Issue with [site-monitor] label                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ ⚠️ MANUAL TRIGGER REQUIRED
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 STAGE 2: WORKFLOW ASSIGNMENT                        │
│  Command: python main.py assign-workflows --config config.yaml     │
│  Workflow: ops-workflow-assignment.yml (manual/scheduled)           │
│  Process:                                                           │
│    • Find issues with [site-monitor]                               │
│    • GitHub Models API semantic analysis                           │
│    • Add specialist labels (intelligence-analyst, etc.)            │
│    ⚠️ Does NOT remove [site-monitor] label                         │
│    ⚠️ Does NOT trigger next stage                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ ⚠️ MANUAL TRIGGER REQUIRED
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STAGE 3A: ISSUE PROCESSING (Option 1)                  │
│  Command: python main.py process-issues --config config.yaml       │
│  Workflow: ops-issue-processing-pr.yml                              │
│  Process:                                                           │
│    • Find issues with [site-monitor]                               │
│    • Label-based workflow matching (NO AI)                         │
│    • Generate deliverables directly                                │
│    • Create PR with documents                                      │
│    ⚠️ Does NOT assign to Copilot                                   │
│    ⚠️ Does NOT remove [site-monitor]                               │
└─────────────────────────────────────────────────────────────────────┘

         OR (User must choose which path!)

┌─────────────────────────────────────────────────────────────────────┐
│           STAGE 3B: COPILOT PROCESSING (Option 2)                   │
│  Command: python main.py process-copilot-issues --config config.yaml│
│  Workflow: ops-copilot-auto-process.yml                             │
│  Process:                                                           │
│    • Find issues ALREADY assigned to github-copilot[bot]           │
│    ⚠️ Requires MANUAL Copilot assignment first!                    │
│    • Validate specialist labels                                    │
│    • Generate specialist guidance                                  │
│    • Update issue body with instructions                           │
│    • Copilot processes separately                                  │
└─────────────────────────────────────────────────────────────────────┘

🚨 PROBLEMS:
   1. No automatic progression between stages
   2. Labels accumulate, never removed
   3. Two different stage-3 paths with different outcomes
   4. User confusion: "Which command do I use?"
   5. Manual Copilot assignment required
   6. No end-to-end automation
```

### AFTER: Unified Automated Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                   STAGE 1: SITE MONITORING                          │
│  Command: python main.py monitor --config config.yaml              │
│  Workflow: ops-site-monitoring.yml                                  │
│  Output: Issue with [site-monitor] label                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ ✅ AUTO-TRIGGERED by label event
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 STAGE 2: AI ANALYSIS (Unified)                      │
│  Command: python main.py process-pipeline --stage auto             │
│  Workflow: ops-unified-pipeline.yml (auto on site-monitor label)    │
│  Process:                                                           │
│    • Detect stage = 'analysis' (has site-monitor label)            │
│    • Add [analyzing] label (temp visibility)                       │
│    • GitHub Models API semantic analysis                           │
│    • Assign specialist labels                                      │
│    • Remove [site-monitor, analyzing] ✅                           │
│    • Triggers next stage via label event ✅                        │
│  Labels: [site-monitor] → [analyzing] → [specialist-type]         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ ✅ AUTO-TRIGGERED by specialist label
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STAGE 3: PREPARATION (Unified)                         │
│  Command: python main.py process-pipeline --stage auto             │
│  Workflow: ops-unified-pipeline.yml (auto on specialist label)      │
│  Process:                                                           │
│    • Detect stage = 'preparation' (has specialist label)           │
│    • Add [processing] label (temp visibility)                      │
│    • Find matching specialists via config                          │
│    • Generate comprehensive guidance for Copilot                   │
│    • Update issue body with structured instructions               │
│    • Assign to github-copilot[bot] automatically ✅                │
│    • Add [copilot-assigned], remove [processing] ✅                │
│  Labels: [specialist-type] → [processing] → [copilot-assigned]    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Issue assigned, Copilot processes
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 STAGE 4: COPILOT EXECUTION                          │
│  Handler: github-copilot[bot] (built-in)                           │
│  Process:                                                           │
│    • Read specialist guidance from issue body                      │
│    • Generate required deliverables per instructions              │
│    • Create feature branch                                         │
│    • Commit documents                                              │
│    • Create PR linking to issue                                    │
│  Labels: [copilot-assigned] → [completed] (on PR merge)           │
└─────────────────────────────────────────────────────────────────────┘

✅ BENEFITS:
   1. End-to-end automation, zero manual intervention
   2. Clean label lifecycle with automatic transitions
   3. Single unified command and workflow
   4. Clear, predictable behavior
   5. Automatic Copilot assignment
   6. AI-enhanced throughout
```

## Label State Machine

### Current State (Broken)

```
[site-monitor] ──────────────┐
                             │
                             ├──► [intelligence-analyst]
                             │    (manual trigger)
                             │
                             ├──► Labels accumulate!
                             │    [site-monitor, intelligence-analyst]
                             │
                             └──► No clear path to Copilot
                                  Manual assignment required
```

### Desired State (Clean)

```
State Machine with Automatic Transitions:

[Initial]
   │
   │ Site monitoring creates issue
   ▼
[site-monitor] ←── Discovery state
   │
   │ AUTO: Label event triggers pipeline
   │ Transition: add [analyzing]
   ▼
[analyzing] ←── Temporary analysis state
   │
   │ AI analysis completes
   │ Transition: add [specialist], remove [site-monitor, analyzing]
   ▼
[intelligence-analyst] ←── Specialist assigned
[osint-researcher]         (mutually exclusive)
[target-profiler]
   │
   │ AUTO: Label event triggers pipeline
   │ Transition: add [processing]
   ▼
[processing] ←── Temporary preparation state
   │
   │ Guidance generated, Copilot assigned
   │ Transition: add [copilot-assigned], remove [processing]
   ▼
[copilot-assigned] ←── Ready for Copilot
   │
   │ Copilot creates PR
   │ PR merged
   │ Transition: add [completed], remove all workflow labels
   ▼
[completed] ←── Final state

Temporary Labels:
  • [analyzing] - Removed after AI analysis
  • [processing] - Removed after guidance generation

Persistent Labels (until completion):
  • Specialist labels - Kept for reference
  • [copilot-assigned] - Removed when completed
```

## Command Consolidation

### BEFORE: Confusing Command Landscape

```
┌─────────────────────────────────────────────────────────────┐
│  USER DILEMMA: Which command should I use?                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Option 1: python main.py process-issues                   │
│    ✅ Creates deliverables automatically                    │
│    ✅ Makes PRs                                             │
│    ❌ Doesn't use AI for workflow matching                  │
│    ❌ Doesn't assign to Copilot                             │
│    ❌ Labels stay messy                                      │
│                                                             │
│  Option 2: python main.py process-copilot-issues           │
│    ✅ Uses AI workflow matching                             │
│    ✅ Generates guidance for Copilot                        │
│    ❌ Requires manual Copilot assignment first              │
│    ❌ Doesn't create deliverables directly                  │
│    ❌ Different behavior for same input                      │
│                                                             │
│  Option 3: python main.py assign-workflows                 │
│    ✅ AI-powered specialist assignment                      │
│    ❌ Only assigns labels, doesn't process                  │
│    ❌ Requires another command after                         │
│                                                             │
│  Result: User confusion, inconsistent outcomes              │
└─────────────────────────────────────────────────────────────┘
```

### AFTER: Single Unified Command

```
┌─────────────────────────────────────────────────────────────┐
│  CLEAR SOLUTION: One command, intelligent routing           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  python main.py process-pipeline --stage auto              │
│                                                             │
│  Automatic Stage Detection:                                │
│    • Has [site-monitor]? → Run analysis stage              │
│    • Has [specialist]? → Run preparation stage             │
│    • Has [copilot-assigned]? → Skip (already processed)    │
│                                                             │
│  Manual Stage Override (optional):                         │
│    --stage analysis     → Force analysis stage             │
│    --stage preparation  → Force preparation stage          │
│    --stage all          → Process all stages sequentially  │
│                                                             │
│  Batch Processing:                                         │
│    --batch-size 10      → Process up to 10 issues          │
│    --from-monitor       → Only process site-monitor issues │
│                                                             │
│  Safety:                                                   │
│    --dry-run            → Preview without changes          │
│    --verbose            → Detailed progress output         │
│                                                             │
│  Examples:                                                 │
│    # Process specific issue (auto-detect stage)            │
│    process-pipeline --issue 123 --stage auto               │
│                                                             │
│    # Process batch (auto-detect all stages)                │
│    process-pipeline --stage all --batch-size 20            │
│                                                             │
│    # Test before running                                   │
│    process-pipeline --dry-run --verbose                    │
│                                                             │
│  Result: Clear, predictable, one command does it all       │
└─────────────────────────────────────────────────────────────┘
```

## GitHub Actions Consolidation

### BEFORE: Multiple Workflows

```
ops-site-monitoring.yml
  ├── Discovers content
  ├── Creates issues with [site-monitor]
  └── No automatic next step

ops-workflow-assignment.yml
  ├── Searches for [site-monitor] issues
  ├── Assigns specialist labels
  └── Doesn't trigger processing

ops-issue-processing-pr.yml
  ├── Creates deliverables
  ├── Makes PRs
  └── Doesn't assign Copilot

ops-copilot-auto-process.yml
  ├── Finds Copilot-assigned issues
  ├── Generates guidance
  └── Requires manual assignment first

❌ Four separate workflows
❌ Manual triggers between stages
❌ Inconsistent behavior
```

### AFTER: Unified Workflow

```
ops-unified-pipeline.yml
  │
  ├── Trigger 1: issues.labeled (automatic)
  │   ├── site-monitor label → analysis stage
  │   └── specialist label → preparation stage
  │
  ├── Trigger 2: schedule (batch processing)
  │   └── Every 2 hours, process pending issues
  │
  └── Trigger 3: workflow_dispatch (manual)
      └── On-demand with stage selection

Job Flow:
  ┌─────────────────────┐
  │  detect-stage       │  What needs processing?
  └──────────┬──────────┘
             │
             ├──► analysis needed?
             │    └─► Run AI workflow assignment
             │        └─► Assign specialist labels
             │            └─► Remove site-monitor
             │                └─► Triggers next stage (via label)
             │
             └──► preparation needed?
                  └─► Generate specialist guidance
                      └─► Assign to Copilot
                          └─► Add copilot-assigned label

✅ Single unified workflow
✅ Automatic stage progression
✅ Event-driven architecture
```

## Migration Path

### Week-by-Week Transition

```
Week 1-2: DEVELOPMENT
┌─────────────────────────────────────────────────┐
│  • Build PipelineOrchestrator                   │
│  • Build GuidanceGenerator                      │
│  • Build LabelStateManager                      │
│  • Create unified command                       │
│  • Write comprehensive tests                    │
│  Status: New code ready, old code untouched     │
└─────────────────────────────────────────────────┘

Week 3: SOFT LAUNCH (Beta)
┌─────────────────────────────────────────────────┐
│  • Deploy with feature flag OFF                 │
│  • Test with 5 beta issues                      │
│  • Manual validation                            │
│  • Old system continues normal operation        │
│  Status: New code validated, low risk           │
└─────────────────────────────────────────────────┘

Week 4: PARALLEL OPERATION
┌─────────────────────────────────────────────────┐
│  OLD:  process-issues, process-copilot-issues   │
│  NEW:  process-pipeline (limited use)           │
│  • Both systems process same issues             │
│  • Compare outputs for consistency             │
│  • Build confidence in new system               │
│  Status: Validation in progress                 │
└─────────────────────────────────────────────────┘

Week 5: GRADUAL CUTOVER (50%)
┌─────────────────────────────────────────────────┐
│  • Enable auto-triggers in new workflow         │
│  • Add deprecation warnings to old commands     │
│  • ~50% traffic on new system                   │
│  • Monitor closely                              │
│  Status: Migration in progress                  │
└─────────────────────────────────────────────────┘

Week 6: FULL CUTOVER (100%)
┌─────────────────────────────────────────────────┐
│  • Disable old workflows                        │
│  • Redirect old commands to new                 │
│  • 100% traffic on new system                   │
│  • Old code kept for emergency rollback         │
│  Status: Migration complete, monitoring         │
└─────────────────────────────────────────────────┘

Week 7: CLEANUP
┌─────────────────────────────────────────────────┐
│  • Remove old commands completely               │
│  • Archive old workflows                        │
│  • Update all documentation                     │
│  • Celebrate success! 🎉                        │
│  Status: Cleanup complete                       │
└─────────────────────────────────────────────────┘

Week 8+: OPTIMIZATION
┌─────────────────────────────────────────────────┐
│  • Performance tuning                           │
│  • Cost optimization                            │
│  • Feature enhancements                         │
│  Status: Continuous improvement                 │
└─────────────────────────────────────────────────┘
```

## Key Benefits Summary

### For Users

✅ **"Assign and forget"** - No manual intervention needed  
✅ **Clear expectations** - Predictable, automatic workflow  
✅ **Better guidance** - Copilot gets comprehensive instructions  
✅ **Faster processing** - No waiting for manual triggers  

### For Operators

✅ **Single command** - Easy to understand and use  
✅ **Clean labels** - Automatic lifecycle management  
✅ **Better monitoring** - Clear pipeline stages  
✅ **Less maintenance** - No duplicate code  

### For the System

✅ **AI-enhanced** - Smart workflow assignment throughout  
✅ **Event-driven** - Automatic stage progression  
✅ **Scalable** - Batch processing with concurrency  
✅ **Reliable** - Comprehensive error handling  

---

**Status**: Planning Complete, Ready for Implementation  
**See Also**: [EXECUTIVE-SUMMARY.md](EXECUTIVE-SUMMARY.md) for complete project details
