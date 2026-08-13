"""Phase 0 hello-world: send yourself one WhatsApp message via Twilio.

Run:  python -m src.integrations.whatsapp
Requires: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, MY_WHATSAPP_NUMBER in .env

WhatsApp only allows freeform `body` messages inside the 24h session window opened
by the recipient messaging you first (e.g. the sandbox join code). Any message you
initiate outside that window — which includes the eventual 4AM daily digest — must
be sent as a pre-approved Content Template via TWILIO_CONTENT_SID instead. See
CREDENTIALS.md for how to create one. If TWILIO_CONTENT_SID is unset, this sends
freeform text (only works within an active session).
"""

from twilio.rest import Client

from src import config


def send_test_message() -> str:
    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    kwargs = {"from_": config.TWILIO_WHATSAPP_FROM, "to": config.MY_WHATSAPP_NUMBER}
    if config.TWILIO_CONTENT_SID:
        kwargs["content_sid"] = config.TWILIO_CONTENT_SID
        kwargs["content_variables"] = config.TWILIO_CONTENT_VARIABLES or "{}"
    else:
        kwargs["body"] = "Hello from your assistant — Phase 0 connectivity test."
    message = client.messages.create(**kwargs)
    return message.sid


if __name__ == "__main__":
    sid = send_test_message()
    print(f"Sent. Message SID: {sid}")
    print("Check your WhatsApp for the message.")
