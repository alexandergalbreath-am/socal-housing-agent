#!/usr/bin/env python3
"""Daily orchestrator: scrape Realtor.com, read Zillow/Redfin/Homes.com alert
emails, merge + filter + dedupe, log results, and email a digest of anything new.
Designed to run in GitHub Actions (see .github/workflows/daily.yml)."""
import json
import sys
from datetime import datetime, timezone

from common import append_log, load_config, load_seen, save_seen
from drive_time import drive_minutes
from email_alerts import fetch_alert_listings
from geocode import geocode
from render_listings import render as render_listings
from scrape_realtor import scrape_new_realtor_listings
from send_digest import send_digest


def _safe_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _process_alert_item(item, config, seen, claimed_urls):
    url = item["url"]
    if url in seen or url in claimed_urls:
        return None

    s = config["search"]
    price = _safe_float(item.get("price"))
    beds = _safe_float(item.get("beds"))
    baths = _safe_float(item.get("baths"))

    if price is not None and not (s["price_min"] <= price <= s["price_max"]):
        return None
    if beds is not None and beds < s["beds_min"]:
        return None
    if baths is not None and baths < s["baths_min"]:
        return None

    f = config["filters"]
    address = item.get("address") or ""
    city = item.get("city") or ""
    lat, lon = geocode(address, city)
    minutes = drive_minutes(lat, lon, f["anchor_lat"], f["anchor_lon"])
    if minutes is not None and minutes > f["max_drive_minutes"]:
        return None
    drive_time_str = f"{minutes} min" if minutes is not None else "Unknown (couldn't geocode address)"

    note_parts = []
    if price is None:
        note_parts.append("Auto-parsed from email alert — verify price/beds/baths on the listing page")
    if item["source"] == "Homes.com":
        note_parts.append(
            "Verify this is actually For Rent before reaching out — Homes.com sometimes shows a "
            "rent-estimate figure on For Sale listings too, and that can't be told apart from the "
            "email alone (confirmed on 2026-09-05: a $1.785M for-sale home showed as \"$5,500/mo\")."
        )
    notes = " ".join(note_parts)
    return {
        "url": url,
        "address": address or item.get("context", "")[:100] or "(see link)",
        "city": city,
        "price": price if price is not None else "unknown",
        "beds": beds if beds is not None else "?",
        "baths": baths if baths is not None else "?",
        "sqft": item.get("sqft") or "",
        "laundry": "Unknown",
        "drive_time": drive_time_str,
        "source": item["source"],
        "notes": notes,
    }


def main():
    config = load_config()
    seen = load_seen(config)

    all_new = scrape_new_realtor_listings(config, seen)
    realtor_found = len(all_new)
    claimed_urls = {item["url"] for item in all_new}

    alert_debug = {}
    try:
        alert_items, alert_debug = fetch_alert_listings(lookback_days=1)
    except Exception as e:
        alert_items = []
        alert_debug = {"error": str(e)}
        print(f"warning: email alert fetch failed: {e}", file=sys.stderr)

    alert_accepted = 0
    for raw in alert_items:
        processed = _process_alert_item(raw, config, seen, claimed_urls)
        if processed:
            all_new.append(processed)
            claimed_urls.add(processed["url"])
            alert_accepted += 1

    summary = {
        "new_listings": len(all_new),
        "realtor_found": realtor_found,
        "alert_debug": alert_debug,
        "alert_listings_accepted": alert_accepted,
    }

    if not all_new:
        render_listings()  # keep the "last checked" timestamp fresh even with no new hits
        print(json.dumps(summary))
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    append_log(config, [{**item, "date_found": today} for item in all_new])
    seen |= claimed_urls
    save_seen(config, seen)
    render_listings()

    try:
        send_digest(config, all_new)
    except Exception as e:
        print(f"warning: digest email failed to send: {e}", file=sys.stderr)

    by_source = {}
    for item in all_new:
        by_source[item["source"]] = by_source.get(item["source"], 0) + 1
    summary["by_source"] = by_source

    print(json.dumps(summary))


if __name__ == "__main__":
    main()
