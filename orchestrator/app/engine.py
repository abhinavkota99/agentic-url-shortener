from datetime import datetime, timezone
from langgraph.types import Command
from .models import Workflow, Task, TaskStatus, WorkflowStatus
from .store import store
from .graph import build_graph, create_checkpointer

_checkpointer = create_checkpointer()
_graph = build_graph(_checkpointer)

def _config(workflow):
    return {"configurable": {"thread_id": workflow.graph_thread_id or workflow.id}}

def audit(w, actor, action, detail=None):
    w.audit.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor, "action": action, "detail": detail or {}
    })

def _sync(w, result):
    for key in ("analysis", "tasks", "architecture", "security", "repository",
                "implementation", "qa", "documentation", "release", "approval",
                "qa_attempts", "correction_attempts", "diagnostics", "correction", "correction_history"):
        if key in result:
            w.artifacts[key] = result[key]
    if "tasks" in result:
        w.tasks = [Task(**t) for t in result["tasks"]]

def execute_workflow(w):
    w.status = WorkflowStatus.RUNNING
    if not w.graph_thread_id:
        w.graph_thread_id = w.id
    audit(w, "orchestrator", "WORKFLOW_STARTED")
    store.save(w)
    result = _graph.invoke({
        "workflow_id": w.id, "requirement": w.requirement, "scenario": w.scenario.value
    }, config=_config(w))
    _sync(w, result)
    snapshot = _graph.get_state(_config(w))
    if snapshot and snapshot.next:
        w.status = WorkflowStatus.WAITING_FOR_APPROVAL
        w.current_stage = "DESIGN_APPROVAL"
        w.approvals.append({
            "approvalId": f"APR-{w.id}-V{w.requirement_version}",
            "status": "PENDING", "artifact": "architecture",
            "artifactVersion": w.requirement_version
        })
        for task in w.tasks:
            if task.id in ("T1", "T2", "T3", "T4", "TB"):
                task.status = TaskStatus.COMPLETED
            elif task.id == "T5":
                task.status = TaskStatus.WAITING_FOR_APPROVAL
            else:
                task.status = TaskStatus.BLOCKED
        audit(w, "governance", "APPROVAL_REQUESTED", {"artifact":"architecture"})
    else:
        _finish(w)
    store.save(w)

def _finish(w):
    qa_status = w.artifacts.get("qa", {}).get("status")
    if qa_status != "PASSED":
        w.status = WorkflowStatus.FAILED
        w.current_stage = "VALIDATION_FAILED"
        for task in w.tasks:
            if task.id == "T7":
                task.status = TaskStatus.FAILED
                task.output = {"qaAttempts": w.artifacts.get("qa_attempts", 1), "correctionAttempts": w.artifacts.get("correction_attempts", 0), "manualValidationRetries": task.retries}
            elif task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                task.status = TaskStatus.BLOCKED
        audit(w, "orchestrator", "VALIDATION_FAILED", {"qaStatus": qa_status})
        return
    for task in w.tasks:
        task.status = TaskStatus.COMPLETED
        if task.id == "T7":
            task.output = {"qaAttempts": w.artifacts.get("qa_attempts", 1), "correctionAttempts": w.artifacts.get("correction_attempts", 0), "manualValidationRetries": task.retries}
    w.status = WorkflowStatus.COMPLETED
    w.current_stage = "COMPLETED"
    audit(w, "orchestrator", "WORKFLOW_COMPLETED")

def approve_and_resume(w, actor="human"):
    pending = next((a for a in w.approvals if a["status"] == "PENDING"), None)
    if not pending:
        raise ValueError("No pending approval")
    pending["status"] = "APPROVED"
    pending["approvedAt"] = datetime.now(timezone.utc).isoformat()
    audit(w, actor, "APPROVAL_GRANTED", {"approvalId":pending["approvalId"]})
    result = _graph.invoke(Command(resume={"decision":"approve","approver":"human"}), config=_config(w))
    _sync(w, result)
    if "qa_attempts" in w.artifacts:
        audit(w, "qa-agent", "QA_ATTEMPTS_FINISHED", {
            "attempts": w.artifacts.get("qa_attempts"),
            "finalStatus": w.artifacts.get("qa", {}).get("status")
        })
    for item in w.artifacts.get("correction_history", []):
        audit(w, "correction-agent", "CORRECTION_ATTEMPT", {
            "attempt": item.get("attempt"),
            "status": item.get("status"),
            "changedFiles": item.get("changedFiles", []),
            "reason": item.get("reason")
        })
    _finish(w)
    store.save(w)

def reject_approval(w, reason, actor="human"):
    pending = next((a for a in w.approvals if a["status"] == "PENDING"), None)
    if not pending:
        raise ValueError("No pending approval")
    pending["status"] = "REJECTED"
    pending["reason"] = reason
    _graph.invoke(Command(resume={"decision":"reject","reason":reason}), config=_config(w))
    w.status = WorkflowStatus.SAFE_STOPPED
    w.current_stage = "SAFE_STOPPED"
    audit(w, actor, "APPROVAL_REJECTED", {"reason":reason})
    store.save(w)

def replan(w, new_requirement):
    # A new graph thread prevents an earlier approval from authorizing changed requirements.
    w.requirement = new_requirement
    w.requirement_version += 1
    w.status = WorkflowStatus.REPLANNING
    w.artifacts = {}
    w.tasks = []
    w.approvals = []
    audit(w, "orchestrator", "REPLAN_TRIGGERED", {"requirementVersion":w.requirement_version})
    w.graph_thread_id = f"{w.id}-V{w.requirement_version}"
    execute_workflow(w)


def retry_validation(w):
    from .agents import qa_agent, release_agent
    if w.status != WorkflowStatus.FAILED:
        raise ValueError("Only failed workflows can retry validation")
    task = next((t for t in w.tasks if t.id == "T7"), None)
    if task is None:
        raise ValueError("QA task does not exist")
    if task.retries >= task.max_retries:
        raise ValueError("Validation retry limit exceeded")
    implementation = w.artifacts.get("implementation", {})
    workspace = implementation.get("workspace")
    if not workspace:
        raise ValueError("Generated workspace is unavailable")
    task.retries += 1
    task.status = TaskStatus.RUNNING
    audit(w, "qa-agent", "VALIDATION_RETRY_STARTED", {"attempt": task.retries})
    result = qa_agent(workspace)
    w.artifacts["qa"] = result
    w.artifacts["qa_attempts"] = int(w.artifacts.get("qa_attempts", 1)) + 1
    w.artifacts["release"] = release_agent(result, w.artifacts.get("security", {}))
    _finish(w)
    store.save(w)
    return result
