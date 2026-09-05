# SoCal Housing Agent

Daily automated rental search for Irvine / Costa Mesa, CA. Runs entirely as a
GitHub Actions workflow (`.github/workflows/daily.yml`) — no local machine or
Google Cloud dependency.

- **Realtor.com**: scraped directly via [HomeHarvest](https://github.com/ZacharyHampton/HomeHarvest).
- **Zillow / Redfin / Homes.com**: read from saved-search email alerts via Gmail IMAP
  (these sites block automated scraping, so this uses the alert feature they provide instead).
- **Drive-time filter**: free [OSRM](https://project-osrm.org/) routing, no API key.
- **State**: `data/seen_urls.json` (dedup) and `data/listings_log.jsonl` (full history), committed by the workflow each run.
- **Notifications**: a plaintext email digest of new listings, sent via the same Gmail account.

See [SETUP.md](SETUP.md) for one-time setup (Gmail App Password, GitHub secrets, saved searches).
Search criteria live in [config.yaml](config.yaml) — edit anytime, no code changes needed.
