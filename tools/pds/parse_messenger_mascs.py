#!/usr/bin/env python3
"""Wrapper for legacy tools.parse_messenger_mascs."""
from __future__ import annotations

import runpy


def main() -> None:
    runpy.run_module("tools.parse_messenger_mascs", run_name="__main__")


if __name__ == "__main__":
    main()
