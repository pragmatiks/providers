# Pragma Providers Context

## Overview
`pragma-providers` is a collection of official resource providers for the Pragmatiks platform. Each provider is a Python package that implements the `pragma-sdk` Provider interface.

## Architecture
*   **Monorepo**: Uses `uv` workspaces to manage multiple packages in `packages/`.
*   **Providers**:
    *   `gcp`: Google Cloud (Secret Manager, GKE).
    *   `anthropic`: Claude Messages API.
    *   `openai`: Chat Completions & Embeddings.
    *   `docling`: Document parsing.
    *   `qdrant`: Vector database.
    *   `agno`: AI Agents.

## Development

### Key Commands
Run these from the `pragma-providers` directory or via `task <provider>:<command>` from the root.

*   `task test`: Run tests across all providers.
*   `task <provider>:test`: Run tests for a specific provider (e.g., `task gcp:test`).
*   `task <provider>:check`: Run linting and type checking for a specific provider.

### Dependencies
*   **Runtime**: `pragmatiks-sdk`, plus provider-specific SDKs (e.g., `google-cloud-secret-manager`, `anthropic`).
*   **Dev**: `pytest`, `pytest-asyncio`, `ruff`.

## Conventions
*   **Structure**: Each provider lives in `packages/<provider_name>`.
*   **Testing**: Use `ProviderHarness` from `pragma-sdk` to test lifecycle methods (`on_create`, `on_update`) without deploying.
*   **Configuration**: All resource configs must be Pydantic models inheriting from `Config`.
