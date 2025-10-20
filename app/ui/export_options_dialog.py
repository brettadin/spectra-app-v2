"""Export configuration dialog for provenance bundle generation."""

from __future__ import annotations

from dataclasses import dataclass

from app.qt_compat import get_qt

_, _, QtWidgets, _ = get_qt()


@dataclass(frozen=True)
class ExportOptions:
    """User selections captured from :class:`ExportOptionsDialog`."""

    include_manifest: bool = True
    include_wide_csv: bool = False
    include_composite_csv: bool = False
    composite_strategy: str = "mean"

    @property
    def has_selection(self) -> bool:
        return self.include_manifest or self.include_wide_csv or self.include_composite_csv


class ExportOptionsDialog(QtWidgets.QDialog):
    """Collect export bundle preferences prior to writing provenance artefacts."""

    def __init__(self, parent: QtWidgets.QWidget | None = None, *, allow_composite: bool = True) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Options")
        self.setModal(True)

        self._manifest_checkbox = QtWidgets.QCheckBox("Manifest bundle (JSON, per-spectrum CSV, plot snapshot)")
        self._manifest_checkbox.setChecked(True)

        self._wide_checkbox = QtWidgets.QCheckBox("Wide CSV (paired wavelength/intensity columns per spectrum)")
        self._wide_checkbox.setChecked(False)

        self._composite_checkbox = QtWidgets.QCheckBox("Composite CSV (mean intensity across spectra)")
        self._composite_checkbox.setChecked(False)
        self._composite_checkbox.setEnabled(allow_composite)

        composite_hint = QtWidgets.QLabel(
            "A composite is only available when multiple spectra are visible."
        )
        composite_hint.setWordWrap(True)
        composite_hint.setContentsMargins(20, 0, 0, 0)
        composite_hint.setEnabled(allow_composite)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel(
            "Select which artefacts to generate. Additional CSVs are written alongside the manifest using suffixed filenames."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addWidget(self._manifest_checkbox)
        layout.addWidget(self._wide_checkbox)
        layout.addWidget(self._composite_checkbox)
        layout.addWidget(composite_hint)
        layout.addStretch(1)
        layout.addWidget(button_box)

    def result(self) -> ExportOptions:
        """Return the current selections."""

        return ExportOptions(
            include_manifest=self._manifest_checkbox.isChecked(),
            include_wide_csv=self._wide_checkbox.isChecked(),
            include_composite_csv=self._composite_checkbox.isChecked(),
        )
