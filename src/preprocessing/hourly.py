"""Hourly -> daily CPCB aggregates (24-h means; 8-h running means for CO and O3), then AQI."""
import pandas as pd

from src.aqi.calculator import category, compute_aqi
from src.config import CITIES, INTERIM_DIR
from src.preprocessing.diagnose import read_raw

HOURLY = {"PM2.5": "pm25", "PM10": "pm10", "NO2": "no2", "SO2": "so2",
          "NH3": "nh3", "CO": "co", "O3": "o3"}
MEAN_24H = ["pm25", "pm10", "no2", "so2", "nh3"]
MAX_8H = ["co", "o3"]
MIN_HOURS_24H = 16  # CPCB: at least 16 hours of data for a 24-hour value
MIN_HOURS_8H = 6    # ASSUMPTION: verify the 8-hour completeness rule in the CPCB document


def aggregate_city(g: pd.DataFrame) -> pd.DataFrame:
    """One city's hourly readings -> one row per day of CPCB-style averages."""
    g = g.set_index("Datetime").sort_index()
    g = g[~g.index.duplicated()].asfreq("h")  # regular hourly grid, gaps become NaN

    daily = g[MEAN_24H].resample("D")
    out = daily.mean().where(daily.count() >= MIN_HOURS_24H)
    for col in MAX_8H:
        out[col] = g[col].rolling(8, min_periods=MIN_HOURS_8H).mean().resample("D").max()
    return out


def run() -> pd.DataFrame:
    raw = read_raw("city_hour", parse_dates=["Datetime"]).rename(columns=HOURLY)
    raw = raw[raw["City"].isin(CITIES)]

    parts = []
    for city, g in raw.groupby("City"):
        d = aggregate_city(g)
        d["city"] = city
        parts.append(d.rename_axis("date").reset_index())
    daily = pd.concat(parts, ignore_index=True)

    res = [compute_aqi({name: getattr(r, col) for name, col in HOURLY.items()})
           for r in daily.itertuples()]
    daily["aqi_cpcb"] = pd.Series([x[0] for x in res], dtype="float")
    daily["dominant_cpcb"] = [x[1] for x in res]
    daily.to_csv(INTERIM_DIR / "city_day_cpcb.csv", index=False)

    ref = pd.read_csv(INTERIM_DIR / "city_day_stage3.csv", parse_dates=["date"])
    ref = ref[["city", "date", "aqi_reported", "aqi_computed"]].rename(
        columns={"aqi_computed": "aqi_daily_mean"})
    m = ref.merge(daily[["city", "date", "aqi_cpcb", "dominant_cpcb"]], on=["city", "date"])
    m = m.dropna(subset=["aqi_reported", "aqi_daily_mean", "aqi_cpcb"])  # same rows for both

    for col, label in (("aqi_daily_mean", "BEFORE: daily means for all pollutants"),
                       ("aqi_cpcb", "AFTER: 24-h means, 8-h running means for CO and O3")):
        diff = m[col] - m["aqi_reported"]
        same = (m[col].apply(category) == m["aqi_reported"].apply(category)).mean()
        print(f"{label}\n  n={len(m):,} | within 5 pts {(diff.abs() <= 5).mean():.1%} | "
              f"same category {same:.1%} | MAE {diff.abs().mean():.1f} | "
              f"median diff {diff.median():+.1f}")

    m["diff"] = m["aqi_cpcb"] - m["aqi_reported"]
    print("\nAFTER, by dominant pollutant:")
    print(m.groupby("dominant_cpcb").agg(
        n=("diff", "size"),
        median_diff=("diff", "median"),
        within5_pct=("diff", lambda s: round((s.abs() <= 5).mean() * 100, 1)),
    ).round(1))
    return daily


if __name__ == "__main__":
    run()