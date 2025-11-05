# Reference Data Browser

The **Reference** tab in the Inspector exposes curated spectroscopy datasets that ship with the preview shell. All
entries are stored in `app/data/reference` so they can be browsed without a network connection and reused by agents or
future automation. Each dataset advertises a `provenance` status in the metadata pane so you can distinguish
authoritative NIST assets from digitised JWST placeholders that still need regeneration. For additional leads (UV/VIS,
IR, mass spectrometry, elemental standards, instrument handbooks), consult `docs/link_collection.md`—it tracks
spectroscopy-focused resources that align with the app’s analytical goals.

## NIST spectral line queries

- Source: [NIST Atomic Spectra Database (ver. 5.11)](https://physics.nist.gov/asd) — Y. Ralchenko, A.E. Kramida,
  J. Reader, and the NIST ASD Team (2024).
- Controls: the **Spectral lines** tab exposes element, ion stage (Roman or numeric), wavelength bounds, a vacuum/air
  selector, a “Prefer Ritz wavelengths” toggle, and a **Pinned line sets** browser. Enter an element symbol (e.g. `Fe`), refine
  the bounds to the region of interest, and press **Fetch lines**. Example presets (Hydrogen I, Helium II, Iron II)
  pre-populate the fields when you need a quick sanity check. Use **Use uniform line colour** to collapse every pinned set to a
  single hue when the rainbow becomes distracting.
- Results: the table lists the observed and Ritz wavelengths (nm), relative and normalised intensities, lower/upper energy
  levels, and transition type. Metadata on the right records the astroquery provenance, wavelength medium, and retrieval
  timestamp so notebook and CI runs can reference identical queries. Each fetch is automatically pinned so multiple species or
  ranges can remain visible simultaneously.
- Overlay: the preview plot renders each transition as a bar scaled by the normalised intensity and keeps every pinned set on
  screen using distinct palette colours (or the uniform colour, when enabled). When you toggle **Overlay on plot**, all pinned
  sets are projected into the main workspace in the current unit system so you can compare multiple laboratory references
  against imported spectra without re-parsing JSON manifests.
- **Caching**: NIST line lists are automatically cached on disk (in `downloads/_cache/line_lists/`) after the first fetch. Subsequent
  queries for the same element, ion stage, and wavelength range return instantly from the cache without hitting the network. Cache
  entries expire after 365 days (spectral lines are stable reference data). Cached fetches show a `[cached]` indicator in the status
  message. Use the **Clear Cache** button to remove all cached line lists (e.g., to force fresh downloads or free disk space). The cache
  can be disabled entirely by setting the `SPECTRA_DISABLE_LINE_CACHE=1` environment variable before launching the app.

## Infrared functional groups

- Primary reference: [NIST Chemistry WebBook](https://webbook.nist.gov/chemistry/) — P.J. Linstrom and W.G. Mallard
  (2024 update); supplemental ranges from Pavia *et al.*, *Introduction to Spectroscopy*, 5th ed. (2015); Silverstein
  *et al.*, *Spectrometric Identification of Organic Compounds*, 8th ed. (2015); and SDBS (AIST Japan) database.

### Extended Database (50+ Functional Groups)

**As of 2025-10-25**, the application provides a comprehensive IR functional groups database with **50+ groups** organized into 8 chemical families:

**Coverage**:
1. **Hydroxyl groups** (6 variants): O-H free, hydrogen-bonded, phenolic, carboxylic; primary/secondary alcohols
2. **Carbonyl groups** (7 variants): ketone, aldehyde, ester, carboxylic acid, amide, anhydride, acid chloride
3. **Amine groups** (4 variants): primary (NH₂), secondary (NH), tertiary (N), with characteristic doublets/singlets
4. **Aromatic groups** (4 variants): C-H aromatic stretch, C=C stretch/bending, out-of-plane bending (substitution patterns)
5. **Aliphatic groups** (5 variants): sp³/sp²/sp C-H systems, C=C alkene, C≡C alkyne
6. **Nitrogen groups** (3 variants): nitrile (C≡N), nitro (characteristic doublet), azo (N=N)
7. **Sulfur groups** (4 variants): thiol (S-H), sulfoxide (S=O), sulfone (SO₂), disulfide (S-S)
8. **Halogen groups** (4 variants): C-F, C-Cl, C-Br, C-I with characteristic frequencies

**Rich Metadata**: Each functional group includes:
- **Wavenumber ranges**: minimum, maximum, and characteristic peak positions (cm⁻¹)
- **Intensity descriptors**: strong, medium, weak, variable (concentration/matrix-dependent)
- **Vibrational modes**: stretch (ν), bend (δ), rock (ρ), wag (ω), twist (τ), symmetric/asymmetric
- **Chemical classes**: alcohols, ketones, aromatic, etc.
- **Related groups**: functional groups that commonly co-occur (e.g., carboxylic acid has both C=O and O-H)
- **Diagnostic value** (1-5 scale): reliability for unambiguous identification
- **Identification notes**: interference patterns, concentration effects, matrix dependencies

**Database Location**: `app/data/reference/ir_functional_groups_extended.json` (auto-detected by application; falls back to basic 8-group database if unavailable)

### Usage

1. Navigate to **Reference** tab → **IR Functional Groups**
2. Browse the complete list of 50+ functional groups with wavenumber ranges and metadata
3. **Filter/Search**:
   - By name: "carbonyl", "alcohol", "amine"
   - By wavenumber: Enter a value to find groups with bands near that position
   - By chemical class: "aromatic", "aliphatic", "nitrogen"
   - By vibrational mode: "stretch", "bend", "rock"
4. **Preview**: Click a row to see the band position(s) highlighted on the inspector preview plot
5. **Overlay**: Toggle **Show on plot** to project IR band ranges onto your main spectrum
   - Bands appear as filled, labeled regions anchored to your trace's intensity span
   - Multiple overlapping bands automatically stack labels on separate rows for legibility
   - Colors differentiate functional group families (hydroxyl=blue, carbonyl=orange, etc.)

### Example Workflows

**Identifying an Unknown Organic Compound**:
1. Import your FTIR spectrum (File → Open or drag-and-drop)
2. Reference tab → IR Functional Groups
3. Look for strong bands in your spectrum:
   - Strong, broad band at 3300 cm⁻¹? Search "O-H" → likely alcohol or carboxylic acid
   - Sharp band at 1710 cm⁻¹? Search "carbonyl" → ketone, aldehyde, ester, or acid
   - Doublet at 1550 + 1350 cm⁻¹? Search "nitro" → nitro compound
4. Enable overlays for candidate groups to compare expected ranges with your peaks
5. Cross-reference related groups (e.g., if C=O at 1710 + broad O-H at 2500-3300 → carboxylic acid)

**Student Lab Exercise - Comparing Functional Groups**:
1. Import multiple IR spectra (e.g., ethanol, acetone, benzoic acid)
2. Toggle between datasets in the Data dock
3. Keep IR functional group overlays enabled
4. Observe how different compounds show characteristic bands:
   - Ethanol: O-H at 3350 (broad), C-O at 1050 (strong)
   - Acetone: C=O at 1715 (strong, sharp)
   - Benzoic acid: O-H at 3000 (very broad), C=O at 1690 (strong), aromatic C=C at 1600/1500

**Advanced: Contextual Identification**:
- **Carboxylic acid detection**: Broad O-H (2500-3300 cm⁻¹) + C=O at 1710 cm⁻¹ → high confidence COOH
- **Primary amine**: Doublet at 3500+3300 cm⁻¹ (N-H₂ asymmetric + symmetric) + N-H bend at 1600 cm⁻¹
- **Aromatic compound**: C-H at 3030 cm⁻¹ + C=C at 1600/1500 cm⁻¹ + out-of-plane bending patterns (900-690 cm⁻¹) reveal substitution (mono/ortho/meta/para)

### Future: Automated Functional Group Prediction (Planned)

The extended database is designed to support **machine learning-powered functional group identification**:

**Phase 1 (4 weeks)**: Enhanced rule-based peak detection
- Automated peak detection using `scipy.signal.find_peaks`
- Match peaks to database ranges with confidence scoring
- Contextual rules for group interactions (e.g., COOH = broad O-H + sharp C=O)
- Performance target: 80% precision, 70% recall

**Phases 2-3 (14 weeks)**: Neural network training
- Training data: ~52,000 IR spectra from NIST WebBook and SDBS
- 1D CNN with attention mechanisms for diagnostic region focus
- Multi-label classification with confidence scores
- Performance target: 90% precision, 85% recall

**Phase 4 (4 weeks)**: UI integration
- "Analyze Functional Groups" button/panel
- Display predictions with confidence bars and supporting evidence
- Annotated spectrum view with color-coded diagnostic regions
- Export predictions with full provenance

**Phase 5 (4 weeks)**: Hybrid ensemble
- Combine rule-based and neural network predictions
- Tunable weights (default: 40% rules, 60% neural)
- Interpretability: show which method contributed to each prediction
- Performance target: 92% precision, 88% recall

For complete technical details, see:
- ML design document: `docs/specs/ml_functional_group_prediction.md`
- Architectural decision: `docs/brains/2025-10-25T0230-ir-ml-integration.md`
- Atlas coverage: Chapter 1 (§3.1a Functional Group Coverage), Chapter 7 (§7a IR Identification)

### Provenance

- **Database**: `app/data/reference/ir_functional_groups_extended.json`
- **Citations**: NIST Chemistry WebBook, Pavia et al. (2015), Silverstein et al. (2015), SDBS (AIST Japan)
- **Curation status**: Comprehensive (version 2.0, 2025-10-24)
- **ML compatibility**: Structured for neural network training with relationship mapping

Each band now renders as a filled, labelled lane that anchors itself to the active trace's intensity span, keeping the annotation inside the plotted data rather than floating above it. Bands automatically stack their labels on discrete rows within the filled region so overlapping annotations remain legible even when multiple functional classes share a range.

## Line-shape placeholders

- References: B.W. Mangum & S. Shirley (2015) PASP 127, 266–298; G. Herzberg (1950) *Spectra of Diatomic Molecules*.
- Purpose: captures Doppler shifts, pressure and Stark broadening, instrumental resolution, and other scaffolding so the
  feature backlog is visible to users and agents.
- Models marked `ready` (Doppler shift, pressure broadening, Stark broadening) now include physical units and example
  parameters pulled from those references. Highlighting a row renders a normalised sample profile and records Doppler
  factors, Lorentzian kernel widths, or Stark wing scaling derived from the seeded inputs.
- Usage: select **Line-shape Placeholders** and click a row to refresh the preview plot. The **Overlay on plot** toggle
  projects the simulated profile into the main workspace, letting you compare the seeded broadening or velocity shift
  against active spectra before wiring real metadata into the pipeline.

### Workflow tips

1. Choose the appropriate tab (Spectral lines, IR groups, or Line-shape models). For NIST queries, press **Fetch lines** after
   configuring the element and bounds; IR and line-shape data load instantly.
2. Use the filter field below the tabs to narrow long tables by wavelength, functional group, or parameter name. Filtering only
   affects the active pinned line set—other sets stay visible for cross-comparison.
3. Manage pinned sets from the list beneath the controls: select an entry to focus the table, remove it when a study is
   complete, and toggle **Use uniform line colour** when you need visual parity across dozens of species.
4. Enable **Overlay on plot** to project the preview into the main workspace. Spectral lines respect their relative intensities
   in the current unit system (all pinned NIST sets appear together using their assigned palette), IR bands shade their ranges
   with clustered labels, and line-shape previews overlay simulated profiles returned by `app/services/line_shapes.py`.
5. The metadata drawer captures citations, astroquery parameters, and retrieval timestamps so exported manifests can trace the
   exact reference dataset used during analysis.

## Roadmap hooks

- Doppler, Stark, and pressure broadening models are placeholders awaiting velocity/thermodynamic metadata capture.
- JWST records include spectral resolution fields so future convolution or instrument-matching steps can pick up the
  stored resolving power.
- Additional species (He I, O III, Fe II, etc.) can be fetched live via the NIST form today; a persistent catalogue export can
  still be generated under `app/data/reference/` for offline snapshots.
- Remote catalogue tooling now rewrites provider-specific queries and downloads via astroquery so agents should focus on
  spectroscopic targets (UV/VIS, IR, mass-spec benchmarks) when wiring new data sources.
- JWST quick-look placeholders have been retired from the Reference tab until calibrated spectra are regenerated from MAST; see
  the workplan for the outstanding ingestion task.

## Further reading
- [Atlas: NIST spectral line identification](../atlas/README.md#identification-peak-scoring)
- [Atlas: overlays and NIST anchoring](../atlas/README.md#overlays-nist-anchoring-and-scaling)
- [Atlas: IR functional group coverage](../atlas/README.md#ir-functional-group-coverage)
