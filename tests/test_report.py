import json

import pytest

from simagent import report


def test_build_report_rejects_bad_status():
    with pytest.raises(ValueError):
        report.build_report("t", "b", [{"name": "x", "status": "weird", "detail": ""}])


def test_write_json_round_trip(tmp_path):
    rep = report.build_report(
        "check",
        "all passed",
        [{"name": "build", "status": "pass", "detail": "ok"}],
        screenshots=["screenshots/a.png"],
        notes=["note one"],
    )
    path = tmp_path / "report.json"
    report.write_json(rep, str(path))
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["bottom_line"] == "all passed"
    assert loaded["steps"][0]["status"] == "pass"


def test_write_html_forces_light_background(tmp_path):
    rep = report.build_report(
        "check",
        "bottom line here",
        [{"name": "build", "status": "pass", "detail": "ok"}],
        screenshots=["screenshots/a.png"],
    )
    path = tmp_path / "report.html"
    report.write_html(rep, str(path))
    text = path.read_text(encoding="utf-8")
    assert "background: #ffffff" in text
    assert "bottom line here" in text
    assert "build" in text
    assert "How to read this report" in text
    assert "a.png" in text
    body_pos = text.index("Bottom line")
    steps_pos = text.index("<h2>Steps</h2>")
    assert body_pos < steps_pos
