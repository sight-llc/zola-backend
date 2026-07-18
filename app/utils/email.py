import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_html(subject: str, headline: str, body_line: str, amount: str | None) -> str:
    amount_block = f"""
    <div style="margin:32px 0;padding:24px;background:#f5f5f5;border-radius:8px;text-align:center;">
        <span style="font-size:28px;font-weight:700;letter-spacing:-0.5px;">{amount}</span>
    </div>""" if amount else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{subject}</title></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:'Inter',system-ui,sans-serif;color:#000;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;margin:0 auto;padding:48px 24px;">
    <tr><td>
      <div style="margin-bottom:40px;"><span style="font-size:20px;font-weight:700;">Zola</span></div>
      <div style="height:1px;background:#000;margin-bottom:40px;"></div>
      <h1 style="font-size:22px;font-weight:600;margin:0 0 12px;">{headline}</h1>
      <p style="font-size:15px;color:#444;margin:0 0 8px;line-height:1.6;">{body_line}</p>
      {amount_block}
      <div style="height:1px;background:#e5e5e5;margin:40px 0 24px;"></div>
      <p style="font-size:12px;color:#999;margin:0;">Automated notification from Zola. Do not reply.</p>
    </td></tr>
  </table>
</body></html>"""


def send_notification_email(to_email: str, to_name: str, event_type: str, amount_naira: str | None) -> None:
    try:
        first = to_name.split()[0] if to_name else "there"
        subject_map = {
            "PAYMENT.RECEIVED": "You've received money",
            "TRANSFER.SUCCESS": "Your transfer was successful",
            "TRANSFER.FAILED": "Your transfer failed",
        }
        headline_map = {
            "PAYMENT.RECEIVED": f"Hi {first}, money just landed.",
            "TRANSFER.SUCCESS": f"Hi {first}, your transfer went through.",
            "TRANSFER.FAILED": f"Hi {first}, your transfer didn't go through.",
        }
        body_map = {
            "PAYMENT.RECEIVED": "Funds have been credited to your Zola wallet.",
            "TRANSFER.SUCCESS": "The recipient's account has been credited.",
            "TRANSFER.FAILED": "Something went wrong. No funds were debited. Please try again.",
        }

        html = _build_html(
            subject_map.get(event_type, "Zola notification"),
            headline_map.get(event_type, "Account update"),
            body_map.get(event_type, ""),
            amount_naira,
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject_map.get(event_type, "Zola notification")
        msg["From"] = f"Zola <{settings.gmail_sender}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.gmail_sender, settings.gmail_app_password)
            server.sendmail(settings.gmail_sender, to_email, msg.as_string())

        logger.info(f"Email sent to {to_email} for {event_type}")
    except Exception as e:
        logger.error(f"Email failed for {to_email} ({event_type}): {e}")


def send_welcome_email(to_email: str, to_name: str, nuban: str, bank_name: str = "Nomba") -> None:
    try:
        first_name = to_name.split()[0] if to_name else "there"
        subject = f"Welcome to Zola, {first_name}"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{subject}</title></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:'Inter',system-ui,-apple-system,sans-serif;color:#000000;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;margin:0 auto;padding:48px 24px;">
    <tr><td>
      <div style="margin-bottom:40px;"><span style="font-size:20px;font-weight:700;letter-spacing:-0.5px;">Zola</span></div>
      <div style="height:1px;background:#000000;margin-bottom:40px;"></div>
      <h1 style="font-size:22px;font-weight:600;margin:0 0 12px 0;letter-spacing:-0.3px;">Welcome, {first_name}.</h1>
      <p style="font-size:15px;color:#444444;margin:0 0 32px 0;line-height:1.6;">
        Your Zola account is ready. Here's your dedicated virtual account &mdash;
        anyone can send money directly to this number from any Nigerian bank.
      </p>
      <div style="border:1px solid #000000;border-radius:8px;padding:24px 28px;margin-bottom:32px;">
        <p style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin:0 0 8px 0;color:#999999;">Your Account Number</p>
        <p style="font-size:32px;font-weight:700;letter-spacing:0.06em;font-variant-numeric:tabular-nums;margin:0 0 6px 0;">{nuban}</p>
        <p style="font-size:13px;color:#666666;margin:0;">{bank_name}</p>
      </div>
      <p style="font-size:13px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;margin:0 0 16px 0;color:#999999;">Get started</p>
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:40px;">
        <tr>
          <td style="padding:14px 0;border-top:1px solid #e5e5e5;">
            <span style="font-size:15px;font-weight:500;">Add money</span>
            <p style="font-size:13px;color:#666666;margin:4px 0 0 0;">Send a transfer to your account number above from any bank app.</p>
          </td>
        </tr>
        <tr>
          <td style="padding:14px 0;border-top:1px solid #e5e5e5;">
            <span style="font-size:15px;font-weight:500;">Send money</span>
            <p style="font-size:13px;color:#666666;margin:4px 0 0 0;">Transfer instantly to any Nigerian bank account from your dashboard.</p>
          </td>
        </tr>
      </table>
      <div style="height:1px;background:#e5e5e5;margin-bottom:24px;"></div>
      <p style="font-size:12px;color:#999999;margin:0;line-height:1.6;">This is an automated message from Zola. Do not reply to this email.</p>
    </td></tr>
  </table>
</body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Zola <{settings.gmail_sender}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.gmail_sender, settings.gmail_app_password)
            server.sendmail(settings.gmail_sender, to_email, msg.as_string())

        logger.info(f"Welcome email sent to {to_email}")
    except Exception as e:
        logger.error(f"Welcome email failed for {to_email}: {e}")
