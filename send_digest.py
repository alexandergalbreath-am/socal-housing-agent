import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_digest(config, new_listings):
    if not new_listings:
        return False

    sender = config["email"]["sender_address"]
    recipients = config["email"]["recipients"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]

    lines = []
    for item in new_listings:
        note = f"\n  Note: {item['notes']}" if item.get("notes") else ""
        lines.append(
            f"- {item.get('address') or '(address not parsed — open link)'}\n"
            f"  ${item.get('price', '?')}/mo · {item.get('beds', '?')}bd/{item.get('baths', '?')}ba · {item.get('source', '')}\n"
            f"  Drive time: {item.get('drive_time', 'Unknown')}\n"
            f"  {item['url']}{note}"
        )
    body = (
        f"{len(new_listings)} new rental listing(s) found today in Irvine / Costa Mesa:\n\n"
        + "\n\n".join(lines)
    )

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = f"New rental listing(s) found — Irvine/Costa Mesa ({len(new_listings)})"
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, app_password)
        server.sendmail(sender, recipients, msg.as_string())
    return True
