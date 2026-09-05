"""Scrape Realtor.com for new rentals matching config.yaml."""
import pandas as pd
from homeharvest import scrape_property

from drive_time import drive_minutes

LAUNDRY_KEYWORDS = [
    "in-unit laundry", "in unit laundry", "washer", "dryer",
    "w/d hookup", "washer/dryer", "laundry room",
]


def val(x, default=""):
    return default if pd.isna(x) else x


def has_laundry(text):
    if not isinstance(text, str):
        return False
    t = text.lower()
    return any(k in t for k in LAUNDRY_KEYWORDS)


def scrape_new_realtor_listings(config, seen):
    """Returns a list of new listing dicts (not yet in `seen`), already filtered."""
    s = config["search"]
    f = config["filters"]
    anchor_lat, anchor_lon = f["anchor_lat"], f["anchor_lon"]

    new_items = []
    new_urls = set()

    for location in s["locations"]:
        df = scrape_property(
            location=location,
            listing_type=s["listing_type"],
            beds_min=s["beds_min"],
            baths_min=s["baths_min"],
            price_min=s["price_min"],
            price_max=s["price_max"],
            past_hours=s.get("past_hours", 24),
        )
        if df is None or df.empty:
            continue

        for _, r in df.iterrows():
            url = r.get("property_url")
            if not url or url in seen or url in new_urls:
                continue

            laundry_ok = has_laundry(r.get("text"))
            if f.get("require_laundry_keyword") and not laundry_ok:
                continue

            minutes = drive_minutes(val(r.get("latitude"), None), val(r.get("longitude"), None), anchor_lat, anchor_lon)
            if minutes is not None and minutes > f["max_drive_minutes"]:
                continue

            baths = val(r.get("full_baths"), 0) + 0.5 * val(r.get("half_baths"), 0)
            new_items.append({
                "url": url,
                "address": val(r.get("full_street_line"), val(r.get("formatted_address"), "")),
                "city": val(r.get("city"), ""),
                "price": val(r.get("list_price"), ""),
                "beds": val(r.get("beds"), ""),
                "baths": baths,
                "sqft": val(r.get("sqft"), ""),
                "laundry": "Yes" if laundry_ok else "Unknown",
                "drive_time": f"{minutes} min" if minutes is not None else "Unknown",
                "source": "Realtor.com",
                "notes": "",
            })
            new_urls.add(url)

    return new_items
