# Ermes Backend

Public backend/API gateway for Ermes.

## Responsibilities

- expose a stable HTTP API for clients such as `ermes-frontend`;
- proxy non-streaming chat requests to `ermes-orchestrator`;
- proxy SSE chat streams without reconstructing the response;
- expose health and readiness endpoints;
- keep frontend-specific concerns outside `ermes-orchestrator`.

## Architecture

```text
ermes-frontend
      |
      | HTTP / SSE
      v
ermes-backend :8091
      |
      | private HTTP / SSE
      v
ermes-orchestrator :8090
```

## Requirements

- Python 3.12+
- Poetry 2.x
- Task
- Docker (optional)

## Install

```bash
task install
```

This executes:

```bash
poetry install --no-root
```

To generate or refresh the dependency lock file:

```bash
task lock
```

Commit `poetry.lock` once it has been generated.

## Run locally

```bash
task run
```

Development mode with reload:

```bash
task dev
```

Default environment:

```text
ERMES_ORCHESTRATOR_URL=http://localhost:8090
ERMES_ALLOWED_ORIGINS=http://localhost:5173
```

Override them when necessary:

```bash
export ERMES_ORCHESTRATOR_URL=http://localhost:8090
export ERMES_ALLOWED_ORIGINS=http://localhost:5173
task dev
```

## Quality tasks

```bash
task lint
task format
task test
task check
```

## Health

```bash
curl http://localhost:8091/health
```

## Readiness

Checks connectivity to the orchestrator:

```bash
curl http://localhost:8091/ready
```

## WebSocket chat

Connect to `ws://localhost:8091/v1/ws`, send `session.sync`, and wait for
`session.synced` before sending `message.commit`. Run `task test:ws-smoke` to
exercise the exchange against a running stack.

## Docker

Build:

```bash
task docker:build
```

Run:

```bash
task docker:run
```

The Docker image installs production dependencies directly from
`pyproject.toml` using Poetry. There is no `requirements.txt`.

For reproducible builds, generate `poetry.lock` with:

```bash
task lock
```

and commit it to the repository. Once a lock file is committed, the Dockerfile
can also be changed to copy it before `poetry install`.

## ermes-stack example

```yaml
backend:
  build:
    context: ../ermes-backend

  restart: unless-stopped

  environment:
    ERMES_ORCHESTRATOR_URL: http://orchestrator:8090
    ERMES_ALLOWED_ORIGINS: http://localhost:5173

  ports:
    - "8091:8091"

  depends_on:
    - orchestrator

  healthcheck:
    test:
      [
        "CMD",
        "python",
        "-c",
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8091/health', timeout=2)"
      ]
    interval: 10s
    timeout: 3s
    retries: 5
```

Adjust the Compose service name `orchestrator` if your `ermes-stack`
uses a different service name.
