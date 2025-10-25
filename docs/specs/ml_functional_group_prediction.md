# ML-Based Functional Group Prediction for IR Spectra

## Overview

This document outlines the design for integrating machine learning-based functional group prediction into the Spectra application, enabling automated identification of chemical functional groups from infrared spectroscopy data.

## Background Research

### Existing Approaches

1. **FG-BERT** (idrugLab)
   - **Method**: BERT-style transformer model with masked functional group prediction pre-training
   - **Input**: SMILES strings converted to molecular graphs
   - **Output**: Predicts presence/absence of 85 functional groups
   - **Strengths**: Self-supervised learning, high accuracy on downstream tasks
   - **Limitations**: Requires molecular structure (SMILES), not directly applicable to IR spectra

2. **FTIR Functional Group Prediction** (aaditagarwal)
   - **Method**: Neural network trained on FTIR spectroscopy data
   - **Input**: FTIR spectra (wavelength vs absorbance/transmittance)
   - **Output**: Multi-label classification of functional groups
   - **Strengths**: Directly uses spectral data, chemometric analysis
   - **Limitations**: Requires large labeled training dataset

### Proposed Hybrid Approach

We will implement a **spectral pattern recognition system** that combines:
1. Traditional peak detection and rule-based identification
2. Neural network-based pattern matching for ambiguous cases
3. Ensemble learning with spectral features and chemical context

## Architecture

### Phase 1: Enhanced Rule-Based System (Current Implementation)

**Status**: Partially implemented in `ReferenceLibrary.ir_functional_groups()`

**Enhancements**:
```python
class IRFunctionalGroupAnalyzer:
    """Enhanced analyzer with peak detection and pattern matching."""
    
    def analyze_spectrum(self, spectrum: Spectrum) -> List[FunctionalGroupPrediction]:
        """
        Analyze IR spectrum and predict functional groups.
        
        Args:
            spectrum: Spectrum object with x (wavenumber cm⁻¹) and y (absorbance/transmittance)
            
        Returns:
            List of predictions with confidence scores and evidence
        """
        # 1. Convert to wavenumber if needed
        wavenumber_cm1, absorbance = self._prepare_spectrum(spectrum)
        
        # 2. Peak detection with SciPy
        peaks = self._detect_peaks(wavenumber_cm1, absorbance)
        
        # 3. Match peaks to functional group database
        matches = self._match_peaks_to_groups(peaks)
        
        # 4. Apply contextual rules (e.g., broad O-H + C=O = carboxylic acid)
        predictions = self._apply_contextual_rules(matches)
        
        # 5. Score and rank predictions
        return self._rank_predictions(predictions)
```

**Key Features**:
- Peak detection using `scipy.signal.find_peaks` with prominence and width filtering
- Confidence scoring based on:
  - Peak intensity vs expected intensity
  - Peak width (sharp vs broad)
  - Peak position accuracy
  - Presence of correlated peaks (e.g., C=O with O-H for COOH)
- Pattern matching for characteristic doublets/multiplets

### Phase 2: Neural Network Predictor (Future Implementation)

**Model Architecture**:
```
Input Layer: 
  - IR spectrum resampled to fixed wavenumber grid (e.g., 4000-400 cm⁻¹ at 2 cm⁻¹ resolution)
  - Shape: (1800,) for absorbance values

Convolutional Layers:
  - Conv1D layers to capture local spectral features
  - Pooling to reduce dimensionality
  - Residual connections for deep feature learning

Attention Mechanism:
  - Self-attention to focus on diagnostic regions
  - Multi-head attention for different functional group families

Output Layer:
  - Multi-label classification (50-100 functional groups)
  - Sigmoid activation for independent probabilities
  - Threshold tuning for precision/recall balance
```

**Training Strategy**:
```python
# Pseudo-code for training pipeline
class FunctionalGroupPredictor:
    def __init__(self):
        self.model = self._build_model()
        self.scaler = StandardScaler()
        
    def _build_model(self):
        """Build 1D CNN with attention for IR spectra."""
        return Sequential([
            Conv1D(64, kernel_size=11, activation='relu', padding='same'),
            MaxPooling1D(2),
            Conv1D(128, kernel_size=7, activation='relu', padding='same'),
            MaxPooling1D(2),
            MultiHeadAttention(num_heads=4, key_dim=128),
            GlobalAveragePooling1D(),
            Dense(256, activation='relu'),
            Dropout(0.3),
            Dense(num_functional_groups, activation='sigmoid')
        ])
    
    def train(self, spectra: List[Spectrum], labels: np.ndarray):
        """
        Train on labeled IR spectra.
        
        Args:
            spectra: List of IR spectrum objects
            labels: (n_samples, n_functional_groups) binary matrix
        """
        # Preprocess and augment data
        X = self._preprocess_spectra(spectra)
        X_aug = self._augment_data(X)
        
        # Train with class weights for imbalanced data
        self.model.fit(
            X_aug, labels,
            validation_split=0.2,
            epochs=100,
            callbacks=[EarlyStopping(), ModelCheckpoint()]
        )
```

**Data Augmentation**:
- Baseline correction variations
- Noise addition (realistic instrument noise)
- Spectral shifting (±5 cm⁻¹)
- Intensity scaling
- Peak broadening/sharpening

### Phase 3: Hybrid Ensemble (Advanced)

**Combination Strategy**:
```python
class HybridFunctionalGroupPredictor:
    def __init__(self):
        self.rule_based = IRFunctionalGroupAnalyzer()
        self.neural_net = FunctionalGroupPredictor()
        self.ensemble_weights = {'rules': 0.4, 'nn': 0.6}
        
    def predict(self, spectrum: Spectrum) -> List[FunctionalGroupPrediction]:
        """Ensemble prediction combining rule-based and ML approaches."""
        # Get predictions from both systems
        rule_predictions = self.rule_based.analyze_spectrum(spectrum)
        nn_predictions = self.neural_net.predict(spectrum)
        
        # Weighted ensemble
        final_predictions = self._combine_predictions(
            rule_predictions, 
            nn_predictions,
            weights=self.ensemble_weights
        )
        
        # Add interpretability (show which method contributed)
        return self._add_interpretability(final_predictions)
```

## Data Requirements

### Training Data Sources

1. **NIST Chemistry WebBook**
   - Source: https://webbook.nist.gov/chemistry/
   - ~18,000 IR spectra with chemical structures
   - Functional groups can be extracted from SMILES/InChI

2. **SDBS (Spectral Database for Organic Compounds)**
   - Source: https://sdbs.db.aist.go.jp/
   - ~34,000 IR spectra
   - Includes chemical structure data

3. **Bio-Rad/Sadtler IR Database**
   - Commercial but comprehensive
   - ~200,000+ spectra with annotations

4. **ChemSpider**
   - API access to chemical structures
   - Can link to spectral databases

### Data Preparation Pipeline

```python
class IRTrainingDataBuilder:
    """Build training dataset from spectral databases."""
    
    def build_dataset(self, source: str) -> pd.DataFrame:
        """
        Extract and label IR spectra with functional groups.
        
        Pipeline:
        1. Download/load IR spectra
        2. Extract molecular structure (SMILES/InChI)
        3. Parse structure to identify functional groups using RDKit
        4. Create binary label matrix (n_samples, n_functional_groups)
        5. Preprocess spectra (baseline, normalization, resampling)
        6. Save as HDF5/Parquet for efficient loading
        """
        spectra = self._load_spectra(source)
        structures = self._extract_structures(spectra)
        labels = self._identify_functional_groups(structures)
        
        return self._create_training_dataset(spectra, labels)
    
    def _identify_functional_groups(self, smiles: List[str]) -> np.ndarray:
        """Use RDKit to identify functional groups from SMILES."""
        from rdkit import Chem
        from rdkit.Chem import Fragments
        
        fg_matrix = []
        for smi in smiles:
            mol = Chem.MolFromSmiles(smi)
            fg_vector = [
                Fragments.fr_Al_OH(mol),        # Alcohols
                Fragments.fr_Ar_OH(mol),        # Phenols
                Fragments.fr_ketone(mol),       # Ketones
                Fragments.fr_aldehyde(mol),     # Aldehydes
                Fragments.fr_ester(mol),        # Esters
                Fragments.fr_amide(mol),        # Amides
                # ... 50+ functional group descriptors available
            ]
            fg_matrix.append([int(count > 0) for count in fg_vector])
        
        return np.array(fg_matrix)
```

## Implementation Roadmap

### Milestone 1: Enhanced Rule-Based System (4 weeks)
- [ ] Implement peak detection with `scipy.signal.find_peaks`
- [ ] Create comprehensive functional group database (done - 50+ groups)
- [ ] Build peak-to-group matching algorithm
- [ ] Implement contextual rules for group interactions
- [ ] Add confidence scoring system
- [ ] Create UI for displaying predictions with evidence
- [ ] Write unit tests for peak detection and matching

### Milestone 2: Data Collection & Preparation (6 weeks)
- [ ] Scrape/download NIST WebBook IR spectra (with permission)
- [ ] Extract chemical structures and metadata
- [ ] Use RDKit to generate functional group labels
- [ ] Preprocess spectra (baseline correction, normalization)
- [ ] Create train/validation/test splits
- [ ] Build data augmentation pipeline
- [ ] Store in efficient format (HDF5/Parquet)

### Milestone 3: Neural Network Prototype (8 weeks)
- [ ] Implement 1D CNN architecture in TensorFlow/PyTorch
- [ ] Add attention mechanisms
- [ ] Train initial model on subset of data
- [ ] Evaluate performance (precision, recall, F1)
- [ ] Tune hyperparameters
- [ ] Implement model persistence and loading
- [ ] Create prediction API

### Milestone 4: Integration & UI (4 weeks)
- [ ] Integrate ML predictor into Spectra app
- [ ] Create "Analyze Functional Groups" button/tab
- [ ] Display predictions with confidence bars
- [ ] Show supporting evidence (peaks, patterns)
- [ ] Add export functionality for predictions
- [ ] Implement batch processing
- [ ] Write integration tests

### Milestone 5: Hybrid Ensemble (4 weeks)
- [ ] Implement ensemble prediction logic
- [ ] Tune ensemble weights
- [ ] Add interpretability features
- [ ] Compare performance: rules-only vs NN-only vs ensemble
- [ ] Document prediction methodology
- [ ] Create user guide

## Technical Dependencies

### Python Packages
```toml
# Add to requirements.txt or pyproject.toml
scipy >= 1.11.0           # Peak detection
numpy >= 1.24.0           # Numerical operations
pandas >= 2.0.0           # Data handling
rdkit >= 2023.3.1         # Molecular structure parsing
tensorflow >= 2.13.0      # Neural network (or pytorch)
scikit-learn >= 1.3.0     # Preprocessing, metrics
h5py >= 3.9.0             # Efficient data storage
```

### Optional ML Frameworks
- **TensorFlow/Keras**: Easier for prototyping, better documentation
- **PyTorch**: More flexible, better for research
- **JAX**: Fastest, but steeper learning curve

## UI/UX Design

### Functional Group Analysis Panel

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
│  │                                                    │ │
│  │ ⚫ Aromatic Ring (C=C)        Confidence: 88%     │ │
│  │    Evidence: C-H 3030, C=C 1600, 1500 cm⁻¹       │ │
│  │                                                    │ │
│  │ ⚪ Primary Amine (NH₂)        Confidence: 42%     │ │
│  │    Evidence: Weak doublet ~3400 cm⁻¹ (uncertain) │ │
│  └───────────────────────────────────────────────────┘ │
│                                                          │
│  [ Show Annotated Spectrum ]  [ Export Results ]        │
└─────────────────────────────────────────────────────────┘
```

### Annotated Spectrum View

Show spectrum with functional group regions highlighted and labeled:
- Color-coded bands for each identified group
- Tooltips showing diagnostic peaks
- Toggle visibility of each functional group

## Performance Metrics

### Rule-Based System
- **Target**: 80% precision, 70% recall for common groups
- **Speed**: Real-time (<100ms per spectrum)

### Neural Network
- **Target**: 90% precision, 85% recall for common groups
- **Speed**: <500ms per spectrum (GPU), <2s (CPU)

### Ensemble
- **Target**: 92% precision, 88% recall
- **Interpretability**: Show contribution from each method

## Future Enhancements

1. **Active Learning**: User corrections improve model
2. **Transfer Learning**: Pre-train on large chemical databases, fine-tune on specific domains
3. **Uncertainty Quantification**: Bayesian neural networks for better confidence estimates
4. **Multi-Modal Learning**: Combine IR with NMR, MS, UV-Vis data
5. **Compound Suggestion**: Suggest possible molecular structures based on functional groups
6. **Literature Integration**: Link predictions to reference papers and examples

## References

1. FG-BERT: https://github.com/idrugLab/FG-BERT
2. FTIR Prediction: https://github.com/aaditagarwal/prediction_of_functional_groups
3. Pavia et al. (2015). Introduction to Spectroscopy, 5th ed.
4. Silverstein et al. (2015). Spectrometric Identification of Organic Compounds, 8th ed.
5. NIST Chemistry WebBook: https://webbook.nist.gov/chemistry/
6. RDKit Documentation: https://www.rdkit.org/docs/
