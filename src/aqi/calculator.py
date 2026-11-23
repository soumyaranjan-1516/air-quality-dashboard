"""CPCB National AQI calculator."""
import math

# Each band: (conc_low, conc_high, index_low, index_high)
# Concentrations in µg/m³, except CO in mg/m³.
# The CPCB table leaves the top band open-ended (e.g. "250+"). Here it is capped
# at the concentration where the index reaches 500, using the width of the band
# below it. This is an assumption: state it in your README.
# TODO: verify every number against the official CPCB AQI technical document.
BREAKPOINTS = {
    "PM2.5": [(0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200),
              (91, 120, 201, 300), (121, 250, 301, 400), (251, 380, 401, 500)],
    "PM10":  [(0, 50, 0, 50), (51, 100, 51, 100), (101, 250, 101, 200),
              (251, 350, 201, 300), (351, 430, 301, 400), (431, 510, 401, 500)],
    "NO2":   [(0, 40, 0, 50), (41, 80, 51, 100), (81, 180, 101, 200),
              (181, 280, 201, 300), (281, 400, 301, 400), (401, 520, 401, 500)],
    "O3":    [(0, 50, 0, 50), (51, 100, 51, 100), (101, 168, 101, 200),
              (169, 208, 201, 300), (209, 748, 301, 400), (749, 1287, 401, 500)],
    "CO":    [(0, 1.0, 0, 50), (1.1, 2.0, 51, 100), (2.1, 10, 101, 200),
              (10.1, 17, 201, 300), (17.1, 34, 301, 400), (34.1, 51, 401, 500)],
    "SO2":   [(0, 40, 0, 50), (41, 80, 51, 100), (81, 380, 101, 200),
              (381, 800, 201, 300), (801, 1600, 301, 400), (1601, 2400, 401, 500)],
    "NH3":   [(0, 200, 0, 50), (201, 400, 51, 100), (401, 800, 101, 200),
              (801, 1200, 201, 300), (1201, 1800, 301, 400), (1801, 2400, 401, 500)],
}

CATEGORIES = [(50, "Good"), (100, "Satisfactory"), (200, "Moderate"),
              (300, "Poor"), (400, "Very Poor")]


def sub_index(pollutant: str, conc: float | None) -> int | None:
    """Linear-interpolated sub-index for one pollutant."""
    if conc is None or math.isnan(conc) or conc < 0:
        return None
    for blo, bhi, ilo, ihi in BREAKPOINTS[pollutant]:
        if conc <= bhi:
            conc = max(conc, blo)  # handles the small gaps between bands
            return round((ihi - ilo) / (bhi - blo) * (conc - blo) + ilo)
    return 500  # above the top band: capped at the scale maximum


def compute_aqi(conc: dict) -> tuple[int | None, str | None]:
    """Overall AQI = highest sub-index. Needs >= 3 pollutants, at least one PM.

    Returns (aqi, responsible_pollutant), or (None, None) if the data is insufficient.
    """
    subs = {p: sub_index(p, conc.get(p)) for p in BREAKPOINTS}
    valid = {p: v for p, v in subs.items() if v is not None}
    if len(valid) < 3 or not ({"PM2.5", "PM10"} & valid.keys()):
        return None, None
    dominant = max(valid, key=valid.get)
    return valid[dominant], dominant


def category(aqi: int) -> str:
    for upper, name in CATEGORIES:
        if aqi <= upper:
            return name
    return "Severe"