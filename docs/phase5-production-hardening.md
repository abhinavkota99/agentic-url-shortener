# Phase 5: Production hardening

## Included
- Bearer API-key authentication. Keys are configured as JSON in `ORCHESTRATOR_API_KEYS`; only SHA-256 digests are retained in process memory.
- RBAC roles: `admin`, `developer`, `reviewer`, `viewer`.
- Tenant isolation: workflow owner is recorded at creation; non-admin users can only read or mutate their own workflows. Cross-tenant reads return 404.
- Redis fixed-window rate limiting per authenticated subject. The production Compose configuration fails closed if Redis is unavailable.
- Prometheus-compatible HTTP request counters and latency histograms at `/metrics` (admin role required).
- `/health` liveness and `/ready` PostgreSQL/Redis dependency checks.
- Durable host workspace directory in the recommended local mode; the optional containerized API uses a named workspace volume. PostgreSQL and Redis use persistent volumes.
- Input validation for replan requirements and commit messages.

## Configure and run

Use the Phase 6 runbook for the supported local deployment topology. In this topology, Docker Compose starts PostgreSQL, Redis, the Spring Boot backend, Prometheus and Grafana, while the LangGraph orchestrator runs as a host Python process so it can invoke the restricted Docker Maven QA runner without mounting the host Docker socket into the API container.

```bash
python scripts/bootstrap.py
python scripts/warm_maven_cache.py
docker compose up -d postgres redis backend prometheus grafana
cd orchestrator
python -m venv .venv
# Activate the virtual environment, then:
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The optional Compose profile `containerized-api` is intended for API-only evaluation. It does not receive Docker daemon access, so sandbox QA is blocked in that mode. Do not mount the host Docker socket into an internet-facing API container.

The bootstrap script creates separate admin, developer, reviewer and viewer keys, a database password, a Grafana password, and the Prometheus metrics token. Developer and reviewer identities share the same tenant subject in the local setup. Use the generated keys in the `Authorization: Bearer <key>` header.

## Metrics and probes
- `GET /health`: process liveness.
- `GET /ready`: checks PostgreSQL and Redis.
- `GET /metrics`: Prometheus exposition format; requires an admin bearer key. Configure Prometheus with an Authorization bearer credential for a dedicated admin key. Protect the metrics route at the network layer as well.

## Security and operational notes
- API keys are long-lived shared secrets in environment configuration. Use a secrets manager in production, rotate keys, and never commit `.env`.
- This starter does not include an API-key issuance/revocation UI, OIDC/JWT federation, per-resource delegated approvals, or immutable audit storage.
- Redis rate limits use a fixed one-minute window and are per subject. A burst can occur at a window boundary.
- In the recommended host-run mode, workspaces are persisted under `.agentic-workspaces`; back up that directory and PostgreSQL. The optional containerized API uses a named workspace volume. Implement retention/garbage collection before high-volume deployment.
- The local Compose database password fallback is for development only. Supply a strong secret in production.
- The workflow JSON payload store still uses full-record updates. Concurrent mutation of the same workflow should be serialized by a job/worker layer before multi-replica production rollout.
- `/metrics` is role-protected but an admin key should be dedicated to scraping and not reused by humans.
- The existing Maven sandbox needs Docker CLI and a deliberately provisioned Docker execution boundary. Do not mount the host Docker socket into an internet-facing API container without a separate security review.
- TLS termination, WAF/network policy, secrets manager integration, backup/restore drills, database migrations, and external log aggregation remain deployment responsibilities.
