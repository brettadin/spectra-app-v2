#!/usr/bin/env python3
"""Wrapper for legacy tools.pds_wget_bulk."""
from __future__ import annotations

import runpy


def main() -> None:
    runpy.run_module("tools.pds_wget_bulk", run_name="__main__")


if __name__ == "__main__":
    main()
