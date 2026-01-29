# Qdrant Provider

Qdrant vector database provider for Pragmatiks.

## Resources

### database

Deploys a Qdrant database to a GKE cluster with external LoadBalancer access.

```yaml
provider: qdrant
resource: database
name: my-qdrant
config:
  cluster:
    provider: gcp
    resource: gke
    name: my-cluster
  replicas: 1
  generate_api_key: true
  storage:
    size: 20Gi
    class: premium-rwo
  resources:
    memory: 4Gi
    cpu: "2"
```

#### Configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cluster` | `Dependency[GKE]` | Yes | GKE cluster to deploy to |
| `replicas` | `int` | No | Number of replicas (default: `1`) |
| `api_key` | `str` | No | API key for authentication (mutually exclusive with `generate_api_key`) |
| `generate_api_key` | `bool` | No | Generate a secure 32-char API key (default: `false`) |
| `storage` | `StorageConfig` | No | Persistent storage configuration |
| `resources` | `ResourceConfig` | No | CPU and memory limits |

#### StorageConfig

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `size` | `str` | No | Volume size (default: `10Gi`) |
| `class` | `str` | No | Storage class (default: `standard-rwo`) |

#### ResourceConfig

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `memory` | `str` | No | Memory limit (default: `2Gi`) |
| `cpu` | `str` | No | CPU limit (default: `1`) |

#### Outputs

| Field | Type | Description |
|-------|------|-------------|
| `url` | `str` | HTTP endpoint (e.g., `http://34.x.x.x:6333`) |
| `grpc_url` | `str` | gRPC endpoint (e.g., `http://34.x.x.x:6334`) |
| `api_key` | `str \| None` | API key if configured |
| `ready` | `bool` | Whether database is ready |

---

### collection

Manages Qdrant vector collections.

```yaml
apiVersion: qdrant/v1
kind: collection
metadata:
  name: company-docs
  namespace: demo
spec:
  api_key: $ref{qdrant-secret.data.api_key}  # Optional for local
  url: https://xyz.qdrant.io:6333  # Or http://localhost:6333
  name: company-docs
  vectors:
    size: 1536
    distance: Cosine  # Cosine, Euclid, Dot
  on_disk: true  # Optional
```

## Configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `api_key` | `Field[str]` | No | API key for Qdrant Cloud (optional for local) |
| `url` | `str` | No | Qdrant server URL (default: `http://localhost:6333`) |
| `name` | `str` | Yes | Collection name |
| `vectors` | `VectorConfig` | Yes | Vector configuration |
| `on_disk` | `bool` | No | Store vectors on disk (default: `false`) |

### VectorConfig

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `size` | `int` | Yes | Vector dimension |
| `distance` | `str` | No | Distance metric: `Cosine`, `Euclid`, `Dot` (default: `Cosine`) |

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Collection name |
| `indexed_vectors_count` | `int` | Number of indexed vectors |
| `points_count` | `int` | Number of points in collection |
| `status` | `str` | Collection status (`green`, `yellow`, `red`) |

## Lifecycle

- **on_create**: Creates collection if it doesn't exist
- **on_update**: Recreates collection if vector config changes (destructive)
- **on_delete**: Deletes collection

## Installation

```bash
pip install pragmatiks-qdrant-provider
```

## Development

```bash
# Run tests
task qdrant:test

# Format code
task qdrant:format

# Lint and type check
task qdrant:check
```
