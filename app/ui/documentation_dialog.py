"""Documentation viewer dialog."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()


class DocumentationDialog(QtWidgets.QDialog):
    """Dialog for viewing application documentation."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Spectra Documentation")
        self.resize(900, 700)

        self.docs_list: QtWidgets.QListWidget
        self.doc_viewer: QtWidgets.QTextEdit | QtWidgets.QPlainTextEdit

        self._build_ui()
        self._load_docs()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Horizontal splitter: list on left, viewer on right
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        # Document list
        self.docs_list = QtWidgets.QListWidget()
        self.docs_list.setMinimumWidth(200)
        self.docs_list.currentRowChanged.connect(self._on_doc_selected)
        splitter.addWidget(self.docs_list)

        # Document viewer
        try:
            self.doc_viewer = QtWidgets.QTextEdit()
            self.doc_viewer.setReadOnly(True)
        except Exception:
            self.doc_viewer = QtWidgets.QPlainTextEdit()
            self.doc_viewer.setReadOnly(True)
        splitter.addWidget(self.doc_viewer)

        # Set initial splitter sizes (list: 1, viewer: 2)
        splitter.setSizes([300, 600])

        layout.addWidget(splitter)

        # Close button at bottom
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

    def _load_docs(self) -> None:
        """Load documentation files from docs/user/."""
        if self.docs_list.count() > 0:
            return  # Already loaded

        root_docs = Path(__file__).resolve().parents[2] / "docs"
        user_docs = root_docs / "user"

        def _category_for(path: Path) -> str:
            pstr = str(path).lower()
            if str(user_docs).lower() in pstr:
                return "User"
            if (root_docs / "history").exists() and str((root_docs / "history").resolve()).lower() in pstr:
                return "History"
            if any(tok in pstr for tok in ("developer", "dev\\", "specs\\", "reviews\\")):
                return "Developer"
            return "Other"

        def _title_for(path: Path) -> str:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                for line in text.splitlines():
                    l = line.strip()
                    if l.startswith("# "):
                        return l.lstrip("# ").strip()
            except Exception:
                pass
            return path.stem.replace("_", " ").replace("-", " ").strip().title()

        candidates: list[Path] = []
        if user_docs.exists():
            candidates.extend(sorted(user_docs.glob("*.md")))
        # If user docs are empty, fall back to a minimal curated landing page
        if not candidates:
            for fallback in (root_docs / "INDEX.md", root_docs / "README.md"):
                if fallback.exists():
                    candidates.append(fallback)

        entries: list[tuple[str, Path, str]] = [(_title_for(p), p, _category_for(p)) for p in candidates]

        # Group by category with alphabetical sort inside categories
        from collections import defaultdict as _defaultdict
        grouped: dict[str, list[tuple[str, Path]]] = _defaultdict(list)
        for title, path, cat in entries:
            grouped[cat].append((title, path))

        ordered_cats = sorted(grouped.keys(), key=lambda s: (s != "User", s))
        first = True
        for cat in ordered_cats:
            cat_entries = sorted(grouped[cat], key=lambda t: t[0].lower())
            if first:
                # For the very first category, add items without a header so row 0 is a real doc
                for title, path in cat_entries:
                    item = QtWidgets.QListWidgetItem(title)
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, str(path))
                    self.docs_list.addItem(item)
                first = False
            else:
                # Other categories get a header
                header_item = QtWidgets.QListWidgetItem(f"── {cat} ──")
                header_item.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)  # Non-selectable
                font = header_item.font()
                font.setBold(True)
                header_item.setFont(font)
                self.docs_list.addItem(header_item)
                for title, path in cat_entries:
                    item = QtWidgets.QListWidgetItem(f"  {title}")
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, str(path))
                    self.docs_list.addItem(item)

        # Select first doc
        if self.docs_list.count() > 0:
            self.docs_list.setCurrentRow(0)
            self._on_doc_selected(0)

    def _on_doc_selected(self, row: int) -> None:
        """Load and display the selected document."""
        item = self.docs_list.item(row)
        if item is None:
            return

        path_str = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not path_str:
            return  # Header item

        path = Path(path_str)
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            # Try to render as markdown if supported
            if hasattr(self.doc_viewer, "setMarkdown"):
                try:
                    self.doc_viewer.setMarkdown(content)  # type: ignore
                except Exception:
                    self.doc_viewer.setPlainText(content)
            else:
                self.doc_viewer.setPlainText(content)
        except Exception:
            self.doc_viewer.setPlainText(f"Failed to load documentation from {path}")
