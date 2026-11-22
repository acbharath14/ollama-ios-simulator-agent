import json
import os

import pytest

from simagent import simctl

DEVICES_JSON = json.dumps(
    {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-0": [
                {
                    "name": "iPhone 16 Pro",
                    "udid": "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
                    "state": "Shutdown",
                    "isAvailable": True,
                },
                {
                    "name": "iPhone SE",
                    "udid": "11111111-2222-3333-4444-555555555555",
                    "state": "Booted",
                    "isAvailable": True,
                },
            ]
        }
    }
)


def test_list_devices_cmd():
    assert simctl.list_devices_cmd() == [
        "xcrun",
        "simctl",
        "list",
        "devices",
        "--json",
    ]


def test_boot_shutdown_cmds():
    assert simctl.boot_cmd("UDID-1") == ["xcrun", "simctl", "boot", "UDID-1"]
    assert simctl.shutdown_cmd("UDID-1") == ["xcrun", "simctl", "shutdown", "UDID-1"]


def test_install_launch_screenshot_cmds():
    assert simctl.install_cmd("/tmp/MyApp.app") == [
        "xcrun",
        "simctl",
        "install",
        "booted",
        "/tmp/MyApp.app",
    ]
    assert simctl.launch_cmd("com.example.app") == [
        "xcrun",
        "simctl",
        "launch",
        "booted",
        "com.example.app",
    ]
    assert simctl.screenshot_cmd("/tmp/shot.png") == [
        "xcrun",
        "simctl",
        "io",
        "booted",
        "screenshot",
        "/tmp/shot.png",
    ]


def test_xcodebuild_cmd_project():
    cmd = simctl.xcodebuild_cmd(
        project="MyApp.xcodeproj", scheme="MyApp", device_name="iPhone SE"
    )
    assert cmd == [
        "xcodebuild",
        "-project",
        "MyApp.xcodeproj",
        "-scheme",
        "MyApp",
        "-destination",
        "platform=iOS Simulator,name=iPhone SE",
        "build",
    ]


def test_xcodebuild_cmd_workspace_and_default_device():
    cmd = simctl.xcodebuild_cmd(workspace="MyApp.xcworkspace", scheme="MyApp")
    assert "-workspace" in cmd and "MyApp.xcworkspace" in cmd
    assert "platform=iOS Simulator,name=iPhone 16 Pro" in cmd


def test_xcodebuild_cmd_validation():
    with pytest.raises(simctl.SimctlError):
        simctl.xcodebuild_cmd(scheme="MyApp")
    with pytest.raises(simctl.SimctlError):
        simctl.xcodebuild_cmd(project="A.xcodeproj", workspace="A.xcworkspace", scheme="A")
    with pytest.raises(simctl.SimctlError):
        simctl.xcodebuild_cmd(project="A.xcodeproj")


def test_parse_devices():
    devices = simctl.parse_devices(DEVICES_JSON)
    assert len(devices) == 2
    assert devices[0]["name"] == "iPhone 16 Pro"
    assert devices[0]["state"] == "Shutdown"
    assert devices[0]["available"] is True
    assert devices[1]["state"] == "Booted"


def test_parse_devices_bad_json():
    with pytest.raises(simctl.SimctlError):
        simctl.parse_devices("not json")


def test_find_device():
    devices = simctl.parse_devices(DEVICES_JSON)
    found = simctl.find_device(devices, "iPhone SE")
    assert found["udid"] == "11111111-2222-3333-4444-555555555555"
    assert simctl.find_device(devices, "No Such Phone") is None


def test_bundle_id_from_app(tmp_path):
    app = tmp_path / "Sample.app"
    app.mkdir()
    (app / "Info.plist").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>'
        "<key>CFBundleIdentifier</key><string>com.example.sample</string>"
        "</dict></plist>\n",
        encoding="utf-8",
    )
    assert simctl.bundle_id_from_app(str(app)) == "com.example.sample"


def test_bundle_id_from_app_missing(tmp_path):
    with pytest.raises(simctl.SimctlError):
        simctl.bundle_id_from_app(str(tmp_path / "Nope.app"))


def test_run_command_missing_binary():
    with pytest.raises(simctl.SimctlError):
        simctl.run_command(["definitely-not-a-real-binary-xyz"])
