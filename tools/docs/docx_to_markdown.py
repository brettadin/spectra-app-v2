#!/usr/bin/env python3
"""Wrapper for legacy tools.docx_to_markdown."""
from __future__ import annotations

import runpy


def main() -> None:
    runpy.run_module("tools.docx_to_markdown", run_name="__main__")


if __name__ == "__main__":
    main()
