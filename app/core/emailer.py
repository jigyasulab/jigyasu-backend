import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv('TWILLIO_SENDGRID_API_KEY')
REGISTERED_FROM_MAIL = os.getenv('REGISTERED_FROM_MAIL')

def send_email(to_email: str, subject: str, content: str):
    """
    Function to send an email using SendGrid API.
    """
    message = Mail(
        from_email=REGISTERED_FROM_MAIL,
        to_emails=to_email,
        subject=subject,
        plain_text_content=content
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent to {to_email}, Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")