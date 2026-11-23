# Data cleaning log (stage 1)

- Loaded 29,531 rows across 26 cities
- Dropped xylene (61.3% missing) and the reported AQI bucket
- co: 2,328 zero readings set to missing
- nox: 740 zero readings set to missing
- aqi_reported: 543 values above 500 set to missing
- Flagged 256 rows where PM2.5 > PM10
- Kept 10,901 rows for 8 cities within their valid windows