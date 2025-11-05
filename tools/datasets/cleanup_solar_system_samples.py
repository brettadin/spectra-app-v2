#!/usr/bin/env python3
"""Wrapper for legacy tools.cleanup_solar_system_samples.

Run with:
  python -m tools.datasets.cleanup_solar_system_samples --dry-run
"""
from __future__ import annotations

import runpy


def main() -> None:
    runpy.run_module("tools.cleanup_solar_system_samples", run_name="__main__")


if __name__ == "__main__":
    main()
