"""Agno tools/mcp resource wrapping MCPTools for MCP server integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal
from urllib.parse import urlparse

from agno.tools.mcp import MCPTools
from pragma_sdk import Config, Field, Outputs, Resource
from pydantic import model_validator


if TYPE_CHECKING:
    from agno.agent import Agent
    from agno.run import RunContext
    from agno.team import Team


TransportType = Literal["stdio", "sse", "streamable-http"]


class ToolsMCPConfig(Config):
    """Configuration for MCP server integration.

    Attributes:
        command: Command to run the MCP server (for stdio transport).
        url: URL for SSE or streamable-http transport.
        transport: Transport type (stdio, sse, streamable-http). Auto-detected if not specified.
        env: Environment variables for the server process.
        headers: Static HTTP headers for remote transports (e.g., Authorization).
        include_run_context_headers: Forward RunContext as headers (X-User-ID, X-Session-ID, X-Run-ID).
        timeout_seconds: Connection timeout in seconds.
        include_tools: Only include these tool names (optional filter).
        exclude_tools: Exclude these tool names (optional filter).
        tool_name_prefix: Prefix to add to all tool names (avoids collisions).
    """

    command: str | None = None
    url: str | None = None
    transport: TransportType | None = None
    env: dict[str, Field[str]] | None = None
    headers: dict[str, Field[str]] | None = None
    include_run_context_headers: bool = False
    timeout_seconds: int = 10
    include_tools: list[str] | None = None
    exclude_tools: list[str] | None = None
    tool_name_prefix: str | None = None

    @model_validator(mode="after")
    def validate_transport_config(self) -> ToolsMCPConfig:
        """Validate that the appropriate config is provided for the transport type.

        Returns:
            Validated config.

        Raises:
            ValueError: If transport config is invalid.
        """
        has_command = self.command is not None
        has_url = self.url is not None

        if not has_command and not has_url:
            msg = "Either 'command' (for stdio) or 'url' (for sse/streamable-http) is required"
            raise ValueError(msg)

        if has_command and has_url:
            msg = "Cannot specify both 'command' and 'url' - choose one transport"
            raise ValueError(msg)

        if self.transport:
            if self.transport == "stdio" and not has_command:
                msg = "stdio transport requires 'command'"
                raise ValueError(msg)

            if self.transport in ("sse", "streamable-http") and not has_url:
                msg = f"{self.transport} transport requires 'url'"
                raise ValueError(msg)

        return self


class ToolsMCPOutputs(Outputs):
    """Outputs from tools/mcp resource.

    Attributes:
        name: Server identifier derived from command or URL.
        tools: List of tool names provided by this MCP server.
        ready: Whether the server connection was validated.
    """

    name: str
    tools: list[str]
    ready: bool


class ToolsMCP(Resource[ToolsMCPConfig, ToolsMCPOutputs]):
    """MCP server integration resource wrapping Agno's MCPTools.

    Provides Model Context Protocol server integration. Supports stdio
    transport (local processes) and SSE/streamable-http (remote servers).

    Lifecycle:
        - on_create: Connect to MCP server, discover tools, return metadata
        - on_update: Reconnect with new config, refresh tool list
        - on_delete: No-op (stateless wrapper)
    """

    provider: ClassVar[str] = "agno"
    resource: ClassVar[str] = "tools/mcp"

    def _server_name(self) -> str:
        """Derive server name from command or URL.

        Returns:
            Human-readable server identifier.
        """
        if self.config.command:
            parts = self.config.command.split()
            for part in reversed(parts):
                if part.startswith("@") or part.startswith("mcp-server"):
                    return part.split("/")[-1]

            return parts[-1] if parts else "mcp-server"

        if self.config.url:
            parsed = urlparse(self.config.url)
            return parsed.netloc or parsed.path.split("/")[-1] or "mcp-server"

        return "mcp-server"

    def _resolve_env(self) -> dict[str, str] | None:
        """Resolve environment variables to strings.

        Field values are resolved by the SDK before lifecycle handlers run,
        so we just need to convert them to str.

        Returns:
            Resolved environment dict or None.
        """
        if not self.config.env:
            return None

        return {key: str(value) for key, value in self.config.env.items()}

    def _resolve_headers(self) -> dict[str, str] | None:
        """Resolve static headers to strings.

        Returns:
            Resolved headers dict or None.
        """
        if not self.config.headers:
            return None

        return {key: str(value) for key, value in self.config.headers.items()}

    def _build_header_provider(self) -> Any:
        """Build a header_provider function for MCPTools.

        Combines static headers from config with optional RunContext headers.

        Returns:
            A callable header_provider or None if no headers configured.
        """
        static_headers = self._resolve_headers()
        include_run_context = self.config.include_run_context_headers

        if not static_headers and not include_run_context:
            return None

        def header_provider(
            run_context: RunContext | None = None,
            agent: Agent | None = None,
            team: Team | None = None,
        ) -> dict[str, Any]:
            headers: dict[str, Any] = {}

            if static_headers:
                headers.update(static_headers)

            if include_run_context and run_context:
                if run_context.user_id:
                    headers["X-User-ID"] = run_context.user_id

                if run_context.session_id:
                    headers["X-Session-ID"] = run_context.session_id

                if run_context.run_id:
                    headers["X-Run-ID"] = run_context.run_id

            if agent and agent.name:
                headers["X-Agent-Name"] = agent.name

            if team and team.name:
                headers["X-Team-Name"] = team.name

            return headers

        return header_provider

    def _build_mcp_tools(self) -> MCPTools:
        """Build MCPTools instance from config.

        Returns:
            Configured MCPTools instance (not yet connected).
        """
        kwargs: dict = {
            "timeout_seconds": self.config.timeout_seconds,
        }

        if self.config.command:
            kwargs["command"] = self.config.command

        if self.config.url:
            kwargs["url"] = self.config.url

        if self.config.transport:
            kwargs["transport"] = self.config.transport

        env = self._resolve_env()
        if env:
            kwargs["env"] = env

        if self.config.include_tools:
            kwargs["include_tools"] = self.config.include_tools

        if self.config.exclude_tools:
            kwargs["exclude_tools"] = self.config.exclude_tools

        if self.config.tool_name_prefix:
            kwargs["tool_name_prefix"] = self.config.tool_name_prefix

        header_provider = self._build_header_provider()
        if header_provider:
            kwargs["header_provider"] = header_provider

        return MCPTools(**kwargs)

    async def _discover_tools(self) -> list[str]:
        """Connect to MCP server and discover available tools.

        Returns:
            List of tool names from the server.
        """
        mcp_tools = self._build_mcp_tools()

        try:
            await mcp_tools.connect()
            functions = mcp_tools.get_functions()
            return list(functions.keys())

        finally:
            await mcp_tools.close()

    async def _build_outputs(self) -> ToolsMCPOutputs:
        """Build outputs by connecting and discovering tools.

        Returns:
            ToolsMCPOutputs with server name, tools, and ready status.
        """
        try:
            tools = await self._discover_tools()
            return ToolsMCPOutputs(
                name=self._server_name(),
                tools=tools,
                ready=True,
            )

        except Exception:
            return ToolsMCPOutputs(
                name=self._server_name(),
                tools=[],
                ready=False,
            )

    def toolkit(self) -> MCPTools:
        """Returns a new MCPTools instance for use by agents.

        The caller is responsible for calling connect() and close()
        on the returned instance.

        Returns:
            Configured MCPTools instance (not connected).
        """
        return self._build_mcp_tools()

    async def on_create(self) -> ToolsMCPOutputs:
        """Create resource by validating MCP server connection.

        Returns:
            ToolsMCPOutputs with discovered tools and connection status.
        """
        return await self._build_outputs()

    async def on_update(self, previous_config: ToolsMCPConfig) -> ToolsMCPOutputs:  # noqa: ARG002
        """Update resource and refresh tool discovery.

        Args:
            previous_config: The previous configuration (unused for stateless resource).

        Returns:
            ToolsMCPOutputs with updated tools and connection status.
        """
        return await self._build_outputs()

    async def on_delete(self) -> None:
        """Delete is a no-op since this resource is stateless."""
