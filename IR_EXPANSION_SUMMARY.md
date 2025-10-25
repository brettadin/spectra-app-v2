# IR Functional Group Database Expansion - Summary

## What Was Created

### 1. Extended IR Functional Groups Database
**File**: `app/data/reference/ir_functional_groups_extended.json`

**Content**:
- **50+ functional groups** (expanded from original 8)
- **Comprehensive coverage**: alcohols, carbonyls, amines, aromatics, nitriles, nitro, sulfur, phosphorus, halogens
- **Rich metadata** for each group:
  - Wavenumber ranges (min, max, peak)
  - Intensity descriptions
  - Associated vibrational modes
  - Chemical classes
  - Related functional groups
  - Diagnostic value ratings
  - Notes on identification

**Organization**:
- **8 major categories**: hydroxyl, carbonyl, amine, aromatic, aliphatic, nitrogen, sulfur, halogen groups
- **Relationship mapping**: Shows which groups appear together or are related
- **ML-ready format**: Structured for machine learning training

**Examples of New Groups**:
- O-H free vs hydrogen-bonded (distinguishes concentration effects)
- Specific carbonyl variants (ketone, aldehyde, ester, acid, amide, anhydride, acid chloride)
- Aromatic substitution patterns
- Nitro compounds (doublet pattern)
- Sulfur compounds (thiols, sulfoxides, sulfones)
- Halogen compounds
- Phosphates (for biochemistry)

### 2. ML Prediction Design Document
**File**: `docs/specs/ml_functional_group_prediction.md`

**Comprehensive roadmap including**:
- **3-Phase Implementation**:
  1. Enhanced rule-based peak detection (immediate)
  2. Neural network predictor (medium-term)
  3. Hybrid ensemble system (advanced)

- **Technical Architecture**:
  - Peak detection with scipy
  - 1D CNN with attention mechanisms
  - Multi-label classification
  - Confidence scoring
  - Interpretability features

- **Data Strategy**:
  - Training sources: NIST WebBook (~18K spectra), SDBS (~34K spectra)
  - Label generation using RDKit molecular structure parsing
  - Data augmentation techniques
  - Storage in HDF5/Parquet format

- **Implementation Milestones**:
  - Phase 1: 4 weeks - Enhanced rule-based system
  - Phase 2: 6 weeks - Data collection & preparation
  - Phase 3: 8 weeks - Neural network prototype
  - Phase 4: 4 weeks - Integration & UI
  - Phase 5: 4 weeks - Hybrid ensemble

- **Performance Targets**:
  - Rule-based: 80% precision, 70% recall
  - Neural network: 90% precision, 85% recall
  - Ensemble: 92% precision, 88% recall

- **UI/UX Design**:
  - Functional Group Analysis panel with confidence scores
  - Annotated spectrum view with color-coded regions
  - Evidence display showing diagnostic peaks
  - Export functionality

### 3. Code Integration
**File**: `app/services/reference_library.py`

**Change**: Modified `ir_groups` property to automatically use extended database when available:
```python
@property
def ir_groups(self) -> Path:
    # Try extended database first, fall back to basic
    extended = self.base_dir / "ir_functional_groups_extended.json"
    if extended.exists():
        return extended
    return self.base_dir / "ir_functional_groups.json"
```

## How It Works Now

1. **Current State**: The app will now load 50+ functional groups instead of 8 when you switch to the IR Functional Groups tab
2. **Display**: All groups show in the table with wavenumber ranges
3. **Preview**: Overlay shows band positions on preview plot
4. **Checkbox**: User clicks "Show on plot" to apply overlay to main spectrum

## Next Steps to Enable ML Prediction

### Immediate (Can Start Now)
1. **Implement Peak Detection**:
   ```python
   from scipy.signal import find_peaks
   
   # Detect peaks in IR spectrum
   peaks, properties = find_peaks(
       absorbance, 
       prominence=0.1,  # Adjust for signal strength
       width=5          # Adjust for peak sharpness
   )
   ```

2. **Match Peaks to Database**:
   - Compare detected peak positions to functional group ranges
   - Score matches based on intensity, width, position accuracy
   - Apply contextual rules (e.g., C=O + broad O-H = COOH)

### Short-Term (1-2 months)
1. **Data Collection**:
   - Script to scrape NIST WebBook IR spectra (with permission/API)
   - Use RDKit to parse molecular structures into functional group labels
   - Build training dataset: (spectrum, label_vector) pairs

2. **Initial ML Model**:
   - Simple 1D CNN for proof-of-concept
   - Train on subset of data (1000-5000 spectra)
   - Evaluate and iterate

### Medium-Term (3-6 months)
1. **Full Neural Network**:
   - Attention-based architecture
   - Large-scale training (10K+ spectra)
   - Hyperparameter optimization
   - Cross-validation

2. **Integration**:
   - Add "Analyze Functional Groups" button
   - Display predictions with confidence
   - Show supporting evidence

### Long-Term (6-12 months)
1. **Hybrid Ensemble**:
   - Combine rule-based + ML predictions
   - Active learning from user corrections
   - Multi-modal learning (IR + NMR + MS)

## Research References Used

### FG-BERT (idrugLab)
- **Approach**: BERT-style transformer with functional group masking
- **Key Insight**: Self-supervised pre-training on large molecular databases
- **Limitation**: Requires SMILES input, not directly applicable to spectra
- **Adaptation**: Use similar attention mechanism in spectral domain

### FTIR Functional Group Prediction (aaditagarwal)
- **Approach**: Neural network on FTIR data
- **Key Insight**: Direct spectral pattern learning
- **Challenge**: Requires large labeled dataset
- **Adaptation**: Combine with rule-based system for sparse data regime

## Benefits of This Approach

1. **Comprehensive Coverage**: 6x more functional groups than before
2. **Scientific Rigor**: All data sourced from authoritative references (NIST, Pavia, Silverstein)
3. **Practical Design**: Phased implementation allows incremental value
4. **ML-Ready**: Database structure supports both traditional and ML approaches
5. **Interpretability**: Hybrid system explains predictions with evidence
6. **Extensible**: Easy to add more groups or new prediction methods

## Testing the Extended Database

Try it now:
1. Launch Spectra app
2. Switch to Reference tab → IR Functional Groups
3. You should see 50+ groups instead of 8
4. Filter them (e.g., search "carbonyl" to see all C=O variants)
5. Click "Show on plot" to overlay bands on your spectrum

## Dependencies for ML Features

When ready to implement ML:
```bash
pip install scipy           # Peak detection (already have)
pip install rdkit          # Molecular structure parsing
pip install tensorflow     # or pytorch for neural networks
pip install scikit-learn   # Preprocessing, metrics
pip install h5py           # Efficient data storage
```

## Questions?

The design document has detailed pseudocode, architecture diagrams, and implementation guidance. Ready to proceed with Phase 1 (rule-based peak detection) whenever you'd like!
