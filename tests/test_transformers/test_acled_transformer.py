import pandas as pd

from pipeline.transformers import acled as t_acled
from pipeline.utils.id_gen import make_uuid
from pipeline.utils.iso3 import name_to_iso3


def _write_regional_csv(path):
    df = pd.DataFrame(
        [
            {
                "WEEK": "2026-01-04",
                "REGION": "Northern Africa",
                "COUNTRY": "Turkey",
                "ADMIN1": "Istanbul",
                "EVENT_TYPE": "Violence against civilians",
                "SUB_EVENT_TYPE": "Attack",
                "EVENTS": 3,
                "FATALITIES": 5,
                "DISORDER_TYPE": "Political violence",
                "ID": "47.0",
                "CENTROID_LATITUDE": 41.0082,
                "CENTROID_LONGITUDE": 28.9784,
            },
            {
                "WEEK": "2026-01-11",
                "REGION": "Europe",
                "COUNTRY": "Bailiwick of Jersey",
                "ADMIN1": "Jersey",
                "EVENT_TYPE": "Protests",
                "SUB_EVENT_TYPE": "Peaceful protest",
                "EVENTS": 2,
                "FATALITIES": 0,
                "DISORDER_TYPE": "Demonstrations",
                "ID": "48",
                "CENTROID_LATITUDE": 49.2144,
                "CENTROID_LONGITUDE": -2.1313,
            },
        ]
    )
    df.to_csv(path, index=False)


def test_transform_acled_regional_csv(monkeypatch, tmp_path):
    csv_path = tmp_path / "Africa_aggregated_data_up_to-2026-02-21.csv"
    _write_regional_csv(csv_path)
    (tmp_path / "number_of_political_violence_events_by_country-year.csv").write_text("COUNTRY,YEAR,EVENTS\n")

    monkeypatch.setattr(t_acled, "ACLED_RAW_DIR", tmp_path)

    out = t_acled.transform()

    assert len(out) == 2
    assert out["event_count"].tolist() == [3, 2]
    assert out["fatalities_best"].tolist() == [5, 0]
    assert out["civilian_targeting"].tolist() == [True, False]
    assert out["country_iso3"].tolist() == ["TUR", "JEY"]

    source_event_id = "2026-01-04|Turkey|Istanbul|Violence against civilians|Attack|47"
    expected_incident_id = make_uuid("ACLED", source_event_id)
    first = out.iloc[0]
    assert first["source_event_id"] == source_event_id
    assert first["incident_id"] == expected_incident_id
    assert first["notes"] == "ACLED weekly aggregate (local CSV snapshot)"


def test_transform_drops_invalid_rows(monkeypatch, tmp_path):
    df = pd.DataFrame(
        [
            {
                "WEEK": "bad-date",
                "REGION": "X",
                "COUNTRY": "Turkey",
                "ADMIN1": "X",
                "EVENT_TYPE": "Protests",
                "SUB_EVENT_TYPE": "Peaceful protest",
                "EVENTS": 1,
                "FATALITIES": 0,
                "DISORDER_TYPE": "Demonstrations",
                "ID": 1,
                "CENTROID_LATITUDE": 0.0,
                "CENTROID_LONGITUDE": 0.0,
            },
            {
                "WEEK": "2026-01-01",
                "REGION": "X",
                "COUNTRY": "Turkey",
                "ADMIN1": "X",
                "EVENT_TYPE": "Protests",
                "SUB_EVENT_TYPE": "Peaceful protest",
                "EVENTS": -3,
                "FATALITIES": 0,
                "DISORDER_TYPE": "Demonstrations",
                "ID": 2,
                "CENTROID_LATITUDE": 0.0,
                "CENTROID_LONGITUDE": 0.0,
            },
        ]
    )
    df.to_csv(tmp_path / "Africa_aggregated_data_up_to-2026-02-21.csv", index=False)
    monkeypatch.setattr(t_acled, "ACLED_RAW_DIR", tmp_path)

    out = t_acled.transform()
    assert out.empty


def test_iso3_overrides():
    assert name_to_iso3("Turkey") == "TUR"
    assert name_to_iso3("Bailiwick of Jersey") == "JEY"
    assert name_to_iso3("Bailiwick of Guernsey") == "GGY"
    assert name_to_iso3("Caribbean Netherlands") == "BES"
    assert name_to_iso3("Akrotiri and Dhekelia") == "CYP"
