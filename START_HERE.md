# Start Here - Spectra App Development Guide

## 🎯 Welcome to Spectra App Development

Welcome to the Spectra App project! This guide will help you get started with development and understand our workflow. Whether you're implementing new features, fixing bugs, or exploring the codebase, this document is your starting point.

## 📋 Essential Reading (Start Here)

### Core Documentation
- **`docs/history/MASTER_PROMPT.md`** - Comprehensive product specification and acceptance criteria
  - Defines the application's vision, architecture, and scientific goals
  - Outlines non-negotiable principles and technical constraints
  - Contains detailed feature requirements and validation criteria
- **`docs/atlas/brains.md`** - Current architectural decisions for ingest, caching, and remote services
  - Summarises the production pipeline and cache policies referenced by the Master Prompt
  - Keep this log in sync when altering importer wiring or remote integrations

- **`docs/history/RUNNER_PROMPT.md`** - Development workflow and iteration loop
  - Describes the plan → implement → test → document → PR cycle
  - Explains our docs-first development philosophy
  - Provides guidance for AI-assisted development sessions

### Quick Reference
- **`README.md`** - Project overview, installation, and basic usage
- **`docs/architecture.md`** - Technical architecture and system design
- **`agents.md`** - Development guidelines and UI contract specifications

## 🚀 Getting Started

### 1. Environment Setup
```bash
# Quick start (Windows)
RunSpectraApp.cmd

# Manual setup
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Verify Installation
```bash
# Run tests to verify everything works
pytest

# Launch the application
python -m app.main
```

### 3. Explore the Codebase
- **`app/`** - Main application code (PySide6/Qt)
- **`tests/`** - Test suite (pytest)
- **`samples/`** - Example datasets and manifests
- **`specs/`** - Technical specifications and architecture

## 🔄 Development Workflow

### Phase 1: Planning & Documentation
1. **Review Existing Context**
   - Consult `docs/ai_log/` for recent development history
   - Check `reports/feature_parity_matrix.md` for legacy compatibility
   - Review `specs/ui_contract/` for UI component requirements

2. **Create Work Plan**
   ```bash
   # Create or update your development workplan
   docs/reviews/workplan.md
   ```
   - Break down tasks into small, atomic units
   - Define acceptance criteria for each task
   - Identify documentation and testing requirements

### Phase 2: Implementation Loop
Follow the **RUNNER_PROMPT** workflow for each development session:

1. **Plan** - Review goals and constraints from MASTER_PROMPT
2. **Implement** - Code with docs-first approach
3. **Test** - Run pytest suite and verify functionality
4. **Document** - Update all relevant documentation
5. **Review** - Self-review against acceptance criteria

### Phase 3: Quality Assurance
- **Run Full Test Suite**: `pytest -v`
- **Verify UI Responsiveness**: Test with 1M+ point datasets
- **Check Documentation**: Ensure all changes are documented
- **Update Version**: Bump version in `app/version.json`
- **Write Patch Notes**: Add entry in `docs/patch_notes/`

## 📝 Creating Your Workplan

Create or update `docs/reviews/workplan.md` with this template:

```markdown
# Development Workplan - [Your Name/Feature]

## Overview
Brief description of the feature or fix being implemented.

## Tasks
- [ ] Task 1: Description
- [ ] Task 2: Description 
- [ ] Task 3: Description

## Acceptance Criteria
- [ ] All tests pass (pytest)
- [ ] UI remains responsive with large datasets
- [ ] Documentation updated
- [ ] Version bumped and patch notes written
- [ ] No regression in existing functionality

## References
- Related issues: #[issue numbers]
- Documentation: [links to relevant docs]
- Technical specs: [links to specs]
```

## 🛠 Branch Strategy

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Follow Atomic PR Principles**
   - Small, focused changes
   - Comprehensive documentation
   - Complete test coverage
   - Clear commit messages

3. **PR Checklist**
   - [ ] All tests pass
   - [ ] Documentation updated
   - [ ] UI contract preserved (if UI changes)
   - [ ] Performance validated
   - [ ] Patch notes included

## 🎯 Key Development Principles

### Non-Negotiable Rules
- **Desktop First**: PySide6/Qt only - no web components
- **Offline-First Data**: All data cached locally, persists across sessions
- **Unit Canon**: Store raw data in nanometers, convert at display time only
- **Provenance Everywhere**: Complete audit trail for all operations
- **Docs-First**: Documentation precedes implementation

### Quality Standards
- **Performance**: UI must remain responsive with 1M+ point datasets
- **Scientific Accuracy**: All algorithms must be mathematically sound
- **User Experience**: Clean, intuitive interface that doesn't overwhelm
- **Maintainability**: Modular, tested, documented code

## 🔍 Exploring Further

### For UI Development
- Review `specs/ui_contract/` for component specifications
- Study existing UI patterns in `app/ui/`
- Verify against the UI contract in `agents.md`

### For Data Processing
- Examine `app/services/` for ingestion and analysis services
- Review unit conversion patterns in `app/services/units/`
- Study provenance tracking in `app/services/provenance/`

### For Testing
- Explore existing tests in `tests/` for patterns
- Check `specs/testing/` for testing strategy
- Verify performance with large datasets in `tests/performance/`

## 🆘 Getting Help

- **Documentation**: Check `docs/` directory first
- **AI Logs**: Review `docs/ai_log/` for similar past work
- **Technical Specs**: Consult `specs/` for architecture decisions
- **Test Suite**: Use tests as living documentation

## 🎉 Next Steps

1. ✅ Read MASTER_PROMPT and RUNNER_PROMPT
2. ✅ Set up development environment
3. ✅ Create your workplan in `docs/reviews/workplan.md`
4. 🔄 Start development loop with small, atomic changes
5. 📝 Document everything as you go
6. 🧪 Test thoroughly before committing
7. 🔀 Open PR when all criteria are met

---

**Remember**: Work in small batches, document everything, and keep the tests passing. Welcome to the Spectra App project! 🚀