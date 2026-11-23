import pandas as pd

from src.config import INTERIM_DIR

df = pd.read_csv(INTERIM_DIR / "city_day_stage2.csv", parse_dates=["date"])

for city, g in df.groupby("city"):
    g = g.sort_values("date")
    is_na = g["pm25"].isna()
    run_id = (is_na != is_na.shift()).cumsum()
    gaps = g[is_na].groupby(run_id[is_na])["date"].agg(start="min", end="max", days="size")
    gaps = gaps.sort_values("days", ascending=False).head(3)
    if len(gaps):
        print(f"\n{city}: longest PM2.5 gaps")
        print(gaps.to_string(index=False))