"""GCP Cloud SQL user resource."""

from __future__ import annotations

import asyncio
import json
from typing import Any, ClassVar

from google.oauth2 import service_account
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from pragma_sdk import Config, Dependency, Field, Outputs, Resource

from gcp_provider.resources.cloudsql.database_instance import DatabaseInstance


class UserConfig(Config):
    """Configuration for a Cloud SQL user.

    Attributes:
        project_id: GCP project ID where the user will be created.
        credentials: GCP service account credentials JSON object or string.
        instance_name: Name of the Cloud SQL instance that hosts this user.
        username: Username for the database user.
        password: Password for the database user. Use Field[str] for secret injection.
        instance: Optional dependency on the database instance resource.
    """

    project_id: str
    credentials: dict[str, Any] | str
    instance_name: str
    username: str
    password: Field[str]
    instance: Dependency[DatabaseInstance] | None = None


class UserOutputs(Outputs):
    """Outputs from Cloud SQL user creation.

    Attributes:
        username: Username of the created user.
        host: Host pattern for the user (% for all hosts).
    """

    username: str
    host: str


class User(Resource[UserConfig, UserOutputs]):
    """GCP Cloud SQL user resource.

    Creates and manages database users within a Cloud SQL instance
    using user-provided service account credentials (multi-tenant SaaS pattern).

    Lifecycle:
        - on_create: Creates user in the instance
        - on_update: Updates user password if changed
        - on_delete: Deletes user
    """

    provider: ClassVar[str] = "gcp"
    resource: ClassVar[str] = "cloudsql/user"

    def _get_credentials(self) -> service_account.Credentials:
        """Get credentials from config."""
        creds_data = self.config.credentials

        if isinstance(creds_data, str):
            creds_data = json.loads(creds_data)

        return service_account.Credentials.from_service_account_info(creds_data)

    def _get_service(self) -> Any:
        """Get Cloud SQL Admin API service."""
        return discovery.build("sqladmin", "v1", credentials=self._get_credentials())

    async def _run_in_executor(self, func: Any) -> Any:
        """Run a blocking function in the default executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func)

    async def _get_user(self, service: Any) -> dict | None:
        """Get user if it exists, None otherwise."""
        try:
            request = service.users().list(
                project=self.config.project_id,
                instance=self.config.instance_name,
            )
            result = await self._run_in_executor(request.execute)

            for user in result.get("items", []):
                if user.get("name") == self.config.username:
                    return user

            return None
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise

    def _build_outputs(self, user: dict) -> UserOutputs:
        """Build outputs from user dict."""
        return UserOutputs(
            username=user.get("name", self.config.username),
            host=user.get("host", "%"),
        )

    async def on_create(self) -> UserOutputs:
        """Create user in the Cloud SQL instance.

        Idempotent: If user already exists, updates the password.

        Returns:
            UserOutputs with user details.
        """
        service = self._get_service()

        existing = await self._get_user(service)

        if existing is None:
            user_body = {
                "name": self.config.username,
                "password": self.config.password,
                "project": self.config.project_id,
                "instance": self.config.instance_name,
            }

            try:
                request = service.users().insert(
                    project=self.config.project_id,
                    instance=self.config.instance_name,
                    body=user_body,
                )
                await self._run_in_executor(request.execute)
            except HttpError as e:
                if "already exists" not in str(e).lower():
                    raise

            existing = await self._get_user(service)

            if existing is None:
                existing = {"name": self.config.username, "host": "%"}

        return self._build_outputs(existing)

    async def on_update(self, previous_config: UserConfig) -> UserOutputs:
        """Update user configuration.

        Username cannot be changed. Password changes are applied.

        Args:
            previous_config: The previous configuration before update.

        Returns:
            UserOutputs with current user state.

        Raises:
            ValueError: If immutable fields changed (requires delete + create).
        """
        if previous_config.project_id != self.config.project_id:
            msg = "Cannot change project_id; delete and recreate resource"
            raise ValueError(msg)

        if previous_config.instance_name != self.config.instance_name:
            msg = "Cannot change instance_name; delete and recreate resource"
            raise ValueError(msg)

        if previous_config.username != self.config.username:
            msg = "Cannot change username; delete and recreate resource"
            raise ValueError(msg)

        service = self._get_service()

        if previous_config.password != self.config.password:
            user_body = {
                "name": self.config.username,
                "password": self.config.password,
            }

            request = service.users().update(
                project=self.config.project_id,
                instance=self.config.instance_name,
                name=self.config.username,
                body=user_body,
            )
            await self._run_in_executor(request.execute)

        user = await self._get_user(service)

        if user is None:
            msg = f"User '{self.config.username}' not found"
            raise RuntimeError(msg)

        return self._build_outputs(user)

    async def on_delete(self) -> None:
        """Delete user.

        Idempotent: Succeeds if user doesn't exist.
        """
        service = self._get_service()

        try:
            request = service.users().delete(
                project=self.config.project_id,
                instance=self.config.instance_name,
                name=self.config.username,
            )
            await self._run_in_executor(request.execute)
        except HttpError as e:
            if e.resp.status != 404:
                raise
