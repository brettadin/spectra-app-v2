# IR Functional Groups and ML Integration - Quick Reference

**Last Updated**: 2025-10-25  
**Status**: Extended database ✅ complete; ML implementation 📋 planned

## Overview

The Spectra application now includes a comprehensive IR functional groups reference database with 50+ groups, up from the original 8. This expansion supports detailed organic chemistry analysis and sets the foundation for future machine learning-powered functional group identification.

## Current State (As of 2025-10-25)

### ✅ Completed: Extended IR Functional Groups Database

**File**: `app/data/reference/ir_functional_groups_extended.json`

**Coverage**: 50+ functional groups in 8 chemical families:
1. Hydroxyl groups (6 variants)
2. Carbonyl groups (7 variants)  
3. Amine groups (4 variants)
4. Aromatic groups (4 variants)
5. Aliphatic groups (5 variants)
6. Nitrogen groups (3 variants)
7. Sulfur groups (4 variants)
8. Halogen groups (4 variants)

**Integration**: Auto-detection via `ReferenceLibrary.ir_groups` property with graceful fallback to basic database

**Metadata per Group**:
- Wavenumber ranges (min, max, peak in cm⁻¹)
- Intensity descriptors (strong, medium, weak, variable)
- Vibrational modes (stretch, bend, rock, wag, twist)
- Chemical classes
- Related groups (co-occurrence patterns)
- Diagnostic value (1-5 scale)
- Identification notes

**Usage**:
- Reference tab → IR Functional Groups
- Filter by name, wavenumber, chemical class, or vibrational mode
- Preview on inspector plot
- Toggle "Show on plot" to overlay on main spectrum

## Planned: ML-Powered Functional Group Identification

### Implementation Phases (26 weeks total)

**Phase 1: Enhanced Rule-Based Analyzer** (4 weeks)
- Peak detection with scipy
- Match peaks to database ranges
- Contextual rules (e.g., COOH = broad O-H + sharp C=O)
- Confidence scoring
- Target: 80% precision, 70% recall, <100ms latency

**Phase 2: Data Collection & Preparation** (6 weeks)
- Download NIST WebBook IR spectra (~18K)
- Download SDBS spectra (~34K)
- Generate labels using RDKit molecular structure parsing
- Preprocess and augment data
- Store in HDF5/Parquet format

**Phase 3: Neural Network Prototype** (8 weeks)
- 1D CNN with multi-head attention
- Multi-label classification (50+ groups)
- Train on ~52K labeled spectra
- Target: 90% precision, 85% recall, <500ms GPU/<2s CPU

**Phase 4: UI Integration** (4 weeks)
- "Analyze Functional Groups" panel
- Confidence bars and evidence display
- Annotated spectrum view
- Export predictions with provenance
- Batch processing

**Phase 5: Hybrid Ensemble** (4 weeks)
- Combine rule-based + neural network
- Tunable weights (default 40%/60%)
- Interpretability features
- User feedback collection
- Target: 92% precision, 88% recall

## Quick Start for Developers

### Using the Extended Database (Current)

```python
from app.services.reference_library import ReferenceLibrary

# Load reference library
ref_lib = ReferenceLibrary()

# Get all IR functional groups (automatically uses extended database)
groups = ref_lib.ir_functional_groups()  # Returns list of 50+ group dicts

# Filter groups by wavenumber range
carbonyl_groups = [
    g for g in groups 
    if 1800 >= g.get("peak_cm1", 0) >= 1600
]

# Get metadata
metadata = ref_lib.ir_metadata()
print(f"Source: {metadata['source_id']}")
print(f"Version: {metadata['provenance']['version']}")
```

### Implementing Phase 1 (Future)

When implementing the rule-based analyzer:

```python
from scipy.signal import find_peaks
from app.services.units_service import UnitsService
from app.services.reference_library import ReferenceLibrary

class IRFunctionalGroupAnalyzer:
    def __init__(self):
        self.ref_lib = ReferenceLibrary()
        self.groups_db = self.ref_lib.ir_functional_groups()
    
    def analyze_spectrum(self, spectrum):
        # Convert to wavenumber if needed
        units = UnitsService()
        view = spectrum.view(units, "wavenumber", "absorbance")
        wavenumber, absorbance = view["x"], view["y"]
        
        # Detect peaks
        peaks, properties = find_peaks(
            absorbance,
            prominence=0.1,
            width=5
        )
        
        # Match peaks to functional groups
        predictions = []
        for peak_idx in peaks:
            peak_cm1 = wavenumber[peak_idx]
            for group in self.groups_db:
                if group["min_cm1"] <= peak_cm1 <= group["max_cm1"]:
                    confidence = self._calculate_confidence(
                        peak_cm1, 
                        absorbance[peak_idx],
                        group
                    )
                    predictions.append({
                        "group": group["name"],
                        "confidence": confidence,
                        "peak_position": peak_cm1,
                        "evidence": f"Peak at {peak_cm1:.0f} cm⁻¹"
                    })
        
        # Apply contextual rules
        predictions = self._apply_contextual_rules(predictions)
        
        # Rank by confidence
        return sorted(predictions, key=lambda p: p["confidence"], reverse=True)
    
    def _calculate_confidence(self, peak_cm1, intensity, group):
        # Gaussian likelihood based on distance from characteristic peak
        import math
        distance = abs(peak_cm1 - group["peak_cm1"])
        sigma = (group["max_cm1"] - group["min_cm1"]) / 6  # ~99% within range
        likelihood = math.exp(-0.5 * (distance / sigma) ** 2)
        
        # Adjust for intensity consistency
        # (implement based on group["intensity"] descriptor)
        
        return likelihood
    
    def _apply_contextual_rules(self, predictions):
        # Example: If both broad O-H (2500-3300) and sharp C=O (1710)
        # present, boost carboxylic acid confidence
        has_broad_oh = any(
            p["group"] == "O-H hydrogen-bonded" and p["confidence"] > 0.5
            for p in predictions
        )
        has_co_1710 = any(
            p["group"] == "C=O carboxylic acid" and 1700 <= p["peak_position"] <= 1720
            for p in predictions
        )
        
        if has_broad_oh and has_co_1710:
            for p in predictions:
                if p["group"] in ["O-H hydrogen-bonded", "C=O carboxylic acid"]:
                    p["confidence"] *= 1.2  # Boost confidence
                    p["evidence"] += " (carboxylic acid context)"
        
        return predictions
```

## File Locations

### Current Implementation
- Database: `app/data/reference/ir_functional_groups_extended.json`
- Service: `app/services/reference_library.py` (auto-detection logic)
- Tests: `tests/test_reference_library.py`

### Future ML Implementation (Planned)
- Rule-based: `app/services/ir_analysis.py` (Phase 1)
- Neural network: `app/services/ml/functional_group_predictor.py` (Phase 3)
- Hybrid ensemble: `app/services/ml/hybrid_predictor.py` (Phase 5)
- UI panel: `app/ui/functional_group_analysis_panel.py` (Phase 4)
- Tests: `tests/test_ir_analysis.py`, `tests/test_functional_group_analysis.py`

### Data Pipeline (Planned)
- NIST fetcher: `tools/data/fetch_nist_ir.py`
- SDBS fetcher: `tools/data/fetch_sdbs_ir.py`
- Label generator: `tools/data/generate_fg_labels.py`
- Training script: `tools/ml/train_fg_model.py`
- Model weights: `app/models/ir_fg_predictor_v1.h5` (not in repo; document regeneration)

## Documentation References

- **Complete specification**: `docs/specs/ml_functional_group_prediction.md`
- **Architectural decision**: `docs/brains/2025-10-25T0230-ir-ml-integration.md`
- **Atlas coverage**: 
  - Chapter 1, §3.1a: Comprehensive Functional Group Coverage
  - Chapter 7, §7a: IR Functional Group Identification — Hybrid Approach
- **User guide**: `docs/user/reference_data.md` (IR Functional Groups section)
- **Workplan**: `docs/reviews/workplan.md` (IR Functional Groups and ML Integration Roadmap)
- **Developer notes**: `docs/developer_notes.md` (IR Functional Groups and ML Integration section)

## Dependencies

### Current (Implemented)
- None beyond core requirements (scipy already available)

### Future ML Phases
```toml
# Add to requirements.txt when implementing ML features (mark as optional)
rdkit>=2023.3.1              # Phase 2: Molecular structure parsing
tensorflow>=2.13.0           # Phase 3: Neural network (or pytorch>=2.0.0)
scikit-learn>=1.3.0          # Phase 2-3: Preprocessing, metrics
h5py>=3.9.0                  # Phase 2: Efficient dataset storage
```

## Testing Strategy

### Current (Extended Database)
- ✅ Database loading: `tests/test_reference_library.py::test_ir_functional_groups`
- ✅ Auto-detection: `tests/test_reference_library.py::test_ir_groups_extended_fallback`
- ✅ UI integration: Reference tab loads and displays 50+ groups

### Future Phases
- **Phase 1**: Unit tests on synthetic spectra, integration tests on known compounds
- **Phase 3**: Hold-out test set (20%), 5-fold cross-validation, adversarial tests
- **Phase 5**: Ensemble consistency, interpretability validation, user acceptance testing

## Research References

1. **FG-BERT**: https://github.com/idrugLab/FG-BERT  
   Transformer-based functional group prediction from SMILES

2. **FTIR Neural Networks**: https://github.com/aaditagarwal/prediction_of_functional_groups  
   Direct spectral pattern learning

3. **NIST Chemistry WebBook**: https://webbook.nist.gov/chemistry/  
   Primary source for IR spectra (~18K spectra)

4. **SDBS Database**: https://sdbs.db.aist.go.jp/  
   AIST Japan spectral database (~34K IR spectra)

5. **RDKit**: https://www.rdkit.org/docs/  
   Molecular structure parsing for training label generation

6. **Spectroscopy Textbooks**:
   - Pavia et al. (2015). *Introduction to Spectroscopy*, 5th ed.
   - Silverstein et al. (2015). *Spectrometric Identification of Organic Compounds*, 8th ed.

## Key Principles

1. **Canonical unit storage**: IR data stored in cm⁻¹, never mutated
2. **Provenance-first**: All predictions recorded with method, confidence, evidence, model version
3. **Offline-first**: Extended database works without ML; rule-based works without neural network
4. **Immutable spectra**: Predictions are derived data, never modify original `Spectrum` objects
5. **Explainability**: Every prediction decomposes into understandable components
6. **Phased rollout**: Each phase delivers value independently; no "big bang" releases

## Change Log

- **2025-10-25**: Extended database (50+ groups) implemented and documented across all documentation areas
- **Future**: ML implementation phases to be tracked in this document as they progress
