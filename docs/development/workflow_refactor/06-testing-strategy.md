# Testing Strategy

## Testing Philosophy

The unified pipeline refactoring requires comprehensive testing at multiple levels to ensure:
- **Correctness**: Pipeline produces expected results
- **Reliability**: System handles errors gracefully
- **Performance**: Meets speed and cost requirements
- **Safety**: No data loss or corruption during migration

## Test Pyramid

```
                    /\
                   /  \
                  / E2E \           10 tests (10%)
                 /      \
                /--------\
               /          \
              / Integration \      30 tests (30%)
             /              \
            /----------------\
           /                  \
          /    Unit Tests      \   60 tests (60%)
         /                      \
        /________________________\
```

## Unit Tests (60% of tests)

### Coverage Requirements

**Minimum Coverage**: 85% overall
- Core components: 95%
- Utilities: 80%
- CLI handlers: 70%

### Test Files Structure

```
tests/
├── core/
│   ├── test_pipeline_orchestrator.py
│   ├── test_label_state_manager.py
│   └── test_issue_finder.py
├── workflow/
│   ├── test_guidance_generator.py
│   └── test_specialist_selector.py
└── cli/
    └── test_process_pipeline_command.py
```

### PipelineOrchestrator Tests

**File**: `tests/core/test_pipeline_orchestrator.py`

```python
import pytest
from unittest.mock import Mock, MagicMock
from src.core.pipeline_orchestrator import PipelineOrchestrator

class TestPipelineOrchestrator:
    """Test suite for PipelineOrchestrator"""
    
    @pytest.fixture
    def orchestrator(self, mock_config):
        return PipelineOrchestrator(mock_config)
    
    @pytest.fixture
    def mock_issue_site_monitor(self):
        """Issue with site-monitor label"""
        issue = Mock()
        issue.number = 123
        issue.labels = [Mock(name='site-monitor')]
        return issue
    
    @pytest.fixture
    def mock_issue_specialist(self):
        """Issue with specialist label"""
        issue = Mock()
        issue.number = 124
        issue.labels = [Mock(name='intelligence-analyst')]
        return issue
    
    # Stage Detection Tests
    def test_detect_stage_site_monitor(self, orchestrator, mock_issue_site_monitor):
        """Should detect analysis stage for site-monitor issues"""
        stage = orchestrator._detect_stage(mock_issue_site_monitor)
        assert stage == 'analysis'
    
    def test_detect_stage_specialist(self, orchestrator, mock_issue_specialist):
        """Should detect preparation stage for specialist issues"""
        stage = orchestrator._detect_stage(mock_issue_specialist)
        assert stage == 'preparation'
    
    def test_detect_stage_copilot_assigned(self, orchestrator):
        """Should skip already processed issues"""
        issue = Mock()
        issue.labels = [
            Mock(name='intelligence-analyst'),
            Mock(name='copilot-assigned')
        ]
        stage = orchestrator._detect_stage(issue)
        assert stage == 'skip'
    
    # Analysis Stage Tests
    def test_process_analysis_stage_success(self, orchestrator, mock_issue_site_monitor, mocker):
        """Should successfully assign specialist labels"""
        mock_ai_agent = mocker.patch.object(orchestrator, 'ai_agent')
        mock_ai_agent.assign_workflows.return_value = [
            Mock(assigned_workflows=[Mock(specialist_type='intelligence-analyst')])
        ]
        
        result = orchestrator._process_analysis_stage(mock_issue_site_monitor)
        
        assert result.status == 'success'
        assert 'intelligence-analyst' in result.specialist_labels
        mock_issue_site_monitor.add_to_labels.assert_called()
    
    def test_process_analysis_stage_no_match(self, orchestrator, mock_issue_site_monitor, mocker):
        """Should handle no matching workflow gracefully"""
        mock_ai_agent = mocker.patch.object(orchestrator, 'ai_agent')
        mock_ai_agent.assign_workflows.return_value = [
            Mock(assigned_workflows=[])
        ]
        
        result = orchestrator._process_analysis_stage(mock_issue_site_monitor)
        
        assert result.status == 'no_match'
    
    # Preparation Stage Tests
    def test_process_preparation_stage_success(self, orchestrator, mock_issue_specialist, mocker):
        """Should generate guidance and assign to Copilot"""
        mock_specialist_config = mocker.patch.object(orchestrator, 'specialist_config')
        mock_specialist_config.find_matching_specialists.return_value = [
            Mock(name='Intelligence Analyst', type='intelligence-analyst')
        ]
        
        mock_guidance_gen = mocker.patch.object(orchestrator, 'guidance_generator')
        mock_guidance_gen.generate_guidance.return_value = "## Guidance\nTest guidance"
        
        result = orchestrator._process_preparation_stage(mock_issue_specialist)
        
        assert result.status == 'success'
        assert result.stage == 'preparation'
        mock_issue_specialist.add_to_assignees.assert_called_with('github-copilot[bot]')
        mock_issue_specialist.edit.assert_called_once()
    
    # Batch Processing Tests
    def test_process_batch_multiple_issues(self, orchestrator, mocker):
        """Should process multiple issues in batch"""
        mock_find = mocker.patch.object(orchestrator, '_find_processable_issues')
        mock_find.return_value = [Mock(number=i) for i in range(5)]
        
        mocker.patch.object(orchestrator, 'process_issue', return_value=Mock(status='success'))
        
        result = orchestrator.process_batch(stage='analysis', batch_size=3)
        
        assert len(result.results) == 3  # Respects batch_size
    
    # Error Handling Tests
    def test_analysis_stage_rollback_on_error(self, orchestrator, mock_issue_site_monitor, mocker):
        """Should rollback label changes on error"""
        mocker.patch.object(orchestrator, 'ai_agent').assign_workflows.side_effect = Exception("API Error")
        
        with pytest.raises(Exception):
            orchestrator._process_analysis_stage(mock_issue_site_monitor)
        
        # Should have removed 'analyzing' label
        mock_issue_site_monitor.remove_from_labels.assert_called_with('analyzing')
```

### LabelStateManager Tests

**File**: `tests/core/test_label_state_manager.py`

```python
class TestLabelStateManager:
    """Test label state machine logic"""
    
    def test_valid_transition_discovery_to_analysis(self, manager, mock_issue):
        """Should allow valid state transition"""
        mock_issue.labels = [Mock(name='site-monitor')]
        manager.transition_to_state(mock_issue, 'analysis')
        # Verify labels updated correctly
    
    def test_invalid_transition_raises_error(self, manager, mock_issue):
        """Should reject invalid transition"""
        mock_issue.labels = [Mock(name='site-monitor')]
        
        with pytest.raises(InvalidTransitionError):
            manager.transition_to_state(mock_issue, 'ready')  # Can't skip states
    
    def test_cleanup_labels_removed(self, manager, mock_issue):
        """Should remove old labels during transition"""
        mock_issue.labels = [Mock(name='site-monitor'), Mock(name='analyzing')]
        manager.transition_to_state(mock_issue, 'assigned')
        
        # Both site-monitor and analyzing should be removed
        assert 'site-monitor' not in [l.name for l in mock_issue.labels]
        assert 'analyzing' not in [l.name for l in mock_issue.labels]
```

### GuidanceGenerator Tests

**File**: `tests/workflow/test_guidance_generator.py`

```python
class TestGuidanceGenerator:
    """Test specialist guidance generation"""
    
    def test_generate_single_specialist_guidance(self, generator, mock_issue):
        """Should generate guidance for single specialist"""
        specialist = Mock(
            name='Intelligence Analyst',
            type='intelligence-analyst',
            config={'requirements': {...}}
        )
        
        guidance = generator.generate_guidance(mock_issue, [specialist])
        
        assert '### Intelligence Analyst Requirements' in guidance
        assert 'Deliverable:' in guidance
        assert 'Analysis Framework:' in guidance
    
    def test_generate_multi_specialist_guidance(self, generator, mock_issue):
        """Should generate guidance for multiple specialists"""
        specialists = [
            Mock(name='Intelligence Analyst', type='intelligence-analyst'),
            Mock(name='OSINT Researcher', type='osint-researcher')
        ]
        
        guidance = generator.generate_guidance(mock_issue, specialists)
        
        assert guidance.count('###') == 2  # Two specialist sections
    
    def test_extract_entities_from_issue(self, generator):
        """Should extract key entities from issue body"""
        issue_body = "Analysis of APT29 campaign targeting energy sector"
        entities = generator._extract_entities(issue_body)
        
        assert 'APT29' in entities
        assert 'energy sector' in entities or 'energy' in entities
```

## Integration Tests (30% of tests)

### End-to-End Stage Flow

**File**: `tests/integration/test_pipeline_flow.py`

```python
class TestPipelineFlow:
    """Integration tests for complete pipeline flow"""
    
    @pytest.fixture
    def live_orchestrator(self, integration_config):
        """Orchestrator with real (mocked) GitHub client"""
        return PipelineOrchestrator(integration_config)
    
    def test_site_monitor_to_specialist_assignment(self, live_orchestrator, mock_github_api):
        """Test flow: site-monitor → analysis → specialist labels"""
        
        # Create issue with site-monitor label
        issue = mock_github_api.create_issue(
            title="New threat report",
            body="Analysis of APT threat",
            labels=['site-monitor']
        )
        
        # Process issue (should trigger analysis stage)
        result = live_orchestrator.process_issue(issue.number, stage='auto')
        
        # Verify specialist label assigned
        updated_issue = mock_github_api.get_issue(issue.number)
        labels = [l.name for l in updated_issue.labels]
        
        assert 'site-monitor' not in labels
        assert any(l in labels for l in ['intelligence-analyst', 'osint-researcher', 'target-profiler'])
        assert result.status == 'success'
    
    def test_specialist_to_copilot_assignment(self, live_orchestrator, mock_github_api):
        """Test flow: specialist label → preparation → Copilot assigned"""
        
        # Create issue with specialist label
        issue = mock_github_api.create_issue(
            title="Intelligence analysis needed",
            body="Analyze threat actor",
            labels=['intelligence-analyst']
        )
        
        # Process issue (should trigger preparation stage)
        result = live_orchestrator.process_issue(issue.number, stage='auto')
        
        # Verify Copilot assigned and guidance added
        updated_issue = mock_github_api.get_issue(issue.number)
        
        assert 'github-copilot[bot]' in [a.login for a in updated_issue.assignees]
        assert 'copilot-assigned' in [l.name for l in updated_issue.labels]
        assert '## Copilot Processing Instructions' in updated_issue.body
    
    def test_full_pipeline_site_monitor_to_copilot(self, live_orchestrator, mock_github_api):
        """Test complete pipeline: discovery → analysis → preparation → Copilot"""
        
        # Stage 1: Create discovery issue
        issue = mock_github_api.create_issue(
            title="New content discovered",
            body="Security report on APT campaign",
            labels=['site-monitor']
        )
        
        # Stage 2: Analysis (assign specialist)
        result1 = live_orchestrator.process_issue(issue.number, stage='auto')
        assert result1.stage == 'analysis'
        
        # Stage 3: Preparation (assign Copilot)
        result2 = live_orchestrator.process_issue(issue.number, stage='auto')
        assert result2.stage == 'preparation'
        
        # Verify final state
        final_issue = mock_github_api.get_issue(issue.number)
        assert 'copilot-assigned' in [l.name for l in final_issue.labels]
        assert 'github-copilot[bot]' in [a.login for a in final_issue.assignees]
```

### GitHub Actions Integration

**File**: `tests/integration/test_github_actions.py`

```python
class TestGitHubActionsIntegration:
    """Test GitHub Actions workflow integration"""
    
    def test_label_event_triggers_correct_stage(self, mock_github_webhook):
        """Should trigger analysis when site-monitor label added"""
        
        event = mock_github_webhook.create_label_event(
            issue_number=123,
            label='site-monitor'
        )
        
        # Simulate workflow trigger
        stage = determine_stage_from_event(event)
        assert stage == 'analysis'
    
    def test_scheduled_batch_processing(self, live_orchestrator, mock_github_api):
        """Should process batch of issues on schedule"""
        
        # Create multiple processable issues
        for i in range(5):
            mock_github_api.create_issue(
                title=f"Issue {i}",
                labels=['intelligence-analyst']
            )
        
        # Simulate scheduled run
        result = live_orchestrator.process_batch(stage='all', batch_size=3)
        
        assert len(result.results) == 3  # Batch size respected
        assert all(r.status == 'success' for r in result.results)
```

## End-to-End Tests (10% of tests)

### System Tests

**File**: `tests/e2e/test_complete_workflow.py`

```python
@pytest.mark.e2e
class TestCompleteWorkflow:
    """End-to-end system tests"""
    
    def test_real_issue_processing(self, real_github_repo):
        """Test with real GitHub API (requires test repo)"""
        
        # This test uses a real test repository
        # Run only in CI with proper credentials
        
        if not os.getenv('E2E_TEST_REPO'):
            pytest.skip("E2E tests require E2E_TEST_REPO env var")
        
        # Complete workflow test...
```

## Performance Tests

### Load Testing

**File**: `tests/performance/test_load.py`

```python
class TestPerformance:
    """Performance and load tests"""
    
    def test_batch_processing_performance(self, orchestrator, mock_github_api):
        """Should process 100 issues in under 5 minutes"""
        
        issues = [
            mock_github_api.create_issue(f"Issue {i}", labels=['site-monitor'])
            for i in range(100)
        ]
        
        start_time = time.time()
        results = orchestrator.process_batch(stage='all', batch_size=100)
        elapsed = time.time() - start_time
        
        assert elapsed < 300  # 5 minutes
        assert len(results.results) == 100
    
    def test_api_call_efficiency(self, orchestrator, mock_github_api):
        """Should minimize GitHub API calls"""
        
        issue = mock_github_api.create_issue("Test", labels=['site-monitor'])
        
        with mock_github_api.call_counter():
            orchestrator.process_issue(issue.number, stage='auto')
        
        # Should not exceed reasonable limits
        assert mock_github_api.call_count < 10  # Adjust based on actual needs
```

## Test Fixtures

### Shared Fixtures

**File**: `tests/conftest.py`

```python
import pytest
from unittest.mock import Mock, MagicMock

@pytest.fixture
def mock_config():
    """Standard mock configuration"""
    config = Mock()
    config.github_token = 'test_token'
    config.github_repo = 'test/repo'
    return config

@pytest.fixture
def mock_github_issue():
    """Mock GitHub issue"""
    issue = Mock()
    issue.number = 123
    issue.title = "Test Issue"
    issue.body = "Test body content"
    issue.labels = []
    issue.assignees = []
    issue.add_to_labels = Mock()
    issue.remove_from_labels = Mock()
    issue.add_to_assignees = Mock()
    issue.edit = Mock()
    return issue

@pytest.fixture
def mock_github_client(mock_github_issue):
    """Mock GitHub client"""
    client = Mock()
    client.get_issue.return_value = mock_github_issue
    client.search_issues.return_value = [mock_github_issue]
    return client

@pytest.fixture
def mock_ai_agent():
    """Mock AI workflow assignment agent"""
    agent = Mock()
    agent.assign_workflows.return_value = [
        Mock(
            assigned_workflows=[
                Mock(specialist_type='intelligence-analyst')
            ],
            confidence=0.85
        )
    ]
    return agent
```

## Test Execution

### Local Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/core/test_pipeline_orchestrator.py -v

# Run tests matching pattern
pytest -k "test_analysis" -v

# Run with markers
pytest -m "not e2e"  # Skip E2E tests locally
```

### CI/CD Testing

**GitHub Actions Test Workflow**:

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
      
      - name: Run unit tests
        run: pytest tests/ -m "not e2e" --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
  
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run integration tests
        run: pytest tests/integration/ -v
  
  e2e-tests:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Run E2E tests
        env:
          E2E_TEST_REPO: ${{ secrets.E2E_TEST_REPO }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: pytest tests/e2e/ -v
```

## Quality Gates

### Pre-Merge Checks

- [ ] All unit tests pass
- [ ] Code coverage ≥ 85%
- [ ] All integration tests pass
- [ ] No linting errors
- [ ] Documentation updated

### Pre-Release Checks

- [ ] All E2E tests pass
- [ ] Performance tests meet SLA
- [ ] Security scan clean
- [ ] Manual smoke test complete
- [ ] Migration tests pass

---

**Next**: See `07-rollout-plan.md` for deployment strategy
