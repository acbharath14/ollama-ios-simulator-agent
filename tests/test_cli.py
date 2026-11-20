import json

from simagent import cli
from simagent import config as config_mod
from simagent import simctl

DEVICES_JSON = json.dumps(
    {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-0": [
                {
                    "name": "iPhone 17",
                    "udid": "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
                    "state": "Shutdown",
                    "isAvailable": True,
                }
            ]
        }
    }
)


def _cfg(tmp_path):
    return config_mod.resolve(
        screenshots_dir=str(tmp_path / "shots"),
        reports_dir=str(tmp_path / "reports"),
    )


def _stub_runner_factory(shot_path=None, fail_on=None):
    def runner(cmd, timeout=300):
        if cmd == simctl.list_devices_cmd():
            return DEVICES_JSON
        if fail_on and fail_on in " ".join(cmd):
            raise simctl.SimctlError("stub failure on: %s" % " ".join(cmd))
        if "screenshot" in cmd:
            with open(cmd[-1], "wb") as fh:
                fh.write(b"\x89PNG stub")
        return ""

    return runner


def test_parse_devices_command():
    args = cli.build_parser().parse_args(["devices"])
    assert args.command == "devices"


def test_parse_boot_command():
    args = cli.build_parser().parse_args(["boot", "--device", "iPhone SE"])
    assert args.device == "iPhone SE"


def test_parse_build_command():
    args = cli.build_parser().parse_args(
        ["build", "--project", "A.xcodeproj", "--scheme", "A"]
    )
    assert args.project == "A.xcodeproj"
    assert args.scheme == "A"


def test_parse_run_command():
    args = cli.build_parser().parse_args(["run", "--app", "/tmp/A.app"])
    assert args.app == "/tmp/A.app"


def test_parse_describe_command():
    args = cli.build_parser().parse_args(["describe", "--screenshot", "s.png"])
    assert args.screenshot == "s.png"


def test_parse_tap_command():
    args = cli.build_parser().parse_args(["tap", "--x", "100", "--y", "200"])
    assert args.x == 100
    assert args.y == 200


def test_parse_check_command():
    args = cli.build_parser().parse_args(["check", "--app", "/tmp/A.app"])
    assert args.app == "/tmp/A.app"


def test_parse_fix_command():
    args = cli.build_parser().parse_args(
        ["fix", "--file", "App.swift", "--problem", "crash on launch"]
    )
    assert args.file == "App.swift"
    assert args.apply is False


def _describe_stub(host, model, image_path, question, timeout=600):
    return "The screen shows a welcome label and a Continue button."


def test_run_check_happy_path(tmp_path):
    cfg = _cfg(tmp_path)
    code, rep = cli.run_check(
        cfg,
        app_path="/tmp/Sample.app",
        bundle_id="com.example.sample",
        runner=_stub_runner_factory(),
        describe_fn=_describe_stub,
    )
    assert code == 0
    statuses = {step["name"]: step["status"] for step in rep["steps"]}
    assert statuses["build"] == "skipped"
    assert statuses["boot"] == "pass"
    assert statuses["run"] == "pass"
    assert statuses["describe"] == "pass"
    assert rep["screenshots"], "screenshot should be recorded"
    assert (tmp_path / "reports").exists()
    assert list((tmp_path / "reports").glob("check-*.json"))
    assert list((tmp_path / "reports").glob("check-*.html"))


def test_run_check_stops_at_failed_step(tmp_path):
    cfg = _cfg(tmp_path)
    code, rep = cli.run_check(
        cfg,
        app_path="/tmp/Sample.app",
        bundle_id="com.example.sample",
        runner=_stub_runner_factory(fail_on="install"),
        describe_fn=_describe_stub,
    )
    assert code == 1
    statuses = {step["name"]: step["status"] for step in rep["steps"]}
    assert statuses["run"] == "fail"
    assert "describe" not in statuses
    assert list((tmp_path / "reports").glob("check-*.html"))


def test_run_check_skips_build_without_project(tmp_path):
    cfg = _cfg(tmp_path)
    code, rep = cli.run_check(
        cfg,
        app_path="/tmp/Sample.app",
        bundle_id="com.example.sample",
        runner=_stub_runner_factory(),
        describe_fn=_describe_stub,
    )
    assert code == 0
    statuses = {step["name"]: step["status"] for step in rep["steps"]}
    assert statuses["build"] == "skipped"
