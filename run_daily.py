#!/usr/bin/env python3
"""Daily orchestrator: scrape Realtor.com, read Zillow/Redfin/Homes.com alert
emails, merge + filter + dedupe, log results, and email a digest of anything new.
Designed to run in GitHub Actions (see .github/workflows/daily.yml)."""
import json
import sys
from datetime import datetime, timezone

from common import append_log, load_config, load_seen, save_seen
from email_alerts import fetch_alert_listings
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

    notes = "" if price is not None else "Auto-parsed from email alert — verify price/beds/baths on the listing page"
    return {
        "url": url,
        "address": item.get("context", "")[:100] or "(see link)",
        "city": "",
        "price": price if price is not None else "unknown",
        "beds": beds if beds is not None else "?",
        "baths": baths if baths is not None else "?",
        "sqft": "",
        "laundry": "Unknown",
        "drive_time": "Not checked (email alert has no coordinates)",
        "source": item["source"],
        "notes": notes,
    }


def main():
    config = load_config()
    seen = load_seen(config)

    all_new = scrape_new_realtor_listings(config, seen)
    claimed_urls = {item["url"] for item in all_new}

    try:
        alert_items = fetch_alert_listings(lookback_days=1)
    except Exception as e:
        alert_items = []
        print(f"warning: email alert fetch failed: {e}", file=sys.stderr)

    for raw in alert_items:
        processed = _process_alert_item(raw, config, seen, claimed_urls)
        if processed:
            all_new.append(processed)
            claimed_urls.add(processed["url"])

    if not all_new:
        print(json.dumps({"new_listings": 0}))
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    append_log(config, [{**item, "date_found": today} for item in all_new])
    seen |= claimed_urls
    save_seen(config, seen)

    try:
        send_digest(config, all_new)
    except Exception as e:
        print(f"warning: digest email failed to send: {e}", file=sys.stderr)

    by_source = {}
    for item in all_new:
        by_source[item["source"]] = by_source.get(item["source"], 0) + 1

    print(json.dumps({"new_listings": len(all_new), "by_source": by_source}))


if __name__ == "__main__":
    main()
