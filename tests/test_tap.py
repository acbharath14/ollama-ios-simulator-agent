import pytest

from simagent import tap


def test_pixel_to_point_retina_default():
    assert tap.pixel_to_point(1170, 2532) == (585.0, 1266.0)


def test_pixel_to_point_scale_one():
    assert tap.pixel_to_point(100, 200, scale=1) == (100.0, 200.0)


def test_pixel_to_point_bad_scale():
    with pytest.raises(tap.TapError):
        tap.pixel_to_point(100, 100, scale=0)


def test_point_to_screen():
    assert tap.point_to_screen(585.0, 1266.0, 120, 45) == (705.0, 1311.0)


def test_click_script_contains_coords():
    script = tap.click_script(705, 1311)
    assert "705" in script
    assert "1311" in script
    assert "CGEventCreateMouseEvent" in script
    assert "CGEventPost" in script


def test_parse_window_position():
    assert tap.parse_window_position("{120, 45}") == (120, 45)
    assert tap.parse_window_position("  {  0, 0 }  ") == (0, 0)


def test_parse_window_position_garbage():
    with pytest.raises(tap.TapError):
        tap.parse_window_position("no position here")


def test_tap_pixel_uses_origin_and_scale():
    seen = {}

    def fake_run(script):
        seen["script"] = script
        return ""

    result = tap.tap_pixel(1170, 2532, scale=2, origin=(120, 45), run=fake_run)
    assert result == (705.0, 1311.0)
    assert "705.0" in seen["script"] or "705" in seen["script"]


def test_tap_pixel_queries_window_when_no_origin():
    def fake_run(script):
        if "System Events" in script:
            return "{10, 20}"
        return ""

    result = tap.tap_pixel(200, 100, scale=2, run=fake_run)
    assert result == (110.0, 70.0)
