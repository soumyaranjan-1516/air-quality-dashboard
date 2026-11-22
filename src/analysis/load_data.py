from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")


def _read(name: str, **kwargs) -> pd.DataFrame:
    """Read data/raw/<name>.csv or data/raw/<name>.xlsx."""
    csv_path = RAW_DIR / f"{name}.csv"
    xlsx_path = RAW_DIR / f"{name}.xlsx"
    if csv_path.exists():
        return pd.read_csv(csv_path, **kwargs)
    if xlsx_path.exists():
        return pd.read_excel(xlsx_path, **kwargs)
    raise FileNotFoundError(f"Put {name}.csv or {name}.xlsx in {RAW_DIR}")


def load_city_day() -> pd.DataFrame:
    """Load the daily city-level air quality dataset."""
    return _read("city_day", parse_dates=["Date"])