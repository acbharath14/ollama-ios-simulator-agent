"""Command line interface.

Commands:
  devices   list simulator devices
  boot      boot a simulator by name
  build     build the app with xcodebuild
  run       install, launch, and screenshot the app
  describe  ask the vision model one narrow question about a screenshot
  tap       tap a point measured in screenshot pixels (EXPERIMENTAL)
  check     full loop: build, run, screenshot, describe, report. Report-first,
            never auto-fixes.
  fix       apply one model-proposed single-file fix. Dry run is the default.

Exit code is 0 on success, 1 on any failed step. Errors print as one line.
"""

import argparse
import datetime
import os
import sys

from . import config as config_mod
from . import fix as fix_mod
from . import ollama
from . import report as report_mod
from . import simctl
from . import tap as tap_mod

DEFAULT_DESCRIBE_QUESTION = (
    "Describe what is on this screen, element by element. "
    "Name each visible button, label, and text field."
)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="simagent",
        description="Drive the iOS Simulator with local Ollama models.",
    )
    parser.add_argument("--config", default=None, help="path to simagent.json")
    parser.add_argument("--ollama-host", default=None, help="Ollama base URL")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("devices", help="list simulator devices")
    p.set_defaults(func=cmd_devices)

    p = sub.add_parser("boot", help="boot a simulator by name")
    p.add_argument("--device", default=None, help="simulator device name")
    p.set_defaults(func=cmd_boot)

    p = sub.add_parser("build", help="build the app with xcodebuild")
    p.add_argument("--project", default=None)
    p.add_argument("--workspace", default=None)
    p.add_argument("--scheme", default=None)
    p.add_argument("--device", default=None, help="simulator device name")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("run", help="install, launch, and screenshot the app")
    p.add_argument("--app", required=True, help="path to the .app bundle")
    p.add_argument("--bundle-id", default=None)
    p.add_argument("--screenshot", default=None, help="where to write the PNG")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("describe", help="ask the vision model about a screenshot")
    p.add_argument("--screenshot", required=True)
    p.add_argument("--question", default=DEFAULT_DESCRIBE_QUESTION)
    p.add_argument("--vision-model", default=None)
    p.set_defaults(func=cmd_describe)

    p = sub.add_parser("tap", help="tap a point (EXPERIMENTAL)")
    p.add_argument("--x", type=float, required=True, help="x in screenshot pixels")
    p.add_argument("--y", type=float, required=True, help="y in screenshot pixels")
    p.add_argument("--scale", type=float, default=None, help="pixels per point, default 2")
    p.add_argument("--origin-x", type=float, default=None)
    p.add_argument("--origin-y", type=float, default=None)
    p.set_defaults(func=cmd_tap)

    p = sub.add_parser("check", help="full loop: build, run, describe, report")
    p.add_argument("--app", required=True, help="path to the .app bundle")
    p.add_argument("--bundle-id", default=None)
    p.add_argument("--project", default=None)
    p.add_argument("--workspace", default=None)
    p.add_argument("--scheme", default=None)
    p.add_argument("--device", default=None, help="simulator device name")
    p.add_argument("--question", default=DEFAULT_DESCRIBE_QUESTION)
    p.add_argument("--vision-model", default=None)
    p.add_argument("--screenshots-dir", default=None)
    p.add_argument("--reports-dir", default=None)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("fix", help="apply one model-proposed single-file fix")
    p.add_argument("--file", required=True, help="file to fix, relative to the repo")
    p.add_argument("--problem", required=True, help="one sentence describing the problem")
    p.add_argument("--repo", default=".", help="repo directory, default current directory")
    p.add_argument("--coder-model", default=None)
    p.add_argument("--apply", action="store_true", help="write the fix; default is dry run")
    p.set_defaults(func=cmd_fix)

    return parser


def load_cfg(args):
    path = config_mod.find_config(args.config)
    if args.config and path and not os.path.exists(path):
        raise SystemExit("error: config file not found: %s" % path)
    cfg = config_mod.load_config(path)
    return config_mod.resolve(
        cfg,
        ollama_host=args.ollama_host,
    )


def cmd_devices(args, cfg):
    out = simctl.run_command(simctl.list_devices_cmd())
    devices = simctl.parse_devices(out)
    if not devices:
        print("no simulator devices found")
        return 0
    for dev in devices:
        print("%s  %s  %s  %s" % (dev["name"], dev["udid"], dev["state"], dev["runtime"]))
    return 0


def _boot_device(device_name, runner=None):
    runner = runner or simctl.run_command
    out = runner(simctl.list_devices_cmd())
    devices = simctl.parse_devices(out)
    device = simctl.find_device(devices, device_name)
    if device is None:
        raise simctl.SimctlError("no simulator named %r" % device_name)
    if device["state"] == "Booted":
        return "already booted: %s (%s)" % (device["name"], device["udid"])
    runner(simctl.boot_cmd(device["udid"]))
    return "booted: %s (%s)" % (device["name"], device["udid"])


def cmd_boot(args, cfg):
    device_name = args.device or cfg["device_name"]
    print(_boot_device(device_name))
    return 0


def cmd_build(args, cfg):
    cmd = simctl.xcodebuild_cmd(
        project=args.project or cfg.get("project"),
        workspace=args.workspace or cfg.get("workspace"),
        scheme=args.scheme or cfg.get("scheme"),
        device_name=args.device or cfg["device_name"],
    )
    print("running: %s" % " ".join(cmd))
    simctl.run_command(cmd, timeout=1200)
    print("build passed")
    return 0


def _run_app(app_path, bundle_id, screenshot_path, runner=None):
    runner = runner or simctl.run_command
    if bundle_id is None:
        bundle_id = simctl.bundle_id_from_app(app_path)
    runner(simctl.install_cmd(app_path))
    runner(simctl.launch_cmd(bundle_id))
    if screenshot_path:
        runner(simctl.screenshot_cmd(screenshot_path))
    return bundle_id


def cmd_run(args, cfg):
    shot = args.screenshot
    if shot is None:
        os.makedirs(cfg["screenshots_dir"], exist_ok=True)
        shot = os.path.join(cfg["screenshots_dir"], "latest.png")
    else:
        parent = os.path.dirname(shot)
        if parent:
            os.makedirs(parent, exist_ok=True)
    bundle_id = _run_app(args.app, args.bundle_id, shot)
    print("launched %s" % bundle_id)
    print("screenshot: %s" % shot)
    return 0


def cmd_describe(args, cfg):
    model = args.vision_model or cfg["vision_model"]
    answer = ollama.describe_image(cfg["ollama_host"], model, args.screenshot, args.question)
    print(answer)
    return 0


def cmd_tap(args, cfg):
    scale = args.scale if args.scale is not None else cfg["tap_scale"]
    origin = None
    if args.origin_x is not None and args.origin_y is not None:
        origin = (args.origin_x, args.origin_y)
    screen_x, screen_y = tap_mod.tap_pixel(args.x, args.y, scale=scale, origin=origin)
    print("tapped screen point (%s, %s)" % (screen_x, screen_y))
    return 0


def run_check(cfg, app_path, bundle_id=None, project=None, workspace=None,
              scheme=None, device_name=None, question=None,
              vision_model=None, screenshots_dir=None, reports_dir=None,
              runner=None, describe_fn=None):
    """Full loop. Returns (exit_code, report_dict). Never auto-fixes."""
    runner = runner or simctl.run_command
    describe_fn = describe_fn or ollama.describe_image
    shots_dir = screenshots_dir or cfg["screenshots_dir"]
    reps_dir = reports_dir or cfg["reports_dir"]
    os.makedirs(shots_dir, exist_ok=True)
    os.makedirs(reps_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    shot_path = os.path.join(shots_dir, "check-%s.png" % stamp)
    steps = []
    model = vision_model or cfg["vision_model"]
    device = device_name or cfg["device_name"]
    question = question or DEFAULT_DESCRIBE_QUESTION
    description = ""
    failed = False

    build_cmd = None
    proj = project or cfg.get("project")
    ws = workspace or cfg.get("workspace")
    sch = scheme or cfg.get("scheme")
    if proj or ws:
        try:
            build_cmd = simctl.xcodebuild_cmd(proj, ws, sch, device)
        except simctl.SimctlError as exc:
            steps.append({"name": "build", "status": "fail", "detail": str(exc)})
            failed = True
    if build_cmd is not None and not failed:
        try:
            runner(build_cmd, timeout=1200)
            steps.append({"name": "build", "status": "pass", "detail": "xcodebuild succeeded"})
        except simctl.SimctlError as exc:
            steps.append({"name": "build", "status": "fail", "detail": str(exc)})
            failed = True
    elif build_cmd is None:
        steps.append({"name": "build", "status": "skipped", "detail": "no project given"})

    if not failed:
        try:
            detail = _boot_device(device, runner=runner)
            steps.append({"name": "boot", "status": "pass", "detail": detail})
        except simctl.SimctlError as exc:
            steps.append({"name": "boot", "status": "fail", "detail": str(exc)})
            failed = True

    if not failed:
        try:
            resolved = _run_app(app_path, bundle_id, shot_path, runner=runner)
            steps.append({"name": "run", "status": "pass",
                          "detail": "launched %s, screenshot %s" % (resolved, shot_path)})
        except simctl.SimctlError as exc:
            steps.append({"name": "run", "status": "fail", "detail": str(exc)})
            failed = True

    if not failed:
        try:
            description = describe_fn(cfg["ollama_host"], model, shot_path, question)
            steps.append({"name": "describe", "status": "pass",
                          "detail": description[:200]})
        except ollama.OllamaError as exc:
            steps.append({"name": "describe", "status": "fail", "detail": str(exc)})
            failed = True

    if failed:
        bottom = "check stopped at the first failed step; see the steps below."
    else:
        bottom = "build, launch, and screenshot all passed. Vision model description: %s" % description
    report = report_mod.build_report(
        title="simagent check %s" % stamp,
        bottom_line=bottom,
        steps=steps,
        screenshots=[shot_path] if os.path.exists(shot_path) else [],
        notes=["Human is the judge. The model describes; you decide whether the screen is right."],
    )
    json_path = os.path.join(reps_dir, "check-%s.json" % stamp)
    html_path = os.path.join(reps_dir, "check-%s.html" % stamp)
    report_mod.write_json(report, json_path)
    report_mod.write_html(report, html_path)
    print(bottom)
    print("report: %s" % html_path)
    return (1 if failed else 0, report)


def cmd_check(args, cfg):
    code, _report = run_check(
        cfg,
        app_path=args.app,
        bundle_id=args.bundle_id,
        project=args.project,
        workspace=args.workspace,
        scheme=args.scheme,
        device_name=args.device,
        question=args.question,
        vision_model=args.vision_model,
        screenshots_dir=args.screenshots_dir,
        reports_dir=args.reports_dir,
    )
    return code


def cmd_fix(args, cfg):
    model = args.coder_model or cfg["coder_model"]
    repo_dir = args.repo
    file_path = os.path.join(repo_dir, args.file)
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            file_text = fh.read()
    except OSError as exc:
        print("error: cannot read %s: %s" % (file_path, exc), file=sys.stderr)
        return 1
    prompt = ollama.fix_prompt(args.file, file_text, args.problem)
    answer = ollama.chat(
        cfg["ollama_host"], model,
        [{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    new_text = fix_mod.extract_file(answer)
    diff = fix_mod.compute_diff(args.file, file_text, new_text)
    result = fix_mod.apply_fix(repo_dir, diff, dry_run=not args.apply)
    print(result)
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        cfg = load_cfg(args)
        return args.func(args, cfg)
    except (simctl.SimctlError, ollama.OllamaError, tap_mod.TapError, fix_mod.FixError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
