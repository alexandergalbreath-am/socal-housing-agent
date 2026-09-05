"""Render data/listings_log.jsonl into a human-readable LISTINGS.md table."""
import json
import os
from datetime import datetime, timezone

from common import ROOT, load_config

HEADER = ["Date Found", "Address", "City", "Price/mo", "Beds", "Baths", "Drive Time", "Source", "Link", "Notes"]


def render():
    config = load_config()
    log_path = os.path.join(ROOT, config["state"]["log_file"])

    rows = []
    if os.path.exists(log_path):
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))

    rows.sort(key=lambda r: r.get("date_found", ""), reverse=True)

    lines = [
        "# SoCal Housing Listings",
        "",
        f"_Last checked: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} — {len(rows)} total listing(s) tracked_",
        "",
        "| " + " | ".join(HEADER) + " |",
        "|" + "|".join(["---"] * len(HEADER)) + "|",
    ]
    for r in rows:
        lines.append(
            "| " + " | ".join([
                str(r.get("date_found", "")),
                str(r.get("address", "")).replace("|", "-"),
                str(r.get("city", "")),
                str(r.get("price", "")),
                str(r.get("beds", "")),
                str(r.get("baths", "")),
                str(r.get("drive_time", "")),
                str(r.get("source", "")),
                f"[link]({r.get('url', '')})" if r.get("url") else "",
                str(r.get("notes", "")).replace("|", "-"),
            ]) + " |"
        )

    with open(os.path.join(ROOT, "LISTINGS.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    render()
