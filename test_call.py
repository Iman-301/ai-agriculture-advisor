"""Test script to make an outbound call from Twilio to your Ethiopian number."""

from twilio.rest import Client
from config import settings

# Your Twilio credentials
account_sid = settings.twilio_account_sid
auth_token = settings.twilio_auth_token

client = Client(account_sid, auth_token)

# Your ngrok URL - make sure ngrok is running!
NGROK_URL = "https://dawna-fibrinous-lonely.ngrok-free.dev"

# Your Twilio phone number (no spaces)
FROM_NUMBER = "+17405966137"

# Make the call using your webhook URL (not inline TwiML)
print("Making call to +251988189380...")
print("Make sure:")
print("1. ngrok is running at:", NGROK_URL)
print("2. FastAPI server is running (without --reload for stability)")
print("3. Your Ethiopian number is verified in Twilio")
print()

# Use the /voice/incoming endpoint which returns proper TwiML
call = client.calls.create(
    to="+251988189380",
    from_=FROM_NUMBER,
    url=f"{NGROK_URL}/voice/incoming",
    method="POST"
)

print(f"✓ Call initiated!")
print(f"Call SID: {call.sid}")
print(f"Status: {call.status}")
print()
print("Your phone should ring shortly. Answer it and speak your farming question in Amharic!")
