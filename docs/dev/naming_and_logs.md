# Log and Patch Naming Inconsistencies

The current repository retains a wealth of historical notes scattered across `brains/`, `atlas/`, and various `PATCHLOG` files.  Unfortunately, the naming conventions for these logs are inconsistent, making it difficult to reconstruct the timeline of development or trace specific changes.  This document summarises the observed problems and proposes a normalisation strategy.

## Observed Problems

1. **Day‑only filenames** – Several patches are named after a numerical day with no month or year (e.g. `05.txt`, `17.md`).  Without context, it is impossible to know whether “05” refers to May 5th or another day.  The redesign brief notes that the AI sometimes labelled logs “as a day of the month” incorrectly【875267955107972†L63-L74】.

2. **Mixed formats** – Some logs use `.txt` while others are `.md` or `.docx`.  The choice appears arbitrary.  A consistent extension would simplify parsing and documentation generation.

3. **Misaligned dates** – In a few cases, the date mentioned inside the file (e.g. in a header) does not match the filename.  For example, a log labelled `07-12-2025_fix-units.md` contains work performed on July 11th.

4. **Scattered location** – Historical notes are stored in multiple locations (`brains/`, `atlas/`, `docs/tech_notes/`, etc.).  Some directories have been renamed, leaving dangling references.

5. **No indexing** – There is no master index listing all logs and their contents.  Consequently, important decisions are effectively hidden.

## Normalisation Plan

To address these issues and create a coherent history for future agents, we propose the following steps:

1. **Define a canonical filename scheme:** Use ISO‑8601 dates and descriptive slugs, e.g. `YYYY‑MM‑DD_short-description.md`.  This provides chronological ordering and human‑readable context.  For example, a patch applied on 2025‑10‑05 to fix unit conversions would be named `2025‑10‑05_fix-unit-conversions.md`.

2. **Consolidate locations:** Move all historical notes into a single directory (`docs/history/`).  Subdirectories can group related entries (e.g. `patches/`, `brains/`, `atlas/`).  This way, a single index can list the entire development history.

3. **Write a normalisation script:** Implement a script (e.g. `tools/normalize_logs.py`) that performs the following:
   * Parses each existing log, extracts date information from headers or content, and infers missing month/year values based on nearby commits and file timestamps.
   * Renames the file according to the canonical scheme.
   * Inserts a front‑matter block at the top of each normalised file recording the original filename, its original location, and any assumptions made during normalisation.
   * Updates references within the repository (e.g. patch logs referencing other files) to the new names.

4. **Generate a knowledge index:** After normalisation, generate `docs/history/KNOWLEDGE_LOG.md`, a chronological index of all entries.  Each entry should include:
   * Date and time of the entry.
   * Short description or title.
   * Link to the log file.
   * Tags (e.g. `bugfix`, `feature`, `refactor`, `note`).
   * Author (if known; otherwise mark as AI agent or human user).

5. **Adopt guidelines for future logs:** Document the naming convention and index procedure in `docs/knowledge_guidelines.md`.  Require future agents to append new entries using the canonical scheme and update the index accordingly.

This normalisation will improve traceability and ensure continuity of knowledge across agent sessions.

---

## 2025-11-04 — Duplicate docs consolidation (user guides)

We identified multiple copies of two user-facing documents scattered across the repo:

- Telescope-Based Planetary Datasets (UV-VIS and IR)
   - docs/Telescope-Based Planetary datasets.md (legacy)
   - docs/uploads/Telescope-Based Planetary Datasets (UV-VIS and IR).md (converted)
   - docs/user/Telescope-Based Planetary Datasets (UV-VIS and IR).md (canonical)
   - Also found binary sources/exports in both docs/ and docs/reference_sources/ (.docx/.pdf)

- Relating Lab Spectra to Astronomical Data
   - docs/uploads/Relating Lab Spectra to Astronomical Data.md (converted)
   - docs/user/Relating Lab Spectra to Astronomical Data.md (canonical)

Actions taken:

- Promoted the canonical Markdown copies into `docs/user/` (ensures in-app visibility).
- Rewrote legacy root file `docs/Telescope-Based Planetary datasets.md` to a short redirect stub pointing to the canonical path.
- Linked both guides in `docs/INDEX.md` under “Data Guides.”

Pending/next steps:

- Remove duplicate Markdown copies from `docs/uploads/` after verifying no consumers rely on those paths.
- Normalize binary sources: keep `.docx/.pdf` in `docs/reference_sources/` only; remove duplicates from `docs/` root.
- Grep for references to `docs/Telescope-Based Planetary datasets.md` and update to the canonical `docs/user/...` path where appropriate (the stub will keep old links functional meanwhile).

## 2025-11-04 — Move NORMALIZATION_VERIFICATION.md into docs/reviews

Action taken:

- Promoted `NORMALIZATION_VERIFICATION.md` from repository root to `docs/reviews/NORMALIZATION_VERIFICATION.md` as the canonical verification guide for normalization behaviour.
- Replaced the root `NORMALIZATION_VERIFICATION.md` with a redirect stub pointing to `docs/reviews/NORMALIZATION_VERIFICATION.md`.

Rationale:

- The document is user-facing documentation tied to plot behaviour, so `docs/reviews/` is an appropriate canonical location that makes it discoverable by maintainers and the Docs UI.
- The redirect stub preserves backward compatibility for existing links while encouraging migration to the canonical path.

Next steps:

- Run a quick grep for references to the root path and update to the `docs/reviews/` path where safe.
- Consider adding this file to the docs index if you want it surfaced under a specific guide category (e.g., "Plotting & Normalization").

Rationale:

- Canonicalize user guides under `docs/user/` to match the in-app documentation loader and reduce drift.
- Maintain a temporary redirect stub to avoid breaking existing links in notes and worklogs.