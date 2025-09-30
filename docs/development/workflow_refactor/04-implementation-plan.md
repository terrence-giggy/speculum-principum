# Implementation Plan

## Phase Overview

| Phase | Duration | Focus | Deliverables |
|-------|----------|-------|--------------|
| 1 | 3 days | Core Infrastructure | PipelineOrchestrator, LabelStateManager |
| 2 | 2 days | Guidance Generation | GuidanceGenerator, specialist templates |
| 3 | 2 days | CLI & GitHub Actions | New command, unified workflow |
| 4 | 2 days | Testing & Validation | Unit tests, integration tests |
| 5 | 1 day | Documentation | User guide, API docs |

**Total Duration**: 10 working days (2 weeks)

## Phase 1: Core Infrastructure (Days 1-3)

### Day 1: Pipeline Orchestrator Foundation

#### Tasks

1. **Create PipelineOrchestrator class** (`src/core/pipeline_orchestrator.py`)
   ```python
   class PipelineOrchestrator:
       def __init__(self, config)
       def process_issue(self, issue_number, stage='auto')
       def process_batch(self, stage='auto', batch_size=10)
       def _detect_stage(self, issue)
   ```

2. **Implement stage detection logic**
   - Extract labels from issue
   - Apply decision tree for stage determination
   - Return 'analysis', 'preparation', or 'skip'

3. **Add basic routing**
   - Route to analysis stage handler
   - Route to preparation stage handler
   - Handle skip/unknown states

4. **Unit tests**
   ```python
   # tests/core/test_pipeline_orchestrator.py
   def test_detect_stage_site_monitor()
   def test_detect_stage_specialist_label()
   def test_detect_stage_already_processed()
   ```

#### Acceptance Criteria
- [ ] PipelineOrchestrator instantiates correctly
- [ ] Stage detection correctly identifies analysis vs preparation
- [ ] Routing logic delegates to correct handlers
- [ ] Unit test coverage > 80%

### Day 2: Label State Manager

#### Tasks

1. **Create LabelStateManager class** (`src/core/label_state_manager.py`)
   ```python
   class LabelStateManager:
       STATES = {...}
       TRANSITIONS = {...}
       CLEANUP_RULES = {...}
       
       def transition_to_state(self, issue, target_state)
       def _detect_current_state(self, issue)
       def _get_cleanup_labels(self, target_state, issue)
   ```

2. **Define state machine**
   - Map state names to labels
   - Define valid transitions
   - Create cleanup rules

3. **Implement transition logic**
   - Validate state transitions
   - Apply label additions
   - Apply label removals
   - Handle errors gracefully

4. **Integration with PipelineOrchestrator**
   ```python
   # In PipelineOrchestrator
   self.label_manager = LabelStateManager()
   
   def _process_analysis_stage(self, issue):
       self.label_manager.transition_to_state(issue, 'analysis')
       # ... analysis logic
       self.label_manager.transition_to_state(issue, 'assigned')
   ```

#### Acceptance Criteria
- [ ] State machine correctly validates transitions
- [ ] Labels are added/removed atomically
- [ ] Invalid transitions raise appropriate errors
- [ ] Integration tests pass with mock GitHub API

### Day 3: Analysis Stage Integration

#### Tasks

1. **Implement _process_analysis_stage method**
   ```python
   def _process_analysis_stage(self, issue):
       # Transition to analysis state (add 'analyzing' label)
       self.label_manager.transition_to_state(issue, 'analysis')
       
       # Delegate to AI workflow assignment agent
       assignment = self.ai_agent.assign_workflows([issue])[0]
       
       # Transition to assigned state (add specialist, remove site-monitor)
       specialist_labels = [w.specialist_type for w in assignment.assigned_workflows]
       self._apply_specialist_labels(issue, specialist_labels)
       self.label_manager.transition_to_state(issue, 'assigned')
       
       # Add explanatory comment
       self._add_assignment_comment(issue, assignment)
   ```

2. **Reuse existing AIWorkflowAssignmentAgent**
   - No changes needed to agent itself
   - Integration point: call `assign_workflows([issue])`
   - Process assignment result

3. **Add comment generation**
   - Explain AI reasoning
   - Show confidence scores
   - Link to specialist documentation

4. **Error handling**
   - Handle AI API failures
   - Rollback label changes on error
   - Add error comments to issue

#### Acceptance Criteria
- [ ] Analysis stage successfully calls AI agent
- [ ] Specialist labels correctly assigned
- [ ] site-monitor label removed automatically
- [ ] Error handling prevents partial state updates

## Phase 2: Guidance Generation (Days 4-5)

### Day 4: GuidanceGenerator Implementation

#### Tasks

1. **Create GuidanceGenerator class** (`src/workflow/guidance_generator.py`)
   ```python
   class GuidanceGenerator:
       def generate_guidance(self, issue, specialists)
       def _generate_specialist_section(self, issue, specialist)
       def _format_framework(self, framework_items)
       def _format_requirements(self, requirements)
       def _extract_entities(self, text)  # Simple NLP
   ```

2. **Load specialist configurations**
   - Read from SpecialistWorkflowConfigManager
   - Extract requirements, frameworks, templates
   - Map to guidance sections

3. **Generate structured guidance**
   - Header with context
   - Per-specialist sections with deliverable paths
   - Analysis frameworks
   - Content requirements
   - Processing checklist

4. **Template integration**
   - Reference existing templates
   - Format template paths correctly
   - Ensure Copilot can find templates

#### Acceptance Criteria
- [ ] Guidance generated includes all specialist sections
- [ ] Template references are correct
- [ ] Framework and requirements are clear
- [ ] Generated markdown is well-formatted

### Day 5: Preparation Stage Integration

#### Tasks

1. **Implement _process_preparation_stage method**
   ```python
   def _process_preparation_stage(self, issue):
       # Transition to processing state
       self.label_manager.transition_to_state(issue, 'processing')
       
       # Find matching specialists
       specialists = self.specialist_config.find_matching_specialists(issue)
       
       # Generate guidance
       guidance = self.guidance_generator.generate_guidance(issue, specialists)
       
       # Update issue body
       updated_body = f"{issue.body}\n\n---\n\n{guidance}"
       issue.edit(body=updated_body)
       
       # Assign to Copilot
       issue.add_to_assignees('github-copilot[bot]')
       
       # Transition to ready state
       self.label_manager.transition_to_state(issue, 'ready')
   ```

2. **Issue body formatting**
   - Preserve original content
   - Add clear separator
   - Append guidance section
   - Ensure markdown rendering works

3. **Copilot assignment**
   - Use GitHub API to add assignee
   - Verify assignee is valid
   - Handle assignment errors

4. **Comment notifications**
   - Notify about Copilot assignment
   - List assigned specialists
   - Provide next steps

#### Acceptance Criteria
- [ ] Preparation stage generates and appends guidance
- [ ] Issue successfully assigned to Copilot
- [ ] Labels transition correctly (specialist → copilot-assigned)
- [ ] Original issue content preserved

## Phase 3: CLI & GitHub Actions (Days 6-7)

### Day 6: Unified CLI Command

#### Tasks

1. **Add process-pipeline command** (`main.py`)
   ```python
   def handle_process_pipeline_command(args):
       config = ConfigManager.load_config(args.config)
       orchestrator = PipelineOrchestrator(config)
       
       if args.issue:
           result = orchestrator.process_issue(args.issue, args.stage)
       else:
           result = orchestrator.process_batch(args.stage, args.batch_size)
   ```

2. **Update argument parser**
   - Add process-pipeline subcommand
   - Define arguments: --stage, --issue, --batch-size, --dry-run
   - Add help text and examples

3. **Add deprecation warnings**
   ```python
   def handle_process_issues_command(args):
       print("⚠️  WARNING: 'process-issues' is deprecated")
       print("   Use 'process-pipeline --stage preparation' instead")
       print("   This command will be removed in v2.0\n")
       # Continue with old behavior...
   ```

4. **Dry-run mode**
   - Implement dry-run flag throughout pipeline
   - Log actions without executing
   - Validate configuration

#### Acceptance Criteria
- [ ] process-pipeline command works for single issue
- [ ] Batch mode processes multiple issues
- [ ] Deprecation warnings show for old commands
- [ ] Dry-run mode doesn't modify issues

### Day 7: GitHub Actions Workflow

#### Tasks

1. **Create ops-unified-pipeline.yml**
   ```yaml
   name: Operations - Unified Pipeline
   
   on:
     issues:
       types: [labeled]
     schedule:
       - cron: '0 */2 * * *'
     workflow_dispatch:
   ```

2. **Implement stage routing job**
   - Detect which stage from event type
   - Output stage to next job
   - Handle label events vs scheduled

3. **Implement processing job**
   - Receive stage from routing job
   - Execute process-pipeline command
   - Upload logs and artifacts

4. **Add monitoring and notifications**
   - Generate GitHub Actions summary
   - Post comments on processed issues
   - Notify on failures

#### Acceptance Criteria
- [ ] Workflow triggers on site-monitor label
- [ ] Workflow triggers on specialist label
- [ ] Scheduled runs process batches
- [ ] Manual dispatch works with all options

## Phase 4: Testing & Validation (Days 8-9)

### Day 8: Unit & Integration Tests

#### Tasks

1. **Unit tests for new components**
   ```python
   # tests/core/test_pipeline_orchestrator.py
   # tests/core/test_label_state_manager.py
   # tests/workflow/test_guidance_generator.py
   ```

2. **Integration tests**
   ```python
   # tests/integration/test_end_to_end_pipeline.py
   def test_full_pipeline_site_monitor_to_copilot():
       # Create issue with site-monitor label
       # Run analysis stage
       # Verify specialist labels added
       # Run preparation stage
       # Verify Copilot assigned
   ```

3. **Mock GitHub API**
   - Use existing fixtures from conftest.py
   - Add new fixtures for label operations
   - Mock issue body updates

4. **Edge case testing**
   - No matching specialists
   - AI API failures
   - Invalid label states
   - Network errors

#### Acceptance Criteria
- [ ] Unit test coverage > 85%
- [ ] Integration tests cover happy path
- [ ] Edge cases handled gracefully
- [ ] All tests pass in CI

### Day 9: Validation & Bug Fixes

#### Tasks

1. **Manual testing with real issues**
   - Create test issue with site-monitor
   - Verify analysis stage
   - Verify preparation stage
   - Verify Copilot receives correct guidance

2. **Performance testing**
   - Measure API call counts
   - Check batch processing speed
   - Validate cost per issue

3. **Bug fixes**
   - Address issues found in manual testing
   - Fix any test failures
   - Optimize slow operations

4. **Security review**
   - Check token handling
   - Validate input sanitization
   - Review error messages for info leakage

#### Acceptance Criteria
- [ ] End-to-end test completes successfully
- [ ] Performance meets targets (< 30s per issue)
- [ ] No critical or high-severity bugs
- [ ] Security review complete

## Phase 5: Documentation & Rollout (Day 10)

### Day 10: Documentation

#### Tasks

1. **Update user documentation**
   - README.md: Add process-pipeline command
   - Add migration guide from old commands
   - Update workflow diagrams

2. **API documentation**
   - Document PipelineOrchestrator public methods
   - Document GuidanceGenerator usage
   - Add docstrings to all new code

3. **Operator guide**
   ```markdown
   # Operating the Unified Pipeline
   
   ## Quick Start
   1. Monitor creates issue with site-monitor label
   2. Pipeline automatically triggers analysis
   3. AI assigns specialist labels
   4. Pipeline automatically triggers preparation
   5. Issue assigned to Copilot with guidance
   
   ## Manual Operations
   - Force analysis: `process-pipeline --stage analysis --issue 123`
   - Process batch: `process-pipeline --stage all --batch-size 20`
   ```

4. **Troubleshooting guide**
   - Common errors and solutions
   - How to check pipeline state
   - Manual recovery procedures

#### Acceptance Criteria
- [ ] All documentation updated
- [ ] Migration guide complete
- [ ] Operator guide covers all scenarios
- [ ] Troubleshooting guide tested

## Implementation Checklist

### Pre-Implementation
- [ ] Review and approve technical architecture
- [ ] Set up feature branch: `feature/unified-pipeline`
- [ ] Create GitHub project for tracking
- [ ] Prepare test environment

### Phase 1: Core Infrastructure
- [ ] PipelineOrchestrator skeleton
- [ ] Stage detection logic
- [ ] LabelStateManager implementation
- [ ] Analysis stage integration
- [ ] Unit tests for core components

### Phase 2: Guidance Generation
- [ ] GuidanceGenerator class
- [ ] Specialist section generation
- [ ] Preparation stage integration
- [ ] Issue body formatting

### Phase 3: CLI & GitHub Actions
- [ ] process-pipeline command
- [ ] Deprecation warnings
- [ ] ops-unified-pipeline.yml workflow
- [ ] Stage routing logic

### Phase 4: Testing
- [ ] Unit tests (>85% coverage)
- [ ] Integration tests
- [ ] Manual validation
- [ ] Bug fixes

### Phase 5: Documentation
- [ ] User documentation
- [ ] API documentation
- [ ] Operator guide
- [ ] Migration guide

## Risk Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| AI API failures | High | Medium | Implement retry logic, fallback to rule-based |
| Label race conditions | Medium | Low | Use atomic label updates, transaction-like logic |
| State machine bugs | High | Medium | Comprehensive testing, validation layer |
| GitHub API rate limits | Medium | Low | Batch operations, request caching |

### Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| User confusion | Medium | High | Clear migration guide, deprecation warnings |
| Breaking changes | High | Low | Maintain backward compatibility during transition |
| Data loss | High | Low | Dry-run mode, backups, rollback procedures |
| Performance issues | Medium | Medium | Performance testing, optimization, monitoring |

## Success Metrics

### Development Metrics
- Code coverage: >85%
- Build time: <5 minutes
- Test pass rate: 100%

### Operational Metrics
- Pipeline completion time: <30s per issue
- API cost per issue: <$0.05
- Error rate: <1%
- Manual intervention rate: <5%

## Rollout Strategy

See `05-migration-strategy.md` for detailed rollout plan.

---

**Next**: See `05-migration-strategy.md` for migration approach
