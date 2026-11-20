#!/usr/bin/env python3
"""Preflight: check the machine has what simagent needs.

Checks only, never installs. Prints the fix command for each gap.
Exit code 0 means Python and git are present and tests can run.
Ollama, Xcode, and simctl are warnings, not failures.
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from simagent import ollama

MIN_PYTHON = (3, 10)


def check(name, ok, fix=None):
    print("%s %s" % ("PASS" if ok else "WARN", name))
    if not ok and fix:
        print("     fix: %s" % fix)
    return ok


def main():
    ok = True
    ok = check(
        "python %s or later" % ".".join(str(v) for v in MIN_PYTHON),
        sys.version_info >= MIN_PYTHON,
        "install Python 3.10 or later",
    ) and ok
    ok = check("git", shutil.which("git") is not None, "install git") and ok
    try:
        import pytest  # noqa: F401

        pytest_ok = True
    except ImportError:
        pytest_ok = False
    check(
        "pytest",
        pytest_ok,
        "python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt",
    )
    host = ollama.DEFAULT_HOST
    check(
        "Ollama reachable at %s" % host,
        ollama.reachable(host),
        "start Ollama, then run: ollama pull qwen2.5vl:7b && ollama pull qwen2.5-coder:7b",
    )
    check(
        "xcodebuild (Xcode 26.0-26.3 on macOS Sequoia 15.6+, 26.4+ needs Tahoe)",
        shutil.which("xcodebuild") is not None,
        "install Xcode from the App Store or developer.apple.com",
    )
    check(
        "simctl (ships with Xcode)",
        shutil.which("xcrun") is not None,
        "install Xcode, then run: xcode-select --install",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
