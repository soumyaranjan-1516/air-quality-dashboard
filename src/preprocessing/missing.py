"""Stage 2: make gaps explicit, fill only short gaps, flag every filled value."""
import pandas as pd

from src.config import DOCS_DIR, INTERIM_DIR

CORE = ["pm25", "pm10", "no2", "so2", "co", "o3", "nh3"]
MAX_GAP_DAYS = 3  # fill gaps up to this many consecutive days; leave longer gaps empty


def run_ids(is_na: pd.Series) -> pd.Series:
    """Number each consecutive run of missing / non-missing values."""
    return (is_na != is_na.shift()).cumsum()


def longest_gap(s: pd.Series) -> int:
    is_na = s.isna()
    return int(is_na.groupby(run_ids(is_na)).sum().max())


def fill_short_gaps(s: pd.Series, max_gap: int) -> pd.Series:
    """Linear interpolation inside gaps of <= max_gap days; longer gaps stay empty."""
    is_na = s.isna()
    run_len = is_na.groupby(run_ids(is_na)).transform("sum")
    interpolated = s.interpolate(method="linear", limit_area="inside")
    return interpolated.mask(is_na & (run_len > max_gap))


def add_missing_days(df: pd.DataFrame) -> pd.DataFrame:
    """Give every city a complete daily calendar so gaps become explicit rows."""
    parts = []
    for city, g in df.groupby("city"):
        calendar = pd.date_range(g["date"].min(), g["date"].max(), freq="D")
        out = g.set_index("date").reindex(calendar)
        out["city"] = city
        out["day_absent_in_source"] = ~out.index.isin(g["date"])
        parts.append(out.rename_axis("date").reset_index())
    return pd.concat(parts, ignore_index=True)


def run() -> pd.DataFrame:
    log = []
    df = pd.read_csv(INTERIM_DIR / "city_day_stage1.csv", parse_dates=["date"])
    rows_before = len(df)

    df = add_missing_days(df)
    absent = int(df["day_absent_in_source"].sum())
    log.append(f"Added {absent:,} absent calendar days as explicit rows "
               f"({rows_before:,} -> {len(df):,} rows)")

    df["pm_inconsistent"] = df["pm25"] > df["pm10"]

    missing_before = df[CORE].isna().mean() * 100
    gap_before = df.groupby("city")["pm25"].apply(longest_gap)

    print("PM2.5 missing % by calendar month (all cities pooled, before filling):")
    print(df.groupby(df["date"].dt.month)["pm25"]
            .apply(lambda s: s.isna().mean() * 100).round(1))

    for col in CORE:
        was_missing = df[col].isna()
        df[col] = df.groupby("city")[col].transform(
            lambda s: fill_short_gaps(s, MAX_GAP_DAYS))
        df[f"{col}_imputed"] = was_missing & df[col].notna()
        n = int(df[f"{col}_imputed"].sum())
        log.append(f"{col}: filled {n:,} values in gaps of <= {MAX_GAP_DAYS} days")

    missing_after = df[CORE].isna().mean() * 100
    print("\nMissing % per pollutant, before and after:")
    print(pd.DataFrame({"before": missing_before.round(1),
                        "after": missing_after.round(1)}))

    per_city = df.groupby("city").agg(
        days=("date", "size"),
        absent_days=("day_absent_in_source", "sum"),
        pm25_missing_after_pct=("pm25", lambda s: round(s.isna().mean() * 100, 1)),
        pm25_longest_gap_after=("pm25", longest_gap),
    )
    per_city["pm25_longest_gap_before"] = gap_before
    print("\nPer-city summary:")
    print(per_city)

    df.to_csv(INTERIM_DIR / "city_day_stage2.csv", index=False)
    text = ("# Data cleaning log (stage 2: missing values)\n\n"
            + "\n".join(f"- {line}" for line in log))
    (DOCS_DIR / "data_cleaning_log_stage2.md").write_text(text, encoding="utf-8")
    print("\n" + "\n".join(log))
    return df


if __name__ == "__main__":
    run()