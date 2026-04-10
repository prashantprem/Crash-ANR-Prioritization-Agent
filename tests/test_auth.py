import json
import pytest
from unittest.mock import patch, MagicMock
from agent.auth import get_access_token


FAKE_SA = json.dumps({
    "type": "service_account",
    "project_id": "test-project",
    "private_key_id": "key-id",
    "private_key": "fake-key",
    "client_email": "test@test-project.iam.gserviceaccount.com",
    "client_id": "123",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
})


def test_get_access_token_returns_string():
    mock_creds = MagicMock()
    mock_creds.token = "ya29.fake-token"

    with patch("agent.auth.service_account.Credentials.from_service_account_info",
               return_value=mock_creds), \
         patch("agent.auth.google.auth.transport.requests.Request"), \
         patch.object(mock_creds, "refresh"):
        token = get_access_token(FAKE_SA)

    assert token == "ya29.fake-token"


def test_get_access_token_uses_correct_scopes():
    mock_creds = MagicMock()
    mock_creds.token = "ya29.fake"

    with patch("agent.auth.service_account.Credentials.from_service_account_info",
               return_value=mock_creds) as mock_from_info, \
         patch("agent.auth.google.auth.transport.requests.Request"), \
         patch.object(mock_creds, "refresh"):
        get_access_token(FAKE_SA)

    _, kwargs = mock_from_info.call_args
    assert "https://www.googleapis.com/auth/cloud-platform" in kwargs["scopes"]
    assert "https://www.googleapis.com/auth/analytics.readonly" in kwargs["scopes"]
