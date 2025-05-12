import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get SMTP settings from environment variables
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_NAME = os.getenv("SENDER_NAME")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
CONTENT_TEMPLATE = """Pozdravljeni,

v priponki vam pošiljam račun za članarino za mesec {month} 2025{extras_str}.

Lep pozdrav,
Ula
"""


def send_email(month: str, to_email: str, bill_names: list[str], extras: list[str] = None):
    """
    Send an email with bill attachments to the recipient.

    Args:
        month: Month of the bills
        to_email: Recipient's email address
        bill_names: List of bill file paths to attach
        extras: List of extras to mention in the email

    Returns:
        True if email was sent successfully, False otherwise
    """
    # Create the email
    email = EmailMessage()
    email["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"  # Include the sender's name
    email["To"] = to_email
    email["Subject"] = f"račun {month} 2025"

    # Construct the extras string
    extras_str = ""
    if extras:  # Only process extras if they exist
        if len(extras) == 1 and extras[0].strip():
            extras_str = f" in {extras[0]}"
        elif len(extras) > 1:
            extras_str = f" {', '.join(extras[:-1])} in {extras[-1]}"

    # Set the email content
    content = CONTENT_TEMPLATE.format(month=month, extras_str=extras_str)
    email.set_content(content)

    # Add bills as attachments
    seen_filenames = {}  # Track filenames that have been seen

    # First pass - identify duplicates
    for bill_path in bill_names:
        basename = os.path.basename(bill_path)
        if basename in seen_filenames:
            # We have a duplicate
            seen_filenames[basename] = True  # Mark as duplicate
        else:
            seen_filenames[basename] = False  # Mark as first occurrence (not duplicate yet)

    # Second pass - add attachments with prefixes for duplicates
    for bill_path in bill_names:
        basename = os.path.basename(bill_path)
        # Extract just the month folder name, not the full path
        folder_parts = os.path.dirname(bill_path).split(os.path.sep)
        month_folder = folder_parts[-1] if folder_parts else ""

        if seen_filenames[basename]:  # If this filename exists multiple times
            # Add month prefix to all occurrences of duplicates
            attachment_filename = f"{month_folder}_{basename}"
        else:
            # Use original filename for non-duplicates
            attachment_filename = basename

        with open(bill_path, "rb") as bill_file:
            email.add_attachment(
                bill_file.read(),
                maintype="application",
                subtype="pdf",
                filename=attachment_filename,
            )

    # Send the email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(email)
        print(f"Email uspešno poslan na: {to_email}")
        return True
    except Exception as e:
        print(f"Napaka pri pošiljanju emaila na {to_email}: {e}")
        return False
