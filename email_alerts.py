"""Read Zillow/Redfin/Homes.com saved-search alert emails from Gmail via IMAP.

Requires GMAIL_ADDRESS + GMAIL_APP_PASSWORD env vars (a Gmail "App Password",
not the account password — see SETUP.md). This reads alerts the sites already
send by design; it does not scrape or automate those sites in any way.
"""
import email
import imaplib
import os
import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

SITE_PATTERNS = {
    "Zillow": re.compile(r"https?://(?:www\.)?zillow\.com/homedetails/[^\s\"'<>]+"),
    "Redfin": re.compile(r"https?://(?:www\.)?redfin\.com/[^\s\"'<>]*/home/\d+[^\s\"'<>]*"),
    "Homes.com": re.compile(r"https?://(?:www\.)?homes\.com/property/[^\s\"'<>]+"),
}
SENDER_DOMAINS = ["zillow.com", "redfin.com", "homes.com"]

PRICE_RE = re.compile(r"\$[\d,]{3,}")
BEDS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:bd|bed)", re.I)
BATHS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:ba|bath)", re.I)


def fetch_alert_listings(lookback_days=1):
    """Returns a list of dicts: url, source, price, beds, baths, context (best-effort)."""
    address = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not address or not app_password:
        return []

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(address, app_password)
    imap.select("INBOX")

    since = (datetime.utcnow() - timedelta(days=lookback_days)).strftime("%d-%b-%Y")
    results = []
    try:
        for domain in SENDER_DOMAINS:
            typ, data = imap.search(None, f'(SINCE {since} FROM "{domain}")')
            if typ != "OK" or not data or not data[0]:
                continue
            for num in data[0].split():
                typ, msg_data = imap.fetch(num, "(RFC822)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                html = _get_html_body(msg)
                if html:
                    results.extend(_extract_listings(html))
    finally:
        imap.logout()

    return results


def _get_html_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                except Exception:
                    continue
        return None
    if msg.get_content_type() == "text/html":
        return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")
    return None


def _extract_listings(html):
    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(" ", strip=True)
    found = []
    seen_in_email = set()

    for source, pattern in SITE_PATTERNS.items():
        for match in pattern.finditer(html):
            url = match.group(0).split('"')[0].split("'")[0]
            if url in seen_in_email:
                continue
            seen_in_email.add(url)

            context = ""
            anchor = soup.find("a", href=lambda h: bool(h) and url in h)
            if anchor:
                container = anchor
                for _ in range(4):
                    if container.parent:
                        container = container.parent
                context = container.get_text(" ", strip=True)
            if not context:
                context = full_text

            price_match = PRICE_RE.search(context)
            beds_match = BEDS_RE.search(context)
            baths_match = BATHS_RE.search(context)

            found.append({
                "url": url,
                "source": source,
                "price": price_match.group(0).replace("$", "").replace(",", "") if price_match else None,
                "beds": beds_match.group(1) if beds_match else None,
                "baths": baths_match.group(1) if baths_match else None,
                "context": context[:300],
            })
    return found
