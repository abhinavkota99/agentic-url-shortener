import os
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from .retry_policy import MAX_CORRECTIONS, after_qa as _after_qa, after_correction as _after_correction
from .agents import (
    requirement_agent, planner_agent, architecture_agent, security_agent,
    repository_agent, developer_agent, qa_agent, documentation_agent, release_agent
)

class GraphState(TypedDict, total=False):
    workflow_id: str
    requirement: str
    scenario: str
    analysis: dict[str, Any]
    tasks: list[dict[str, Any]]
    architecture: dict[str, Any]
    security: dict[str, Any]
    repository: dict[str, Any]
    implementation: dict[str, Any]
    qa: dict[str, Any]
    documentation: dict[str, Any]
    release: dict[str, Any]
    approval: dict[str, Any]
    rejected: bool
    qa_attempts: int
    correction_attempts: int
    diagnostics: dict[str, Any]
    correction: dict[str, Any]
    correction_history: list[dict[str, Any]]

def _analyze(s): return {"analysis": requirement_agent(s["requirement"], s["scenario"])}
def _plan(s): return {"tasks": planner_agent(s["scenario"])}
def _repository(s): return {"repository": repository_agent()}
def _architecture(s): return {"architecture": architecture_agent(s["analysis"])}
def _security(s): return {"security": security_agent()}

def _approval(s):
    decision = interrupt({
        "kind": "HUMAN_APPROVAL",
        "workflowId": s["workflow_id"],
        "artifact": "architecture",
        "summary": "Review architecture and security assessment before implementation."
    })
    rejected = isinstance(decision, dict) and decision.get("decision") == "reject"
    return {"approval": decision if isinstance(decision, dict) else {"decision": "approve"},
            "rejected": rejected}

def _implement(s):
    return {"implementation": developer_agent(
        s["architecture"], s["requirement"], s["workflow_id"]
    )}

def _qa(s):
    workspace = s.get("implementation", {}).get("workspace")
    result = qa_agent(workspace)
    return {"qa": result, "qa_attempts": s.get("qa_attempts", 0) + 1}

def _diagnose(s):
    from .diagnostics import parse_maven_diagnostics
    return {"diagnostics": parse_maven_diagnostics(s.get("qa", {}))}

def _correct(s):
    from .correction import propose_and_apply_correction
    attempt = s.get("correction_attempts", 0) + 1
    result = propose_and_apply_correction(
        s.get("implementation", {}).get("workspace", ""),
        s.get("requirement", ""),
        s.get("diagnostics", {}),
        attempt
    )
    history = list(s.get("correction_history", []))
    history.append({"attempt": attempt, **result})
    return {
        "correction": result,
        "correction_attempts": attempt,
        "correction_history": history
    }

def _docs(s): return {"documentation": documentation_agent()}
def _release(s):
    return {"release": release_agent(s["qa"], s["security"])}

# Routers keep returning the same keys as before; only the mapped node names changed.
def _after_plan(s):
    return "repository" if s["scenario"] == "BROWNFIELD" else "architecture"

def _after_approval(s):
    return "stop" if s.get("rejected") else "implement"

# Node names must not match any GraphState key, so every node gets a suffix.
N_ANALYZE = "analyze_node"
N_PLAN = "plan_node"
N_REPOSITORY = "repository_node"
N_ARCHITECTURE = "architecture_node"
N_SECURITY = "security_node"
N_APPROVAL = "approval_node"
N_IMPLEMENT = "implement_node"
N_QA = "qa_node"
N_DIAGNOSE = "diagnose_node"
N_CORRECT = "correct_node"
N_DOCS = "documentation_node"
N_RELEASE = "release_node"

def build_graph(checkpointer=None):
    g = StateGraph(GraphState)
    for name, fn in [
        (N_ANALYZE, _analyze), (N_PLAN, _plan), (N_REPOSITORY, _repository),
        (N_ARCHITECTURE, _architecture), (N_SECURITY, _security),
        (N_APPROVAL, _approval), (N_IMPLEMENT, _implement), (N_QA, _qa),
        (N_DIAGNOSE, _diagnose), (N_CORRECT, _correct),
        (N_DOCS, _docs), (N_RELEASE, _release)
    ]:
        g.add_node(name, fn)

    g.set_entry_point(N_ANALYZE)
    g.add_edge(N_ANALYZE, N_PLAN)
    g.add_conditional_edges(N_PLAN, _after_plan, {
        "repository": N_REPOSITORY,
        "architecture": N_ARCHITECTURE,
    })
    g.add_edge(N_REPOSITORY, N_ARCHITECTURE)
    g.add_edge(N_PLAN, N_SECURITY)
    g.add_edge([N_ARCHITECTURE, N_SECURITY], N_APPROVAL)
    g.add_conditional_edges(N_APPROVAL, _after_approval, {
        "implement": N_IMPLEMENT,
        "stop": END,
    })
    g.add_edge(N_IMPLEMENT, N_QA)
    g.add_conditional_edges(N_QA, _after_qa, {
        "diagnose": N_DIAGNOSE,
        "documentation": N_DOCS,
    })
    g.add_edge(N_DIAGNOSE, N_CORRECT)
    g.add_conditional_edges(N_CORRECT, _after_correction, {
        "qa": N_QA,
        "documentation": N_DOCS,
    })
    g.add_edge(N_DOCS, N_RELEASE)
    g.add_edge(N_RELEASE, END)
    return g.compile(checkpointer=checkpointer)

def create_checkpointer():
    if not os.getenv("DATABASE_URL"):
        return None
    try:
        import psycopg
        from psycopg.rows import dict_row
        from langgraph.checkpoint.postgres import PostgresSaver
        url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
        conn = psycopg.connect(url, autocommit=True, prepare_threshold=0, row_factory=dict_row)
        saver = PostgresSaver(conn)
        saver.setup()
        return saver
    except Exception as exc:
        raise RuntimeError(f"PostgreSQL checkpointer initialization failed: {exc}") from exc