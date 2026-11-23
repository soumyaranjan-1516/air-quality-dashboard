import pytest

from src.aqi.calculator import category, compute_aqi, sub_index


@pytest.mark.parametrize("pollutant, conc, expected", [
    ("PM2.5", 0, 0), ("PM2.5", 30, 50), ("PM2.5", 45, 75), ("PM2.5", 60, 100),
    ("PM2.5", 380, 500), ("PM2.5", 1000, 500),
    ("PM10", 100, 100), ("PM10", 250, 200),
    ("NO2", 40, 50), ("NO2", 80, 100),
    ("CO", 2.0, 100), ("CO", 10, 200),
    ("O3", 168, 200), ("SO2", 380, 200), ("NH3", 200, 50),
])
def test_sub_index(pollutant, conc, expected):
    assert sub_index(pollutant, conc) == expected


def test_invalid_input():
    assert sub_index("PM2.5", None) is None
    assert sub_index("PM2.5", -5) is None
    assert sub_index("PM2.5", float("nan")) is None


def test_compute_aqi_takes_the_highest_subindex():
    assert compute_aqi({"PM2.5": 45, "PM10": 80, "NO2": 20}) == (80, "PM10")


def test_missing_values_are_ignored():
    data = {"PM2.5": 45, "PM10": float("nan"), "NO2": 20, "SO2": 10}
    assert compute_aqi(data) == (75, "PM2.5")


def test_needs_three_pollutants():
    assert compute_aqi({"PM2.5": 45, "NO2": 20}) == (None, None)


def test_needs_a_pm_pollutant():
    assert compute_aqi({"NO2": 20, "SO2": 10, "CO": 0.5}) == (None, None)


def test_category():
    assert category(50) == "Good"
    assert category(75) == "Satisfactory"
    assert category(301) == "Very Poor"
    assert category(450) == "Severe"