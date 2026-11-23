"""Stage 1 cleaning: standardize names, remove invalid values, keep chosen cities."""
import numpy as np
import pandas as pd

from src.analysis.load_data import load_city_day
from src.config import CITIES, DOCS_DIR, INTERIM_DIR

RENAME = {
    "City": "city", "Date": "date", "PM2.5": "pm25", "PM10": "pm10",
    "NO": "no", "NO2": "no2", "NOx": "nox", "NH3": "nh3", "CO": "co",
    "SO2": "so2", "O3": "o3", "Benzene": "benzene", "Toluene": "toluene",
    "Xylene": "xylene", "AQI": "aqi_reported", "AQI_Bucket": "aqi_bucket_reported",
}


def clean_stage1() -> pd.DataFrame:
    log = []
    df = load_city_day().rename(columns=RENAME)
    df["city"] = df["city"].str.strip()
    log.append(f"Loaded {len(df):,} rows across {df['city'].nunique()} cities")

    absent = set(CITIES) - set(df["city"])
    if absent:
        raise ValueError(f"Cities not found in data: {absent}")

    # 1. Drop mostly-empty column and the bucket (we recompute categories ourselves)
    df = df.drop(columns=["xylene", "aqi_bucket_reported"])
    log.append("Dropped xylene (61.3% missing) and the reported AQI bucket")

    # 2. Zero readings are physically implausible for CO and NOx -> missing
    for col in ["co", "nox"]:
        mask = df[col] == 0
        log.append(f"{col}: {int(mask.sum()):,} zero readings set to missing")
        df.loc[mask, col] = np.nan

    # 3. AQI above the 500 scale maximum is invalid
    mask = df["aqi_reported"] > 500
    log.append(f"aqi_reported: {int(mask.sum()):,} values above 500 set to missing")
    df.loc[mask, "aqi_reported"] = np.nan

    # 4. Flag (do not delete) rows where PM2.5 > PM10
    df["pm_inconsistent"] = df["pm25"] > df["pm10"]
    log.append(f"Flagged {int(df['pm_inconsistent'].sum()):,} rows where PM2.5 > PM10")

    # 5. Keep chosen cities, each from its own valid start date
    kept = [df[(df["city"] == c) & (df["date"] >= cfg["start"])] for c, cfg in CITIES.items()]
    df = pd.concat(kept).sort_values(["city", "date"]).reset_index(drop=True)
    log.append(f"Kept {len(df):,} rows for {len(CITIES)} cities within their valid windows")

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(INTERIM_DIR / "city_day_stage1.csv", index=False)

    DOCS_DIR.mkdir(exist_ok=True)
    text = "# Data cleaning log (stage 1)\n\n" + "\n".join(f"- {line}" for line in log)
    (DOCS_DIR / "data_cleaning_log.md").write_text(text, encoding="utf-8")

    print("\n".join(log))
    return df


if __name__ == "__main__":
    result = clean_stage1()
    print("\nPer-city summary:")
    print(result.groupby("city").agg(
        rows=("date", "size"),
        first=("date", "min"),
        last=("date", "max"),
        pm25_missing_pct=("pm25", lambda s: round(s.isna().mean() * 100, 1)),
    ))