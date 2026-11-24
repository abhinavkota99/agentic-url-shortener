# Agentic Software Engineering Platform - URL Shortener

A cumulative six-phase project containing:

- `backend/`: Java 21 / Spring Boot URL shortener with PostgreSQL, Redis caching and click analytics.
- `orchestrator/`: Python / LangGraph SDLC orchestration with agents, DAG tasks, human approval, persistence, constrained code generation, sandbox QA and bounded self-correction.
- `monitoring/`: Prometheus and Grafana provisioning.
- `scripts/`: bootstrap, local launch, Maven cache warm-up, validation and smoke tests.
- `.github/workflows/ci.yml`: CI pipeline including end-to-end workflow validation.

**Download and run the Phase 6 archive only.** It contains the cumulative project from Phases 1 through 6. Do not combine older phase ZIPs.

## Quick start

Prerequisites: Docker Desktop / Docker Engine with Compose, Python 3.11 (the Windows launcher explicitly selects it), Git, and internet access for first-time image/dependency downloads. Java and Maven are not required on the host.

1. Extract the Phase 6 ZIP and open a terminal in the project root.
2. Run the platform launcher:

   - Windows PowerShell: `./scripts/run_local.ps1`
   - macOS/Linux: `bash scripts/run_local.sh`

   The launcher creates local credentials if needed, warms the Maven cache, starts PostgreSQL, Redis, Spring Boot, Prometheus and Grafana, creates a Python virtual environment, installs dependencies and starts the host orchestrator.

3. In a second terminal, activate the virtual environment and run validation:

   ```bash
   # macOS/Linux
   source orchestrator/.venv/bin/activate

   # Windows PowerShell
   # .\orchestrator\.venv\Scripts\Activate.ps1

   python scripts/validate_project.py
   python scripts/smoke_test.py
   python scripts/smoke_test.py --workflow --workflow-timeout 900
   ```

The full workflow smoke test exercises human approval, code generation, Docker-based Maven QA, Git diff and audit verification. It can take several minutes.

## Service URLs

| Service | URL |
|---|---|
| Spring Boot API | http://localhost:8080 |
| Spring Boot OpenAPI | http://localhost:8080/swagger-ui.html |
| Orchestrator API docs | http://localhost:8000/docs |
| Orchestrator health | http://localhost:8000/health |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Bootstrap prints the admin, developer, reviewer and viewer API keys plus the Grafana password. Save them securely. Production-mode orchestrator requests require `Authorization: Bearer <api-key>`.

## Manual setup

See [`docs/phase6-runbook.md`](docs/phase6-runbook.md) for complete Windows, macOS and Linux instructions, manual commands, API examples, troubleshooting and stop/restart steps.

## Architecture and security notes

- Human approval is required before implementation.
- Agent-generated changes are restricted to isolated Git workspaces and allowlisted source/test paths.
- Maven tests run in a fixed-command Docker container with networking disabled, a read-only root filesystem and resource limits.
- The recommended local topology runs the orchestrator on the host so it can invoke Docker without mounting the host Docker socket into the API container.
- The optional Compose profile `containerized-api` is for API-only evaluation; its QA sandbox cannot access the host Docker daemon.
- The project is not a turnkey production deployment. Before production use, add managed secrets, OIDC/federated identity, TLS/WAF/network policies, immutable audit storage, workspace retention, backup/restore drills and a multi-replica worker/locking strategy.

See `docs/` for architecture, decisions, security, API specifications and phase runbooks.
