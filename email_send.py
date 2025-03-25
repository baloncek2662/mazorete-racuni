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


def send_email(
    recipient_email: str, month: str, person_bills: list[str], extras: list[str]
):
    # Create the email
    email = EmailMessage()
    email["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"  # Include the sender's name
    email["To"] = recipient_email
    email["Subject"] = f"račun {month} 2025"

    # Construct the extras string
    extras_str = ""
    if len(extras) == 1 and extras[0].strip():
        extras_str = f" in {extras[0]}"
    elif len(extras) > 1:
        extras_str = f" {', '.join(extras[:-1])} in {extras[-1]}"

    # Set the email content
    content = CONTENT_TEMPLATE.format(month=month, extras_str=extras_str)
    email.set_content(content)

    # Add bills as attachments
    for person_bill in person_bills:
        with open(person_bill, "rb") as bill_file:
            email.add_attachment(
                bill_file.read(),
                maintype="application",
                subtype="pdf",
                filename=os.path.basename(person_bill),
            )

    # Send the email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(email)
        print("Email uspešno poslan!")
    except Exception as e:
        print(f"Napaka pri pošiljanju emaila: {e}")
