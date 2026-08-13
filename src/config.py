import os

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var {name}. Copy .env.example to .env and fill it in.")
    return value


TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")
MY_WHATSAPP_NUMBER = os.environ.get("MY_WHATSAPP_NUMBER", "")
TWILIO_CONTENT_SID = os.environ.get("TWILIO_CONTENT_SID", "")
TWILIO_CONTENT_VARIABLES = os.environ.get("TWILIO_CONTENT_VARIABLES", "")

GOOGLE_CLIENT_SECRET_FILE = os.environ.get("GOOGLE_CLIENT_SECRET_FILE", "./credentials.json")
GOOGLE_TOKEN_FILE = os.environ.get("GOOGLE_TOKEN_FILE", "./token.json")
GOOGLE_TEST_CALENDAR_ID = os.environ.get("GOOGLE_TEST_CALENDAR_ID", "")

MOODLE_BASE_URL = os.environ.get("MOODLE_BASE_URL", "")
MOODLE_TOKEN = os.environ.get("MOODLE_TOKEN", "")
MOODLE_ICS_URL = os.environ.get("MOODLE_ICS_URL", "")

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
WEATHER_CITY = os.environ.get("WEATHER_CITY", "Raleigh,US")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
