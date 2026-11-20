"""Reports. JSON is the machine layer, HTML is the human layer.

The HTML report forces a light background so it stays readable on any
machine. It leads with the bottom line, then the per-step table, then the
screenshots, then a plain-language legend.
"""

import html
import json
import os

STEP_STATUSES = ("pass", "fail", "skipped")


def build_report(title, bottom_line, steps, screenshots=None, notes=None):
    """Assemble a report dict. Steps are dicts with name, status, detail."""
    for step in steps:
        if step.get("status") not in STEP_STATUSES:
            raise ValueError("bad step status: %r" % (step.get("status"),))
    return {
        "title": title,
        "bottom_line": bottom_line,
        "steps": list(steps),
        "screenshots": list(screenshots or []),
        "notes": list(notes or []),
    }


def write_json(report, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    return path


def write_html(report, path):
    rows = []
    for step in report["steps"]:
        rows.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (
                html.escape(step["name"]),
                html.escape(step["status"]),
                html.escape(step.get("detail", "")),
            )
        )
    shots = []
    for shot in report["screenshots"]:
        shots.append(
            '<li><a href="%s">%s</a></li>'
            % (html.escape(shot), html.escape(os.path.basename(shot)))
        )
    notes = "".join("<li>%s</li>" % html.escape(note) for note in report["notes"])
    body = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ background: #ffffff; color: #111111; font-family: -apple-system, Helvetica, Arial, sans-serif; margin: 2em auto; max-width: 760px; padding: 0 1em; }}
h1 {{ font-size: 1.4em; }}
h2 {{ font-size: 1.1em; margin-top: 1.5em; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #cccccc; padding: 0.4em 0.6em; text-align: left; vertical-align: top; }}
th {{ background: #f0f0f0; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p><strong>Bottom line:</strong> {bottom}</p>
<h2>Steps</h2>
<table>
<tr><th>Step</th><th>Status</th><th>Detail</th></tr>
{rows}
</table>
<h2>Screenshots</h2>
<ul>
{shots}
</ul>
<h2>Notes</h2>
<ul>
{notes}
</ul>
<h2>How to read this report</h2>
<p><strong>Build</strong> compiles the app with xcodebuild. <strong>Boot</strong> starts the
simulator device. <strong>Install</strong> copies the app onto the booted simulator.
<strong>Launch</strong> starts the app. <strong>Screenshot</strong> captures the screen to a
file. <strong>Describe</strong> asks the vision model one narrow question about that
screenshot. <strong>Fix</strong> applies a model-proposed diff to one file, or reports
that it was left as a dry run. A step marked fail stops the loop at that step.
The model describes what it sees; the human decides whether the screen is right.</p>
</body>
</html>
""".format(
        title=html.escape(report["title"]),
        bottom=html.escape(report["bottom_line"]),
        rows="\n".join(rows),
        shots="\n".join(shots) if shots else "<li>None</li>",
        notes=notes if notes else "<li>None</li>",
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path
