from pathlib import Path as _Path
from dotenv import load_dotenv as _load_dotenv
_load_dotenv(_Path(__file__).resolve().parents[2] / ".env", override=False)

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest
from .models import WorkflowRequest, Workflow
from .store import store
from .engine import execute_workflow, approve_and_resume, reject_approval, replan, retry_validation
from .persistence import initialize_database
from .auth import Principal, get_current_principal, require_roles, check_workflow_access, _key_index

app = FastAPI(
    title="Agentic Software Engineering Platform",
    version="0.6.0",
    description="Controlled, stateful SDLC orchestration platform"
)
HTTP_REQUESTS = Counter("agentic_http_requests_total", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram("agentic_http_request_duration_seconds", "HTTP request duration", ["method", "route"])

@app.on_event("startup")
def startup():
    import os
    if os.getenv("APP_ENV", "production").lower() != "development" and os.getenv("AUTH_ENABLED", "true").lower() == "true":
        if not _key_index():
            raise RuntimeError("ORCHESTRATOR_API_KEYS must contain at least one API key in production")
    initialize_database()

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    import time
    started = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    route_name = getattr(route, "path", "unmatched")
    HTTP_REQUESTS.labels(request.method, route_name, str(response.status_code)).inc()
    HTTP_LATENCY.labels(request.method, route_name).observe(time.perf_counter() - started)
    return response

def _owned(workflow_id: str, principal: Principal):
    try:
        workflow = store.get(workflow_id)
    except KeyError:
        raise HTTPException(404, "Workflow not found")
    check_workflow_access(workflow, principal)
    return workflow

@app.get("/health")
def health():
    return {"status": "UP"}

@app.get("/ready")
def readiness():
    try:
        from sqlalchemy import text
        from .persistence import _engine
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        import redis, os
        redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/1"), socket_connect_timeout=1).ping()
        return {"status": "READY", "dependencies": {"postgres": "UP", "redis": "UP"}}
    except Exception as exc:
        raise HTTPException(503, detail=f"Dependency check failed: {type(exc).__name__}")

@app.get("/metrics")
def metrics(_: Principal = Depends(require_roles("admin"))):
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/api/workflows", status_code=202)
def create_workflow(request: WorkflowRequest, principal: Principal = Depends(require_roles("developer", "admin"))):
    workflow = Workflow(requirement=request.requirement, scenario=request.scenario, owner_id=principal.subject)
    execute_workflow(workflow)
    return store.get(workflow.id)

@app.get("/api/workflows")
def list_workflows(principal: Principal = Depends(get_current_principal)):
    return store.all() if principal.role == "admin" else store.all(owner_id=principal.subject)

@app.get("/api/workflows/{workflow_id}")
def get_workflow(workflow_id: str, principal: Principal = Depends(get_current_principal)):
    return _owned(workflow_id, principal)

@app.get("/api/workflows/{workflow_id}/tasks")
def get_tasks(workflow_id: str, principal: Principal = Depends(get_current_principal)):
    return _owned(workflow_id, principal).tasks

@app.get("/api/workflows/{workflow_id}/artifacts")
def get_artifacts(workflow_id: str, principal: Principal = Depends(get_current_principal)):
    return _owned(workflow_id, principal).artifacts

@app.get("/api/workflows/{workflow_id}/audit")
def get_audit(workflow_id: str, principal: Principal = Depends(get_current_principal)):
    return _owned(workflow_id, principal).audit

@app.post("/api/workflows/{workflow_id}/approve")
def approve(workflow_id: str, principal: Principal = Depends(require_roles("reviewer", "admin"))):
    try:
        workflow = _owned(workflow_id, principal)
        approve_and_resume(workflow, actor=principal.subject)
        return store.get(workflow_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc))

@app.post("/api/workflows/{workflow_id}/reject")
def reject(workflow_id: str, body: dict, principal: Principal = Depends(require_roles("reviewer", "admin"))):
    try:
        workflow = _owned(workflow_id, principal)
        reject_approval(workflow, str(body.get("reason", "Rejected by reviewer"))[:1000], actor=principal.subject)
        store.save(workflow)
        return store.get(workflow_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc))

@app.post("/api/workflows/{workflow_id}/replan")
def replan_workflow(workflow_id: str, body: dict, principal: Principal = Depends(require_roles("developer", "admin"))):
    workflow = _owned(workflow_id, principal)
    requirement = body.get("requirement")
    if not isinstance(requirement, str) or not 10 <= len(requirement) <= 10000:
        raise HTTPException(400, "requirement must contain 10 to 10000 characters")
    replan(workflow, requirement)
    store.save(workflow)
    return workflow

@app.get("/api/workflows/{workflow_id}/diff")
def get_diff(workflow_id: str, principal: Principal = Depends(get_current_principal)):
    workflow = _owned(workflow_id, principal)
    implementation = workflow.artifacts.get("implementation", {})
    return {
        "changedFiles": implementation.get("changedFiles", []),
        "diff": implementation.get("diff", ""),
        "gitStatus": implementation.get("gitStatus", ""),
        "workspace": implementation.get("workspace")
    }

@app.post("/api/workflows/{workflow_id}/commit")
def commit_reviewed_changes(workflow_id: str, body: dict, principal: Principal = Depends(require_roles("developer", "admin"))):
    from pathlib import Path
    from .workspace import commit_changes
    workflow = _owned(workflow_id, principal)
    if workflow.status.value != "COMPLETED":
        raise HTTPException(409, "Only successfully validated workflows can be committed")
    workspace = workflow.artifacts.get("implementation", {}).get("workspace")
    if not workspace:
        raise HTTPException(409, "No generated workspace exists")
    message = body.get("message", "feat: agent-generated change")
    if not isinstance(message, str) or not message.strip():
        raise HTTPException(400, "Commit message is required")
    sha = commit_changes(Path(workspace), message)
    from datetime import datetime, timezone
    workflow.audit.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": principal.subject, "action": "LOCAL_COMMIT_CREATED", "detail": {"commit": sha}
    })
    store.save(workflow)
    return {"commit": sha, "workspace": workspace}

@app.post("/api/workflows/{workflow_id}/retry-validation")
def retry_workflow_validation(workflow_id: str, principal: Principal = Depends(require_roles("developer", "admin"))):
    workflow = _owned(workflow_id, principal)
    try:
        result = retry_validation(workflow)
        return {"workflow": store.get(workflow_id), "validation": result}
    except ValueError as exc:
        raise HTTPException(409, str(exc))
