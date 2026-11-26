"""Download hourly weather per city from Open-Meteo's archive API (cached on disk)."""
import time

import pandas as pd
import requests

from src.config import CITIES, RAW_DIR

URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY = ["temperature_2m", "relative_humidity_2m", "precipitation",
          "surface_pressure", "wind_speed_10m", "wind_direction_10m"]
WEATHER_DIR = RAW_DIR / "weather"
END_DATE = "2020-07-01"  # last date in the AQI dataset


def fetch_chunk(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "hourly": ",".join(HOURLY),
        "timezone": "Asia/Kolkata",
        "wind_speed_unit": "ms",
    }
    for attempt in range(5):
        try:
            resp = requests.get(URL, params=params, timeout=60)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            wait = 10 * (attempt + 1)
            print(f"    network error ({type(exc).__name__}), retrying in {wait}s...")
            time.sleep(wait)
            continue
        if resp.status_code == 200:
            return pd.DataFrame(resp.json()["hourly"]).rename(columns={"time": "datetime"})
        if resp.status_code == 429:  # rate limited: wait, then retry
            print("    rate limited, waiting...")
            time.sleep(30 * (attempt + 1))
            continue
        if resp.status_code == 400:
            raise ValueError(resp.json().get("reason", resp.text))
        resp.raise_for_status()
    raise RuntimeError(f"Could not fetch {start}..{end} after several attempts")

def fetch_city(city: str, cfg: dict) -> pd.DataFrame:
    start, end = pd.Timestamp(cfg["start"]), pd.Timestamp(END_DATE)
    parts = []
    for year in range(start.year, end.year + 1):
        s = max(start, pd.Timestamp(year=year, month=1, day=1))
        e = min(end, pd.Timestamp(year=year, month=12, day=31))
        print(f"  {city}: {s.date()} -> {e.date()}")
        parts.append(fetch_chunk(cfg["lat"], cfg["lon"],
                                 s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")))
        time.sleep(1)
    df = pd.concat(parts, ignore_index=True)
    df.insert(0, "city", city)
    return df


def summary() -> None:
    frames = [pd.read_csv(p, parse_dates=["datetime"])
              for p in sorted(WEATHER_DIR.glob("*_hourly.csv"))]
    w = pd.concat(frames)
    print("\nRows, date range and missing values per city:")
    print(w.groupby("city").agg(
        rows=("datetime", "size"),
        first=("datetime", "min"),
        last=("datetime", "max"),
        missing_values=("temperature_2m", lambda s: int(s.isna().sum())),
    ))
    print("\nMean values per city:")
    print(w.groupby("city")[["temperature_2m", "relative_humidity_2m",
                             "wind_speed_10m", "precipitation"]].mean().round(1))


def run(force: bool = False) -> None:
    WEATHER_DIR.mkdir(parents=True, exist_ok=True)
    for city, cfg in CITIES.items():
        path = WEATHER_DIR / f"{city.lower()}_hourly.csv"
        if path.exists() and not force:
            print(f"{city}: already downloaded, skipping")
            continue
        df = fetch_city(city, cfg)
        df.to_csv(path, index=False)
        print(f"{city}: saved {len(df):,} hourly rows")
    summary()


if __name__ == "__main__":
    run()