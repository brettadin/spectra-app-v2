"""Application entry point for the Spectra desktop shell."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6 import QtCore, QtWidgets

from .services import (
    UnitsService,
    ProvenanceService,
    DataIngestService,
    OverlayService,
    MathService,
)

SAMPLES_DIR = Path(__file__).resolve().parent.parent / 'samples'


class SpectraMainWindow(QtWidgets.QMainWindow):
    """Minimal yet functional shell that wires UI actions to services."""

    def __init__(self, container: object | None = None) -> None:
        super().__init__()
        self._container = container
        self.setWindowTitle("Spectra Desktop Preview")
        self.resize(1024, 720)

        self.units_service = self._resolve_service("units_service", UnitsService)
        self.provenance_service = self._resolve_service("provenance_service", ProvenanceService)
        self.ingest_service = self._resolve_service(
            "ingest_service", lambda: DataIngestService(self.units_service)
        )
        self.overlay_service = self._resolve_service(
            "overlay_service", lambda: OverlayService(self.units_service)
        )
        self.math_service = self._resolve_service("math_service", MathService)

        self._setup_menu()
        self._setup_ui()
        self._load_default_samples()

    # ------------------------------------------------------------------
    def _setup_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        open_action = QtWidgets.QAction("&Open…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        sample_action = QtWidgets.QAction("Load &Sample", self)
        sample_action.triggered.connect(self.load_sample_via_menu)
        file_menu.addAction(sample_action)

        export_action = QtWidgets.QAction("Export &Manifest", self)
        export_action.triggered.connect(self.export_manifest)
        file_menu.addAction(export_action)

        file_menu.addSeparator()
        exit_action = QtWidgets.QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _setup_ui(self) -> None:
        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        self.spectra_list = QtWidgets.QListWidget()
        self.spectra_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.spectra_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.spectra_list, 2)

        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs, 5)

        self.data_view = QtWidgets.QTextEdit(readOnly=True)
        self.tabs.addTab(self.data_view, "Data")

        self.overlay_widget = self._build_overlay_tab()
        self.tabs.addTab(self.overlay_widget, "Overlay")

        self.math_widget = self._build_math_tab()
        self.tabs.addTab(self.math_widget, "Math")

        self.provenance_view = QtWidgets.QTextEdit(readOnly=True)
        self.tabs.addTab(self.provenance_view, "Provenance")

        self.setCentralWidget(central)

        self.status_bar = self.statusBar()

    def _build_overlay_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        controls = QtWidgets.QHBoxLayout()
        layout.addLayout(controls)

        controls.addWidget(QtWidgets.QLabel("X unit:"))
        self.overlay_x_unit = QtWidgets.QComboBox()
        self.overlay_x_unit.addItems(["nm", "µm", "Å", "cm^-1"])
        self.overlay_x_unit.setCurrentText("nm")
        controls.addWidget(self.overlay_x_unit)

        controls.addWidget(QtWidgets.QLabel("Y unit:"))
        self.overlay_y_unit = QtWidgets.QComboBox()
        self.overlay_y_unit.addItems(["absorbance", "transmittance", "%T", "absorbance_e"])
        self.overlay_y_unit.setCurrentText("absorbance")
        controls.addWidget(self.overlay_y_unit)

        update_btn = QtWidgets.QPushButton("Refresh Overlay")
        update_btn.clicked.connect(self.refresh_overlay)
        controls.addWidget(update_btn)
        controls.addStretch(1)

        self.overlay_table = QtWidgets.QTableWidget()
        self.overlay_table.setColumnCount(4)
        self.overlay_table.setHorizontalHeaderLabels(["Spectrum", "Point", "X", "Y"])
        self.overlay_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.overlay_table)

        return widget

    def _build_math_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        selector_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(selector_layout)

        self.math_a = QtWidgets.QComboBox()
        self.math_b = QtWidgets.QComboBox()
        selector_layout.addWidget(QtWidgets.QLabel("Spectrum A:"))
        selector_layout.addWidget(self.math_a)
        selector_layout.addWidget(QtWidgets.QLabel("Spectrum B:"))
        selector_layout.addWidget(self.math_b)

        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)
        subtract_btn = QtWidgets.QPushButton("A − B")
        subtract_btn.clicked.connect(self.compute_subtract)
        btn_layout.addWidget(subtract_btn)
        ratio_btn = QtWidgets.QPushButton("A ÷ B")
        ratio_btn.clicked.connect(self.compute_ratio)
        btn_layout.addWidget(ratio_btn)
        btn_layout.addStretch(1)

        self.math_log = QtWidgets.QTextEdit(readOnly=True)
        layout.addWidget(self.math_log)

        return widget

    # ------------------------------------------------------------------
    def _resolve_service(self, key: str, factory) -> object:
        if self._container is None:
            return factory() if callable(factory) else factory

        container = self._container

        if isinstance(container, dict):
            if key in container:
                return container[key]
            if hasattr(container, "get"):
                value = container.get(key)
                if value is not None:
                    return value
            return factory() if callable(factory) else factory

        attr = getattr(container, key, None)
        if attr is not None:
            return attr

        resolver = getattr(container, "resolve", None)
        if callable(resolver):
            for candidate in (key, factory):
                try:
                    value = resolver(candidate)
                except Exception:  # pragma: no cover - defensive fallback
                    value = None
                if value is not None:
                    return value

        getter = getattr(container, "get", None)
        if callable(getter):
            for candidate in (key, factory):
                try:
                    value = getter(candidate)
                except Exception:  # pragma: no cover - defensive fallback
                    value = None
                if value is not None:
                    return value

        return factory() if callable(factory) else factory

    def _load_default_samples(self) -> None:
        for sample_file in sorted(SAMPLES_DIR.glob('sample_*.csv')):
            if sample_file.exists():
                self._ingest_path(sample_file)

    # Actions -----------------------------------------------------------
    def open_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Spectrum", str(Path.home()),
                                                        "Spectra (*.csv *.txt)")
        if path:
            self._ingest_path(Path(path))

    def load_sample_via_menu(self) -> None:
        files = list(SAMPLES_DIR.glob('*.csv'))
        if not files:
            self.status_bar.showMessage("No samples found", 5000)
            return
        self._ingest_path(files[0])

    def export_manifest(self) -> None:
        if not self.overlay_service.list():
            QtWidgets.QMessageBox.information(self, "No Data", "Load spectra before exporting provenance.")
            return
        manifest = self.provenance_service.create_manifest(self.overlay_service.list())
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Manifest", str(Path.home() / 'manifest.json'),
                                                             "JSON (*.json)")
        if save_path:
            self.provenance_service.save_manifest(manifest, Path(save_path))
            self.status_bar.showMessage(f"Manifest saved to {save_path}", 5000)
            self.provenance_view.setPlainText(json_pretty(manifest))

    def refresh_overlay(self) -> None:
        selected_ids = [item.data(QtCore.Qt.UserRole) for item in self.spectra_list.selectedItems()]
        if not selected_ids:
            selected_ids = [item.data(QtCore.Qt.UserRole) for item in self._iter_items(self.spectra_list)]
        if not selected_ids:
            self.overlay_table.clearContents()
            self.overlay_table.setRowCount(0)
            return
        views = self.overlay_service.overlay(selected_ids, self.overlay_x_unit.currentText(),
                                             self._normalise_y(self.overlay_y_unit.currentText()))
        self._populate_overlay_table(views)

    def compute_subtract(self) -> None:
        ids = self._selected_math_ids()
        if not ids:
            return
        spec_a = self.overlay_service.get(ids[0])
        spec_b = self.overlay_service.get(ids[1])
        result, info = self.math_service.subtract(spec_a, spec_b)
        self._log_math(info)
        if result:
            self.overlay_service.add(result)
            self._add_spectrum_to_list(result)

    def compute_ratio(self) -> None:
        ids = self._selected_math_ids()
        if not ids:
            return
        spec_a = self.overlay_service.get(ids[0])
        spec_b = self.overlay_service.get(ids[1])
        result, info = self.math_service.ratio(spec_a, spec_b)
        self._log_math(info)
        self.overlay_service.add(result)
        self._add_spectrum_to_list(result)

    # Internal helpers --------------------------------------------------
    def _ingest_path(self, path: Path) -> None:
        try:
            spectrum = self.ingest_service.ingest(path)
        except Exception as exc:  # pragma: no cover - UI feedback
            QtWidgets.QMessageBox.critical(self, "Import failed", str(exc))
            return
        self.overlay_service.add(spectrum)
        self._add_spectrum_to_list(spectrum)
        self.status_bar.showMessage(f"Loaded {path.name}", 5000)
        self._update_math_selectors()
        self.refresh_overlay()
        self._show_metadata(spectrum)

    def _add_spectrum_to_list(self, spectrum: 'Spectrum') -> None:
        item = QtWidgets.QListWidgetItem(spectrum.name)
        item.setData(QtCore.Qt.UserRole, spectrum.id)
        self.spectra_list.addItem(item)

    def _show_metadata(self, spectrum: 'Spectrum') -> None:
        lines = [f"Name: {spectrum.name}", f"Source: {spectrum.source_path or 'N/A'}"]
        for key, value in spectrum.metadata.items():
            lines.append(f"{key}: {value}")
        self.data_view.setPlainText("\n".join(lines))

    def _on_selection_changed(self) -> None:
        items = self.spectra_list.selectedItems()
        if items:
            spectrum_id = items[-1].data(QtCore.Qt.UserRole)
            spectrum = self.overlay_service.get(spectrum_id)
            self._show_metadata(spectrum)
        self.refresh_overlay()

    def _populate_overlay_table(self, views: Iterable[dict]) -> None:
        rows = sum(min(100, len(view['x'])) for view in views)
        self.overlay_table.setRowCount(rows)
        row_index = 0
        for view in views:
            x_arr = view['x']
            y_arr = view['y']
            for idx, (x, y) in enumerate(zip(x_arr[:100], y_arr[:100])):  # limit to first 100 points for display
                self.overlay_table.setItem(row_index, 0, QtWidgets.QTableWidgetItem(view['name']))
                self.overlay_table.setItem(row_index, 1, QtWidgets.QTableWidgetItem(str(idx)))
                self.overlay_table.setItem(row_index, 2, QtWidgets.QTableWidgetItem(f"{x:.6g}"))
                self.overlay_table.setItem(row_index, 3, QtWidgets.QTableWidgetItem(f"{y:.6g}"))
                row_index += 1
        if rows == 0:
            self.overlay_table.clearContents()
            self.overlay_table.setRowCount(0)

    def _update_math_selectors(self) -> None:
        spectra = self.overlay_service.list()
        self.math_a.clear()
        self.math_b.clear()
        for spec in spectra:
            self.math_a.addItem(spec.name, spec.id)
            self.math_b.addItem(spec.name, spec.id)

    def _selected_math_ids(self) -> list[str]:
        if self.math_a.count() < 2 or self.math_b.count() < 2:
            QtWidgets.QMessageBox.information(self, "Need more spectra", "Load at least two spectra for math operations.")
            return []
        return [self.math_a.currentData(), self.math_b.currentData()]

    def _log_math(self, info: dict) -> None:
        existing = self.math_log.toPlainText()
        new_line = json_pretty(info)
        self.math_log.setPlainText("\n".join(filter(None, [existing, new_line])))

    def _iter_items(self, widget: QtWidgets.QListWidget):
        for index in range(widget.count()):
            yield widget.item(index)

    def _normalise_y(self, label: str) -> str:
        mapping = {"%T": "percent_transmittance"}
        return mapping.get(label, label)


def json_pretty(data: dict) -> str:
    import json
    return json.dumps(data, indent=2, ensure_ascii=False)


def main() -> None:
    import sys as _sys

    app = QtWidgets.QApplication(_sys.argv)
    window = SpectraMainWindow()
    window.show()
    _sys.exit(app.exec())


if __name__ == "__main__":
    main()
