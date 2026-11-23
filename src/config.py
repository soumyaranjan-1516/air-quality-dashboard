from pathlib import Path

RAW_DIR = Path("data/raw")
INTERIM_DIR = Path("data/interim")
PROCESSED_DIR = Path("data/processed")
DOCS_DIR = Path("docs")

# start = first date from which PM2.5 is reasonably complete (from the audit)
CITIES = {
    "Delhi":     {"lat": 28.6139, "lon": 77.2090, "start": "2015-01-01"},
    "Lucknow":   {"lat": 26.8467, "lon": 80.9462, "start": "2016-01-01"},
    "Patna":     {"lat": 25.5941, "lon": 85.1376, "start": "2018-01-01"},
    "Amritsar":  {"lat": 31.6340, "lon": 74.8723, "start": "2017-01-01"},
    "Chennai":   {"lat": 13.0827, "lon": 80.2707, "start": "2016-01-01"},
    "Hyderabad": {"lat": 17.3850, "lon": 78.4867, "start": "2016-01-01"},
    "Bengaluru": {"lat": 12.9716, "lon": 77.5946, "start": "2017-01-01"},
    "Mumbai":    {"lat": 19.0760, "lon": 72.8777, "start": "2019-01-01"},
}