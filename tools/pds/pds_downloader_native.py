#!/usr/bin/env python3
"""Wrapper for legacy tools.pds_downloader_native.

Use:
  python -m tools.pds.pds_downloader_native [args]
"""
from __future__ import annotations

import runpy


def main() -> None:
    runpy.run_module("tools.pds_downloader_native", run_name="__main__")


if __name__ == "__main__":
    main()
