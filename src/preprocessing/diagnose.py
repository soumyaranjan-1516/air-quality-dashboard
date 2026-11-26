"""Diagnostic: does our calculator reproduce the dataset's AQI at station level?"""
import pandas as pd

from src.aqi.calculator import category, compute_aqi
from src.config import CITIES, INTERIM_DIR, RAW_DIR

RENAME = {"PM2.5": "pm25", "PM10": "pm10", "NO2": "no2", "O3": "o3",
          "CO": "co", "SO2": "so2", "NH3": "nh3"}


def read_raw(name: str, **kwargs) -> pd.DataFrame:
    for ext, reader in ((".csv", pd.read_csv), (".xlsx", pd.read_excel)):
        path = RAW_DIR / f"{name}{ext}"
        if path.exists():
            return reader(path, **kwargs)
    raise FileNotFoundError(f"Put {name}.csv or {name}.xlsx in {RAW_DIR}")


def summarize(df: pd.DataFrame, reported: str, computed: str, label: str) -> None:
    diff = df[computed] - df[reported]
    same_cat = (df[computed].apply(category) == df[reported].apply(category)).mean()
    print(f"{label}: n={len(df):,} | within 5 pts {(diff.abs() <= 5).mean():.1%} | "
          f"same category {same_cat:.1%} | MAE {diff.abs().mean():.1f} | "
          f"mean diff {diff.mean():+.1f}")


def station_level() -> None:
    sd = read_raw("station_day", parse_dates=["Date"]).rename(columns=RENAME)
    st = read_raw("stations")[["StationId", "City"]]
    sd = sd.merge(st, on="StationId", how="left")

    keep = pd.Series(False, index=sd.index)
    for city, cfg in CITIES.items():
        keep |= (sd["City"] == city) & (sd["Date"] >= cfg["start"])
    sd = sd[keep].copy()

    results = [compute_aqi({name: getattr(r, col) for name, col in RENAME.items()})
               for r in sd.itertuples()]
    sd["aqi_computed"] = [r[0] for r in results]

    cmp = sd[sd["AQI"].notna() & sd["aqi_computed"].notna() & (sd["AQI"] <= 500)].copy()
    cmp["aqi_computed"] = cmp["aqi_computed"].astype(float)
    cmp["abs_diff"] = (cmp["aqi_computed"] - cmp["AQI"]).abs()
    cmp["pm_bad"] = cmp["pm25"] > cmp["pm10"]

    print("STATION LEVEL (station_day)")
    summarize(cmp, "AQI", "aqi_computed", "All rows")
    summarize(cmp[~cmp["pm_bad"]], "AQI", "aqi_computed", "PM2.5 <= PM10 (or PM10 missing)")
    summarize(cmp[cmp["pm_bad"]], "AQI", "aqi_computed", "PM2.5 > PM10")
    print("\nPer city (station level):")
    print(cmp.groupby("City").agg(
        stations=("StationId", "nunique"),
        rows=("abs_diff", "size"),
        within5_pct=("abs_diff", lambda s: round((s <= 5).mean() * 100, 1)),
        mae=("abs_diff", lambda s: round(s.mean(), 1)),
    ))


def city_level() -> None:
    df = pd.read_csv(INTERIM_DIR / "city_day_stage3.csv", parse_dates=["date"])
    cmp = df[df["aqi_reported"].notna() & df["aqi_computed"].notna()].copy()

    print("\nCITY LEVEL (city_day, for comparison)")
    summarize(cmp, "aqi_reported", "aqi_computed", "All rows")
    summarize(cmp[~cmp["pm_inconsistent"]], "aqi_reported", "aqi_computed", "PM2.5 <= PM10 (or PM10 missing)")
    summarize(cmp[cmp["pm_inconsistent"]], "aqi_reported", "aqi_computed", "PM2.5 > PM10")

    print("\nMissing % by city and pollutant (after stage 2):")
    print(df.groupby("city")[list(RENAME.values())]
            .apply(lambda g: g.isna().mean() * 100).round(0))


if __name__ == "__main__":
    station_level()
    city_level()