"""Agno Agent resource - deploys AI agents to GKE via kubectl."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from agno.agent import Agent as AgnoAgent
from pragma_sdk import Config, Dependency, Outputs

from agno_provider.resources.base import AgnoResource, AgnoSpec
from agno_provider.resources.knowledge.knowledge import Knowledge, KnowledgeSpec
from agno_provider.resources.memory.manager import MemoryManager, MemoryManagerSpec
from agno_provider.resources.models.anthropic import (
    AnthropicModelOutputs,
    AnthropicModelSpec,
)
from agno_provider.resources.models.base import model_from_spec
from agno_provider.resources.models.openai import (
    OpenAIModelOutputs,
    OpenAIModelSpec,
)
from agno_provider.resources.prompt import Prompt, PromptSpec
from agno_provider.resources.tools.mcp import ToolsMCP, ToolsMCPOutputs, ToolsMCPSpec
from agno_provider.resources.tools.websearch import ToolsWebSearch, ToolsWebSearchOutputs, ToolsWebSearchSpec


if TYPE_CHECKING:
    from gcp_provider import GKE


class AgentSpec(AgnoSpec):
    """Specification for reconstructing an Agno Agent at runtime.

    Contains all necessary information to create an Agent instance
    with all nested dependencies. Used for deployment to containers
    where the agent needs to be reconstructed from serialized config.

    Attributes:
        name: Agent name.
        instructions: System instructions for the agent.
        model_spec: Nested spec for the model (OpenAI or Anthropic).
        knowledge_specs: List of nested knowledge specs for RAG.
        memory_spec: Optional nested spec for memory management.
        tools_specs: List of nested tool specs (MCP or WebSearch).
        prompt_spec: Optional nested prompt spec for instructions template.
    """

    name: str
    instructions: str | None = None
    model_spec: OpenAIModelSpec | AnthropicModelSpec
    knowledge_specs: list[KnowledgeSpec] = []
    memory_spec: MemoryManagerSpec | None = None
    tools_specs: list[ToolsMCPSpec | ToolsWebSearchSpec] = []
    prompt_spec: PromptSpec | None = None


class AgentConfig(Config):
    """Configuration for an Agno agent deployment.

    Attributes:
        cluster: GKE cluster dependency providing Kubernetes credentials.
        model: Model dependency (anthropic/messages or openai/chat) for agent LLM.
        embeddings: Optional embeddings dependency for RAG capabilities.
        vector_store: Optional vector store dependency (qdrant collection) for RAG.
        knowledges: Optional list of Knowledge dependencies for RAG.
        memory: Optional MemoryManager dependency for agent memory.
        tools: Optional list of tool dependencies (MCP or WebSearch).
        prompt: Optional Prompt dependency for instructions template.
        instructions: System instructions for the agent.
        image: Container image for the agent deployment.
        replicas: Number of agent replicas.
    """

    cluster: Dependency[GKE]
    model: Dependency
    embeddings: Dependency | None = None
    vector_store: Dependency | None = None
    knowledges: list[Dependency[Knowledge]] = []
    memory: Dependency[MemoryManager] | None = None
    tools: list[Dependency[ToolsMCP] | Dependency[ToolsWebSearch]] = []
    prompt: Dependency[Prompt] | None = None
    instructions: str | None = None
    image: str = "ghcr.io/agno-ai/agno:latest"
    replicas: int = 1


class AgentOutputs(Outputs):
    """Outputs from Agno agent deployment.

    Attributes:
        spec: Specification for reconstructing the agent at runtime.
        url: In-cluster URL for agent API.
    """

    spec: AgentSpec
    url: str


_POLL_INTERVAL_SECONDS = 5
_MAX_POLL_ATTEMPTS = 60


class Agent(AgnoResource[AgentConfig, AgentOutputs, AgentSpec]):
    """Agno AI agent deployed to GKE via kubectl.

    Deploys an Agno agent as a Kubernetes Deployment with a Service.
    Uses cluster credentials from the GKE dependency to authenticate
    with the Kubernetes API. Model, embeddings, and vector store URLs
    are passed as environment variables to the container.

    Lifecycle:
        - on_create: Apply Deployment + Service, wait for ready
        - on_update: Update Deployment with new config
        - on_delete: Delete Deployment and Service
    """

    provider: ClassVar[str] = "agno"
    resource: ClassVar[str] = "agent"

    @staticmethod
    def from_spec(spec: AgentSpec) -> AgnoAgent:
        """Factory: construct Agno Agent from spec.

        Builds all nested dependencies from their specs and constructs
        the Agent with all configured components.

        Args:
            spec: The agent specification.

        Returns:
            Configured Agno Agent instance.
        """
        model = model_from_spec(spec.model_spec)

        knowledge = None
        if spec.knowledge_specs:
            knowledge = Knowledge.from_spec(spec.knowledge_specs[0])

        memory_manager = None
        if spec.memory_spec:
            memory_manager = MemoryManager.from_spec(spec.memory_spec)

        tools: list[Any] = []
        for tool_spec in spec.tools_specs:
            if isinstance(tool_spec, ToolsMCPSpec):
                tools.append(ToolsMCP.from_spec(tool_spec))
            else:
                tools.append(ToolsWebSearch.from_spec(tool_spec))

        instructions = spec.instructions
        if spec.prompt_spec:
            instructions = Prompt.from_spec(spec.prompt_spec)

        return AgnoAgent(
            name=spec.name,
            model=model,
            knowledge=knowledge,
            memory_manager=memory_manager,
            tools=tools if tools else None,
            instructions=instructions,
        )

    def _get_deployment_name(self) -> str:
        """Get Kubernetes Deployment name based on resource name.

        Returns:
            The deployment name prefixed with 'agno-'.
        """
        return f"agno-{self.name}"

    def _get_namespace(self) -> str:
        """Get Kubernetes namespace.

        Returns:
            The namespace name.
        """
        return "default"

    async def _get_kubeconfig(self) -> str:
        """Build kubeconfig from GKE cluster credentials.

        Returns:
            Kubeconfig content as string.

        Raises:
            RuntimeError: If GKE cluster outputs are not available.
        """
        cluster = await self.config.cluster.resolve()
        outputs = cluster.outputs
        if outputs is None:
            msg = "GKE cluster outputs not available"
            raise RuntimeError(msg)

        kubeconfig = f"""
apiVersion: v1
kind: Config
clusters:
- name: gke-cluster
  cluster:
    server: https://{outputs.endpoint}
    certificate-authority-data: {outputs.cluster_ca_certificate}
contexts:
- name: gke-context
  context:
    cluster: gke-cluster
    user: gke-user
current-context: gke-context
users:
- name: gke-user
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gke-gcloud-auth-plugin
      installHint: Install gke-gcloud-auth-plugin for kubectl auth
      provideClusterInfo: true
"""
        return kubeconfig

    async def _get_env_vars(self) -> list[dict[str, str]]:
        """Build environment variables for the agent container.

        Resolves model, embeddings, and vector_store dependencies
        to extract their URLs.

        Returns:
            List of env var dicts with name and value keys.
        """
        env_vars: list[dict[str, str]] = []

        model = await self.config.model.resolve()
        if model.outputs is not None and hasattr(model.outputs, "url"):
            env_vars.append({"name": "AGNO_MODEL_URL", "value": model.outputs.url})

        if self.config.embeddings is not None:
            embeddings = await self.config.embeddings.resolve()
            if embeddings.outputs is not None and hasattr(embeddings.outputs, "url"):
                env_vars.append({"name": "AGNO_EMBEDDINGS_URL", "value": embeddings.outputs.url})

        if self.config.vector_store is not None:
            vector_store = await self.config.vector_store.resolve()
            if vector_store.outputs is not None and hasattr(vector_store.outputs, "url"):
                env_vars.append({"name": "AGNO_VECTOR_STORE_URL", "value": vector_store.outputs.url})

        if self.config.instructions:
            env_vars.append({"name": "AGNO_INSTRUCTIONS", "value": self.config.instructions})

        return env_vars

    def _build_deployment_manifest(self, env_vars: list[dict[str, str]]) -> dict[str, Any]:
        """Build Kubernetes Deployment manifest.

        Args:
            env_vars: Environment variables for the container.

        Returns:
            Deployment manifest as dict.
        """
        deployment_name = self._get_deployment_name()
        namespace = self._get_namespace()

        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": deployment_name,
                "namespace": namespace,
                "labels": {
                    "app": deployment_name,
                    "pragma.io/provider": "agno",
                    "pragma.io/resource": "agent",
                    "pragma.io/name": self.name,
                },
            },
            "spec": {
                "replicas": self.config.replicas,
                "selector": {
                    "matchLabels": {
                        "app": deployment_name,
                    },
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": deployment_name,
                        },
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "agent",
                                "image": self.config.image,
                                "ports": [{"containerPort": 8080}],
                                "env": env_vars,
                                "readinessProbe": {
                                    "httpGet": {
                                        "path": "/health",
                                        "port": 8080,
                                    },
                                    "initialDelaySeconds": 5,
                                    "periodSeconds": 10,
                                },
                                "livenessProbe": {
                                    "httpGet": {
                                        "path": "/health",
                                        "port": 8080,
                                    },
                                    "initialDelaySeconds": 15,
                                    "periodSeconds": 20,
                                },
                            },
                        ],
                    },
                },
            },
        }

    def _build_service_manifest(self) -> dict[str, Any]:
        """Build Kubernetes Service manifest.

        Returns:
            Service manifest as dict.
        """
        deployment_name = self._get_deployment_name()
        namespace = self._get_namespace()

        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": deployment_name,
                "namespace": namespace,
                "labels": {
                    "app": deployment_name,
                    "pragma.io/provider": "agno",
                    "pragma.io/resource": "agent",
                    "pragma.io/name": self.name,
                },
            },
            "spec": {
                "selector": {
                    "app": deployment_name,
                },
                "ports": [
                    {
                        "port": 80,
                        "targetPort": 8080,
                        "protocol": "TCP",
                    },
                ],
                "type": "ClusterIP",
            },
        }

    async def _run_command(self, cmd: list[str], kubeconfig_path: str, name: str) -> subprocess.CompletedProcess:
        """Run a CLI command with kubeconfig.

        Args:
            cmd: Full command with arguments.
            kubeconfig_path: Path to kubeconfig file.
            name: Command name for error messages.

        Returns:
            Completed process result.

        Raises:
            RuntimeError: If command fails.
        """
        env = {"KUBECONFIG": kubeconfig_path, "PATH": os.environ.get("PATH", "")}

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            ),
        )

        if result.returncode != 0:
            msg = f"{name} command failed: {result.stderr}"
            raise RuntimeError(msg)

        return result

    async def _run_kubectl(self, args: list[str], kubeconfig_path: str) -> subprocess.CompletedProcess:
        """Run kubectl command with kubeconfig.

        Args:
            args: kubectl arguments.
            kubeconfig_path: Path to kubeconfig file.

        Returns:
            Completed process result.
        """
        return await self._run_command(["kubectl", *args], kubeconfig_path, "kubectl")

    async def _apply_manifest(self, manifest: dict[str, Any], kubeconfig_path: str) -> None:
        """Apply a Kubernetes manifest via kubectl.

        Args:
            manifest: Kubernetes manifest as dict.
            kubeconfig_path: Path to kubeconfig file.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(manifest, f)
            manifest_path = f.name

        try:
            await self._run_kubectl(["apply", "-f", manifest_path], kubeconfig_path)
        finally:
            Path(manifest_path).unlink(missing_ok=True)

    async def _delete_resource(self, kind: str, name: str, kubeconfig_path: str) -> None:
        """Delete a Kubernetes resource.

        Args:
            kind: Resource kind (e.g., "deployment", "service").
            name: Resource name.
            kubeconfig_path: Path to kubeconfig file.
        """
        namespace = self._get_namespace()
        try:
            await self._run_kubectl(
                ["delete", kind, name, "-n", namespace, "--ignore-not-found"],
                kubeconfig_path,
            )
        except RuntimeError:
            pass

    async def _wait_for_ready(self, kubeconfig_path: str) -> bool:
        """Wait for Deployment to be ready.

        Args:
            kubeconfig_path: Path to kubeconfig file.

        Returns:
            True when Deployment is ready.

        Raises:
            TimeoutError: If Deployment doesn't become ready in time.
        """
        namespace = self._get_namespace()
        deployment_name = self._get_deployment_name()

        for _ in range(_MAX_POLL_ATTEMPTS):
            try:
                result = await self._run_kubectl(
                    [
                        "get",
                        "deployment",
                        deployment_name,
                        "-n",
                        namespace,
                        "-o",
                        "jsonpath={.status.readyReplicas}",
                    ],
                    kubeconfig_path,
                )
                ready_replicas = int(result.stdout.strip()) if result.stdout.strip() else 0
                if ready_replicas >= self.config.replicas:
                    return True
            except (RuntimeError, ValueError):
                pass

            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

        msg = f"Deployment {deployment_name} did not become ready within {_MAX_POLL_ATTEMPTS * _POLL_INTERVAL_SECONDS}s"
        raise TimeoutError(msg)

    def _dependency_changed(self, prev: Dependency | None, curr: Dependency | None) -> bool:
        """Check if an optional dependency changed.

        Args:
            prev: Previous dependency (may be None).
            curr: Current dependency (may be None).

        Returns:
            True if the dependency changed (added, removed, or different ID).
        """
        if (prev is None) != (curr is None):
            return True

        if prev is not None and curr is not None and prev.id != curr.id:
            return True

        return False

    def _list_dependencies_changed(self, prev: list[Dependency], curr: list[Dependency]) -> bool:
        """Check if a list of dependencies changed.

        Args:
            prev: Previous list of dependencies.
            curr: Current list of dependencies.

        Returns:
            True if the list changed (different length or different IDs).
        """
        if len(prev) != len(curr):
            return True

        prev_ids = {dep.id for dep in prev}
        curr_ids = {dep.id for dep in curr}

        return prev_ids != curr_ids

    async def _build_spec(self) -> AgentSpec:
        """Build spec from resolved dependencies.

        Creates a specification that can be serialized and used to
        reconstruct the agent at runtime. Extracts nested specs from
        all resolved dependency outputs.

        Returns:
            AgentSpec with all nested specs from dependencies.

        Raises:
            RuntimeError: If model dependency is not resolved or has no spec.
        """
        model = await self.config.model.resolve()
        model_outputs = model.outputs

        if model_outputs is None:
            msg = "Model dependency not resolved"
            raise RuntimeError(msg)

        model_spec: OpenAIModelSpec | AnthropicModelSpec
        if isinstance(model_outputs, OpenAIModelOutputs):
            model_spec = model_outputs.spec
        elif isinstance(model_outputs, AnthropicModelOutputs):
            model_spec = model_outputs.spec
        else:
            msg = f"Unsupported model outputs type: {type(model_outputs)}"
            raise RuntimeError(msg)

        knowledge_specs: list[KnowledgeSpec] = []
        for kb_dep in self.config.knowledges:
            kb = await kb_dep.resolve()
            if kb.outputs is not None:
                knowledge_specs.append(kb.outputs.spec)

        memory_spec: MemoryManagerSpec | None = None
        if self.config.memory is not None:
            memory = await self.config.memory.resolve()
            if memory.outputs is not None:
                memory_spec = memory.outputs.spec

        tools_specs: list[ToolsMCPSpec | ToolsWebSearchSpec] = []
        for tool_dep in self.config.tools:
            tool = await tool_dep.resolve()
            if tool.outputs is not None:
                if isinstance(tool.outputs, ToolsMCPOutputs):
                    tools_specs.append(tool.outputs.spec)
                elif isinstance(tool.outputs, ToolsWebSearchOutputs):
                    tools_specs.append(tool.outputs.spec)

        prompt_spec: PromptSpec | None = None
        if self.config.prompt is not None:
            prompt = await self.config.prompt.resolve()
            if prompt.outputs is not None:
                prompt_spec = prompt.outputs.spec

        return AgentSpec(
            name=self.name,
            instructions=self.config.instructions,
            model_spec=model_spec,
            knowledge_specs=knowledge_specs,
            memory_spec=memory_spec,
            tools_specs=tools_specs,
            prompt_spec=prompt_spec,
        )

    async def _build_outputs(self) -> AgentOutputs:
        """Build outputs with in-cluster service URL and spec.

        Returns:
            AgentOutputs with the service URL and spec.
        """
        deployment_name = self._get_deployment_name()
        namespace = self._get_namespace()

        url = f"http://{deployment_name}.{namespace}.svc.cluster.local"
        spec = await self._build_spec()

        return AgentOutputs(
            spec=spec,
            url=url,
        )

    async def on_create(self) -> AgentOutputs:
        """Deploy Agno agent to GKE via kubectl.

        Idempotent: Uses kubectl apply which handles both
        initial creation and updates.

        Returns:
            AgentOutputs with in-cluster service URL and spec.
        """
        kubeconfig = await self._get_kubeconfig()
        env_vars = await self._get_env_vars()

        deployment = self._build_deployment_manifest(env_vars)
        service = self._build_service_manifest()

        with tempfile.TemporaryDirectory() as tmpdir:
            kubeconfig_path = Path(tmpdir) / "kubeconfig"
            kubeconfig_path.write_text(kubeconfig)

            await self._apply_manifest(deployment, str(kubeconfig_path))
            await self._apply_manifest(service, str(kubeconfig_path))
            await self._wait_for_ready(str(kubeconfig_path))

        return await self._build_outputs()

    async def on_update(self, previous_config: AgentConfig) -> AgentOutputs:
        """Update Agno agent deployment.

        Args:
            previous_config: The previous configuration before update.

        Returns:
            AgentOutputs with in-cluster service URL and spec.

        Raises:
            ValueError: If cluster dependency changed (immutable field).
        """
        if previous_config.cluster.id != self.config.cluster.id:
            msg = "Cannot change cluster; delete and recreate resource"
            raise ValueError(msg)

        if self.outputs is not None:
            previous_dict = previous_config.model_dump(
                exclude={"cluster", "model", "embeddings", "vector_store", "knowledges", "memory", "tools", "prompt"}
            )
            current_dict = self.config.model_dump(
                exclude={"cluster", "model", "embeddings", "vector_store", "knowledges", "memory", "tools", "prompt"}
            )
            deps_changed = (
                previous_config.model.id != self.config.model.id
                or self._dependency_changed(previous_config.embeddings, self.config.embeddings)
                or self._dependency_changed(previous_config.vector_store, self.config.vector_store)
                or self._dependency_changed(previous_config.memory, self.config.memory)
                or self._dependency_changed(previous_config.prompt, self.config.prompt)
                or self._list_dependencies_changed(previous_config.knowledges, self.config.knowledges)
                or self._list_dependencies_changed(previous_config.tools, self.config.tools)
            )

            if previous_dict == current_dict and not deps_changed:
                return self.outputs

        kubeconfig = await self._get_kubeconfig()
        env_vars = await self._get_env_vars()

        deployment = self._build_deployment_manifest(env_vars)
        service = self._build_service_manifest()

        with tempfile.TemporaryDirectory() as tmpdir:
            kubeconfig_path = Path(tmpdir) / "kubeconfig"
            kubeconfig_path.write_text(kubeconfig)

            await self._apply_manifest(deployment, str(kubeconfig_path))
            await self._apply_manifest(service, str(kubeconfig_path))
            await self._wait_for_ready(str(kubeconfig_path))

        return await self._build_outputs()

    async def on_delete(self) -> None:
        """Delete Agno agent Deployment and Service.

        Idempotent: Succeeds if resources don't exist.
        """
        kubeconfig = await self._get_kubeconfig()
        deployment_name = self._get_deployment_name()

        with tempfile.TemporaryDirectory() as tmpdir:
            kubeconfig_path = Path(tmpdir) / "kubeconfig"
            kubeconfig_path.write_text(kubeconfig)

            await self._delete_resource("deployment", deployment_name, str(kubeconfig_path))
            await self._delete_resource("service", deployment_name, str(kubeconfig_path))
