import requests

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"


def drive_minutes(origin_lat, origin_lon, dest_lat, dest_lon):
    """Driving minutes between two points via the free OSRM demo routing service.
    Returns None if coordinates are missing or the request fails."""
    if origin_lat is None or origin_lon is None:
        return None
    url = OSRM_URL.format(lon1=origin_lon, lat1=origin_lat, lon2=dest_lon, lat2=dest_lat)
    try:
        resp = requests.get(url, params={"overview": "false"}, timeout=10)
        data = resp.json()
        if data.get("code") != "Ok":
            return None
        return round(data["routes"][0]["duration"] / 60)
    except Exception:
        return None
