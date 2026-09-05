"""Read Zillow/Redfin/Homes.com saved-search alert emails from Gmail via IMAP.

Requires GMAIL_ADDRESS + GMAIL_APP_PASSWORD env vars (a Gmail "App Password",
not the account password — see SETUP.md). This reads alerts the sites already
send by design; it does not scrape or automate those sites in any way.

These alert emails route links through the sender's email-marketing platform
(e.g. click.email.homes.com), not the site's own domain, so listing details
are pulled from the email's visible text rather than the link URL.
"""
import email
import imaplib
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

from bs4 import BeautifulSoup

SENDER_DOMAINS = {
    "zillow.com": "Zillow",
    "redfin.com": "Redfin",
    "homes.com": "Homes.com",
}
FOLDERS = ["INBOX", "[Gmail]/Spam"]
EXCLUDE_LINK_KEYWORDS = ["unsubscribe", "preference", "privacy", "manage", "saved-search", "saved_search", "savedsearch"]

PRICE_RE = re.compile(r"\$([\d,]{3,})\s*/\s*mo", re.I)
BEDS_BATHS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:Beds?|Bds?)\D{0,6}?(\d+(?:\.\d+)?)\s*(?:Baths?|Ba)\b", re.I)
SQFT_RE = re.compile(r"([\d,]+)\s*Sq\.?\s*Ft", re.I)
ADDRESS_RE = re.compile(r"([0-9][\w\s.\-#]{2,40}?)\s*[•·|]\s*([A-Za-z][A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5})")


def fetch_alert_listings(lookback_days=1):
    """Returns (listings, debug). `debug` reports what was actually seen in the
    mailbox so "0 new listings" can be diagnosed instead of guessed at."""
    address = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    debug = {"emails_by_domain": {}, "folders_checked": [], "listings_extracted": 0, "skipped_non_listing": 0}
    if not address or not app_password:
        debug["skipped"] = "GMAIL_ADDRESS/GMAIL_APP_PASSWORD not set"
        return [], debug

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(address, app_password)

    since = (datetime.utcnow() - timedelta(days=lookback_days)).strftime("%d-%b-%Y")
    results = []
    try:
        for folder in FOLDERS:
            typ, _ = imap.select(folder)
            if typ != "OK":
                continue
            debug["folders_checked"].append(folder)
            for domain, source in SENDER_DOMAINS.items():
                typ, data = imap.search(None, f'(SINCE {since} FROM "{domain}")')
                if typ != "OK" or not data or not data[0]:
                    continue
                msg_nums = data[0].split()
                debug["emails_by_domain"][domain] = debug["emails_by_domain"].get(domain, 0) + len(msg_nums)
                for num in msg_nums:
                    typ, msg_data = imap.fetch(num, "(RFC822)")
                    if typ != "OK" or not msg_data or not msg_data[0]:
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    html = _get_html_body(msg)
                    if not html:
                        continue
                    parsed = _parse_listing_alert(html, domain, source)
                    if parsed:
                        results.append(parsed)
                    else:
                        debug["skipped_non_listing"] += 1
    finally:
        imap.logout()

    debug["listings_extracted"] = len(results)
    return results, debug


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


def _parse_listing_alert(html, domain, source):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    beds_baths_match = BEDS_BATHS_RE.search(text)
    price_match = PRICE_RE.search(text)
    if not beds_baths_match or not price_match:
        return None  # not a per-listing alert (welcome/verification/newsletter email)

    window = text[beds_baths_match.end():beds_baths_match.end() + 200]
    sqft_match = SQFT_RE.search(window)

    addr_search_start = beds_baths_match.end() + (sqft_match.end() if sqft_match else 0)
    addr_window = text[addr_search_start:addr_search_start + 150]
    addr_match = ADDRESS_RE.search(addr_window)

    url = _find_listing_link(soup, domain)
    if not url:
        return None  # can't dedupe or link to it without a URL

    return {
        "url": url,
        "source": source,
        "price": price_match.group(1).replace(",", ""),
        "beds": beds_baths_match.group(1),
        "baths": beds_baths_match.group(2),
        "sqft": sqft_match.group(1).replace(",", "") if sqft_match else None,
        "address": addr_match.group(1).strip() if addr_match else None,
        "city": addr_match.group(2).split(",")[0].strip() if addr_match else None,
        "context": text[:300],
    }


def _find_listing_link(soup, domain):
    for a in soup.find_all("a", href=True):
        href = a["href"]
        try:
            host = urlparse(href).hostname or ""
        except ValueError:
            continue
        if not host.endswith(domain):
            continue
        link_text = a.get_text(" ", strip=True).lower()
        if any(kw in href.lower() or kw in link_text for kw in EXCLUDE_LINK_KEYWORDS):
            continue
        return href
    return None
