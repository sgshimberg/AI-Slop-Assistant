"""Shared Google OAuth helper for Calendar + Tasks (same client, different scopes)."""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from src import config

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks.readonly",
]


def get_credentials() -> Credentials:
    creds = None
    if os.path.exists(config.GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.GOOGLE_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config.GOOGLE_CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(config.GOOGLE_TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())

    return creds
