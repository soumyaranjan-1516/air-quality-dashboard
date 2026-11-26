"""Stage 3: recompute the AQI with our calculator and compare it with the dataset's AQI."""
import pandas as pd

from src.aqi.calculator import category, compute_aqi
from src.config import DOCS_DIR, INTERIM_DIR

POLLUTANT_COLS = {"PM2.5": "pm25", "PM10": "pm10", "NO2": "no2",
                  "O3": "o3", "CO": "co", "SO2": "so2", "NH3": "nh3"}


def run() -> pd.DataFrame:
    df = pd.read_csv(INTERIM_DIR / "city_day_stage2.csv", parse_dates=["date"])

    results = [compute_aqi({name: getattr(r, col) for name, col in POLLUTANT_COLS.items()})
               for r in df.itertuples()]
    df["aqi_computed"] = [r[0] for r in results]
    df["aqi_dominant"] = [r[1] for r in results]
    df["any_imputed"] = df[[f"{c}_imputed" for c in POLLUTANT_COLS.values()]].any(axis=1)

    has_rep = df["aqi_reported"].notna()
    has_comp = df["aqi_computed"].notna()
    cmp = df[has_rep & has_comp].copy()
    diff = cmp["aqi_computed"] - cmp["aqi_reported"]
    cmp["abs_diff"] = diff.abs()
    cat_match = (cmp["aqi_computed"].apply(category) == cmp["aqi_reported"].apply(category)).mean()
    no_imp = cmp[~cmp["any_imputed"]]

    log = [
        f"Rows with both a reported and a computed AQI: {len(cmp):,}",
        f"Reported but not computable by our rules: {int((has_rep & ~has_comp).sum()):,}",
        f"Computed but no reported value: {int((~has_rep & has_comp).sum()):,}",
        f"Exact match: {(diff == 0).mean():.1%}",
        f"Within 5 points: {(cmp['abs_diff'] <= 5).mean():.1%}",
        f"Same category: {cat_match:.1%}",
        f"Mean absolute difference: {cmp['abs_diff'].mean():.2f} points",
        f"Mean signed difference (computed - reported): {diff.mean():+.2f} points",
        f"Within 5 points, excluding rows with imputed values: "
        f"{(no_imp['abs_diff'] <= 5).mean():.1%} (n={len(no_imp):,})",
    ]
    print("\n".join(log))

    print("\nPer-city agreement:")
    print(cmp.groupby("city").agg(
        rows=("abs_diff", "size"),
        within5_pct=("abs_diff", lambda s: round((s <= 5).mean() * 100, 1)),
        mae=("abs_diff", lambda s: round(s.mean(), 1)),
    ))

    print("\nDominant pollutant by city (computed days):")
    print(pd.crosstab(df["city"], df["aqi_dominant"]))

    print("\n10 largest mismatches:")
    worst = cmp.loc[cmp["abs_diff"].sort_values(ascending=False).index[:10]]
    print(worst[["city", "date", "aqi_reported", "aqi_computed", "aqi_dominant",
                 "pm25", "pm10", "no2", "so2", "co", "o3", "nh3"]].to_string(index=False))

    df.to_csv(INTERIM_DIR / "city_day_stage3.csv", index=False)
    DOCS_DIR.mkdir(exist_ok=True)
    text = "# AQI validation (our calculator vs dataset AQI)\n\n" + "\n".join(f"- {l}" for l in log)
    (DOCS_DIR / "aqi_validation.md").write_text(text, encoding="utf-8")
    return df


if __name__ == "__main__":
    run()