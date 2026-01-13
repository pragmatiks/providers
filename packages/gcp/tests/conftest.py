"""Pytest configuration for gcp provider tests."""

from unittest.mock import MagicMock

import pytest
from pragma_sdk.provider import ProviderHarness


# Sample GCP service account credentials for testing
SAMPLE_CREDENTIALS = {
    "type": "service_account",
    "project_id": "test-project",
    "private_key_id": "key123",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MJ7EH7M7FV8PLVP5\nfake-key-for-testing-only\n-----END RSA PRIVATE KEY-----\n",
    "client_email": "test@test-project.iam.gserviceaccount.com",
    "client_id": "123456789",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project.iam.gserviceaccount.com",
}


@pytest.fixture
def harness() -> ProviderHarness:
    """Test harness for invoking lifecycle methods."""
    return ProviderHarness()


@pytest.fixture
def sample_credentials() -> dict:
    """Sample GCP service account credentials for testing."""
    return SAMPLE_CREDENTIALS.copy()


@pytest.fixture
def mock_secretmanager_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock GCP Secret Manager client with credentials support."""
    mock_client = MagicMock()

    # Mock create_secret response
    mock_secret = MagicMock()
    mock_secret.name = "projects/test-project/secrets/test-secret"
    mock_client.create_secret.return_value = mock_secret
    mock_client.get_secret.return_value = mock_secret

    # Mock add_secret_version response
    mock_version = MagicMock()
    mock_version.name = "projects/test-project/secrets/test-secret/versions/1"
    mock_client.add_secret_version.return_value = mock_version

    # Patch the client constructor to accept credentials arg
    monkeypatch.setattr(
        "gcp_provider.resources.secret.secretmanager.SecretManagerServiceClient",
        lambda credentials=None: mock_client,
    )

    # Mock credentials creation (we don't need real credentials in tests)
    mock_credentials = MagicMock()
    monkeypatch.setattr(
        "gcp_provider.resources.secret.service_account.Credentials.from_service_account_info",
        lambda info: mock_credentials,
    )

    return mock_client
