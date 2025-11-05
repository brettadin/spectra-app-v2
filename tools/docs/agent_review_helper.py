#!/usr/bin/env python3
"""Wrapper for legacy tools.agent_review_helper."""
from __future__ import annotations

import runpy


def main() -> None:
    runpy.run_module("tools.agent_review_helper", run_name="__main__")


if __name__ == "__main__":
    main()
