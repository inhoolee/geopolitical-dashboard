from datetime import date

from pipeline.extractors import gdelt as t_gdelt


def test_quarter_windows_splits_long_range():
    windows = t_gdelt._quarter_windows(date(2020, 1, 1), date(2020, 6, 30))
    assert windows == [
        (date(2020, 1, 1), date(2020, 3, 30)),
        (date(2020, 3, 31), date(2020, 6, 28)),
        (date(2020, 6, 29), date(2020, 6, 30)),
    ]


def test_quarter_windows_includes_single_day():
    windows = t_gdelt._quarter_windows(date(2020, 1, 1), date(2020, 1, 1))
    assert windows == [(date(2020, 1, 1), date(2020, 1, 1))]


def test_extract_backfill_writes_window_tagged_files(monkeypatch, tmp_path):
    monkeypatch.setattr(t_gdelt, "GDELT_RAW_DIR", tmp_path)
    monkeypatch.setattr(t_gdelt.time, "sleep", lambda *_args, **_kwargs: None)

    extractor = t_gdelt.GDELTExtractor()
    monkeypatch.setattr(extractor, "_get_json", lambda _params: {"articles": []})

    extractor.extract(start_date=date(2020, 1, 1), end_date=date(2020, 6, 30))

    files = sorted(p.name for p in tmp_path.glob("artlist_*.json"))
    assert files == [
        "artlist_20200101_20200330.json",
        "artlist_20200331_20200628.json",
        "artlist_20200629_20200630.json",
    ]


def test_extract_default_range_is_recent_90_days(monkeypatch):
    class _FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 4)

    monkeypatch.setattr(t_gdelt, "date", _FixedDate)
    monkeypatch.setattr(t_gdelt.time, "sleep", lambda *_args, **_kwargs: None)

    calls = []
    extractor = t_gdelt.GDELTExtractor()
    monkeypatch.setattr(extractor, "_fetch_window", lambda _q, start, end: calls.append((start, end)))

    extractor.extract()

    assert calls == [(_FixedDate(2025, 12, 5), _FixedDate(2026, 3, 4))]
