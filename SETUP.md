# Housing Agent Setup

Everything runs as a GitHub Actions workflow on GitHub's own servers — no Google Cloud, no local machine dependency, no cost. It fires daily at 7:30 AM Pacific whether your Mac is on, asleep, or off, and whether Claude Code is open or not.

Repo: https://github.com/alexandergalbreath-am/socal-housing-agent (private)

## 1. Turn on IMAP for your Amplemarket Gmail (required)

The agent reads Zillow/Redfin/Homes.com alert emails and sends the daily digest through this inbox.

1. Open Gmail (logged in as alexander.galbreath@amplemarket.com) → **Settings** (gear icon) → **See all settings** → **Forwarding and POP/IMAP** tab.
2. Under "IMAP access," select **Enable IMAP** → **Save Changes**.

⚠️ **Heads-up:** this is a Google Workspace (managed) account. Some company IT admins disable IMAP access or App Passwords fleet-wide. If the option is greyed out or missing, or the App Password step below doesn't work, that's Amplemarket's Workspace admin policy blocking it — you'd need to either ask IT to allow it, or point this at a personal Gmail account instead.

## 2. Create a Gmail App Password (required)

This is a Gmail security feature, unrelated to Google Cloud — free, no billing, no card.

1. Go to https://myaccount.google.com/security (while logged into the Amplemarket account).
2. Turn on **2-Step Verification** if it isn't already on.
3. Go to https://myaccount.google.com/apppasswords, name it something like "housing-agent," and generate it.
4. Copy the 16-character password it gives you (spaces don't matter). You won't be able to see it again after leaving the page.

## 3. Add GitHub repo secrets (required)

1. Go to https://github.com/alexandergalbreath-am/socal-housing-agent/settings/secrets/actions
2. Click **New repository secret** and add:
   - Name: `GMAIL_ADDRESS` → Value: `alexander.galbreath@amplemarket.com`
   - Name: `GMAIL_APP_PASSWORD` → Value: the 16-character password from step 2

That's it — once both secrets exist, the next scheduled run (or a manual "Run workflow" from the Actions tab) will actually scrape, log, and email.

## 4. Zillow / Redfin / Homes.com coverage (recommended, via email alerts — not scraping)

These three sites block automated scraping, so the agent instead reads alert emails they send to you voluntarily:

**Zillow** — zillow.com → search Irvine, CA and Costa Mesa, CA rentals, 3+ bed/2.5+ bath, your price range → **Save search** → turn on **email notifications**, frequency "As soon as possible" or "Daily."

**Redfin** — redfin.com → same rental search in Irvine/Costa Mesa → **Save Search** → enable **email updates**.

**Homes.com** — homes.com → same rental search → save search, enable email alerts.

Point all three at your Amplemarket Gmail (the same inbox from steps 1–2). The parsing is best-effort (these are marketing emails, not structured data) — the digest will flag anything it couldn't fully parse so you can just click through and check.

## Recipients

The daily digest currently goes to:
- a.galbreath16@gmail.com
- peter.cline@servicetosuccess.com
- luowens@chapman.edu

Edit the `email.recipients` list in `config.yaml` to change this.

## Testing it

Once secrets are added, go to https://github.com/alexandergalbreath-am/socal-housing-agent/actions/workflows/daily.yml and click **Run workflow** to trigger it immediately instead of waiting for 7:30 AM.
