# Start Here - Spectra App Development Guide

## 🎯 Welcome to Spectra App Development

Welcome to the Spectra App project! This guide will help you get started with development and understand our workflow. Whether you're implementing new features, fixing bugs, or exploring the codebase, this document is your starting point.

## 📋 Essential Reading (Start Here)

### Core Documentation
- **`docs/history/MASTER PROMPT.md`** - Comprehensive product specification and acceptance criteria
  - Defines the application's vision, architecture, and scientific goals
  - Outlines non-negotiable principles, Atlas alignment, and calibration/identification mandates
  - Contains detailed feature requirements and validation criteria drawn from the pass reviews

- **`docs/history/RUNNER_PROMPT.md`** - Development workflow and iteration loop
  - Describes the plan → implement → test → document → PR cycle
  - Explains our docs-first development philosophy
  - Provides guidance for AI-assisted development sessions

### Quick Reference
- **`README.md`** - Project overview, installation, and basic usage
- **`AGENTS.md`** - Development guidelines, spectroscopy conventions, UI contract expectations
- **`docs/brains/README.md`** - How to log architectural decisions now that `atlas/brains.md` has been decomposed
- **`docs/link_collection.md`** - Curated spectroscopy resources to cite when sourcing new data
- **`docs/reviews/pass1.md` … `docs/reviews/pass4.md`** - Review dossiers outlining calibration, identification, provenance, and UI priorities

## 🚀 Getting Started

### 1. Environment Setup
```bash
# Quick start (Windows)
RunSpectraApp.cmd

# Manual setup
py -3.11 -m venv .venv
.\.venv\Scripts\activate
set PIP_NO_BINARY=
set PIP_ONLY_BINARY=numpy
set PIP_PREFER_BINARY=1
pip install --prefer-binary -r requirements.txt

# If numpy still attempts to build from source (Windows without C++ build tools)
python -m pip install --prefer-binary "numpy>=1.26,<2"
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
- **`samples/`** - Spectroscopy sample data (lamps, forthcoming standards) grouped by instrument/type
- **`specs/`** - Technical specifications (provenance schema, UI contracts)
- **`docs/brains/`** - Timestamped architectural decisions tied back to the Atlas

## 🔄 Development Workflow

### Phase 1: Planning & Documentation
1. **Review Existing Context**
   - Read `docs/history/MASTER PROMPT.md`, `AGENTS.md`, and `docs/reviews/pass*.md`
   - Consult `docs/history/KNOWLEDGE_LOG.md` and `docs/brains/` for the latest decisions
   - Review `docs/reviews/workplan.md`, backlog queues, and brainstorming notes before scoping new work

2. **Create Work Plan**
   ```bash
   # Create or update your development workplan
   docs/reviews/workplan.md
   ```
   - Break down tasks into small, atomic units aligned with Atlas chapters
   - Define acceptance criteria (behaviour, docs, tests, provenance) for each task
   - Identify documentation, brains entries, and test updates before coding

### Phase 2: Implementation Loop
Follow the **RUNNER_PROMPT** workflow for each development session:

1. **Plan** - Review goals and constraints from MASTER_PROMPT
2. **Implement** - Code with docs-first approach
3. **Test** - Run pytest suite and verify functionality
4. **Document** - Update all relevant documentation
5. **Review** - Self-review against acceptance criteria

### Recording Real Timestamps
- Always capture America/New_York and UTC timestamps in ISO-8601 format when
  updating patch notes, the knowledge log, brains entries, or the workplan.
- Follow the platform-specific commands in `AGENTS.md` and the MASTER PROMPT to
  emit both strings in a single pass:
  - **Windows (PowerShell 5.1+/pwsh)**:

    ```powershell
    [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::UtcNow,"Eastern Standard Time").ToString("o")
    (Get-Date).ToUniversalTime().ToString("o")
    ```

  - **macOS/Linux shells** run:

    ```bash
    TZ=America/New_York date --iso-8601=seconds
    date -u --iso-8601=seconds
    ```

    macOS users may need `gdate` from Homebrew coreutils.

  - **Python fallback (any platform)**:

    ```bash
    python - <<'PY'
    from datetime import UTC, datetime
    import zoneinfo

    ny = zoneinfo.ZoneInfo("America/New_York")
    print(datetime.now(ny).isoformat())
    print(datetime.now(UTC).isoformat())
    PY
    ```

  - **WSL users** can invoke `wsl.exe bash -lc 'TZ=America/New_York date --iso-8601=seconds && date -u --iso-8601=seconds'`
    from Windows terminals without leaving the host environment.

### Phase 3: Quality Assurance
- **Run Full Test Suite**: `pytest -v`
- **Verify UI Responsiveness**: Test with 1M+ point datasets
- **Check Documentation**: Ensure all changes are documented
- **Log Changes**: Update `docs/history/PATCH_NOTES.md` and
  `docs/history/KNOWLEDGE_LOG.md` with real timestamps
- **Release Prep**: Follow `packaging/windows_build.md` if a distribution build
  or version bump is required

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
- [ ] Patch notes and knowledge log updated
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
- Review `specs/ui_contract.md` for component specifications
- Study existing UI patterns in `app/ui/`
- Verify against the UI contract in `AGENTS.md`

### For Data Processing
- Examine `app/services/` for ingestion and analysis services
- Review unit conversion patterns in `app/services/units_service.py`
- Study provenance tracking in `app/services/provenance_service.py`

### For Testing
- Explore existing tests in `tests/` for patterns
- Check `specs/testing.md` for testing strategy
- Verify performance with large datasets in `tests/performance/`

## 🆘 Getting Help

- **Documentation**: Check `docs/` directory first
- **Knowledge Log**: Review `docs/history/KNOWLEDGE_LOG.md` for similar past work
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