from src.analysis.load_data import load_city_day

df = load_city_day()

print("Shape:", df.shape)
print("Cities:", df["City"].nunique())
print("Date range:", df["Date"].min().date(), "to", df["Date"].max().date())

print("\nMissing values (fraction per column):")
print(df.isna().mean().sort_values(ascending=False).round(3))

print("\nTop 5 cities by mean AQI:")
print(df.groupby("City")["AQI"].mean().sort_values(ascending=False).head(5).round(1))