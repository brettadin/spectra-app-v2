#!/usr/bin/env python3
"""Wrapper for legacy tools.validate_manifest."""
from __future__ import annotations

import runpy


def main() -> None:
    runpy.run_module("tools.validate_manifest", run_name="__main__")


if __name__ == "__main__":
    main()
