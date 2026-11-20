# ollama-ios-simulator-agent

Drive the iOS Simulator with local Ollama models. It builds an app, boots a
simulator, installs and launches the app, screenshots it, and asks a vision
model what it sees. It is a free, local alternative to the simulator pane in
Claude Code Desktop, built for a Mac that already runs Ollama.

The human is the judge, never the model. The model describes the screen and
proposes fixes. You decide whether the screen is right and whether a fix
goes in.

## How it works

The loop is mechanical and short, on purpose. Each step does one thing and
reports its result.

1. Build the app with `xcodebuild`.
2. Boot a simulator device with `simctl`.
3. Install the `.app` bundle and launch it by bundle id.
4. Screenshot the booted simulator with `simctl io`.
5. Send the screenshot to `qwen2.5vl:7b` with one narrow question, such as
   "Describe what is on this screen, element by element."
6. Write a report: JSON for machines, HTML for people.

A separate `fix` command asks `qwen2.5-coder:7b` for one single-file fix.
Dry run is the default. Nothing is applied unless you pass `--apply`, and
nothing is ever committed or merged by this tool.

## Requirements

- A Mac. The iOS Simulator runs only on macOS.
- Xcode with the iOS platform installed. Use Xcode 26.0 through 26.3 on
  macOS Sequoia 15.6 or later. Xcode 26.4 and later need macOS Tahoe 26.2
  or later. The simulator itself works on Intel Macs.
- Ollama running on the same Mac at `http://127.0.0.1:11434`.
- The two models pulled: `qwen2.5vl:7b` for screenshots and
  `qwen2.5-coder:7b` for fixes.
- Python 3.10 or later and git. Tests need pytest, which is a dev
  dependency only. The runtime is stdlib only.

## Quickstart

These commands are for the iMac, run from the repo root. The preflight
script checks what is present and prints the fix command for each gap. It
never installs anything itself.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
python3 scripts/preflight.py
```

Pull the models once, then start Ollama if it is not already running:

```
ollama pull qwen2.5vl:7b
ollama pull qwen2.5-coder:7b
```

Copy the example config and edit it for your project:

```
cp simagent.json.example simagent.json
```

List the simulators on the Mac:

```
python3 simagent.py devices
```

Run the full loop against a built app:

```
python3 simagent.py check --app build/MyApp.app --project MyApp.xcodeproj --scheme MyApp
```

The report lands in `reports/` as `check-<timestamp>.json` and
`check-<timestamp>.html`. Open the HTML file to read the bottom line and
the per-step table.

## Commands

All commands run from the repo root as `python3 simagent.py <command>`.

- `devices`: list simulator devices with name, UDID, state, and runtime.
- `boot --device "iPhone 17"`: boot a simulator by name. Reports when the
  device is already booted instead of failing.
- `build --project MyApp.xcodeproj --scheme MyApp`: build with xcodebuild
  for the iOS Simulator. `--workspace` works in place of `--project`.
  `--device` picks the destination simulator.
- `run --app build/MyApp.app`: install the app on the booted simulator,
  launch it, and write a screenshot to `screenshots/latest.png`. The bundle
  id comes from the app's Info.plist unless `--bundle-id` is given.
- `describe --screenshot screenshots/latest.png`: ask the vision model one
  narrow question about a screenshot. `--question` overrides the default.
- `tap --x 585 --y 900`: tap a point measured in screenshot pixels.
  Experimental, see below.
- `check --app build/MyApp.app`: the full loop. Build, boot, run,
  screenshot, describe, report. It stops at the first failed step and still
  writes the report. It never fixes anything.
- `fix --file App.swift --problem "Continue button does nothing"`: ask the
  coder model for one single-file fix. Dry run is the default. Pass
  `--apply` to write it. The working tree must be clean.

Global flags: `--config` points at a config file, `--ollama-host`
overrides the Ollama URL for one run.

## Configuration

Defaults live in `simagent.json` in the repo root. CLI flags override the
file, and the file overrides the built-in defaults. Copy
`simagent.json.example` to `simagent.json` and edit it.

| Key | Default | Meaning |
| --- | --- | --- |
| ollama_host | http://127.0.0.1:11434 | Ollama server |
| vision_model | qwen2.5vl:7b | Model that reads screenshots |
| coder_model | qwen2.5-coder:7b | Model that proposes fixes |
| device_name | iPhone 17 | Simulator to boot and target |
| tap_scale | 2 | Screenshot pixels per device point |
| scheme | null | xcodebuild scheme |
| project | null | Path to the .xcodeproj |
| workspace | null | Path to the .xcworkspace |
| screenshots_dir | screenshots | Where screenshots go |
| reports_dir | reports | Where reports go |

## The check loop, in detail

`check` is the command you will use most. It is report-first by design:
the run produces a report whether it passes or fails, and it never changes
your code.

- Build runs only when a project or workspace is configured. Without one,
  the step is marked skipped and the loop continues.
- Boot finds the named device and boots it, or reports it is already booted.
- Run installs the app, launches it, and screenshots it. The bundle id is
  read from the app bundle when you do not pass one.
- Describe sends the screenshot to the vision model with one narrow
  question. The answer is stored in the report, truncated to 200 characters
  in the step detail and kept in full in the bottom line.
- The report is written to `reports/` in both formats before the command
  exits. A failed step ends the loop at that step with exit code 1.

## Fix, in detail

`fix` asks the coder model for a unified diff that changes one file. The
prompt is short: the file, one sentence describing the problem, and the file
contents. The model answers with a diff only.

Before anything is written, the tool checks three things:

1. The working tree is clean. A dirty tree is refused.
2. The output contains real diff hunks.
3. The diff validates with `git apply --check`.

With no `--apply`, the command stops there and reports that the diff
validated. With `--apply`, it runs `git apply` on the working tree. It
never commits, never creates a branch, and never merges. Review the change
with `git diff` afterwards, like any other edit.

## Taps

Taps are experimental. A tap posts a mouse click at a screen point using
AppleScript and CoreGraphics, driven by `osascript`. No third-party tool
is needed.

Coordinates work like this. A screenshot is in device pixels. A tap target
is in device points: points equal pixels divided by scale. Retina
simulators use scale 2, which is the default `--tap-scale`. Set the
Simulator to Physical Size (100 percent) so one device point maps to one
screen point. Then the click lands at the Simulator window origin plus the
device point.

```
python3 simagent.py tap --x 585 --y 900
```

`--origin-x` and `--origin-y` set the window origin by hand. Without them,
the tool asks System Events for the Simulator window position. The device
bezel and title bar sit above the screen, so the first tap usually needs a
small `--origin-y` adjustment. Calibrate once, then reuse the values.

## Demo

The demo runs the whole loop with everything stubbed: a fake simctl, a fake
Ollama responder, and a fake app bundle. It needs no Xcode, no simulator,
no Ollama, and no network, so it runs anywhere, including CI.

```
python demo/run_demo.py
```

It runs `check` against the stubs and a `fix` dry-run against a throwaway
git repo, then writes `demo/output/report.json` and `report.html`.

## Reports

Every `check` writes two files with the same timestamp.

- JSON is the machine layer. It carries the title, the bottom line, the
  per-step table with status and detail, the screenshot paths, and notes.
- HTML is the human layer. It forces a light background, leads with the
  bottom line, then shows the steps, the screenshots, and a plain-language
  legend explaining what each step means.

## Limitations

Read these before trusting the tool with a real app.

- The vision model is coarse. It can say whether a button is visible and
  what the screen contains. It cannot reliably say whether a screen looks
  right, whether spacing is off, or whether a button is clipped. That
  judgment is yours. This is the main reason the human is the judge.
- Taps are experimental. Coordinates depend on the Simulator window size,
  position, and scale. Expect to calibrate the origin once per setup.
- CPU inference is slow. Expect the better part of a minute per screenshot
  read on a CPU-only Mac, and similar for each fix call. The loop is built
  for one screen at a time, not for sweeping a whole app.
- The coder model sees one file at a time. Fixes that span several files
  are out of scope for this version.
- The tool drives simulated devices only. It cannot control a physical
  iPhone or iPad.
- Xcode 26.0 through 26.3 run on Sequoia 15.6 or later. Xcode 26.4 and
  later need Tahoe. Check your pair before installing.

## Example session

A first run against a small app, with a project configured in
`simagent.json`:

```
python3 simagent.py check --app build/MyApp.app
```

When the loop passes, the report says so in the bottom line and shows the
vision model description:

```
build, launch, and screenshot all passed. Vision model description: The
screen shows a welcome label reading 'Welcome to Sample' and a Continue
button at the bottom.
report: reports/check-2026-11-19-233000.html
```

When the description shows a problem, ask for a fix. This is a dry run
unless you pass `--apply`:

```
python3 simagent.py fix --file Sample.swift --problem "Continue button does nothing"
```

The command prints `dry-run: diff validated, nothing written`. Read the
diff with `git diff` after applying, and run your own tests before keeping
it.

## Troubleshooting

- `command not found: xcrun` or `xcodebuild` means Xcode is not installed
  or not selected. Install Xcode, then run `xcode-select -p` to check
  which install is selected.
- `no simulator devices found` means Xcode has no simulators yet. Open
  Xcode, go to Settings, Components, and download an iOS simulator
  runtime, or run `xcodebuild -downloadPlatform iOS`.
- `cannot reach Ollama` means Ollama is not running. Start it, then check
  `curl http://127.0.0.1:11434/api/tags` answers. Pull the models if the
  server answers but a call fails with a model error.
- A tap lands in the wrong place. Set the Simulator to Physical Size
  (100 percent) from the Window menu, then calibrate `--origin-y` once.
  The title bar and bezel sit above the screen, so the origin is usually
  a little lower than the window position suggests.
- `working tree is dirty` from `fix` means the repo has uncommitted
  changes. Commit or stash them first. The tool refuses to apply a fix
  onto a dirty tree so the diff stays reviewable.

## Design notes

- Stdlib only at runtime. The Ollama client uses `urllib`, the plist
  reader uses `plistlib`, and the reports use `json` and `html`. The only
  third-party dependency is pytest, for tests.
- The model never decides. It describes and proposes. Every decision to
  act stays with the person running the command.
- Failures are reported, never hidden. A failed Ollama call is a failed
  step in the report, not a made-up answer.
- Command construction is pure. The simctl and xcodebuild commands are
  built by functions that take values and return lists, so they are tested
  without a simulator present.

## Tests

```
bash scripts/run_tests.sh
```

The runner runs the preflight script first, then pytest. Pass
`--skip-preflight` or set `SIMAGENT_SKIP_PREFLIGHT=1` to skip the
preflight check. Tests live in `tests/` and cover the simulator driver,
the Ollama payloads, tap coordinate conversion, config merging, report
generation, the fix flow against a real temporary git repo, and CLI
parsing. The demo is the end-to-end check.
