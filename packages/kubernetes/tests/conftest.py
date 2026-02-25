"""Pytest configuration for kubernetes provider tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pragma_sdk.provider import ProviderHarness


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


SAMPLE_CREDENTIALS = {
    "type": "service_account",
    "project_id": "test-project",
    "private_key_id": "key123",
    "private_key": (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MJ7EH7M7FV8PLVP5\n"
        "fake-key-for-testing-only\n"
        "-----END RSA PRIVATE KEY-----\n"
    ),
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
def mock_gke_cluster(mocker: MockerFixture) -> Any:
    mock_outputs = mocker.MagicMock()
    mock_outputs.endpoint = "10.0.0.1"
    mock_outputs.cluster_ca_certificate = "Y2VydGlmaWNhdGU="
    mock_outputs.name = "test-cluster"
    mock_outputs.location = "europe-west4"
    mock_outputs.status = "RUNNING"

    mock_config = mocker.MagicMock()
    mock_config.credentials = SAMPLE_CREDENTIALS

    mock_cluster = mocker.MagicMock()
    mock_cluster.outputs = mock_outputs
    mock_cluster.config = mock_config

    return mock_cluster


@pytest.fixture
def mock_lightkube_client(mocker: MockerFixture) -> Any:
    mock_client = mocker.MagicMock()

    mock_client.apply = mocker.AsyncMock()
    mock_client.get = mocker.AsyncMock()
    mock_client.delete = mocker.AsyncMock()
    mock_client.close = mocker.AsyncMock()

    mocker.patch(
        "kubernetes_provider.resources.service.create_client_from_gke",
        return_value=mock_client,
    )

    mocker.patch(
        "kubernetes_provider.resources.configmap.create_client_from_gke",
        return_value=mock_client,
    )

    mocker.patch(
        "kubernetes_provider.resources.secret.create_client_from_gke",
        return_value=mock_client,
    )

    mocker.patch(
        "kubernetes_provider.resources.namespace.create_client_from_gke",
        return_value=mock_client,
    )

    mocker.patch(
        "kubernetes_provider.resources.statefulset.create_client_from_gke",
        return_value=mock_client,
    )

    mocker.patch(
        "kubernetes_provider.resources.statefulset.asyncio.sleep",
        return_value=None,
    )

    return mock_client
