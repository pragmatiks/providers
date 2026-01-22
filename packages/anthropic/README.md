# Anthropic Provider

Anthropic provider for Pragmatiks - wraps the Claude Messages API for reactive AI completions.

## Resources

### `anthropic/messages`

Wraps the Claude Messages API. API keys can be injected via `FieldReference` from `pragma/secret` resources.

**Config:**
- `api_key` - Anthropic API key (use FieldReference for injection)
- `model` - Model identifier (e.g., `claude-sonnet-4-20250514`)
- `messages` - Conversation messages in Anthropic format
- `max_tokens` - Maximum tokens in the response
- `system` - Optional system prompt
- `temperature` - Optional sampling temperature (0.0-1.0)

**Outputs:**
- `id` - Anthropic message ID
- `content` - Response content blocks
- `model` - Model used for generation
- `stop_reason` - Reason generation stopped
- `input_tokens` - Tokens in input
- `output_tokens` - Tokens in output

## Usage

```python
from anthropic_provider import Messages, MessagesConfig

config = MessagesConfig(
    api_key="sk-...",  # Or use FieldReference
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=1024,
    system="You are a helpful assistant.",
)
```

## Development

```bash
# Install dependencies
uv sync --dev

# Run tests
uv run pytest tests/

# Lint
uv run ruff check .
```

## Testing

Use `ProviderHarness` to test lifecycle methods:

```python
from pragma_sdk.provider import ProviderHarness
from anthropic_provider import Messages, MessagesConfig

async def test_create(harness, mock_anthropic_client):
    result = await harness.invoke_create(
        Messages,
        name="test-msg",
        config=MessagesConfig(
            api_key="sk-test",
            model="claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=100,
        ),
    )
    assert result.success
    assert result.outputs.id is not None
```
