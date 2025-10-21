# Chapter 32 — Sources (Compiled from Every Canvas)

* note: this document should be updated to correctly display sources used in each atlas document, including both documents before and after this chapter. once we finish our project and totally compile all credible sources, we will then rename/relabel the `chapter_32_sources.md` to `chapter_99_sources.md` *


> **Purpose.** Provide a single, consistent bibliography and source registry for all chapters. Includes canonical citations, dataset/library versioning, and machine‑readable entries usable by the app’s source resolver.
>
> **Scope.** Textbooks/monographs; standards/specifications; databases and archives; software and algorithms; UI/accessibility guidance. All entries here are referenced throughout Chapters 1–31.
>
> **Path notice.** Any paths below are **placeholders**. The application resolves tokens like `[SOURCE_ID]`, `[VERSION]`, `[YYYYMMDD]` at runtime. Do **not** hardcode paths.

---

## 0. Citation style and policy

- **Style:** ACS (author–year) for prose; BibTeX provided where available. Dataset/library entries include explicit **version/date** and **license**.
- **Pinning:** Always cite `source_id@version`. When a source updates, add a **new entry**; never overwrite. Keep both in the cache with checksums (Ch. 4).
- **Medium:** Record air vs vacuum assumptions for wavelength standards; record units for cross‑sections and band strengths.

---

## 1. Textbooks and monographs (foundational)

- Skoog, D. A.; Holler, F. J.; Crouch, S. R. **Principles of Instrumental Analysis**; 7th ed.; Cengage: Boston, 2017.
- Hollas, J. M. **Modern Spectroscopy**; 4th ed.; Wiley: Chichester, 2004.
- Demtröder, W. **Laser Spectroscopy: Basic Concepts and Instrumentation**; 4th ed.; Springer: Berlin, 2008.
- Lakowicz, J. R. **Principles of Fluorescence Spectroscopy**; 3rd ed.; Springer: New York, 2006.
- Gray, R. O.; Corbally, C. J. **Stellar Spectral Classification**; Princeton Univ. Press: Princeton, 2009.
- Pavia, D. L.; Lampman, G. M.; Kriz, G. S.; Vyvyan, J. R. **Introduction to Spectroscopy**; 5th ed.; Cengage, 2015.
- Silverstein, R. M.; Webster, F. X.; Kiemle, D. J.; Bryce, D. L. **Spectrometric Identification of Organic Compounds**; 8th ed.; Wiley, 2014.
- Cotton, F. A. **Advanced Inorganic Chemistry**; 6th ed.; Wiley, 1999.
- Lever, A. B. P. **Inorganic Electronic Spectroscopy**; 2nd ed.; Elsevier, 1984.
- Atkins, P.; de Paula, J. **Atkins’ Physical Chemistry**; 11th ed.; Oxford Univ. Press, 2018.
- McQuarrie, D. A.; Simon, J. D. **Physical Chemistry: A Molecular Approach**; Univ. Science Books, 1999.
- Laidler, K. J.; Meiser, J. H.; Sanctuary, B. C. **Physical Chemistry**; 4th ed.; Houghton Mifflin, 2003.
- Tielens, A. G. G. M. **The Physics and Chemistry of the Interstellar Medium**; Cambridge Univ. Press, 2005.
- Griffiths, P. R.; de Haseth, J. A. **Fourier Transform Infrared Spectrometry**; 2nd ed.; Wiley, 2007.
- Mirabella, F. M. **Internal Reflection Spectroscopy: Theory and Applications**; Marcel Dekker, 1993.
- Munzner, T. **Visualization Analysis and Design**; CRC Press, 2014.
- Tufte, E. R. **The Visual Display of Quantitative Information**; 2nd ed.; Graphics Press, 2001.

---

## 2. Standards, algorithms, and reference formulas

- **Air–vacuum conversions:** Ciddor, P. E. *Appl. Opt.* **1996**, 35, 1566–1573. Edlén, B. *Metrologia* **1966**, 2, 71.
- **Voigt profile approximations:** Humlíček, J. *J. Quant. Spectrosc. Radiat. Transfer* **1982**, 27, 437–444; Whiting, E. E. *J. Quant. Spectrosc. Radiat. Transfer* **1968**, 8, 1379–1384. Olivero, J. J.; Longbothum, R. L. *JQSRT* **1977**, 17, 233–236 (FWHM approximation).
- **Kubelka–Munk:** Kubelka, P.; Munk, F. *Z. Tech. Phys.* **1931**, 12, 593–601; Kortüm, G. **Reflectance Spectroscopy**; Springer, 1969.
- **ATR penetration depth:** Harrick, N. J. **Internal Reflection Spectroscopy**; Interscience, 1967; Mirabella (1993) above.
- **Barycentric corrections/WCS:** Greisen, E. W.; Calabretta, M. R. *A&A* **2002**, 395, 1061–1075 (FITS/WCS papers I–IV). IAU SOFA documentation.
- **Accessibility:** W3C **WCAG 2.2** Guidelines.
- **Usability heuristics:** Nielsen, J. **10 Heuristics for User Interface Design** (original paper and updates).

---

## 3. Databases and libraries (pin versions)

> Use these via the Source Registry (Ch. 4). Cite **both** the dataset and the version. Licenses must be recorded.

- **NIST Atomic Spectra Database (ASD)** — Atomic lines/levels. `NIST_ASD@[VERSION]`.
- **HITRAN** — High‑resolution molecular spectroscopic database for gases. `HITRAN@[YEAR.RELEASE]`.
- **ExoMol** — Molecular line lists for exoplanet/ISM conditions. `ExoMol@[RELEASE]`.
- **CDMS** — Cologne Database for Molecular Spectroscopy (rotational). `CDMS@[RELEASE]`.
- **JPL** — Submillimeter, Millimeter, and Microwave Spectral Line Catalog. `JPL@[RELEASE]`.
- **LAMDA** — Leiden Atomic and Molecular Database (collisional data). `LAMDA@[RELEASE]`.
- **RADEX** — Non‑LTE radiative transfer tool; record code version and collision data versions.
- **RRUFF** — Raman, X‑ray diffraction, and chemistry for minerals. `RRUFF@[RELEASE]`.
- **CALSPEC** — HST spectrophotometric standards. `CALSPEC@[RELEASE]`.
- **MAST** — Barbara A. Mikulski Archive for Space Telescopes. `MAST@[DATE_RANGE]` for retrieved holdings.
- **NIST Chemistry WebBook** — Thermochemistry and spectra. `NIST_CWB@[RELEASE]`.
- **Ames PAH IR** — PAH infrared database. `AMES_PAH@[RELEASE]`.

Each registry entry includes DOI/URL, license, checksum, and unit notes.

---

## 4. Software libraries (cite in methods)

- **Astropy** Project; Astropy Collaboration papers (2013, 2018, 2022). Cite version and subpackages used (time, coordinates, WCS).
- **NumPy**; **SciPy**; **Pandas**; **h5py**; **pyarrow** (Parquet); **matplotlib** for plotting.
- **TypeScript**, **React** (major version); **Tailwind**; **shadcn/ui**; icon set used.
- **JSON Schema 2020‑12**; **RFC 8259** (JSON); **FITS** and **WCS** standards; **HDF5** format; **Apache Parquet**.

Record versions in environment lockfiles bundled with exports (Ch. 8, 12, 29).

---

## 5. Instrumentation and calibration references

- **Holmium oxide wavelength standards** for UV–Vis (NIST/NRC documentation).
- **Polystyrene film band positions** for FTIR calibration (NIST reference data).
- **Silicon Raman line at 520.7 cm⁻¹** temperature dependence papers (~0.022 cm⁻¹ K⁻¹ scale; cite a chosen standard curve).
- **Neutral density/stray‑light tests** for UV–Vis; manufacturer‑independent protocols.
- **Fluorescence correction** best practices; quinine sulfate standard documentation.

Tie each to acceptance thresholds in Chapter 30 and QC in Ch. 2/6/8.

---

## 6. UI/UX and accessibility

- W3C **WCAG 2.2**; ARIA Authoring Practices Guide.
- Color‑vision deficiency resources with recommended palettes.
- Nielsen–Norman Group usability heuristics; performance UX guidelines for data‑dense apps.

---

## 7. Machine‑readable Source Registry (template)

`sources/registry.json` (schema excerpt):
```json
{
  "schema_version": "1.0.0",
  "sources": [
    {
      "source_id": "HITRAN@2024.1",
      "type": "molecular_lines",
      "provider": "HITRAN",
      "doi": "[DOI]",
      "license": "[LICENSE SPDX]",
      "unit_notes": "air->vacuum conversions applied per Ciddor 1996",
      "checksum": "[SHA256]",
      "retrieved_utc": "[ISO-8601]"
    },
    {
      "source_id": "NIST_ASD@v5.11",
      "type": "atomic_lines",
      "provider": "NIST",
      "url": "[URL]",
      "license": "[LICENSE]",
      "checksum": "[SHA256]"
    }
  ]
}
```

---

## 8. Example BibTeX entries

```bibtex
@book{Skoog2017,
  title={Principles of Instrumental Analysis},
  author={Skoog, D. A. and Holler, F. J. and Crouch, S. R.},
  year={2017}, publisher={Cengage}
}

@article{Ciddor1996,
  title={Refractive index of air: New equations for the visible and near infrared},
  author={Ciddor, P. E.}, journal={Applied Optics}, year={1996}, volume={35}, pages={1566--1573}
}

@article{Humlicek1982,
  title={Optimized computation of the Voigt and complex probability functions},
  author={Huml{\'\i}{\v c}ek, J.}, journal={JQSRT}, year={1982}, volume={27}, pages={437--444}
}
```

---

## 9. Citing datasets and software in reports

**Dataset citation (example, ACS style):**
> HITRAN 2024.1: High‑Resolution Transmission Molecular Absorption Database;
> Gordon, I. E.; et al. Release 2024.1;
> accessed `[YYYY‑MM‑DD]`;
> `source_id@version = HITRAN@2024.1`.

**Software citation (example):**
> Astropy Collaboration; Robitaille, T. P.; et al. (2013, 2018, 2022). *The Astropy Project: Building an Open‑source Scientific Python Ecosystem*; Version `[X.Y]` used.

**Lab standard (example):**
> NIST SRM 2035a: Holmium Oxide Glass Wavelength Calibration Standard; verified `[YYYY‑MM‑DD]`.

Include `source_id@version`, license, DOI/URL, retrieval date, and checksum in the export bundle (Ch. 8, 12).

---

## 10. Maintenance and drift policy

1. When a source updates, add new `source_id@version` to `sources/registry.json`; store checksums; keep old versions.
2. Before adopting a new version, run the **side‑by‑side comparator** on fixtures; record deltas affecting identifications.
3. Update cross‑references in chapters that name the source explicitly (Spectroscopy, Physics, Astrochemistry, Astrophysics, Instrumentation).
4. Bump rubric version if score thresholds depend on library properties (Ch. 11).

---

## 11. Cross‑links

- Ch. 3 (evidence graph cites libraries), Ch. 4 (source registry & adapters), Ch. 5 (units/air–vacuum), Ch. 6 (LSF/response), Ch. 7 (identification), Ch. 8 (provenance), Ch. 12 (formats), Ch. 23–31 (domain chapters).

---

## 12. Quick checklist for authors

- [ ] Cite **versioned** datasets and software
- [ ] Include **license** and **DOI/URL**
- [ ] Record **units**, **frames**, and **medium** where relevant
- [ ] Add **checksums** to export bundles
- [ ] Run **diffs** before adopting new versions
- [ ] Update **Docs module** citations and this chapter in the **same commit**

> This chapter is the single source of truth for references. If a citation isn’t here, add it and pin a version before you use it elsewhere.

