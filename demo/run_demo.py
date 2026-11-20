#!/usr/bin/env python3
"""Stubbed end-to-end demo. Needs no Xcode, no simulator, no Ollama, no network.

Runs the check loop against a stub simulator and a stub Ollama responder,
then runs a fix dry-run against a throwaway git repo. Writes its report to
demo/output/. Exit code 0 means the loop works end to end.
"""

import json
import os
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from simagent import cli, config as config_mod, fix as fix_mod, simctl

OUT_DIR = os.path.join(HERE, "output")

DEVICES_JSON = json.dumps(
    {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-0": [
                {
                    "name": "iPhone 17",
                    "udid": "DEMO0000-0000-0000-0000-000000000000",
                    "state": "Shutdown",
                    "isAvailable": True,
                }
            ]
        }
    }
)

CANNED_DESCRIPTION = (
    "The screen shows a welcome label reading 'Welcome to Sample' "
    "and a Continue button at the bottom."
)

CANNED_DIFF = """--- a/Sample.swift
+++ b/Sample.swift
@@ -1,3 +1,3 @@
 import SwiftUI

-struct SampleView: View { var body: some View { Text("Hello") } }
+struct SampleView: View { var body: some View { Text("Welcome to Sample") } }
"""


def make_png(width, height, rgb):
    def chunk(ctype, data):
        block = struct.pack(">I", len(data)) + ctype + data
        return block + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)

    raw = b""
    for _ in range(height):
        raw += b"\x00" + bytes(rgb) * width
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def stub_runner(cmd, timeout=300):
    if cmd == simctl.list_devices_cmd():
        return DEVICES_JSON
    if "screenshot" in cmd:
        with open(cmd[-1], "wb") as fh:
            fh.write(make_png(64, 64, (200, 220, 240)))
    return ""


def stub_describe(host, model, image_path, question, timeout=600):
    return CANNED_DESCRIPTION


def demo_fix():
    import tempfile

    work = tempfile.mkdtemp(prefix="simagent-demo-fix-")
    env = dict(os.environ, GIT_AUTHOR_NAME="demo", GIT_AUTHOR_EMAIL="demo@example.com",
               GIT_COMMITTER_NAME="demo", GIT_COMMITTER_EMAIL="demo@example.com")
    subprocess.run(["git", "init", "-q", work], check=True, env=env)
    target = os.path.join(work, "Sample.swift")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write('import SwiftUI\n\nstruct SampleView: View { var body: some View { Text("Hello") } }\n')
    subprocess.run(["git", "-C", work, "add", "Sample.swift"], check=True, env=env)
    subprocess.run(["git", "-C", work, "commit", "-q", "-m", "initial"], check=True, env=env)
    diff = fix_mod.extract_diff(CANNED_DIFF)
    return fix_mod.apply_fix(work, diff, dry_run=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cfg = config_mod.resolve(
        screenshots_dir=OUT_DIR,
        reports_dir=OUT_DIR,
    )
    code, report = cli.run_check(
        cfg,
        app_path=os.path.join(HERE, "SampleApp.app"),
        bundle_id="com.example.sampleapp",
        runner=stub_runner,
        describe_fn=stub_describe,
    )
    fix_result = demo_fix()
    print("check exit code: %s" % code)
    print("fix dry-run: %s" % fix_result)
    print("report: %s" % os.path.join(OUT_DIR, "report.html"))
    if code != 0:
        return code
    json_path = os.path.join(OUT_DIR, "report.json")
    html_path = os.path.join(OUT_DIR, "report.html")
    for name in os.listdir(OUT_DIR):
        if name.startswith("check-") and name.endswith(".json"):
            os.rename(os.path.join(OUT_DIR, name), json_path)
        if name.startswith("check-") and name.endswith(".html"):
            os.rename(os.path.join(OUT_DIR, name), html_path)
    print("demo passed: check + fix dry-run, reports in demo/output/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
