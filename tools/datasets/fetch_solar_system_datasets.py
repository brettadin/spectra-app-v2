#!/usr/bin/env python3
"""Wrapper for legacy tools.fetch_solar_system_datasets."""
from __future__ import annotations

import runpy


def main() -> None:
    runpy.run_module("tools.fetch_solar_system_datasets", run_name="__main__")


if __name__ == "__main__":
    main()
