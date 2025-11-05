#!/usr/bin/env python3
"""Wrapper for legacy tools.worklog_helper."""
from __future__ import annotations

import runpy


def main() -> None:
    runpy.run_module("tools.worklog_helper", run_name="__main__")


if __name__ == "__main__":
    main()
