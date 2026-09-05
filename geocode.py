"""Geocode a street address to (lat, lon) via Nominatim (OpenStreetMap) — free,
no API key. Usage policy caps this at 1 request/second, which is fine for our
volume (a handful of listings per run); a real User-Agent is required."""
import time

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "socal-housing-agent/1.0 (personal rental search)"}

_last_call = 0.0


def geocode(address, city, state="CA"):
    global _last_call
    if not address or not city:
        return None, None

    elapsed = time.monotonic() - _last_call
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    query = f"{address}, {city}, {state}"
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers=HEADERS,
            timeout=10,
        )
        _last_call = time.monotonic()
        results = resp.json()
        if not results:
            return None, None
        return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        _last_call = time.monotonic()
        return None, None
