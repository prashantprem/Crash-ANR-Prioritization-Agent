import json

import google.auth.transport.requests
from google.oauth2 import service_account

SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/analytics.readonly",
]


def get_access_token(service_account_json: str) -> str:
    info = json.loads(service_account_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token
