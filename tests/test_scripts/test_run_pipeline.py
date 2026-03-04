import argparse
from datetime import date

import pytest

from scripts import run_pipeline as rp


class _FakeConn:
    def execute(self, *_args, **_kwargs):
        return self

    def fetchone(self):
        return [0]


def _stub_main_dependencies(monkeypatch):
    monkeypatch.setattr(rp, "setup_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(rp, "get_connection", lambda: _FakeConn())
    monkeypatch.setattr(rp, "bootstrap_schema", lambda _conn: None)
    monkeypatch.setattr(
        rp,
        "SOURCES",
        {
            "gdelt": (object(), lambda: None, "fact_news_pulse"),
        },
    )


def test_parse_iso_date_rejects_invalid_format():
    with pytest.raises(argparse.ArgumentTypeError, match="Expected format: YYYY-MM-DD"):
        rp.parse_iso_date("2026/03/04")


def test_validate_gdelt_end_date_requires_start_date():
    with pytest.raises(ValueError, match="--gdelt-end-date requires --gdelt-start-date"):
        rp.validate_gdelt_date_args(
            source_keys=["gdelt"],
            gdelt_start_date=None,
            gdelt_end_date=date(2020, 6, 30),
        )


def test_validate_gdelt_date_args_rejects_start_after_end():
    with pytest.raises(ValueError, match="cannot be after"):
        rp.validate_gdelt_date_args(
            source_keys=["gdelt"],
            gdelt_start_date=date(2020, 7, 1),
            gdelt_end_date=date(2020, 6, 30),
        )


def test_validate_gdelt_date_args_requires_gdelt_source():
    with pytest.raises(ValueError, match="require --sources to include 'gdelt'"):
        rp.validate_gdelt_date_args(
            source_keys=["seed", "wb"],
            gdelt_start_date=date(2020, 1, 1),
            gdelt_end_date=date(2020, 6, 30),
        )


def test_validate_gdelt_start_only_defaults_end_to_today():
    start_date, end_date = rp.validate_gdelt_date_args(
        source_keys=["gdelt"],
        gdelt_start_date=date(2020, 1, 1),
        gdelt_end_date=None,
        today=date(2026, 3, 4),
    )
    assert start_date == date(2020, 1, 1)
    assert end_date == date(2026, 3, 4)


def test_main_passes_gdelt_range_to_run_source(monkeypatch):
    _stub_main_dependencies(monkeypatch)
    calls = []

    def _fake_run_source(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(rp, "run_source", _fake_run_source)
    monkeypatch.setattr(
        rp.sys,
        "argv",
        [
            "run_pipeline.py",
            "--sources",
            "gdelt",
            "--gdelt-start-date",
            "2020-01-01",
            "--gdelt-end-date",
            "2020-06-30",
        ],
    )

    rp.main()

    assert len(calls) == 1
    assert calls[0]["extract_kwargs"] == {
        "start_date": date(2020, 1, 1),
        "end_date": date(2020, 6, 30),
    }


def test_main_start_only_sets_end_to_today(monkeypatch):
    _stub_main_dependencies(monkeypatch)
    calls = []

    def _fake_run_source(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(rp, "run_source", _fake_run_source)
    monkeypatch.setattr(
        rp.sys,
        "argv",
        [
            "run_pipeline.py",
            "--sources",
            "gdelt",
            "--gdelt-start-date",
            "2020-01-01",
        ],
    )

    rp.main()

    assert len(calls) == 1
    assert calls[0]["extract_kwargs"]["start_date"] == date(2020, 1, 1)
    assert calls[0]["extract_kwargs"]["end_date"] == date.today()


def test_main_without_gdelt_dates_keeps_default_behavior(monkeypatch):
    _stub_main_dependencies(monkeypatch)
    calls = []

    def _fake_run_source(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(rp, "run_source", _fake_run_source)
    monkeypatch.setattr(
        rp.sys,
        "argv",
        [
            "run_pipeline.py",
            "--sources",
            "gdelt",
        ],
    )

    rp.main()

    assert len(calls) == 1
    assert calls[0]["extract_kwargs"] == {
        "start_date": None,
        "end_date": None,
    }
