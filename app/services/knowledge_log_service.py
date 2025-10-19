from __future__ import annotations

"""Utilities for recording and reading the Spectra knowledge log."""

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Iterable, List, Sequence


@dataclass(slots=True)
class KnowledgeLogEntry:
    """Structured representation of a knowledge-log entry."""

    timestamp: datetime
    component: str
    summary: str
    references: tuple[str, ...]
    author: str | None
    context: str | None
    raw: str


class KnowledgeLogService:
    """Append and query provenance-ready entries for the knowledge log."""

    HEADER_PATTERN = re.compile(r"^##\s+(?P<timestamp>[^–]+) – (?P<component>.+)$", re.MULTILINE)
    DEFAULT_RUNTIME_ONLY_COMPONENTS = frozenset({
        "Import",
        "Remote Import",
    })

    def __init__(
        self,
        log_path: Path | None = None,
        *,
        author: str | None = "automation",
        default_context: str | None = None,
        runtime_only_components: Iterable[str] | None = None,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        default_path = root / "docs" / "history" / "KNOWLEDGE_LOG.md"
        self.log_path = log_path or default_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.author = author
        self.default_context = default_context
        components = (
            runtime_only_components
            if runtime_only_components is not None
            else self.DEFAULT_RUNTIME_ONLY_COMPONENTS
        )
        self._runtime_only_components = {
            component.strip().lower()
            for component in components
            if component and component.strip()
        }

    # ------------------------------------------------------------------
    def record_event(
        self,
        component: str,
        summary: str,
        references: Sequence[str] | None = None,
        *,
        context: str | None = None,
        timestamp: datetime | None = None,
        persist: bool = True,
    ) -> KnowledgeLogEntry:
        """Create and optionally persist a structured knowledge-log entry.

        Parameters
        ----------
        persist:
            When ``True`` (default) the entry is appended to ``self.log_path``
            unless the ``component`` is registered as runtime-only (e.g.
            ``"Import"`` or ``"Remote Import"``).
            When ``False`` the entry is returned for in-memory history display
            without mutating the on-disk log.
        """

        moment = (timestamp or datetime.now(timezone.utc)).astimezone()
        stamp = moment.strftime("%Y-%m-%d %H:%M")
        entry_context = context or self.default_context
        references = tuple(ref for ref in references or () if ref)
        normalized_component = component.strip().lower()
        should_persist = persist and normalized_component not in self._runtime_only_components

        blocks: List[str] = [f"## {stamp} – {component}", ""]
        if self.author:
            blocks.append(f"**Author**: {self.author}")
            blocks.append("")
        if entry_context:
            blocks.append(f"**Context**: {entry_context}")
            blocks.append("")
        blocks.append(f"**Summary**: {summary.strip()}")
        blocks.append("")
        if references:
            blocks.append("**References**:")
            blocks.extend(f"- {ref}" for ref in references)
        else:
            blocks.append("**References**: None")
        blocks.append("")
        blocks.append("---")
        blocks.append("")

        payload = "\n".join(blocks)
        if should_persist:
            with self.log_path.open("a", encoding="utf-8") as stream:
                stream.write(payload)

        return KnowledgeLogEntry(
            timestamp=moment,
            component=component,
            summary=summary.strip(),
            references=references,
            author=self.author,
            context=entry_context,
            raw=payload,
        )

    # ------------------------------------------------------------------
    def load_entries(
        self,
        *,
        limit: int | None = None,
        component: str | None = None,
        search: str | None = None,
    ) -> list[KnowledgeLogEntry]:
        """Parse the knowledge log and return structured entries."""

        if not self.log_path.exists():
            return []

        text = self.log_path.read_text(encoding="utf-8")
        matches = list(self.HEADER_PATTERN.finditer(text))
        entries: list[KnowledgeLogEntry] = []

        for index, match in enumerate(matches):
            header = match.groupdict()
            try:
                timestamp = datetime.strptime(header["timestamp"].strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                # Skip headings that do not belong to log entries (e.g. documentation sections).
                continue
            timestamp = timestamp.replace(tzinfo=None)
            component_name = header["component"].strip()

            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            summary = self._extract_section(body, "Summary")
            references = tuple(self._extract_references(body))
            author = self._extract_section(body, "Author")
            context = self._extract_section(body, "Context")

            entries.append(
                KnowledgeLogEntry(
                    timestamp=timestamp,
                    component=component_name,
                    summary=summary,
                    references=references,
                    author=author,
                    context=context,
                    raw=f"## {header['timestamp']} – {component_name}\n\n{body.strip()}\n",
                )
            )

        entries.sort(key=lambda entry: entry.timestamp, reverse=True)

        if component:
            entries = [entry for entry in entries if entry.component.lower() == component.lower()]

        if search:
            needle = search.lower()
            entries = [
                entry
                for entry in entries
                if needle in entry.summary.lower()
                or any(needle in ref.lower() for ref in entry.references)
                or needle in entry.component.lower()
            ]

        if limit is not None:
            entries = entries[:limit]

        return entries

    # ------------------------------------------------------------------
    def export_entries(self, destination: Path, entries: Iterable[KnowledgeLogEntry]) -> Path:
        """Write the provided entries to ``destination`` in markdown format."""

        destination.parent.mkdir(parents=True, exist_ok=True)
        contents = "\n".join(entry.raw.strip() for entry in entries if entry.raw.strip())
        destination.write_text(contents + "\n", encoding="utf-8")
        return destination

    # ------------------------------------------------------------------
    @staticmethod
    def _extract_section(block: str, label: str) -> str | None:
        pattern = re.compile(rf"\*\*{re.escape(label)}\*\*:\s*(.+?)(?:(?:\n\s*\n)|$)", re.IGNORECASE | re.DOTALL)
        match = pattern.search(block)
        if not match:
            return None
        value = match.group(1).strip()
        if not value:
            return None
        return value

    @staticmethod
    def _extract_references(block: str) -> List[str]:
        pattern = re.compile(r"\*\*References\*\*:(.*?)(?:\n\s*\n|$)", re.IGNORECASE | re.DOTALL)
        match = pattern.search(block)
        if not match:
            return []

        section = match.group(1).strip()
        if not section or section.lower() == "none":
            return []

        lines = [line.strip() for line in section.splitlines() if line.strip()]
        cleaned = []
        for line in lines:
            cleaned.append(line[2:].strip() if line.startswith("- ") else line)
        return cleaned

