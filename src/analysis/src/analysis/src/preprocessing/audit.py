from src.analysis.load_data import load_city_day

POLLUTANTS = ["PM2.5", "PM10", "NO", "NO2", "NOx", "NH3",
              "CO", "SO2", "O3", "Benzene", "Toluene", "Xylene"]

df = load_city_day()

print("Duplicate rows:", df.duplicated().sum())
print("Duplicate city-date pairs:", df.duplicated(["City", "Date"]).sum())

print("\nMissing % by column:")
print((df[POLLUTANTS + ["AQI"]].isna().mean() * 100).round(1).sort_values(ascending=False))

print("\nNegative values per pollutant:")
print((df[POLLUTANTS] < 0).sum())

print("\nZero values per pollutant:")
print((df[POLLUTANTS] == 0).sum())

print("\nRows where PM2.5 > PM10:", (df["PM2.5"] > df["PM10"]).sum())

span = (df["Date"].max() - df["Date"].min()).days + 1
coverage = df.groupby("City")["Date"].nunique().div(span).mul(100).round(1)
print("\nDate coverage % per city:")
print(coverage.sort_values())

df["Year"] = df["Date"].dt.year
print("\nPM2.5 missing % by city and year:")
print(df.pivot_table(index="City", columns="Year", values="PM2.5",
                     aggfunc=lambda s: round(s.isna().mean() * 100)))
