"""Does the dataset's hourly AQI match ours, and how is its daily AQI built from it?"""
import pandas as pd

from src.aqi.calculator import category, compute_aqi
from src.config import CITIES, INTERIM_DIR
from src.preprocessing.diagnose import read_raw

HOURLY = {"PM2.5": "pm25", "PM10": "pm10", "NO2": "no2", "SO2": "so2",
          "NH3": "nh3", "CO": "co", "O3": "o3"}
MEAN_24H = ["pm25", "pm10", "no2", "so2", "nh3"]
MEAN_8H = ["co", "o3"]


def moving_averages(g: pd.DataFrame) -> pd.DataFrame:
    """CPCB real-time convention: 24-h moving mean (>= 16 h), 8-h moving mean for CO/O3 (>= 6 h, assumed)."""
    g = g.set_index("Datetime").sort_index()
    g = g[~g.index.duplicated()].asfreq("h")
    out = g[["AQI"]].copy()
    for col in MEAN_24H:
        out[col] = g[col].rolling(24, min_periods=16).mean()
    for col in MEAN_8H:
        out[col] = g[col].rolling(8, min_periods=6).mean()
    return out


def stats(diff: pd.Series) -> str:
    return (f"n={len(diff):,} | exact {(diff == 0).mean():.1%} | "
            f"within 5 pts {(diff.abs() <= 5).mean():.1%} | "
            f"MAE {diff.abs().mean():.1f} | median diff {diff.median():+.1f}")


def run() -> None:
    raw = read_raw("city_hour", parse_dates=["Datetime"]).rename(columns=HOURLY)
    if "AQI" not in raw.columns:
        print("No AQI column in city_hour. Columns found:", list(raw.columns))
        return
    raw = raw[raw["City"].isin(CITIES)]

    parts = []
    for city, g in raw.groupby("City"):
        d = moving_averages(g)
        d = d[d.index >= CITIES[city]["start"]]
        d["city"] = city
        parts.append(d)
    hourly = pd.concat(parts)
    hourly.index.name = "Datetime"
    hourly = hourly.reset_index()
    hourly.loc[hourly["AQI"] > 500, "AQI"] = float("nan")

    res = [compute_aqi({name: getattr(r, col) for name, col in HOURLY.items()})
           for r in hourly[list(HOURLY.values())].itertuples()]
    hourly["aqi_ours"] = pd.Series([x[0] for x in res], dtype="float")
    hourly["dominant"] = [x[1] for x in res]

    both = hourly.dropna(subset=["AQI", "aqi_ours"]).copy()
    both["diff"] = both["aqi_ours"] - both["AQI"]
    same_cat = (both["aqi_ours"].apply(category) == both["AQI"].apply(category)).mean()
    print("1. Our hourly AQI vs the dataset's hourly AQI (same timestamp):")
    print("  ", stats(both["diff"]), f"| same category {same_cat:.1%}")

    print("\n   By our dominant pollutant:")
    print(both.groupby("dominant")["diff"].agg(
        n="size", median="median",
        within5_pct=lambda s: round((s.abs() <= 5).mean() * 100, 1)).round(1))

    print("\n   By PM10 availability:")
    both["pm10_available"] = both["pm10"].notna()
    print(both.groupby("pm10_available")["diff"].agg(
        n="size", median="median",
        within5_pct=lambda s: round((s.abs() <= 5).mean() * 100, 1)).round(1))

    print("\n2. How does the dataset's daily AQI relate to its hourly AQI?")
    ref = pd.read_csv(INTERIM_DIR / "city_day_stage3.csv", parse_dates=["date"])
    ref = ref[["city", "date", "aqi_reported"]].dropna()
    hourly["date"] = hourly["Datetime"].dt.normalize()
    hourly["hour"] = hourly["Datetime"].dt.hour
    wide = hourly.pivot_table(index=["city", "date"], columns="hour", values="AQI")

    cands = {f"value at {h:02d}:00": wide[h] for h in wide.columns}
    cands["daily MEAN of hourly AQI"] = wide.mean(axis=1)
    cands["daily MAX of hourly AQI"] = wide.max(axis=1)
    rows = []
    for name, s in cands.items():
        m = ref.merge(s.rename("cand").reset_index(), on=["city", "date"]).dropna(subset=["cand"])
        d = (m["cand"] - m["aqi_reported"]).abs()
        rows.append({"candidate": name, "n": len(m),
                     "exact_pct": round((d == 0).mean() * 100, 1),
                     "within5_pct": round((d <= 5).mean() * 100, 1),
                     "mae": round(d.mean(), 1)})
    print(pd.DataFrame(rows).sort_values("within5_pct", ascending=False)
            .head(6).to_string(index=False))


if __name__ == "__main__":
    run()