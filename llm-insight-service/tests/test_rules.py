from datetime import datetime, timedelta, timezone

from app.service import Reading, determine_level


def make_reading(temp, seconds=0):
    ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc) + timedelta(seconds=seconds)
    return Reading(ts=ts, temp_c=temp, humidity=50.0, rssi=-60)


def test_level_ok():
    current = make_reading(25.0)
    level, reason = determine_level(current, None, 30, 35, 5)
    assert level == "OK"
    assert "aman" in reason.lower()


def test_level_warn_threshold():
    current = make_reading(31.0)
    level, reason = determine_level(current, None, 30, 35, 5)
    assert level == "WARN"
    assert "WARN" in reason.upper()


def test_level_alert_threshold():
    current = make_reading(36.5)
    level, reason = determine_level(current, make_reading(34.0, seconds=-60), 30, 35, 5)
    assert level == "ALERT"
    assert "ALERT" in reason.upper()


def test_level_alert_delta():
    previous = make_reading(28.0, seconds=-60)
    current = make_reading(34.5)
    level, reason = determine_level(current, previous, 30, 35, 5)
    assert level == "ALERT"
    assert "naik" in reason.lower()


def test_level_no_alert_when_delta_slow():
    previous = make_reading(28.0, seconds=-600)
    current = make_reading(34.5)
    level, reason = determine_level(current, previous, 30, 35, 5)
    assert level == "WARN"
