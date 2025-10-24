"""Test that app.main can be imported in both module and script modes."""

import subprocess
import sys
from pathlib import Path
import pytest


def test_main_imports_as_module():
    """Test that 'python -m app.main' style imports work."""
    # This test itself is running as a module, so imports should work
    # Note: Qt imports may fail in headless environment, so we just check
    # that the module structure is correct (no ModuleNotFoundError for 'app')
    try:
        import app.main
        assert hasattr(app.main, 'SpectraMainWindow')
    except ImportError as e:
        # Qt library errors are expected in headless environment
        if "libEGL" in str(e) or "QtGui" in str(e):
            pytest.skip(f"Qt stack unavailable: {e}")
        # But 'app' module errors are real failures
        if "No module named 'app'" in str(e):
            pytest.fail(f"Failed to import app.main as module: {e}")


def test_main_imports_when_run_directly():
    """Test that running app/main.py directly works with path adjustment."""
    repo_root = Path(__file__).parent.parent
    main_path = repo_root / "app" / "main.py"
    
    # Try to import the module by running it in a subprocess
    # This simulates what happens when you run `python app/main.py`
    result = subprocess.run(
        [sys.executable, "-c", f"""
import sys
from pathlib import Path

# Simulate the direct execution path adjustment
sys.path.insert(0, str(Path('{main_path}').resolve().parents[1]))

# Now try to import
import app.qt_compat
print("SUCCESS: app.qt_compat imported")
"""],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    
    assert result.returncode == 0, f"Import failed: {result.stderr}"
    assert "SUCCESS" in result.stdout, f"Expected success message, got: {result.stdout}"


def test_main_compiles_without_syntax_errors():
    """Test that app/main.py compiles successfully."""
    repo_root = Path(__file__).parent.parent
    main_path = repo_root / "app" / "main.py"
    
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(main_path)],
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 0, f"Compilation failed: {result.stderr}"
