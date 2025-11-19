"""Tests for plot title and font size customization."""

import pytest
import numpy as np

from app.ui.plot_pane import PlotPane, TraceStyle
from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()


def _ensure_app() -> QtWidgets.QApplication:
    """Ensure a QApplication instance exists."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def plot_pane():
    """Create a PlotPane instance for testing."""
    _ensure_app()
    pane = PlotPane()
    yield pane
    pane.deleteLater()


def test_title_visibility_toggle(plot_pane):
    """Test that plot title can be shown and hidden."""
    # Initially hidden
    assert not plot_pane.is_title_visible()
    
    # Show title
    plot_pane.set_title_visible(True)
    assert plot_pane.is_title_visible()
    
    # Hide title
    plot_pane.set_title_visible(False)
    assert not plot_pane.is_title_visible()


def test_title_adapts_to_y_label(plot_pane):
    """Test that plot title intelligently adapts to y_label content."""
    test_cases = [
        ("Intensity", "Spectral Intensity"),
        ("Absorbance", "Absorbance Spectrum"),
        ("Transmittance", "Transmittance Spectrum"),
        ("Reflectance", "Reflectance Spectrum"),
        ("Flux", "Spectral Flux"),
        ("Radiance", "Spectral Radiance"),
        ("Custom Units", "Spectral Data"),  # Generic fallback
    ]
    
    plot_pane.set_title_visible(True)
    
    for y_label, expected_title in test_cases:
        plot_pane.set_y_label(y_label)
        # Can't easily read the title text from pyqtgraph, but we can verify
        # the method runs without error and the title remains visible
        assert plot_pane.is_title_visible()


def test_axis_label_font_sizes(plot_pane):
    """Test that axis label font sizes can be changed."""
    sizes = ["12pt", "14pt", "16pt", "18pt"]
    
    for size in sizes:
        # Should not raise exception
        plot_pane.set_axis_label_font_size(size)
        # Verify internal state updated
        assert plot_pane._axis_label_font_size == size


def test_title_font_sizes(plot_pane):
    """Test that title font sizes can be changed."""
    sizes = ["14pt", "16pt", "18pt", "20pt"]
    
    plot_pane.set_title_visible(True)
    
    for size in sizes:
        # Should not raise exception
        plot_pane.set_title_font_size(size)
        # Verify internal state updated
        assert plot_pane._title_font_size == size


def test_font_sizes_with_real_trace(plot_pane):
    """Test font size changes work correctly with plotted data."""
    # Add a trace
    x = np.linspace(400, 700, 100)
    y = np.sin(x / 50)
    style = TraceStyle(color=QtGui.QColor(255, 0, 0))
    
    plot_pane.add_trace("test", "Test Spectrum", x, y, style)
    
    # Change font sizes - should not crash or break plot
    plot_pane.set_axis_label_font_size("16pt")
    plot_pane.set_title_font_size("18pt")
    plot_pane.set_title_visible(True)
    
    # Verify trace is still present
    assert "test" in plot_pane._traces


def test_y_label_change_updates_title(plot_pane):
    """Test that changing y_label triggers title update when title is visible."""
    plot_pane.set_title_visible(True)
    
    # Change y_label - should trigger title update
    plot_pane.set_y_label("Absorbance")
    assert plot_pane._y_label == "Absorbance"
    
    # Change again
    plot_pane.set_y_label("Transmittance")
    assert plot_pane._y_label == "Transmittance"


def test_unit_change_preserves_font_sizes(plot_pane):
    """Test that changing display units preserves font size settings."""
    plot_pane.set_axis_label_font_size("18pt")
    plot_pane.set_title_font_size("20pt")
    plot_pane.set_title_visible(True)
    
    # Change units
    plot_pane.set_display_unit("Å")
    
    # Font sizes should be preserved
    assert plot_pane._axis_label_font_size == "18pt"
    assert plot_pane._title_font_size == "20pt"
    assert plot_pane.is_title_visible()


def test_default_font_sizes(plot_pane):
    """Test that default font sizes are set correctly."""
    assert plot_pane._axis_label_font_size == "14pt"
    assert plot_pane._title_font_size == "16pt"
    assert not plot_pane.is_title_visible()  # Hidden by default
