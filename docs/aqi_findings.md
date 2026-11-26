# AQI validation findings

- The dataset's daily AQI equals the mean of its 24 hourly AQI values (99.4% within 5 points, MAE 0.4, n=10,606).
- CPCB's method applies the AQI formula to 24-hour average concentrations, so the dataset's daily AQI is a different quantity from a CPCB-method daily AQI.
- Our calculator vs the dataset's hourly AQI at the same timestamp: n=250,956, same category 78.0%, within 5 points 43.2%, median difference -3.
- Largest disagreement when O3 or CO dominates (median -29 and -23 points). Cause not yet identified.
- Missing PM10 does not explain the gap (within 5 points: 45.7% without PM10, 41.7% with).
- Decision: the dashboard uses our CPCB-method AQI; the dataset's AQI is kept as a labelled comparison series.