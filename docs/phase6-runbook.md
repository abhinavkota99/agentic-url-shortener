# Phase 6: Complete local runbook and end-to-end validation

## Which project should be downloaded?
Download and run **Phase 6** only. It is the cumulative project snapshot containing Phases 1 through 6. Do not combine files from the older phase ZIPs.

## Recommended execution topology
- Docker Compose: PostgreSQL, Redis, Spring Boot backend, Prometheus, Grafana.
- Host Python process: LangGraph orchestrator.
- Host Docker CLI: launches the restricted, network-disabled Maven QA container.

The orchestrator runs on the host in the recommended mode so the QA sandbox can use the local Docker daemon without mounting `/var/run/docker.sock` into the API container. The optional `containerized-api` Compose profile is for API-only evaluation; it does not receive Docker daemon access, so sandbox QA will be reported as blocked in that mode.

## Prerequisites
- Docker Desktop (Windows/macOS) or Docker Engine + Compose plugin (Linux), running.
- Python 3.11 or newer.
- Git.
- Internet access for initial image and Maven dependency downloads.
- Optional OpenAI API key for LLM-backed requirement/code-generation/correction agents. Deterministic fallback behavior is available without it.

Java and Maven do not need to be installed on the host for the recommended workflow: backend compilation runs in its Docker build image, and agent QA runs in a separate Maven container.

## First-time setup (all operating systems)
1. Extract the Phase 6 ZIP.
2. Open a terminal in the extracted `agentic-url-shortener` directory.
3. Run:
   ```bash
   python scripts/bootstrap.py
   ```
   This creates a root `.env` containing unique local database, Grafana and API-key credentials, and creates `monitoring/metrics_token`. Save the printed API keys and Grafana password. The script refuses to overwrite an existing `.env`.
4. Optionally add your `OPENAI_API_KEY` to `.env`. Leave it empty to use deterministic fallback agents.
5. Start the stack using the operating-system instructions below.

## Windows (PowerShell)
From the project root:
```powershell
.\scripts\run_local.ps1
```
The script bootstraps secrets if needed, warms Maven dependencies, starts the infrastructure and Spring Boot services, creates a Python virtual environment, installs dependencies, and starts the orchestrator.

If PowerShell blocks script execution, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\run_local.ps1
```

## macOS / Linux
From the project root:
```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

## Manual startup (if you prefer separate terminals)

### Terminal 1: start infrastructure and backend
```bash
python scripts/bootstrap.py   # only if .env does not exist
python scripts/warm_maven_cache.py
docker compose up -d postgres redis backend prometheus grafana
docker compose ps
```
Wait until PostgreSQL, Redis and the backend are healthy. Backend health:
```bash
curl http://localhost:8080/actuator/health
```

### Terminal 2: install and start the orchestrator
```bash
cd orchestrator
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
The application loads the root `.env` automatically.

## Service URLs
| Service | URL | Authentication |
|---|---|---|
| Spring Boot API | http://localhost:8080 | No API key in this demo |
| Spring Boot OpenAPI | http://localhost:8080/swagger-ui.html | No API key in this demo |
| Orchestrator API docs | http://localhost:8000/docs | Endpoint calls require bearer keys |
| Orchestrator liveness | http://localhost:8000/health | Public |
| Orchestrator readiness | http://localhost:8000/ready | Public |
| Prometheus | http://localhost:9090 | Localhost-bound |
| Grafana | http://localhost:3000 | User `admin`, generated password in bootstrap output |

## Run validation and smoke tests
In a second terminal, activate the virtual environment created by the launcher:
```bash
# macOS/Linux
source orchestrator/.venv/bin/activate
# Windows PowerShell
# .\orchestrator\.venv\Scripts\Activate.ps1
```
Run the static checks and focused Python tests:
```bash
python scripts/validate_project.py
```
Run the backend and orchestrator API smoke checks:
```bash
python scripts/smoke_test.py
```
Run the complete agent workflow, including human approval, code generation, Docker Maven QA, Git diff and audit verification:
```bash
python scripts/smoke_test.py --workflow --workflow-timeout 900
```
The complete workflow can take several minutes. The first Maven cache warm-up needs internet access; the actual QA container runs with network access disabled.

## Use the platform manually

### 1. Create a workflow
Use the developer API key printed by bootstrap:
```bash
curl -X POST http://localhost:8000/api/workflows \
  -H "Authorization: Bearer <DEVELOPER_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"requirement":"Add URL expiration update support with validation and unit tests","scenario":"GREENFIELD","autonomyLevel":"CONTROLLED"}'
```
The response contains the `workflow.id` and should have status `WAITING_FOR_APPROVAL`.

### 2. Inspect the plan and audit
```bash
curl -H "Authorization: Bearer <DEVELOPER_API_KEY>" http://localhost:8000/api/workflows/<WORKFLOW_ID>
curl -H "Authorization: Bearer <DEVELOPER_API_KEY>" http://localhost:8000/api/workflows/<WORKFLOW_ID>/tasks
curl -H "Authorization: Bearer <DEVELOPER_API_KEY>" http://localhost:8000/api/workflows/<WORKFLOW_ID>/artifacts
curl -H "Authorization: Bearer <DEVELOPER_API_KEY>" http://localhost:8000/api/workflows/<WORKFLOW_ID>/audit
```

### 3. Approve the design
Use the reviewer API key:
```bash
curl -X POST http://localhost:8000/api/workflows/<WORKFLOW_ID>/approve \
  -H "Authorization: Bearer <REVIEWER_API_KEY>"
```
Approval resumes implementation, sandbox QA, bounded correction (when configured and actionable), documentation and release assessment.

### 4. Review generated changes
```bash
curl -H "Authorization: Bearer <DEVELOPER_API_KEY>" http://localhost:8000/api/workflows/<WORKFLOW_ID>/diff
```
Only after the workflow status is `COMPLETED`:
```bash
curl -X POST http://localhost:8000/api/workflows/<WORKFLOW_ID>/commit \
  -H "Authorization: Bearer <DEVELOPER_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"message":"feat: reviewed agent-generated change"}'
```
This creates a local Git commit in the isolated workspace. It does not push or deploy.

## Stop and restart
Stop containers but preserve data:
```bash
docker compose down
```
Restart:
```bash
docker compose up -d postgres redis backend prometheus grafana
```
The orchestrator runs separately in its terminal. Stop it with Ctrl+C.

To delete all local database/cache/workspace data (destructive):
```bash
docker compose down -v
```
The `.agentic-workspaces` folder and `.m2` cache are host directories and are not deleted by `down -v`.

## Troubleshooting
- **Compose says `ORCHESTRATOR_API_KEYS` is missing:** run `python scripts/bootstrap.py` from the project root and verify `.env` exists.
- **Prometheus cannot read metrics token:** verify `monitoring/metrics_token` exists and contains the admin API key printed by bootstrap.
- **Orchestrator returns 503 from `/ready`:** check `docker compose ps`, PostgreSQL/Redis logs, `DATABASE_URL`, and `REDIS_URL`.
- **QA says Docker CLI unavailable:** run the orchestrator on the host using this runbook, not via the optional containerized API profile. Verify `docker info` works in the same terminal.
- **QA fails because dependencies are missing in offline mode:** run `python scripts/warm_maven_cache.py` again with internet access, then retry validation.
- **Permission errors in workspace:** ensure the user running the orchestrator owns the workspace directory and can run Docker.
- **OpenAI agents are unavailable:** check `OPENAI_API_KEY`; without it, deterministic fallback is expected. Automatic correction requires an available model and actionable diagnostics.
- **Port conflicts:** change host port mappings in `docker-compose.yml` and update the corresponding smoke-test base URLs.

## CI pipeline
`.github/workflows/ci.yml` runs Python syntax/unit tests, Spring Boot Maven tests, Docker Compose validation, image builds, service startup, Maven cache warm-up and an end-to-end workflow smoke test with human approval and sandbox QA.

## Phase 6 completion criteria
A successful local/CI end-to-end run should demonstrate:
1. PostgreSQL and Redis readiness.
2. Spring Boot health and URL create/redirect/analytics.
3. Orchestrator authentication, RBAC and tenant-scoped workflow access.
4. Human approval checkpoint and resume.
5. Isolated Git workspace and generated diff.
6. Docker Maven tests passing with network disabled.
7. Release gate completing only after QA passes.
8. Prometheus metrics and audit trail accessible to authorized roles.

A green static test suite or successful image build alone is not proof of a successful end-to-end deployment. Keep the CI and local smoke-test results as the evidence.
