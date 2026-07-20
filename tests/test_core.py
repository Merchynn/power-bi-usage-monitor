from datetime import date

from powerbi_usage_monitor.api import deduplicate, local_day_window_utc
from powerbi_usage_monitor.pipeline import run_demo


def test_deduplicate_keeps_first_event():
    rows = [{"Id": "1", "value": "first"}, {"Id": "1", "value": "duplicate"}]
    assert deduplicate(rows, "Id") == [{"Id": "1", "value": "first"}]


def test_local_day_window_respects_timezone():
    start, end = local_day_window_utc(date(2026, 7, 19), "America/Sao_Paulo")
    assert start.isoformat().startswith("2026-07-19T03:00:00")
    assert end > start


def test_demo_is_idempotent(tmp_path):
    first = run_demo(tmp_path)
    second = run_demo(tmp_path)
    assert first["events_inserted"] == 2
    assert second["events_inserted"] == 0
