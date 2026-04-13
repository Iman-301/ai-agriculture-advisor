"""Configure Twilio number webhook to bypass ngrok browser warning."""

from twilio.rest import Client
from config import settings

# Your Twilio credentials
account_sid = settings.twilio_account_sid
auth_token = settings.twilio_auth_token

client = Client(account_sid, auth_token)

# Your ngrok URL
NGROK_URL = "https://dawna-fibrinous-lonely.ngrok-free.dev"

# Your Twilio phone number SID (we need to find it first)
print("Finding your Twilio number...")
incoming_numbers = client.incoming_phone_numbers.list(phone_number="+17405966137")

if not incoming_numbers:
    print("❌ Could not find number +17405966137")
    print("Please check your Twilio console")
    exit(1)

phone_number = incoming_numbers[0]
print(f"✓ Found number: {phone_number.phone_number}")
print(f"  SID: {phone_number.sid}")
print()

# Update the webhook
print(f"Configuring webhook to: {NGROK_URL}/voice/incoming")
phone_number.update(
    voice_url=f"{NGROK_URL}/voice/incoming",
    voice_method="POST"
)

print("✓ Webhook configured successfully!")
print()
print("Now you can:")
print("1. Call +17405966137 from your Ethiopian number")
print("2. Or use test_call.py to have Twilio call you")
print()
print("Note: The webhook is now permanently configured until you change it.")
