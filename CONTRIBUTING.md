# Contributing to Spectra App

Welcome to the Spectra App project! This guide covers contribution guidelines for both human developers and AI agents. We follow a **docs-first, test-driven** approach to ensure scientific accuracy and maintainable code.

## 🎯 Essential Reading (All Contributors)

### Required Reading for All Work
- **`docs/history/MASTER_PROMPT.md`** - Complete product specification, architecture, and acceptance criteria
- **`docs/history/RUNNER_PROMPT.md`** - Development workflow and iteration loop
- **`agents.md`** - Development guidelines, UI contract, and safety rules
- **`README.md`** - Project overview and setup instructions

### Quick Reference
- **`START_HERE.md`** - Getting started guide
- **`docs/architecture.md`** - Technical architecture decisions
- **`specs/ui_contract/`** - UI component specifications

## 👥 For Human Contributors

### Getting Started
1. **Set Up Environment**
   ```bash
   # Use the quick launch script
   RunSpectraApp.cmd
   
   # Or manual setup
   py -3.11 -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Verify Installation**
   ```bash
   pytest  # Run test suite
   python -m app.main  # Launch application
   ```

3. **Create Work Plan**
   - Create/update `docs/reviews/workplan.md` with your task breakdown
   - Define clear acceptance criteria
   - Identify documentation and testing requirements

### Development Workflow
1. **Create Feature Branch**
   ```bash
   git checkout -b feature/descriptive-name
   ```

2. **Follow Atomic PR Principles**
   - Small, focused changes (single feature/bug fix)
   - Complete test coverage
   - Comprehensive documentation
   - Clear commit messages

3. **PR Checklist**
   - [ ] All tests pass (`pytest`)
   - [ ] UI remains responsive with 1M+ point datasets
   - [ ] Documentation updated (user + developer)
   - [ ] Version bumped in `app/version.json`
   - [ ] Patch notes added to `docs/patch_notes/`
   - [ ] AI log updated in `docs/ai_log/`
   - [ ] No regression in existing functionality

## 🤖 For AI Agent Contributors

### Special Guidelines for AI Development

AI agents must adhere to additional guidelines to ensure consistency and maintainability:

#### Pre-Development Phase
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

#### Development Session Protocol

1. **Session Initialization**
   - Declare session start in work plan
   - State current goals and constraints
   - Confirm understanding of non-negotiable principles

2. **Implementation Loop**
   ```
   PLAN → IMPLEMENT → TEST → DOCUMENT → VALIDATE
   ```

3. **Quality Gates**
   - **Before Coding**: Verify against UI contract and architecture boundaries
   - **During Coding**: Follow existing patterns in `app/services/`
   - **After Coding**: Run full test suite and performance validation

#### Documentation Requirements for AI Work

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
   - Always bump version in `app/version.json`
   - Follow semantic versioning principles
   - Update patch notes with user-visible changes

3. **Provenance Tracking**
   - Ensure all data operations record source and transformations
   - Maintain unit conversion integrity
   - Preserve citation and attribution information

#### Safety and Validation Rules

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
- **Patch Notes**: `docs/patch_notes/` - User-visible changes
- **AI Log**: `docs/ai_log/` - Development rationale and decisions

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
- **Existing Patterns**: Study `docs/ai_log/` for similar work

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