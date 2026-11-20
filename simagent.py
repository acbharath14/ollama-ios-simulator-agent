#!/usr/bin/env python3
"""Entry point. Adds src/ to the path and hands off to the CLI."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from simagent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
