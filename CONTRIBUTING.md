# Contributing to Spectra App

This concise guide covers the essentials for human and AI contributors. For full policies, historical context, templates, and extended guides see the `docs/` directory.

## Essential reading

- Required: `docs/history/MASTER_PROMPT.md`, `docs/history/RUNNER_PROMPT.md`
- Reference: `README.md`, `START_HERE.md`, `specs/architecture.md`

## For human contributors

### Set up environment

```bash
# quick-launch (Windows)
RunSpectraApp.cmd

# manual (cross-platform)
python -m venv .venv
. .venv/bin/activate  # or run the Windows activate script
pip install -r requirements.txt
```

### Verify installation

```bash
pytest
python -m app.main
```

### Work plan & branching

- Update `docs/reviews/workplan.md` with task breakdown and acceptance criteria.
- Create a feature branch: `git checkout -b feature/short-desc`

### PR checklist

- [ ] All tests pass
- [ ] Documentation updated (user + developer)
- [ ] Focused tests added for new behavior
- [ ] Version bumped when user-visible changes occur

## For AI contributors

Follow the agent operating manual (`AGENTS.md`) and the repository `docs/` before editing code. Minimum requirements:

1. Load `docs/history/MASTER_PROMPT.md` and `docs/history/RUNNER_PROMPT.md`.
1. Record changes in `docs/ai_log/` with a short rationale and tests added.
1. Use branch pattern `ai/feature-YYYYMMDD` and make small, test-covered commits.

### AI session protocol (brief)

- PLAN → IMPLEMENT → TEST → DOCUMENT → VALIDATE
- Declare session start in the work plan and list goals and constraints.
- Run the full test suite before finalizing a PR.

## Technical standards (summary)

- Formatting: Black
- Linting: flake8
- Tests: pytest
- Type hints encouraged

## Submission

### Pre-submission checks

```bash
pytest
python -m app.main --test-large
```

### PR creation

- Use the PR template: `.github/pull_request_template.md`.
- Link to work plan and related issues; tag reviewers.

## Getting help

- Technical: `docs/dev/`, `specs/`
- Process: `AGENTS.md`, `docs/history/RUNNER_PROMPT.md`
- Scientific context: `docs/edu/`, `MASTER_PROMPT.md`

---

For a more comprehensive contribution guide and AI-specific templates, see `docs/CONTRIBUTING_FULL.md` and `docs/ai_log/`

For the full contribution guide and AI-specific templates, see `docs/CONTRIBUTING_FULL.md` and `docs/ai_log/`.

- Verify UI contract compliance
   pytest                           # All tests pass
% This file intentionally simplified to resolve lint warnings. See docs/ for full policy.

Essential reading

1. **Required**: `docs/history/MASTER_PROMPT.md`, `docs/history/RUNNER_PROMPT.md`, `docs/atlas/read
1. **Reference**: `README.md`, `START_HERE.md`, `specs/architecture.md`

For human contributors

1. Set up environment

```bash
# quick-launch (Windows)
RunSpectraApp.cmd

# manual (cross-platform)
python -m venv .venv
. .venv/bin/activate  # or activate script on Windows
pip install -r requirements.txt
```

1. Verify install

```bash
pytest
python -m app.main
```

1. Create a work plan and small feature branch

- Update `docs/reviews/workplan.md`
- Create branch: `git checkout -b feature/short-desc`

Checklist before PR

- All tests pass
- Add/update docs and patch notes
- Include focused tests for new behavior

For AI contributors

Follow the agent operating manual in `AGENTS.md` and the repository `docs/` before editing code. Minimal requirements:

1. Start by loading `docs/history/MASTER_PROMPT.md` and `docs/history/RUNNER_PROMPT.md`.
1. Record changes in `docs/ai_log/` with a short rationale and tests added.

Use the standard branch pattern `ai/feature-YYYYMMDD` and make small, test-covered commits.

Technical standards (summary)

- Formatting: Black
- Linting: flake8
- Tests: pytest
- Type hints encouraged

Submission

1. Run tests and CI locally where possible.
1. Open PR with work plan and tests.

---

If you need a longer contribution guide, please see `docs/CONTRIBUTING_FULL.md` or ask maintainers.

AI agents must adhere to additional guidelines to ensure consistency and maintainability:

Pre-Development Phase

1. **Context Loading**
   - Always start by loading the MASTER_PROMPT and RUNNER_PROMPT
   - Review recent entries in `docs/ai_log/` for context
   - Check `reports/feature_parity_matrix.md` for legacy compatibility

2. **Work Plan Creation**

   ```bash
   # Create detailed work plan
   docs/reviews/workplan_AI_[timestamp].md
   ```

   - Include specific file changes and implementations
   - Define test cases and validation criteria
   - List documentation that needs updating

Development Session Protocol

1. **Session Initialization**
   - Declare session start in work plan
   - State current goals and constraints
   - Confirm understanding of non-negotiable principles

2. **Implementation Loop**

   PLAN → IMPLEMENT → TEST → DOCUMENT → VALIDATE

3. **Quality Gates**
   - **Before Coding**: Verify against UI contract and architecture boundaries
   - **During Coding**: Follow existing patterns in `app/services/`
   - **After Coding**: Run full test suite and performance validation

Documentation Requirements for AI Work

1. **AI Log Entry** (`docs/ai_log/`)

   ```markdown
   # YYYY-MM-DD-HHMM - [Feature Description]
   
   ## Changes Made
   - File: description of changes
   - File: description of changes
   
   ## Rationale
   Explanation of design decisions and approach
   
   ## Tests Added/Modified
   - test_file.py: description
   
   ## Documentation Updated
   - docs/path: description
   
   ## Performance Impact
   - UI responsiveness: [verified/maintained/degraded]
   - Memory usage: [unchanged/increased/decreased]
   ```

2. **Version Management**
   - Bump the semantic version in `pyproject.toml`
   - Update any mirrored defaults (e.g. `ProvenanceService.app_version`)
   - Record user-visible changes in `docs/history/PATCH_NOTES.md`

3. **Provenance Tracking**
   - Ensure all data operations record source and transformations
   - Maintain unit conversion integrity
   - Preserve citation and attribution information

Safety and Validation Rules

1. **Non-Negotiable Checks**
   - [ ] Desktop-first (PySide6/Qt only)
   - [ ] Offline-first data caching
   - [ ] Unit canon preservation (x=nm storage)
   - [ ] Provenance tracking intact
   - [ ] Performance budget maintained

2. **Regression Prevention**
   - Run full test suite before and after changes
   - Verify UI contract compliance
   - Check for unit conversion idempotency
   - Validate with sample datasets

3. **Error Handling**
   - Implement graceful degradation for remote services
   - Provide clear error messages to users
   - Maintain application stability during failures

### Branch Strategy for AI Work

```bash
# Branch naming convention
git checkout -b ai/feature-name-YYYYMMDD

# Work in small, atomic commits
git commit -m "feat: describe specific change
- Detail 1
- Detail 2
- Tests: [added/modified/na]
- Docs: [updated/na]"
```

### AI-Specific Best Practices

1. **Code Quality**
   - Follow existing patterns in the codebase
   - Use type hints and docstrings
   - Maintain consistent naming conventions
   - Prefer composition over inheritance

2. **Testing Approach**
   - Add tests for new fetchers and UI elements
   - Include offline fixtures for remote service tests
   - Verify performance with large datasets
   - Ensure deterministic test behavior

3. **Documentation Standards**
   - Update both user and developer documentation
   - Include examples in docstrings
   - Cross-reference related functionality
   - Maintain table of contents accuracy

## 🛠 Technical Standards

### Code Quality

- **Formatting**: Black code formatter
- **Linting**: flake8 compliance
- **Type Checking**: mypy (where applicable)
- **Testing**: pytest with ≥80% coverage

### Scientific Accuracy

- **Unit Conversions**: Mathematically sound and idempotent
- **Algorithm Validation**: Peer-reviewed methods preferred
- **Data Provenance**: Complete lineage tracking
- **Citation Integrity**: Proper attribution of data sources

### Performance Requirements

- **UI Responsiveness**: Smooth interaction with 1M+ point datasets
- **Memory Efficiency**: Smart caching and data management
- **Startup Time**: <5 seconds for application launch
- **Export Performance**: Efficient handling of large exports

## 📚 Documentation Standards

### Required Updates for Every Change

- **User Documentation**: `docs/user/` - Guides, tutorials, FAQs
- **Developer Documentation**: `docs/dev/` - API references, architecture
- **Educational Content**: `docs/edu/` - Spectroscopy primers
- **Patch Notes**: `docs/history/PATCH_NOTES.md` - User-visible changes
- **Knowledge Log**: `docs/history/KNOWLEDGE_LOG.md` - Development rationale and decisions

### Documentation Quality Checklist

- [ ] Clear, concise language
- [ ] Examples provided where helpful
- [ ] Cross-references to related content
- [ ] Updated table of contents
- [ ] Screenshots for UI changes

## 🚀 Submission Process

1. **Pre-Submission Validation**

   ```bash
   pytest                           # All tests pass
   python -m app.main --test-large  # Performance validation
   ```

2. **PR Creation**
   - Use PR template from `.github/pull_request_template.md`
   - Link to work plan and related issues
   - Tag appropriate reviewers

3. **CI Validation**
   - All checks must pass (Windows + Ubuntu)
   - Code coverage maintained or improved
   - Performance benchmarks within tolerance

## 🆘 Getting Help

- **Technical Questions**: Check `docs/dev/` and `specs/`
- **Process Questions**: Review `agents.md` and RUNNER_PROMPT
- **Scientific Context**: Consult `docs/edu/` and MASTER_PROMPT
  - **Existing Patterns**: Study `docs/history/KNOWLEDGE_LOG.md` for similar work

## 🎯 Remember Our Mission

> **Spectroscopic analysis of celestial bodies, and the many ways in which we may approach it.**

Keep the application:

- 🔬 **Scientifically accurate**
- 💻 **Technically robust**  
- 👥 **User-friendly**
- 📚 **Well-documented**
- 🚀 **Continuously improving**

---

*Both human and AI contributors are valued members of our community. Thank you for helping advance spectroscopic science!* 🌟
