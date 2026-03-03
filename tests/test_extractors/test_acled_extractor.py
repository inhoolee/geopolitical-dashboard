from pipeline.extractors.acled import ACLEDExtractor


def test_acled_available_with_regional_csv(monkeypatch, tmp_path):
    (tmp_path / "Africa_aggregated_data_up_to-2026-02-21.csv").write_text("WEEK,COUNTRY\n2026-01-01,Kenya\n")
    (tmp_path / "number_of_political_violence_events_by_country-year.csv").write_text("COUNTRY,YEAR,EVENTS\n")
    (tmp_path / "Africa_aggregated_data_up_to-2026-02-21.xlsx").write_text("placeholder")

    monkeypatch.setattr("pipeline.extractors.acled.ACLED_RAW_DIR", tmp_path)
    extractor = ACLEDExtractor()

    assert extractor.is_available() is True
    extractor.extract()


def test_acled_unavailable_with_only_summary_and_xlsx(monkeypatch, tmp_path):
    (tmp_path / "number_of_reported_fatalities_by_country-year.csv").write_text("COUNTRY,YEAR,FATALITIES\n")
    (tmp_path / "Africa_aggregated_data_up_to-2026-02-21.xlsx").write_text("placeholder")

    monkeypatch.setattr("pipeline.extractors.acled.ACLED_RAW_DIR", tmp_path)
    extractor = ACLEDExtractor()

    assert extractor.is_available() is False
