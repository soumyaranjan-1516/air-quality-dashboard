# AQI validation (our calculator vs dataset AQI)

- Rows with both a reported and a computed AQI: 10,602
- Reported but not computable by our rules: 4
- Computed but no reported value: 207
- Exact match: 2.1%
- Within 5 points: 20.5%
- Same category: 69.8%
- Mean absolute difference: 23.75 points
- Mean signed difference (computed - reported): -9.76 points
- Within 5 points, excluding rows with imputed values: 20.4% (n=10,388)