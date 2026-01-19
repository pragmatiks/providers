# CLAUDE.md

> Tasks tracked in Linear. SessionStart hook injects issue context from branch name.

## Project

**pragma-providers**: Official providers for the Pragmatiks platform (GCP, AWS, etc.).

## Architecture

Providers are KEDA-scaled consumers that:
1. Subscribe to NATS JetStream for work items
2. Execute provider-specific logic (cloud API calls)
3. Return results via NATS

## Development

Always use `task` commands:

| Command | Purpose |
|---------|---------|
| `task test` | Run pytest |
| `task format` | Format with ruff |
| `task check` | Lint + type check |

## Provider Interface

Each provider must implement:
- `authenticate()` - Handle provider credentials
- `validate_request()` - Schema validation
- `execute()` - Provider invocation
- `parse_response()` - Normalize response format

## Testing

- Mock external cloud APIs
- Use respx for httpx mocking
- Test success and failure paths
- Verify request transformation

## Publishing to PyPI

Each provider is a separate PyPI package:

| Provider | Package | Tag Format |
|----------|---------|------------|
| GCP | `pragmatiks-gcp-provider` | `gcp-v{version}` |

**Versioning** (commitizen, per-package):
```bash
cd packages/gcp
cz bump              # Bump version based on conventional commits
```

**Publishing**:
```bash
cd packages/gcp
uv build             # Build wheel and sdist
uv publish           # Publish to PyPI (requires PYPI_TOKEN)
```

**Note**: Each provider has its own version and changelog.

## Related Repositories

- `../pragma-sdk/` - SDK (providers depend on it)
- `../pragma-os/` - Runtime that dispatches to providers
