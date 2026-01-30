"""GCP Cloud SQL database resource."""

from __future__ import annotations

import asyncio
import json
from typing import Any, ClassVar

from google.oauth2 import service_account
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from pragma_sdk import Config, Dependency, Outputs, Resource

from gcp_provider.resources.cloudsql.database_instance import DatabaseInstance


class DatabaseConfig(Config):
    """Configuration for a Cloud SQL database.

    Attributes:
        project_id: GCP project ID where the database will be created.
        credentials: GCP service account credentials JSON object or string.
        instance_name: Name of the Cloud SQL instance that hosts this database.
        database_name: Name of the database to create.
        instance: Optional dependency on the database instance resource.
    """

    project_id: str
    credentials: dict[str, Any] | str
    instance_name: str
    database_name: str
    instance: Dependency[DatabaseInstance] | None = None


class DatabaseOutputs(Outputs):
    """Outputs from Cloud SQL database creation.

    Attributes:
        database_name: Name of the created database.
        url: Connection URL format (without credentials).
    """

    database_name: str
    url: str


class Database(Resource[DatabaseConfig, DatabaseOutputs]):
    """GCP Cloud SQL database resource.

    Creates and manages databases within a Cloud SQL instance
    using user-provided service account credentials (multi-tenant SaaS pattern).

    Lifecycle:
        - on_create: Creates database in the instance
        - on_update: Limited updates (name change requires recreation)
        - on_delete: Deletes database
    """

    provider: ClassVar[str] = "gcp"
    resource: ClassVar[str] = "cloudsql/database"

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

    async def _get_database(self, service: Any) -> dict | None:
        """Get database if it exists, None otherwise."""
        try:
            request = service.databases().get(
                project=self.config.project_id,
                instance=self.config.instance_name,
                database=self.config.database_name,
            )
            return await self._run_in_executor(request.execute)
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise

    async def _get_instance(self, service: Any) -> dict | None:
        """Get instance to extract connection info."""
        try:
            request = service.instances().get(
                project=self.config.project_id,
                instance=self.config.instance_name,
            )
            return await self._run_in_executor(request.execute)
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise

    def _build_outputs(self, instance: dict) -> DatabaseOutputs:
        """Build outputs from instance dict."""
        public_ip = None
        private_ip = None
        for ip_addr in instance.get("ipAddresses", []):
            match ip_addr.get("type"):
                case "PRIMARY":
                    public_ip = ip_addr.get("ipAddress")
                case "PRIVATE":
                    private_ip = ip_addr.get("ipAddress")

        database_version = instance.get("databaseVersion", "POSTGRES_15")

        match database_version.split("_")[0]:
            case "POSTGRES":
                db_type, port = "postgresql", "5432"
            case "MYSQL":
                db_type, port = "mysql", "3306"
            case "SQLSERVER":
                db_type, port = "sqlserver", "1433"
            case _:
                db_type, port = "postgresql", "5432"

        connection_name = f"{self.config.project_id}:{instance.get('region')}:{self.config.instance_name}"
        host = public_ip or private_ip or connection_name
        url = f"{db_type}://USER:PASSWORD@{host}:{port}/{self.config.database_name}"

        return DatabaseOutputs(
            database_name=self.config.database_name,
            url=url,
        )

    async def on_create(self) -> DatabaseOutputs:
        """Create database in the Cloud SQL instance.

        Idempotent: If database already exists, returns its current state.

        Returns:
            DatabaseOutputs with database details.
        """
        service = self._get_service()

        existing = await self._get_database(service)

        if existing is None:
            database_body = {
                "name": self.config.database_name,
                "project": self.config.project_id,
                "instance": self.config.instance_name,
            }

            try:
                request = service.databases().insert(
                    project=self.config.project_id,
                    instance=self.config.instance_name,
                    body=database_body,
                )
                await self._run_in_executor(request.execute)
            except HttpError as e:
                if "already exists" not in str(e).lower():
                    raise

        instance = await self._get_instance(service)

        if instance is None:
            msg = f"Instance '{self.config.instance_name}' not found"
            raise RuntimeError(msg)

        return self._build_outputs(instance)

    async def on_update(self, previous_config: DatabaseConfig) -> DatabaseOutputs:
        """Update database configuration.

        Database names cannot be changed. This method validates
        that immutable fields haven't changed and returns current state.

        Args:
            previous_config: The previous configuration before update.

        Returns:
            DatabaseOutputs with current database state.

        Raises:
            ValueError: If immutable fields changed (requires delete + create).
        """
        if previous_config.project_id != self.config.project_id:
            msg = "Cannot change project_id; delete and recreate resource"
            raise ValueError(msg)

        if previous_config.instance_name != self.config.instance_name:
            msg = "Cannot change instance_name; delete and recreate resource"
            raise ValueError(msg)

        if previous_config.database_name != self.config.database_name:
            msg = "Cannot change database_name; delete and recreate resource"
            raise ValueError(msg)

        if self.outputs is not None:
            return self.outputs

        service = self._get_service()
        instance = await self._get_instance(service)

        if instance is None:
            msg = f"Instance '{self.config.instance_name}' not found"
            raise RuntimeError(msg)

        return self._build_outputs(instance)

    async def on_delete(self) -> None:
        """Delete database.

        Idempotent: Succeeds if database doesn't exist.
        """
        service = self._get_service()

        try:
            request = service.databases().delete(
                project=self.config.project_id,
                instance=self.config.instance_name,
                database=self.config.database_name,
            )
            await self._run_in_executor(request.execute)
        except HttpError as e:
            if e.resp.status != 404:
                raise
