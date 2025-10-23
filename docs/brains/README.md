# Brains (Agent Memory Neurons)

This folder contains small, focused “neurons” — one file per idea — that agents can cross-link and update as we evolve Spectra. Keep each neuron:

- Atomic: a single concept or mechanism
- Portable: link to source files, PRs/commits, and other neurons
- Actionable: include “How to extend/test” snippets

Conventions
- Filename: short-kebab or snake_case, e.g., `remote_data_pipeline.md`
- Top heading: the neuron’s name and one-sentence purpose
- See also: links to sibling neurons for lateral recall
- Source pointers: function/file references in backticks
- Change log: a tiny bullet list as updates land

When to write/update a neuron
- You change a behavior or interface
- You add a workaround or fallback
- You discover constraints, edge cases, or gotchas

Also update
- `docs/dev/worklog/YYYY-MM-DD.md` with a daily narrative
- `docs/reviews/workplan.md` for batch/task tracking
- Any relevant docs in `docs/atlas` and `docs/dev/path_notes.md`
# Brains Log Index

The `docs/brains/` directory replaces the old single `atlas/brains.md` file. Each
entry documents a single architectural, scientific, or workflow decision with
the context required for future agents to reason about it.

## File Naming

Use ISO-8601 timestamps in UTC for every file:

```
YYYY-MM-DDTHH-MM-SSZ-topic.md
```

Example: `2025-10-17T23-30-00Z-remote-data-spectroscopy.md`.

The timestamp reflects when the decision was finalised. Always compute the value
at runtime and convert to UTC before writing.

## Template

Each entry must follow this structure:

```markdown
# Decision Title

**Timestamp (UTC)**: 2025-10-17T23:30:00Z
**Authors**: Spectra Agent, Human Reviewer
**Related Atlas Chapters**: 5 (Units), 6 (Calibration), 7 (Identification)
**Source Docs**: docs/history/KNOWLEDGE_LOG.md, docs/reviews/pass3.md

## Context
Why the decision was necessary. Summarise the motivating bugs, scientific
requirements, or UI concerns and link to specific files (e.g.
`app/services/calibration_service.py`).

## Decision
State the agreed approach and list any constraints (unit canon, calibration
honesty, provenance requirements, UI expectations).

## Consequences
Capture expected follow-up work, tests to add, and any documentation impacts.

## References
Cite external standards, academic papers, or internal documents using the same
citation markers used elsewhere in the repo (e.g. 【F:docs/user/remote_data.md†L12-L34】).
```

## Relationship to Other Logs

- Summaries of these decisions should still flow into
  `docs/history/KNOWLEDGE_LOG.md` so the consolidated log stays comprehensive.
- The Atlas index (`docs/atlas/0_index_stec_master_canvas_index_numbered.md`)
  cross-links to the relevant brain entries.
- When a decision is superseded, update the original file with a note pointing
  to the replacement and log the change in the knowledge log.

## Migration Guidance

Legacy `atlas/brains.md` content should be migrated into individual files here.
When porting a section, keep the original text in the commit history but add a
summary entry following the template above.
