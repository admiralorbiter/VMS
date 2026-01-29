import os

from dotenv import load_dotenv
from mailjet_rest import Client

# Load environment variables from .env file
load_dotenv()

mailjet = Client(
    auth=(os.environ["MJ_APIKEY_PUBLIC"], os.environ["MJ_APIKEY_PRIVATE"]),
    version="v3.1",
)


def send_magic_link_email(to_email: str, magic_url: str) -> dict:
    data = {
        "Messages": [
            {
                "From": {"Email": os.environ["MAIL_FROM"], "Name": "My App"},
                "To": [{"Email": to_email}],
                "Subject": "Your sign-in link",
                "TextPart": f"Sign in:\n{magic_url}\n\nIf you didn’t request this, ignore this email.",
                "HTMLPart": f"""
                    <p>Click to sign in:</p>
                    <p><a href="{magic_url}">Sign in</a></p>
                    <p>If you didn’t request this, ignore this email.</p>
                """,
                # Optional for testing *without* delivery:
                # "SandboxMode": True,
            }
        ]
    }
    result = mailjet.send.create(data=data)
    return {"status": result.status_code, "json": result.json()}


if __name__ == "__main__":
    # Send a test email to the same address as MAIL_FROM
    test_email = os.environ.get("MAIL_FROM")
    if not test_email:
        print("Error: MAIL_FROM environment variable is not set")
        exit(1)

    test_url = "https://example.com/test-sign-in-link"
    print(f"Sending test email to {test_email}...")

    try:
        result = send_magic_link_email(test_email, test_url)
        print(f"Email sent successfully!")
        print(f"Status code: {result['status']}")
        print(f"Response: {result['json']}")
    except Exception as e:
        print(f"Error sending email: {e}")
        exit(1)
