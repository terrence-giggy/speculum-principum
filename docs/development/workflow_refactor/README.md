# Workflow Refactoring Project

## Project Overview

**Goal**: Streamline the three-stage automation workflow into a unified, efficient system that leverages AI-powered workflow assignment and Copilot-based document generation.

**Current State**: Three separate workflows with overlapping functionality and manual handoffs.

**Target State**: Integrated pipeline with automated handoffs, AI-powered analysis, and Copilot-driven deliverable generation.

## Problem Statement

The current system has three distinct workflows that should work as a seamless pipeline:

1. **Site Monitoring** (Operations -1) - Discovers content and creates issues with `site-monitor` label
2. **Workflow Assignment** (Operations -2) - AI analyzes content, assigns specialist labels, removes `site-monitor` label
3. **Issue Processing** (Operations -3) - Generates specialist guidance and assigns to Copilot

### Current Issues

- **Duplicate Processing Logic**: Both `process-issues` and `process-copilot-issues` commands exist with overlapping functionality
- **Manual Handoffs**: No automatic progression from site monitoring → workflow assignment → Copilot processing
- **Inconsistent Label Management**: Labels are added but original discovery labels aren't consistently removed
- **Unclear Workflow Boundaries**: Confusion about when to use which processing command
- **Missing Integration**: Gap between specialist assignment and Copilot execution

## Refactoring Goals

### Primary Objectives

1. **Unified Processing Pipeline**: Single command/workflow that handles all stages from discovery to Copilot assignment
2. **Automated Label Lifecycle**: Automatic label transitions (site-monitor → specialist labels → copilot-assigned)
3. **AI-Enhanced Analysis**: Leverage GitHub Models API for intelligent workflow selection
4. **Specialist-Driven Guidance**: Generate rich prompts based on specialist configurations
5. **Copilot Integration**: Seamless handoff to Copilot with complete context

### Secondary Objectives

1. **Reduce Code Duplication**: Consolidate `process-issues` and `process-copilot-issues` logic
2. **Improve Maintainability**: Clear separation of concerns with well-defined interfaces
3. **Enhanced Monitoring**: Better visibility into pipeline stages and failures
4. **Cost Optimization**: Efficient batching and API usage

## Project Structure

```
docs/development/workflow-refactor/
├── README.md                          # This file - project overview
├── 01-current-state-analysis.md       # Detailed analysis of current implementation
├── 02-desired-workflow.md             # Target workflow design
├── 03-technical-architecture.md       # New system architecture
├── 04-implementation-plan.md          # Step-by-step implementation guide
├── 05-migration-strategy.md           # Migration from old to new system
├── 06-testing-strategy.md             # Testing approach and validation
└── 07-rollout-plan.md                 # Deployment and rollout schedule
```

## Key Documents Reference

The following analysis documents inform this refactoring:

- **command-analysis.md** - Overview of all CLI commands and their overlaps
- **process-comparison.md** - Detailed comparison of process-issues vs process-copilot-issues
- **specialist-workflow-selection.md** - How specialist workflows are matched
- **copilot-auto-processing-gap.md** - Identified automation gaps
- **COPILOT-AUTOMATION-SUMMARY.md** - Complete automation solution overview

## Success Criteria

### Must Have

- [ ] Single unified processing command replaces both `process-issues` and `process-copilot-issues`
- [ ] Automatic label lifecycle management (site-monitor → specialist → copilot-assigned)
- [ ] AI-powered workflow assignment integrated into processing pipeline
- [ ] Specialist guidance automatically generated and included in issue
- [ ] Issues automatically assigned to Copilot after preparation
- [ ] Backward compatibility maintained during transition

### Should Have

- [ ] Batch processing optimizations for cost efficiency
- [ ] Enhanced error handling and retry logic
- [ ] Comprehensive logging and monitoring
- [ ] CLI backward compatibility layer for existing scripts

### Nice to Have

- [ ] Real-time progress reporting in GitHub Actions
- [ ] Automatic rollback on critical failures
- [ ] Performance metrics dashboard

## Timeline

- **Phase 1**: Analysis & Design (Current) - 1 week
- **Phase 2**: Core Implementation - 2 weeks
- **Phase 3**: Testing & Validation - 1 week
- **Phase 4**: Migration & Rollout - 1 week
- **Phase 5**: Monitoring & Optimization - Ongoing

## Next Steps

1. Review and validate current state analysis (01-current-state-analysis.md)
2. Define desired workflow and label lifecycle (02-desired-workflow.md)
3. Design technical architecture (03-technical-architecture.md)
4. Create detailed implementation plan (04-implementation-plan.md)

---

**Project Lead**: Development Team  
**Started**: 2025-09-29  
**Status**: Planning Phase
