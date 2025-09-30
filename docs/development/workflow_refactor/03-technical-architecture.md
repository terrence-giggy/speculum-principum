# Technical Architecture

## System Overview

The refactored system implements a **Pipeline Orchestrator** pattern that coordinates multiple processing stages with automatic state transitions and intelligent routing.

## Core Components

### 1. Pipeline Orchestrator (New)

**File**: `src/core/pipeline_orchestrator.py`

```python
class PipelineOrchestrator:
    """
    Central coordinator for the unified processing pipeline.
    Manages stage detection, routing, and label lifecycle.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.github_client = GitHubClient(config)
        self.ai_agent = AIWorkflowAssignmentAgent(config)
        self.specialist_config = SpecialistWorkflowConfigManager()
        self.guidance_generator = GuidanceGenerator(config)
        
    def process_issue(self, issue_number: int, stage: str = 'auto') -> ProcessingResult:
        """Main entry point for issue processing"""
        issue = self.github_client.get_issue(issue_number)
        
        # Detect current stage if auto
        if stage == 'auto':
            stage = self._detect_stage(issue)
        
        # Route to appropriate stage handler
        if stage == 'analysis':
            return self._process_analysis_stage(issue)
        elif stage == 'preparation':
            return self._process_preparation_stage(issue)
        elif stage == 'skip':
            return ProcessingResult(status='skipped', reason='Already processed')
        else:
            raise ValueError(f"Unknown stage: {stage}")
    
    def process_batch(self, stage: str = 'auto', batch_size: int = 10) -> BatchResult:
        """Process multiple issues in batch mode"""
        issues = self._find_processable_issues(stage)
        results = []
        
        for issue in issues[:batch_size]:
            try:
                result = self.process_issue(issue.number, stage)
                results.append(result)
            except Exception as e:
                results.append(ProcessingResult(status='error', error=str(e)))
        
        return BatchResult(results=results)
    
    def _detect_stage(self, issue: Issue) -> str:
        """Detect which stage this issue should be processed in"""
        labels = {label.name for label in issue.labels}
        
        # Site monitor needs analysis
        if 'site-monitor' in labels:
            return 'analysis'
        
        # Has specialist label but not assigned to Copilot
        specialist_labels = labels & {'intelligence-analyst', 'osint-researcher', 
                                     'target-profiler', 'business-analyst'}
        if specialist_labels and 'copilot-assigned' not in labels:
            return 'preparation'
        
        # Already processed or unknown state
        return 'skip'
    
    def _process_analysis_stage(self, issue: Issue) -> ProcessingResult:
        """Stage 2: AI-powered workflow assignment"""
        
        # Add analyzing label for visibility
        self._update_labels(issue, add=['analyzing'])
        
        try:
            # Run AI analysis
            assignment = self.ai_agent.assign_workflows([issue])[0]
            
            if assignment.assigned_workflows:
                # Add specialist labels
                specialist_labels = [w.specialist_type for w in assignment.assigned_workflows]
                self._update_labels(
                    issue,
                    add=specialist_labels,
                    remove=['site-monitor', 'analyzing']
                )
                
                # Add comment explaining assignment
                self._add_assignment_comment(issue, assignment)
                
                return ProcessingResult(
                    status='success',
                    stage='analysis',
                    specialist_labels=specialist_labels,
                    confidence=assignment.confidence
                )
            else:
                # No suitable workflow found
                self._update_labels(issue, remove=['analyzing'])
                self._add_comment(issue, "No suitable specialist workflow found")
                return ProcessingResult(status='no_match', stage='analysis')
                
        except Exception as e:
            # Remove analyzing label on error
            self._update_labels(issue, remove=['analyzing'])
            raise
    
    def _process_preparation_stage(self, issue: Issue) -> ProcessingResult:
        """Stage 3: Generate specialist guidance and assign to Copilot"""
        
        # Add processing label
        self._update_labels(issue, add=['processing'])
        
        try:
            # Find matching specialists
            specialists = self.specialist_config.find_matching_specialists(issue)
            
            if not specialists:
                self._update_labels(issue, remove=['processing'])
                return ProcessingResult(status='no_specialists', stage='preparation')
            
            # Generate comprehensive guidance
            guidance = self.guidance_generator.generate_guidance(issue, specialists)
            
            # Update issue body with guidance
            updated_body = self._append_guidance_to_issue(issue, guidance)
            issue.edit(body=updated_body)
            
            # Assign to Copilot
            issue.add_to_assignees('github-copilot[bot]')
            
            # Update labels
            self._update_labels(
                issue,
                add=['copilot-assigned'],
                remove=['processing']
            )
            
            # Add comment
            self._add_comment(
                issue,
                f"✅ Issue prepared with specialist guidance and assigned to Copilot\n\n"
                f"**Specialists**: {', '.join(s.name for s in specialists)}"
            )
            
            return ProcessingResult(
                status='success',
                stage='preparation',
                specialists=[s.name for s in specialists],
                guidance_length=len(guidance)
            )
            
        except Exception as e:
            self._update_labels(issue, remove=['processing'])
            raise
    
    def _find_processable_issues(self, stage: str) -> List[Issue]:
        """Find issues that need processing in the specified stage"""
        
        if stage == 'analysis':
            # Find site-monitor issues without specialist labels
            return self.github_client.search_issues(
                labels=['site-monitor'],
                exclude_labels=['intelligence-analyst', 'osint-researcher', 
                              'target-profiler', 'analyzing']
            )
        
        elif stage == 'preparation':
            # Find specialist-labeled issues not yet assigned to Copilot
            return self.github_client.search_issues(
                has_any_label=['intelligence-analyst', 'osint-researcher', 'target-profiler'],
                exclude_labels=['copilot-assigned', 'processing']
            )
        
        elif stage == 'auto':
            # Find any processable issues
            analysis_issues = self._find_processable_issues('analysis')
            prep_issues = self._find_processable_issues('preparation')
            return analysis_issues + prep_issues
        
        return []
    
    def _update_labels(self, issue: Issue, add: List[str] = None, 
                       remove: List[str] = None):
        """Atomically update issue labels"""
        current_labels = {label.name for label in issue.labels}
        
        if remove:
            current_labels -= set(remove)
        
        if add:
            current_labels |= set(add)
        
        issue.set_labels(list(current_labels))
```

### 2. Guidance Generator (New)

**File**: `src/workflow/guidance_generator.py`

```python
class GuidanceGenerator:
    """
    Generates comprehensive specialist guidance for Copilot processing.
    Replaces direct deliverable generation with instruction generation.
    """
    
    def generate_guidance(self, issue: Issue, specialists: List[Specialist]) -> str:
        """Generate complete guidance section for issue"""
        
        sections = []
        sections.append(self._generate_header())
        
        for specialist in specialists:
            sections.append(self._generate_specialist_section(issue, specialist))
        
        sections.append(self._generate_checklist(specialists))
        sections.append(self._generate_footer())
        
        return "\n\n".join(sections)
    
    def _generate_specialist_section(self, issue: Issue, specialist: Specialist) -> str:
        """Generate guidance section for a single specialist"""
        
        # Load specialist template
        template = self._load_specialist_template(specialist.type)
        
        # Extract requirements from specialist config
        requirements = specialist.config.get('requirements', {})
        
        section = f"""### {specialist.name} Requirements

**Deliverable**: `{specialist.deliverable_path}`

**Analysis Framework**:
{self._format_framework(requirements.get('framework', []))}

**Content Requirements**:
{self._format_requirements(requirements.get('content', []))}

**Template**: Use `{template.path}`

**Key Focus Areas**:
{self._format_focus_areas(issue, specialist)}
"""
        return section
    
    def _format_focus_areas(self, issue: Issue, specialist: Specialist) -> str:
        """Generate context-specific focus areas based on issue content"""
        
        # Extract key entities/topics from issue
        entities = self._extract_entities(issue.body)
        
        focus_areas = []
        
        if specialist.type == 'intelligence-analyst':
            if 'threat' in issue.body.lower():
                focus_areas.append("- Threat actor attribution and motivation")
            if 'campaign' in issue.body.lower():
                focus_areas.append("- Campaign timeline and tactics")
            focus_areas.append(f"- Analysis of {entities[0] if entities else 'target'}")
        
        elif specialist.type == 'osint-researcher':
            if entities:
                focus_areas.append(f"- Deep dive on {', '.join(entities[:3])}")
            focus_areas.append("- Infrastructure and technical footprint")
            focus_areas.append("- Historical activity and patterns")
        
        elif specialist.type == 'target-profiler':
            focus_areas.append("- Organizational structure and personnel")
            focus_areas.append("- Business operations and relationships")
            focus_areas.append("- Digital presence and public information")
        
        return "\n".join(focus_areas) if focus_areas else "- Comprehensive analysis per framework"
```

### 3. Label State Manager (New)

**File**: `src/core/label_state_manager.py`

```python
class LabelStateManager:
    """
    Manages the label lifecycle state machine.
    Ensures valid state transitions and cleanup.
    """
    
    # Define state machine
    STATES = {
        'discovery': ['site-monitor'],
        'analysis': ['analyzing'],
        'assigned': ['intelligence-analyst', 'osint-researcher', 'target-profiler', 'business-analyst'],
        'processing': ['processing'],
        'ready': ['copilot-assigned'],
        'complete': ['completed']
    }
    
    # Valid transitions
    TRANSITIONS = {
        'discovery': ['analysis'],
        'analysis': ['assigned'],
        'assigned': ['processing'],
        'processing': ['ready'],
        'ready': ['complete']
    }
    
    # Labels that should be removed when transitioning
    CLEANUP_RULES = {
        'analysis': ['site-monitor'],              # Remove discovery labels
        'assigned': ['analyzing'],                 # Remove temp analysis label
        'ready': ['processing'],                   # Remove temp processing label
        'complete': ['copilot-assigned', '*specialist']  # Remove all workflow labels
    }
    
    def transition_to_state(self, issue: Issue, target_state: str):
        """Transition issue to target state with automatic cleanup"""
        current_state = self._detect_current_state(issue)
        
        # Validate transition
        if target_state not in self.TRANSITIONS.get(current_state, []):
            raise InvalidTransitionError(
                f"Cannot transition from {current_state} to {target_state}"
            )
        
        # Get labels to add and remove
        labels_to_add = self.STATES[target_state]
        labels_to_remove = self._get_cleanup_labels(target_state, issue)
        
        # Apply changes
        self._update_labels(issue, add=labels_to_add, remove=labels_to_remove)
    
    def _detect_current_state(self, issue: Issue) -> str:
        """Detect current state from labels"""
        labels = {label.name for label in issue.labels}
        
        for state, state_labels in self.STATES.items():
            if any(label in labels for label in state_labels):
                return state
        
        return 'unknown'
    
    def _get_cleanup_labels(self, target_state: str, issue: Issue) -> List[str]:
        """Get labels that should be removed for this transition"""
        cleanup_rules = self.CLEANUP_RULES.get(target_state, [])
        current_labels = {label.name for label in issue.labels}
        
        labels_to_remove = []
        
        for rule in cleanup_rules:
            if rule == '*specialist':
                # Remove all specialist labels
                labels_to_remove.extend(
                    label for label in current_labels 
                    if label in self.STATES['assigned']
                )
            else:
                # Remove specific label if present
                if rule in current_labels:
                    labels_to_remove.append(rule)
        
        return labels_to_remove
```

### 4. Unified CLI Command Handler

**File**: `main.py` (modified)

```python
def handle_process_pipeline_command(args):
    """
    Unified pipeline processing command.
    Replaces process-issues and process-copilot-issues.
    """
    from src.core.pipeline_orchestrator import PipelineOrchestrator
    
    config = ConfigManager.load_config(args.config)
    orchestrator = PipelineOrchestrator(config)
    
    if args.issue:
        # Process specific issue
        result = orchestrator.process_issue(
            issue_number=args.issue,
            stage=args.stage
        )
        print(f"✅ Processed issue #{args.issue}: {result.status}")
    
    else:
        # Batch processing
        result = orchestrator.process_batch(
            stage=args.stage,
            batch_size=args.batch_size
        )
        
        print(f"\n📊 Batch Processing Results:")
        print(f"  Total processed: {len(result.results)}")
        print(f"  Successful: {sum(1 for r in result.results if r.status == 'success')}")
        print(f"  Errors: {sum(1 for r in result.results if r.status == 'error')}")

def setup_argument_parser():
    """Updated argument parser"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    
    # New unified command
    pipeline_parser = subparsers.add_parser(
        'process-pipeline',
        help='Unified pipeline processing (replaces process-issues and process-copilot-issues)'
    )
    pipeline_parser.add_argument('--config', required=True)
    pipeline_parser.add_argument('--issue', type=int, help='Specific issue to process')
    pipeline_parser.add_argument(
        '--stage',
        choices=['auto', 'analysis', 'preparation', 'all'],
        default='auto',
        help='Pipeline stage to execute'
    )
    pipeline_parser.add_argument('--batch-size', type=int, default=10)
    pipeline_parser.add_argument('--dry-run', action='store_true')
    
    # Deprecated commands with warnings
    deprecated_process = subparsers.add_parser(
        'process-issues',
        help='[DEPRECATED] Use process-pipeline instead'
    )
    # ... add deprecation wrapper
    
    deprecated_copilot = subparsers.add_parser(
        'process-copilot-issues',
        help='[DEPRECATED] Use process-pipeline instead'
    )
    # ... add deprecation wrapper
```

## Data Flow

### Issue Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Issue Discovery (Site Monitoring)                       │
│    Input: Google Search results                            │
│    Output: Issue with [site-monitor] label                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Pipeline Orchestrator (process-pipeline --stage auto)   │
│    • Detects stage = 'analysis' (has site-monitor)         │
│    • Routes to _process_analysis_stage()                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. AI Workflow Assignment                                   │
│    • Add [analyzing] label                                  │
│    • GitHub Models API content analysis                     │
│    • Multi-factor confidence scoring                        │
│    • Assign specialist labels                               │
│    • Remove [site-monitor, analyzing]                       │
│    • Trigger: Label change event                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Pipeline Orchestrator (triggered by label event)        │
│    • Detects stage = 'preparation' (has specialist label)   │
│    • Routes to _process_preparation_stage()                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Guidance Generation                                      │
│    • Add [processing] label                                 │
│    • Find matching specialists                              │
│    • Generate comprehensive guidance                        │
│    • Update issue body                                      │
│    • Assign to github-copilot[bot]                         │
│    • Add [copilot-assigned], remove [processing]           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Copilot Processing (handled by Copilot)                 │
│    • Read specialist guidance                               │
│    • Generate deliverables                                  │
│    • Create PR                                              │
│    • Trigger: PR merge event                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Cleanup (on PR merge)                                    │
│    • Remove all workflow labels                             │
│    • Add [completed]                                        │
│    • Close issue                                            │
└─────────────────────────────────────────────────────────────┘
```

## GitHub Actions Architecture

### Workflow: `ops-unified-pipeline.yml`

```yaml
name: Operations - Unified Pipeline

on:
  # Trigger on label events (automatic stage progression)
  issues:
    types: [labeled]
  
  # Scheduled batch processing
  schedule:
    - cron: '0 */2 * * *'
  
  # Manual dispatch
  workflow_dispatch:
    inputs:
      stage:
        type: choice
        options: ['auto', 'analysis', 'preparation', 'all']
        default: 'auto'
      batch_size:
        type: number
        default: 10

jobs:
  route-pipeline:
    name: Route to Pipeline Stage
    runs-on: ubuntu-latest
    outputs:
      stage: ${{ steps.route.outputs.stage }}
      should_process: ${{ steps.route.outputs.should_process }}
    
    steps:
      - name: Route to correct stage
        id: route
        run: |
          # Detect which stage based on event
          if [ "${{ github.event_name }}" = "issues" ]; then
            LABEL="${{ github.event.label.name }}"
            
            if [ "$LABEL" = "site-monitor" ]; then
              echo "stage=analysis" >> $GITHUB_OUTPUT
              echo "should_process=true" >> $GITHUB_OUTPUT
            elif [[ "$LABEL" =~ (intelligence-analyst|osint-researcher|target-profiler) ]]; then
              echo "stage=preparation" >> $GITHUB_OUTPUT
              echo "should_process=true" >> $GITHUB_OUTPUT
            fi
          elif [ "${{ github.event_name }}" = "schedule" ]; then
            echo "stage=all" >> $GITHUB_OUTPUT
            echo "should_process=true" >> $GITHUB_OUTPUT
          fi
  
  process-pipeline:
    name: Execute Pipeline Stage
    needs: route-pipeline
    if: needs.route-pipeline.outputs.should_process == 'true'
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Execute pipeline
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python main.py process-pipeline \
            --config config.yaml \
            --stage ${{ needs.route-pipeline.outputs.stage }} \
            --batch-size ${{ inputs.batch_size || 10 }}
```

## Module Dependencies

```
main.py
  └── PipelineOrchestrator
        ├── AIWorkflowAssignmentAgent (existing)
        ├── SpecialistWorkflowConfigManager (existing)
        ├── GuidanceGenerator (new)
        ├── LabelStateManager (new)
        └── GitHubClient (existing)

GuidanceGenerator
  ├── TemplateEngine (existing)
  ├── SpecialistWorkflowConfigManager (existing)
  └── EntityExtractor (new - optional)

LabelStateManager
  └── GitHubClient (existing)
```

## API Integration Points

### GitHub Models API (Analysis Stage)
- **Endpoint**: GitHub Models API via `openai` library
- **Model**: `gpt-4o-mini`
- **Purpose**: Semantic content analysis for specialist assignment
- **Cost**: ~$0.01 per issue

### GitHub REST API (All Stages)
- **Operations**: Issue queries, label updates, comments, assignments
- **Authentication**: `GITHUB_TOKEN`
- **Rate Limits**: 5000 requests/hour (authenticated)

### Template System (Preparation Stage)
- **Engine**: Jinja2
- **Templates**: `templates/specialists/*/`
- **Purpose**: Specialist-specific guidance generation

---

**Next**: See `04-implementation-plan.md` for step-by-step implementation
