"""Simulator driver: builds simctl and xcodebuild commands and parses output.

All command construction is pure and unit-testable without a simulator.
Execution goes through run_command, which raises SimctlError on any failure
instead of returning partial results.
"""

import json
import plistlib
import subprocess


class SimctlError(Exception):
    pass


def list_devices_cmd():
    return ["xcrun", "simctl", "list", "devices", "--json"]


def boot_cmd(device_id):
    return ["xcrun", "simctl", "boot", device_id]


def shutdown_cmd(device_id):
    return ["xcrun", "simctl", "shutdown", device_id]


def install_cmd(app_path):
    return ["xcrun", "simctl", "install", "booted", app_path]


def launch_cmd(bundle_id):
    return ["xcrun", "simctl", "launch", "booted", bundle_id]


def screenshot_cmd(out_path):
    return ["xcrun", "simctl", "io", "booted", "screenshot", out_path]


def xcodebuild_cmd(project=None, workspace=None, scheme=None, device_name=None):
    """Build command for an app. Exactly one of project/workspace is required,
    and a scheme is required so the build target is never ambiguous."""
    if not project and not workspace:
        raise SimctlError("build needs --project or --workspace")
    if project and workspace:
        raise SimctlError("build takes --project or --workspace, not both")
    if not scheme:
        raise SimctlError("build needs --scheme")
    cmd = ["xcodebuild"]
    if workspace:
        cmd += ["-workspace", workspace]
    else:
        cmd += ["-project", project]
    cmd += ["-scheme", scheme]
    cmd += ["-destination", "platform=iOS Simulator,name=%s" % (device_name or "iPhone 16 Pro")]
    cmd += ["build"]
    return cmd


def parse_devices(json_text):
    """Parse `simctl list devices --json` into a flat list of devices."""
    try:
        data = json.loads(json_text)
    except ValueError as exc:
        raise SimctlError("simctl returned unparseable JSON: %s" % exc) from exc
    devices = []
    for runtime, devs in data.get("devices", {}).items():
        for dev in devs:
            devices.append(
                {
                    "name": dev.get("name"),
                    "udid": dev.get("udid"),
                    "state": dev.get("state"),
                    "runtime": runtime,
                    "available": bool(dev.get("isAvailable", False)),
                }
            )
    return devices


def find_device(devices, name):
    for dev in devices:
        if dev.get("name") == name:
            return dev
    return None


def bundle_id_from_app(app_path):
    """Read CFBundleIdentifier from an .app bundle's Info.plist."""
    plist_path = app_path.rstrip("/") + "/Info.plist"
    try:
        with open(plist_path, "rb") as fh:
            info = plistlib.load(fh)
    except (OSError, ValueError) as exc:
        raise SimctlError("cannot read bundle id from %s: %s" % (plist_path, exc)) from exc
    bundle_id = info.get("CFBundleIdentifier")
    if not bundle_id:
        raise SimctlError("Info.plist has no CFBundleIdentifier: %s" % plist_path)
    return bundle_id


def run_command(cmd, timeout=300):
    """Run one command. Returns stdout on success, raises SimctlError otherwise."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise SimctlError("command not found: %s (is Xcode installed?)" % cmd[0]) from exc
    except subprocess.TimeoutExpired as exc:
        raise SimctlError("command timed out after %ss: %s" % (timeout, " ".join(cmd))) from exc
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        raise SimctlError("command failed (%s): %s" % (proc.returncode, detail))
    return proc.stdout
