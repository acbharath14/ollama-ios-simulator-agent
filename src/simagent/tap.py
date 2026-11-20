"""Tap support. EXPERIMENTAL.

A tap posts a mouse click at a screen point through AppleScriptObjC and
CoreGraphics, driven by osascript. No third-party tool is needed.

Coordinate story, read this before using taps:
- A screenshot from simctl is in device PIXELS.
- A tap target is measured in device POINTS: points = pixels / scale.
  Retina simulators use scale 2, which is the default --tap-scale.
- The Simulator app at Physical Size (100 percent) shows one device point
  as one screen point, so the click lands at window origin plus device point.
- Window origin comes from --origin-x and --origin-y, or from asking
  System Events for the Simulator window position. The device bezel and
  title bar sit above the screen, so the first tap usually needs a small
  --origin-y adjustment. Calibrate once, then reuse the values.
- Coordinates are screen points with origin at the top-left of the main
  display, matching System Events window positions.
"""

import re
import subprocess


class TapError(Exception):
    pass


def pixel_to_point(px, py, scale=2):
    """Screenshot pixels to device points."""
    if scale <= 0:
        raise TapError("tap scale must be greater than zero, got %s" % scale)
    return (px / scale, py / scale)


def point_to_screen(px, py, origin_x, origin_y):
    """Device points to absolute screen points, given the window origin."""
    return (origin_x + px, origin_y + py)


def click_script(screen_x, screen_y):
    """AppleScriptObjC snippet that posts a left click at screen coordinates."""
    return (
        'use framework "CoreGraphics"\n'
        "set downEvent to current application's CGEventCreateMouseEvent("
        "missing value, 1, {%s, %s}, 0)\n"
        "current application's CGEventPost(0, downEvent)\n"
        "set upEvent to current application's CGEventCreateMouseEvent("
        "missing value, 2, {%s, %s}, 0)\n"
        "current application's CGEventPost(0, upEvent)\n"
        % (screen_x, screen_y, screen_x, screen_y)
    )


def window_position_script():
    return (
        'tell application "System Events" to tell process "Simulator" '
        "to get position of window 1"
    )


def parse_window_position(text):
    """Parse an AppleScript point such as {120, 45} into (x, y)."""
    match = re.search(r"\{\s*(\d+)\s*,\s*(\d+)\s*\}", text)
    if not match:
        raise TapError("cannot parse Simulator window position from: %r" % text)
    return (int(match.group(1)), int(match.group(2)))


def simulator_window_position(run=None):
    """Ask System Events where the Simulator window is. Returns (x, y)."""
    run = run or _run_osascript
    out = run(window_position_script())
    return parse_window_position(out)


def _run_osascript(script):
    try:
        proc = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=30
        )
    except FileNotFoundError as exc:
        raise TapError("osascript not found (this feature needs macOS)") from exc
    if proc.returncode != 0:
        raise TapError("osascript failed: %s" % proc.stderr.strip())
    return proc.stdout


def tap_at(screen_x, screen_y, run=None):
    """Post one click at absolute screen coordinates."""
    run = run or _run_osascript
    run(click_script(screen_x, screen_y))
    return (screen_x, screen_y)


def tap_pixel(px, py, scale=2, origin=None, run=None):
    """Tap a point measured in screenshot pixels. Origin is the Simulator
    window position (x, y); when omitted it is queried from System Events."""
    if origin is None:
        origin = simulator_window_position(run=run)
    point_x, point_y = pixel_to_point(px, py, scale)
    screen_x, screen_y = point_to_screen(point_x, point_y, origin[0], origin[1])
    return tap_at(screen_x, screen_y, run=run)
