# GCP Provider

GCP provider for Pragmatiks - manage Google Cloud resources declaratively.

## Available Resources

### Secret (gcp/secret)

Manages secrets in GCP Secret Manager using user-provided service account credentials.

```python
from gcp_provider import Secret, SecretConfig

# Define a secret
secret = Secret(
    name="my-api-key",
    config=SecretConfig(
        project_id="my-gcp-project",
        secret_id="api-key",
        data="super-secret-value",
        credentials={"type": "service_account", ...},  # or JSON string
    ),
)
```

**Config:**
- `project_id` - GCP project ID where the secret will be created
- `secret_id` - Identifier for the secret (must be unique per project)
- `data` - Secret payload data to store
- `credentials` - GCP service account credentials (JSON object or string)

**Outputs:**
- `resource_name` - Full GCP resource name (`projects/{project}/secrets/{id}`)
- `version_name` - Full version resource name including version number
- `version_id` - The version number as a string

## Installation

```bash
pip install pragmatiks-gcp-provider
```

## Development

### Testing

```bash
# Install dependencies
uv sync --dev

# Run tests
uv run pytest tests/
```

### Writing Tests

Use `ProviderHarness` to test lifecycle methods:

```python
from pragma_sdk.provider import ProviderHarness
from gcp_provider import Secret, SecretConfig

async def test_create_secret():
    harness = ProviderHarness()
    result = await harness.invoke_create(
        Secret,
        name="test-secret",
        config=SecretConfig(
            project_id="test-project",
            secret_id="my-secret",
            data="secret-value",
            credentials=mock_credentials,
        ),
    )
    assert result.success
    assert result.outputs.resource_name is not None
```

## Deployment

Push your provider to Pragmatiks platform:

```bash
pragma provider push
```
