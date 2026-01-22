# OpenAI Provider

OpenAI provider for Pragmatiks, providing Chat Completions API resources for AI completions with reactive dependency management.

## Installation

```bash
pip install pragmatiks-openai-provider
```

## Usage

```python
from pragma import Resources

# Create a chat completion
resources = Resources()
completion = resources.create(
    "openai/chat_completions",
    name="my-completion",
    config={
        "api_key": {"$ref": "pragma/secret/openai-api-key.value"},
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ],
    }
)

# Access the response
print(completion.outputs.content)
```

## Resources

### chat_completions

Wraps the OpenAI Chat Completions API.

#### Config

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `api_key` | `Field[str]` | Yes | OpenAI API key. Use a FieldReference to inject from pragma/secret. |
| `model` | `str` | Yes | Model identifier (e.g., "gpt-4o", "gpt-4o-mini"). |
| `messages` | `list[dict]` | Yes | Conversation messages including system prompt. |
| `max_tokens` | `int` | No | Maximum tokens in the response. |
| `temperature` | `float` | No | Sampling temperature (0.0-2.0). |

#### Outputs

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | OpenAI completion ID. |
| `content` | `str` | Response content string. |
| `model` | `str` | Model used for generation. |
| `finish_reason` | `str \| None` | Reason generation stopped (stop, length, content_filter). |
| `prompt_tokens` | `int` | Tokens in prompt. |
| `completion_tokens` | `int` | Tokens in completion. |

## Development

```bash
# Install dependencies
uv sync

# Run tests
task openai:test

# Format code
task openai:format

# Run linter
task openai:check
```

## License

MIT
