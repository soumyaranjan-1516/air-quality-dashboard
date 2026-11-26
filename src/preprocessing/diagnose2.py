"""Diagnostic 2: where does our AQI disagree with the dataset's AQI, and why?"""
import pandas as pd

from src.aqi.calculator import compute_aqi
from src.config import CITIES
from src.preprocessing.diagnose import RENAME, read_raw


def load_station_data() -> pd.DataFrame:
    sd = read_raw("station_day", parse_dates=["Date"]).rename(columns=RENAME)
    st = read_raw("stations")[["StationId", "City"]]
    sd = sd.merge(st, on="StationId", how="left")
    keep = pd.Series(False, index=sd.index)
    for city, cfg in CITIES.items():
        keep |= (sd["City"] == city) & (sd["Date"] >= cfg["start"])
    sd = sd[keep].sort_values(["StationId", "Date"]).reset_index(drop=True)
    sd.loc[sd["AQI"] > 500, "AQI"] = float("nan")
    return sd


def computed(sd: pd.DataFrame, skip=()):
    """Return (aqi, dominant_pollutant) series, optionally ignoring some pollutants."""
    res = []
    for r in sd.itertuples():
        conc = {name: getattr(r, col) for name, col in RENAME.items() if name not in skip}
        res.append(compute_aqi(conc))
    return (pd.Series([x[0] for x in res], index=sd.index, dtype="float"),
            pd.Series([x[1] for x in res], index=sd.index))


def main() -> None:
    sd = load_station_data()
    sd["aqi_computed"], sd["dominant"] = computed(sd)

    cmp = sd[sd["AQI"].notna() & sd["aqi_computed"].notna()].copy()
    cmp["diff"] = cmp["aqi_computed"] - cmp["AQI"]

    print("A. Difference (computed - reported), percentiles:")
    print(cmp["diff"].quantile([0.05, 0.25, 0.5, 0.75, 0.95]).round(1).to_string())
    print("\nMedian and mean difference by city:")
    print(cmp.groupby("City")["diff"].agg(median="median", mean="mean").round(1))

    print("\nB. Reported AQI on day t vs our computed AQI on day t+shift:")
    base = sd[["StationId", "Date", "AQI"]].dropna(subset=["AQI"])
    comp = sd[["StationId", "Date", "aqi_computed"]].dropna(subset=["aqi_computed"])
    rows = []
    for k in (-2, -1, 0, 1, 2):
        shifted = comp.assign(Date=comp["Date"] - pd.Timedelta(days=k))
        m = base.merge(shifted, on=["StationId", "Date"])
        d = (m["aqi_computed"] - m["AQI"]).abs()
        rows.append({"shift_days": k, "n": len(m),
                     "within5_pct": round((d <= 5).mean() * 100, 1),
                     "mae": round(d.mean(), 1)})
    print(pd.DataFrame(rows).to_string(index=False))

    print("\nC. By our dominant pollutant:")
    print(cmp.groupby("dominant").agg(
        n=("diff", "size"),
        median_diff=("diff", "median"),
        within5_pct=("diff", lambda s: round((s.abs() <= 5).mean() * 100, 1)),
    ).round(1))

    bad_idx = cmp.index[cmp["pm25"] > cmp["pm10"]]
    without, _ = computed(sd.loc[bad_idx], skip=("PM2.5",))
    both = pd.DataFrame({"reported": sd.loc[bad_idx, "AQI"],
                         "with_pm25": sd.loc[bad_idx, "aqi_computed"],
                         "without_pm25": without}).dropna()
    print(f"\nD. Rows with PM2.5 > PM10 ({len(both)} usable):")
    print("   MAE vs reported, using PM2.5:   ",
          round((both["with_pm25"] - both["reported"]).abs().mean(), 1))
    print("   MAE vs reported, ignoring PM2.5:",
          round((both["without_pm25"] - both["reported"]).abs().mean(), 1))


if __name__ == "__main__":
    main()