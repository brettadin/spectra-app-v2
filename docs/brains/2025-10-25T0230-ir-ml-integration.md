# IR Functional Groups Database Expansion and ML Integration Strategy

**Timestamp (UTC)**: 2025-10-25T02:30:00Z  
**Timestamp (EDT)**: 2025-10-24T22:30:00-04:00  
**Authors**: GitHub Copilot Agent, User Direction  
**Related Atlas Chapters**: 1 (Modalities), 7 (Identification and Prediction Logic)  
**Source Docs**: `docs/specs/ml_functional_group_prediction.md`, `IR_EXPANSION_SUMMARY.md`, `docs/history/KNOWLEDGE_LOG.md`

## Context

The application initially provided basic IR functional group reference data (8 groups: C-H, O-H, N-H, C=O, C=C, C-N, C-O, aromatic) for educational spectroscopy workflows. Users required comprehensive coverage to support advanced organic chemistry instruction and research applications, particularly for:

1. **Educational lab workflows**: Students comparing lab-collected IR/FTIR spectra with planetary/stellar observations need detailed functional group identification
2. **Multi-modal analysis**: Integration with UV-VIS, Raman, and other modalities requires rich chemical context
3. **Automated identification**: Manual peak-by-peak analysis is time-consuming; ML-powered suggestions with confidence scores improve workflow efficiency
4. **Provenance requirements**: All predictions must be explainable with supporting evidence (diagnostic peaks, intensity patterns, contextual rules)

Research into existing ML approaches revealed two promising architectures:
- **FG-BERT** (idrugLab): Transformer-based model using SMILES strings for functional group prediction
- **FTIR Neural Networks** (aaditagarwal): Direct spectral pattern learning from IR data

Challenge: FG-BERT requires molecular structure input (not available from raw spectra alone), while pure neural approaches require large labeled training datasets (10K+ spectra with ground-truth functional group annotations).

## Decision

**Implement a three-tier hybrid system with phased rollout:**

### Tier 1: Extended Reference Database (Completed)
- Expanded IR functional groups from 8 to 50+ with comprehensive metadata
- Organized into 8 major chemical families: hydroxyl, carbonyl, amine, aromatic, aliphatic, nitrogen, sulfur, halogen
- Each group includes:
  - Wavenumber ranges: minimum, maximum, characteristic peak (cm⁻¹)
  - Intensity descriptors: strong, medium, weak, variable
  - Vibrational modes: stretch, bend, rock, wag, twist
  - Chemical classes and related functional groups
  - Diagnostic value ratings (1-5 scale)
  - Identification notes and interference patterns
- Database stored at `app/data/reference/ir_functional_groups_extended.json`
- Auto-detection in `ReferenceLibrary.ir_groups` property with graceful fallback
- **Status**: ✅ Complete, integrated, tested

### Tier 2: Enhanced Rule-Based Analyzer (Phase 1 - 4 weeks)
- Peak detection using `scipy.signal.find_peaks` with prominence/width filtering
- Match detected peaks to functional group database ranges
- Contextual rules for group interactions (e.g., broad O-H + sharp C=O at 1710 cm⁻¹ = carboxylic acid)
- Confidence scoring based on:
  - Peak position accuracy (Gaussian likelihood)
  - Intensity consistency with expected patterns
  - Presence/absence of correlated peaks
  - Pattern matching for doublets/multiplets (e.g., nitro group doublet)
- **Status**: 📋 Design complete, implementation pending

### Tier 3: Neural Network Predictor (Phases 2-3 - 14 weeks)
- **Data Collection (Phase 2 - 6 weeks)**:
  - NIST Chemistry WebBook: ~18,000 IR spectra with SMILES
  - SDBS (AIST Japan): ~34,000 IR spectra with structures
  - Use RDKit to parse molecular structures into functional group labels
  - Generate (spectrum, label_vector) training pairs
  - Apply data augmentation: baseline shifts, noise injection, spectral shifting (±5 cm⁻¹), intensity scaling
  - Store in HDF5/Parquet for efficient loading
- **Model Architecture (Phase 3 - 8 weeks)**:
  - 1D CNN with residual connections
  - Multi-head self-attention to focus on diagnostic regions
  - Multi-label classification (sigmoid output for independent probabilities)
  - Input: IR spectrum resampled to 4000-400 cm⁻¹ at 2 cm⁻¹ resolution (1800 points)
  - Output: Probability vector for 50+ functional groups
- **Status**: 📋 Design complete, awaiting Phase 2 start

### Tier 4: Hybrid Ensemble (Phase 5 - 4 weeks)
- Combine rule-based and neural network predictions with tunable weights
- Default ensemble: 40% rule-based, 60% neural network
- Interpretability features:
  - Show which method contributed to each prediction
  - Display supporting evidence (diagnostic peaks, patterns, neural attention maps)
  - Allow user feedback to tune ensemble weights per session
- **Status**: 📋 Design complete, implementation after Phase 3

## Architectural Constraints

1. **Canonical unit storage**: IR data stored in cm⁻¹ (wavenumber) internally, never mutated
2. **Provenance-first**: All predictions recorded with:
   - Method used (rule-based, neural, ensemble)
   - Confidence score with uncertainty bounds
   - Supporting evidence (peak list, attention weights)
   - Model version and training data provenance
3. **Offline-first**: Extended database and rule-based system work without internet; ML models packaged for offline use once trained
4. **Immutable spectra**: Predictions are derived data, never modify original `Spectrum` objects
5. **Explainability**: Every prediction must decompose into understandable components (peaks, patterns, rules)

## UI/UX Design

**Functional Group Analysis Panel** (Phase 4):
```
┌─────────────────────────────────────────────────────────┐
│  Functional Group Analysis                              │
├─────────────────────────────────────────────────────────┤
│  Method: ☑ Rule-Based  ☑ Neural Network  ☐ Ensemble    │
│                                                          │
│  Detected Functional Groups:                            │
│  ┌───────────────────────────────────────────────────┐ │
│  │ ⚫ Carboxylic Acid (COOH)     Confidence: 95%     │ │
│  │    Evidence: Broad O-H 2500-3300, C=O 1710 cm⁻¹  │ │
│  │    [Show peaks on spectrum]                       │ │
│  │                                                    │ │
│  │ ⚫ Aromatic Ring (C=C)        Confidence: 88%     │ │
│  │    Evidence: C-H 3030, C=C 1600, 1500 cm⁻¹       │ │
│  │    [Show peaks on spectrum]                       │ │
│  │                                                    │ │
│  │ ⚪ Primary Amine (NH₂)        Confidence: 42%     │ │
│  │    Evidence: Weak doublet ~3400 cm⁻¹ (uncertain) │ │
│  │    [Show peaks on spectrum]                       │ │
│  └───────────────────────────────────────────────────┘ │
│                                                          │
│  [ Analyze Current Spectrum ]  [ Export Results ]       │
└─────────────────────────────────────────────────────────┘
```

**Annotated Spectrum View**:
- Overlay color-coded regions on main plot for each predicted group
- Tooltips showing diagnostic peak positions and intensities
- Toggle visibility per functional group
- Export annotated spectrum as image with labels

## Performance Targets

| System Component | Precision | Recall | Latency | Notes |
|-----------------|-----------|--------|---------|-------|
| Rule-Based (Phase 1) | 80% | 70% | <100ms | Common groups, high specificity |
| Neural Network (Phase 3) | 90% | 85% | <500ms GPU / <2s CPU | Requires training data |
| Hybrid Ensemble (Phase 5) | 92% | 88% | <600ms | Best of both approaches |

Metrics evaluated on hold-out test set (20% of collected data) with manual verification on challenging cases.

## Consequences

### Immediate Benefits
1. ✅ **50+ functional groups available now** via extended database
2. ✅ **Educational value**: Students can explore comprehensive IR reference data
3. ✅ **Manual identification support**: Rich metadata guides manual peak interpretation
4. ✅ **Future-ready structure**: Database designed for ML training consumption

### Phase 1 Outcomes (4 weeks)
- Automated peak detection with confidence scores
- Contextual rule engine for ambiguous cases
- Real-time analysis (<100ms per spectrum)
- Explainable predictions with diagnostic peak evidence

### Phases 2-3 Outcomes (14 weeks)
- ~52,000 labeled training examples (NIST + SDBS)
- Trained 1D CNN model with 90%/85% precision/recall
- Model packaging for offline deployment
- Attention visualization showing which spectral regions influenced predictions

### Phase 4 Outcomes (4 weeks)
- Integrated UI panel for functional group analysis
- Export predictions to CSV/JSON with provenance
- Batch processing for multiple spectra
- User feedback collection for active learning

### Phase 5 Outcomes (4 weeks)
- Hybrid ensemble with tunable weights
- Comparison mode: see rule-based vs neural predictions side-by-side
- Active learning: user corrections improve future predictions
- Documentation and user guide for prediction methodology

### Long-Term Extensibility
- **Multi-modal fusion**: Combine IR predictions with NMR, MS, UV-Vis data for compound-level identification
- **Transfer learning**: Pre-train on large databases, fine-tune for specific domains (polymers, pharmaceuticals, minerals)
- **Bayesian uncertainty**: Upgrade to probabilistic neural networks for better confidence estimates
- **Community contributions**: Allow users to contribute labeled spectra to improve model

## Dependencies

### Current (Phase 1)
```toml
scipy >= 1.11.0          # Peak detection (already installed)
numpy >= 1.24.0          # Numerical operations (already installed)
```

### Future ML Phases (2-5)
```toml
rdkit >= 2023.3.1        # Molecular structure parsing for label generation
tensorflow >= 2.13.0     # Neural network training/inference (or pytorch)
scikit-learn >= 1.3.0    # Preprocessing, metrics, cross-validation
h5py >= 3.9.0            # Efficient dataset storage
pandas >= 2.0.0          # Data manipulation (already installed)
```

All ML dependencies remain **optional**; extended database and rule-based system work without them.

## Testing Strategy

### Phase 1 Tests
- Unit tests: Peak detection on synthetic spectra with known peaks
- Integration tests: Analyze known compounds (benzoic acid, acetone, ethanol) and verify functional group detection
- Performance tests: Ensure <100ms latency on typical IR spectra (1800 points)

### Phase 3 Tests
- Model validation: Hold-out test set (20%) never seen during training
- Cross-validation: 5-fold CV on training set
- Adversarial testing: Spectra with overlapping bands, noisy baselines, truncated ranges
- Regression tests: Ensure model updates don't degrade performance on established benchmarks

### Phase 5 Tests
- Ensemble consistency: Verify predictions stable across multiple runs
- Interpretability: Manual review of 100 random predictions to verify explanations match domain knowledge
- User acceptance: Beta testing with chemistry instructors and students

## Migration Path

**Existing users** (using 8-group database):
- No breaking changes; extended database is backward-compatible
- Existing overlays continue to work
- New groups appear in Reference tab automatically when database available

**Future ML users**:
- Rule-based predictions available immediately (Phase 1)
- Neural predictions opt-in via settings (Phase 3)
- Ensemble predictions default after Phase 5 with fallback to rule-based if model unavailable

## References

### Internal Documentation
- `docs/specs/ml_functional_group_prediction.md` - Complete technical specification
- `IR_EXPANSION_SUMMARY.md` - Summary of database expansion and testing guidance
- `app/data/reference/ir_functional_groups_extended.json` - Extended database with 50+ groups
- `app/services/reference_library.py` - Database loading with auto-detection

### External Research
1. **FG-BERT**: https://github.com/idrugLab/FG-BERT  
   Y. Li et al., "FG-BERT: Pre-training BERT on Functional Groups for Drug Discovery"
2. **FTIR Functional Group Prediction**: https://github.com/aaditagarwal/prediction_of_functional_groups  
   Neural network approach for direct spectral analysis
3. **NIST Chemistry WebBook**: https://webbook.nist.gov/chemistry/  
   Primary source for IR spectra and chemical structures (~18K spectra)
4. **SDBS Database**: https://sdbs.db.aist.go.jp/  
   AIST Japan spectral database (~34K IR spectra)

### Spectroscopy References
- D.L. Pavia et al. (2015). *Introduction to Spectroscopy*, 5th ed., Cengage Learning
- R.M. Silverstein et al. (2015). *Spectrometric Identification of Organic Compounds*, 8th ed., Wiley
- RDKit Documentation: https://www.rdkit.org/docs/ (for functional group extraction)

## Future Enhancements

1. **Active Learning**: User corrections fed back to improve model (continuous training pipeline)
2. **Compound-Level Identification**: Combine functional groups + molecular formulas → suggest molecular structures
3. **Multi-Modal Integration**: IR + NMR + MS fusion for comprehensive compound identification
4. **Literature Linking**: Connect predictions to reference papers and example spectra in literature databases
5. **Custom Training**: Allow advanced users to fine-tune model on institution-specific compound libraries
6. **Uncertainty Quantification**: Bayesian neural networks or ensemble disagreement for confidence intervals
7. **Real-Time Feedback**: Show predictions updating as user adjusts baseline correction or peak parameters

## Change Log

- **2025-10-25**: Initial brains entry documenting extended IR database, ML design, and phased implementation strategy
