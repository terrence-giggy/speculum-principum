# Migration Strategy

## Overview

This document outlines the safe, phased migration from the current dual-command system (`process-issues` and `process-copilot-issues`) to the unified `process-pipeline` command.

## Migration Principles

1. **Zero Downtime**: Existing workflows continue to function during migration
2. **Backward Compatibility**: Old commands work alongside new ones during transition
3. **Progressive Rollout**: Gradual adoption with monitoring and rollback capability
4. **Clear Communication**: Users informed of changes with migration guidance
5. **Data Safety**: No loss of existing issues, labels, or processing state

## Migration Phases

### Phase 0: Preparation (Week 0)

#### Tasks
- [ ] Create feature branch `feature/unified-pipeline`
- [ ] Set up parallel testing environment
- [ ] Document current system state
- [ ] Identify all consumers of old commands
- [ ] Create rollback procedures

#### Deliverables
- Migration project plan
- Rollback scripts
- Test environment with sample data
- Communication plan for users

### Phase 1: Development & Testing (Weeks 1-2)

#### Implementation (Week 1)
- [ ] Implement PipelineOrchestrator
- [ ] Implement LabelStateManager
- [ ] Implement GuidanceGenerator
- [ ] Add process-pipeline CLI command
- [ ] Create ops-unified-pipeline.yml

#### Testing (Week 2)
- [ ] Unit tests (>85% coverage)
- [ ] Integration tests
- [ ] Load testing with sample issues
- [ ] Security review
- [ ] Documentation review

#### Acceptance Criteria
- All tests passing
- Performance metrics met
- Documentation complete
- Security review passed

### Phase 2: Soft Launch (Week 3)

#### Deployment Strategy

**Deploy new code with old commands still primary**:
```bash
# Feature flag in config.yaml
features:
  unified_pipeline:
    enabled: false  # Start disabled
    beta_users: []  # Will add users incrementally
```

**Make new command available**:
- process-pipeline command available but not default
- Old commands remain unchanged (no warnings yet)
- ops-unified-pipeline.yml deployed but not triggered automatically

#### Beta Testing
- [ ] Select 3-5 beta issues for manual testing
- [ ] Run `process-pipeline --stage auto --issue <N> --dry-run`
- [ ] Compare output to old command results
- [ ] Validate label transitions
- [ ] Verify Copilot receives correct guidance

#### Monitoring
- Track new command usage via logs
- Monitor error rates
- Collect beta user feedback
- Measure performance metrics

#### Success Criteria
- Beta tests complete successfully
- No regressions in old command functionality
- Performance within expected bounds
- Positive beta user feedback

### Phase 3: Parallel Operation (Week 4)

#### Enable Dual Mode

**Update config to allow both**:
```yaml
features:
  unified_pipeline:
    enabled: true  # Enable for all
    mode: parallel  # Run alongside old commands
    auto_migrate: false  # Don't auto-switch yet
```

#### GitHub Actions Updates

**Run both workflows side-by-side**:
```yaml
# ops-unified-pipeline.yml
on:
  workflow_dispatch:  # Manual only for now
  # Scheduled and label triggers disabled during parallel phase

# ops-workflow-assignment.yml and ops-issue-processing-pr.yml
# Keep running as normal
```

#### Comparative Analysis
- [ ] Process same issues with both old and new commands
- [ ] Compare results (labels, assignments, guidance)
- [ ] Validate consistency
- [ ] Document any discrepancies

#### Training & Documentation
- [ ] Create video tutorial for new command
- [ ] Update operator runbook
- [ ] Hold team training session
- [ ] Publish migration FAQ

#### Success Criteria
- Both systems producing identical results
- Team trained on new command
- Documentation finalized
- Zero critical issues in new code

### Phase 4: Gradual Cutover (Weeks 5-6)

#### Week 5: Enable Auto-Triggers

**Enable automatic pipeline triggers**:
```yaml
# ops-unified-pipeline.yml
on:
  issues:
    types: [labeled]  # Enable automatic triggers
  schedule:
    - cron: '0 */2 * * *'  # Enable scheduled runs
  workflow_dispatch:
```

**Add deprecation warnings to old commands**:
```python
def handle_process_issues_command(args):
    print("""
⚠️  DEPRECATION WARNING
    
The 'process-issues' command is deprecated and will be removed in v2.0
    
Please migrate to: process-pipeline --stage preparation
    
Migration guide: docs/development/workflow-refactor/05-migration-strategy.md
    
This command will continue to work for now...
    """)
    
    # Continue with old behavior
```

**Monitoring Dashboard**:
```
Old Command Usage:
  process-issues: 45 calls (↓ from 120 last week)
  process-copilot-issues: 23 calls (↓ from 65 last week)

New Command Usage:
  process-pipeline: 87 calls (↑ from 12 last week)

Migration Progress: 65% complete
```

#### Week 6: Disable Old Workflows

**Disable old GitHub Actions**:
```yaml
# ops-issue-processing-pr.yml
# DEPRECATED - Use ops-unified-pipeline.yml instead
on:
  workflow_dispatch:  # Keep manual for emergency only
  # Remove all automatic triggers
```

**Update CLI to redirect**:
```python
def handle_process_issues_command(args):
    print("⚠️  Redirecting to process-pipeline command...")
    
    # Convert args and delegate
    args.stage = 'preparation'
    return handle_process_pipeline_command(args)
```

#### Success Criteria
- New command handling >80% of traffic
- Old workflows disabled without incidents
- No manual interventions required
- Team comfortable with new system

### Phase 5: Complete Migration (Week 7)

#### Remove Old Code

**Mark old commands as errors**:
```python
def handle_process_issues_command(args):
    raise DeprecatedCommandError(
        "The 'process-issues' command has been removed.\n"
        "Use: process-pipeline --stage preparation\n"
        "See: docs/development/workflow-refactor/05-migration-strategy.md"
    )
```

**Clean up old files**:
```bash
# Mark for removal (don't delete immediately)
git mv .github/workflows/ops-issue-processing-pr.yml \
       .github/workflows/DEPRECATED-ops-issue-processing-pr.yml

# Update README to remove old command references
# Remove old command handlers from main.py
# Archive old tests
```

#### Final Validation
- [ ] All automated workflows using new command
- [ ] No usage of old commands in logs
- [ ] All documentation updated
- [ ] Team sign-off on completion

#### Communication
- [ ] Announce migration complete
- [ ] Update all documentation
- [ ] Archive old command docs
- [ ] Celebrate success! 🎉

### Phase 6: Cleanup (Week 8+)

#### Remove Deprecated Code
```bash
# After 2 weeks of zero usage
git rm src/core/batch_processor.py  # Old batch logic merged into orchestrator
git rm .github/workflows/DEPRECATED-ops-issue-processing-pr.yml

# Commit cleanup
git commit -m "chore: Remove deprecated processing commands"
```

#### Optimize New System
- [ ] Remove redundant code paths
- [ ] Optimize API calls
- [ ] Improve error messages
- [ ] Performance tuning

## Rollback Procedures

### Rollback Triggers

Execute rollback if:
- Critical bug affects >10% of issues
- Data loss or corruption detected
- Unacceptable performance degradation (>2x slower)
- Security vulnerability discovered

### Rollback Steps

#### Immediate Rollback (< 5 minutes)

1. **Disable new workflow**:
   ```bash
   # Disable ops-unified-pipeline.yml
   gh workflow disable ops-unified-pipeline.yml
   ```

2. **Re-enable old workflows**:
   ```bash
   gh workflow enable ops-workflow-assignment.yml
   gh workflow enable ops-issue-processing-pr.yml
   ```

3. **Revert feature flag**:
   ```yaml
   # config.yaml
   features:
     unified_pipeline:
       enabled: false
   ```

#### Full Rollback (< 30 minutes)

1. **Revert code deployment**:
   ```bash
   git revert <commit-range>
   git push origin main
   ```

2. **Fix any label inconsistencies**:
   ```bash
   python scripts/fix_label_state.py
   ```

3. **Communicate to team**:
   - Notify of rollback
   - Explain reason
   - Timeline for fix

### Post-Rollback

- [ ] Root cause analysis
- [ ] Fix identified issues
- [ ] Additional testing
- [ ] Retry migration when ready

## Command Mapping

### Old → New Command Translation

| Old Command | New Command | Notes |
|------------|------------|-------|
| `process-issues --config config.yaml` | `process-pipeline --stage preparation --config config.yaml` | Direct replacement |
| `process-issues --issue 123` | `process-pipeline --stage auto --issue 123` | Auto-detect stage |
| `process-copilot-issues --config config.yaml` | `process-pipeline --stage preparation --config config.yaml` | Same as process-issues |
| `assign-workflows --config config.yaml` | `process-pipeline --stage analysis --config config.yaml` | Integrated into pipeline |

### Workflow Translation

| Old Workflow | New Workflow | Change |
|--------------|--------------|--------|
| ops-workflow-assignment.yml | ops-unified-pipeline.yml | Merged - Stage: analysis |
| ops-issue-processing-pr.yml | ops-unified-pipeline.yml | Merged - Stage: preparation |
| ops-copilot-auto-process.yml | ops-unified-pipeline.yml | Merged - Auto Copilot assignment |

## Data Migration

### Label Migration

**No data migration needed** - Labels remain compatible:
- Existing `site-monitor` labels → Triggers analysis stage
- Existing specialist labels → Triggers preparation stage
- New temporary labels (`analyzing`, `processing`) added as needed

### Issue State

**Existing issues handled gracefully**:
```python
# In PipelineOrchestrator._detect_stage()
def _detect_stage(self, issue):
    labels = {label.name for label in issue.labels}
    
    # Handle legacy issues with both site-monitor and specialist labels
    if 'site-monitor' in labels and any(specialist in labels):
        # Old issue - skip analysis, go straight to preparation
        return 'preparation'
    
    # Standard flow
    if 'site-monitor' in labels:
        return 'analysis'
    
    # ... rest of logic
```

### Configuration Migration

**Update config.yaml**:
```yaml
# OLD (deprecated)
processing:
  batch_size: 10
  assignee_filter: null

# NEW (unified)
pipeline:
  batch_size: 10
  auto_assign_copilot: true
  stages:
    analysis:
      enabled: true
      ai_powered: true
    preparation:
      enabled: true
      generate_guidance: true
```

## Testing Strategy

### Pre-Migration Testing

1. **Snapshot existing state**:
   ```bash
   python scripts/snapshot_issues.py > pre_migration_state.json
   ```

2. **Test with sample issues**:
   - Create 10 test issues
   - Process with old commands
   - Process with new commands
   - Compare results

3. **Load testing**:
   - Simulate 100 concurrent issues
   - Measure performance
   - Check for race conditions

### During Migration Testing

1. **Parallel processing validation**:
   - Process same issue with both systems
   - Compare outputs
   - Validate consistency

2. **Incremental rollout**:
   - Start with 10% of issues
   - Monitor for 24 hours
   - Increase to 50%
   - Monitor for 24 hours
   - Full cutover

### Post-Migration Testing

1. **Validation**:
   ```bash
   python scripts/validate_migration.py \
     --before pre_migration_state.json \
     --after post_migration_state.json
   ```

2. **Spot checks**:
   - Manually review 20 randomly selected issues
   - Verify all labels correct
   - Confirm Copilot assignments
   - Check guidance quality

## Communication Plan

### Stakeholders

1. **Development Team**: Technical details, implementation support
2. **Operations Team**: Runbook updates, monitoring procedures
3. **End Users**: Copilot users, system behavior changes
4. **Leadership**: Project status, risk updates

### Communication Timeline

| Week | Audience | Message | Channel |
|------|----------|---------|---------|
| -1 | Dev Team | Migration plan review | Team meeting |
| 0 | All | Migration announcement | Email, Slack |
| 1-2 | Dev Team | Implementation updates | Daily standups |
| 3 | Ops Team | Soft launch, monitoring | Training session |
| 4 | All | Parallel mode enabled | Email |
| 5 | All | Deprecation warnings active | Email, in-app |
| 6 | All | Old workflows disabled | Email |
| 7 | All | Migration complete | Email, Slack |

## Success Criteria

### Migration Success Metrics

- [ ] 100% of issues processed by new system
- [ ] Zero data loss or corruption
- [ ] Performance improved or equal to old system
- [ ] Error rate <1%
- [ ] Team satisfaction >80%
- [ ] Zero rollbacks required

### Quality Gates

**Gate 1 (Week 2)**: Development Complete
- All tests passing
- Documentation complete
- Code review approved

**Gate 2 (Week 3)**: Beta Success
- 5 successful beta tests
- No critical bugs
- Beta user approval

**Gate 3 (Week 5)**: Parallel Validation
- Identical results for 100 test cases
- Performance within 10% of baseline
- Team trained and ready

**Gate 4 (Week 7)**: Migration Complete
- Old commands deprecated
- New system handling 100% traffic
- All stakeholders sign-off

---

**Next**: See `06-testing-strategy.md` for detailed test plans
