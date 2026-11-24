import os, json
from typing import Any

def _llm_json(system: str, user: str) -> dict[str, Any] | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
        response = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        raw = response.content
        if isinstance(raw, list):
            raw = "".join(str(x.get("text", "")) for x in raw if isinstance(x, dict))
        return json.loads(str(raw))
    except Exception:
        return None

def requirement_agent(requirement: str, scenario: str) -> dict:
    result = _llm_json(
        "Return strict JSON with functionalRequirements, nonFunctionalRequirements, ambiguities, assumptions, riskLevel. Do not invent confirmed facts.",
        f"Scenario={scenario}\nRequirement={requirement}"
    )
    if result:
        return result
    lower = requirement.lower()
    ambiguities = []
    if "analytics" in lower and not any(x in lower for x in ["real-time", "realtime", "near-real-time"]):
        ambiguities.append("Analytics freshness target is unspecified.")
    if "fast" in lower or "performance" in lower:
        ambiguities.append("No measurable latency or throughput target is specified.")
    if scenario == "AMBIGUOUS":
        ambiguities += ["Expected traffic volume is unspecified.", "Analytics dimensions and retention are unspecified."]
    return {
        "functionalRequirements": ["Create short URLs", "Redirect short URLs", "Manage URL lifecycle", "Track click analytics"],
        "nonFunctionalRequirements": ["Low redirect latency", "Availability", "Horizontal scalability", "Security and auditability"],
        "ambiguities": ambiguities,
        "assumptions": ["Only HTTP and HTTPS destination URLs are accepted", "Short codes are unique"],
        "riskLevel": "MEDIUM"
    }

def planner_agent(scenario: str) -> list[dict]:
    tasks = [
        {"id":"T1","name":"Requirement analysis","agent":"requirement","dependencies":[]},
        {"id":"T2","name":"Task decomposition","agent":"planner","dependencies":["T1"]},
        {"id":"T3","name":"Architecture design","agent":"architect","dependencies":["T2"]},
        {"id":"T4","name":"Security assessment","agent":"security","dependencies":["T2"]},
        {"id":"T5","name":"Human design approval","agent":"approval","dependencies":["T3","T4"]},
        {"id":"T6","name":"Implementation planning","agent":"developer","dependencies":["T5"]},
        {"id":"T7","name":"Unit and integration test plan","agent":"qa","dependencies":["T6"]},
        {"id":"T8","name":"Documentation generation","agent":"documentation","dependencies":["T6"]},
        {"id":"T9","name":"Release readiness assessment","agent":"release","dependencies":["T7","T8"]}
    ]
    if scenario == "BROWNFIELD":
        tasks.insert(1, {"id":"TB","name":"Repository and impact analysis","agent":"repository","dependencies":["T1"]})
        for task in tasks:
            if task["id"] == "T2":
                task["dependencies"] = ["T1", "TB"]
    return tasks

def architecture_agent(requirements: dict) -> dict:
    return {
        "style": "Modular monolith for prototype",
        "components": ["Spring Boot REST API", "PostgreSQL", "Redis", "Analytics module", "LangGraph orchestrator"],
        "decisions": [
            "PostgreSQL provides uniqueness and transactional persistence",
            "Redis cache-aside accelerates redirects",
            "Analytics processing is isolated from redirect resolution",
            "Agent orchestration is separated from the URL application"
        ],
        "open_questions": requirements.get("ambiguities", [])
    }

def security_agent() -> dict:
    return {
        "controls": ["HTTP/HTTPS scheme validation", "Parameterized persistence via JPA", "Rate limiting planned at gateway", "Secrets via environment/secret manager", "Sandboxed tool execution"],
        "risks": ["Open redirect abuse", "SSRF if future preview fetches arbitrary URLs", "Alias enumeration", "Analytics privacy and retention"],
        "blocking_findings": []
    }

def repository_agent() -> dict:
    return {
        "status": "DEMO_REPOSITORY_ANALYSIS",
        "findings": ["Inspect controllers, services, repositories, entities and tests before editing."],
        "change_strategy": "Minimal targeted patch; preserve existing behavior and establish baseline tests."
    }

def developer_agent(architecture: dict) -> dict:
    return {
        "status": "IMPLEMENTATION_PLAN_GENERATED",
        "workspacePolicy": "No arbitrary shell execution; changes must be isolated and reviewed.",
        "plannedArtifacts": ["API contract", "domain model", "service implementation", "unit tests", "Git diff"],
        "architectureStyle": architecture.get("style")
    }

def qa_agent() -> dict:
    return {
        "status": "TEST_PLAN_READY",
        "testSuites": ["URL validation", "short-code uniqueness", "expiration behavior", "redirect behavior", "cache hit/miss", "analytics aggregation", "approval and workflow recovery"],
        "qualityGate": "Build and all required tests must pass; security blockers must be zero."
    }

def documentation_agent() -> dict:
    return {"status":"DOCUMENTATION_PLAN_READY","documents":["README","Architecture overview","API specification","Setup guide","Limitations and trade-offs"]}

def release_agent(qa: dict, security: dict) -> dict:
    tests_passed = qa.get("status") == "PASSED"
    security_clear = not security.get("blocking_findings")
    ready = tests_passed and security_clear
    return {
        "recommendation": "READY_FOR_HUMAN_REVIEW" if ready else "NOT_READY",
        "productionDeploymentAllowed": False,
        "testStatus": qa.get("status", "UNKNOWN"),
        "securityBlockers": security.get("blocking_findings", [])
    }


def developer_agent(architecture: dict, requirement: str = "", workflow_id: str = "local") -> dict:
    from .codegen import generate_and_apply
    return generate_and_apply(workflow_id, requirement or "Implement URL expiration policy with tests")

def qa_agent(workspace: str | None = None) -> dict:
    if not workspace:
        return {
            "status": "NOT_RUN",
            "reason": "No generated workspace was supplied.",
            "testSuites": ["URL validation", "short-code uniqueness", "expiration behavior", "redirect behavior"]
        }
    from pathlib import Path
    from .sandbox import run_maven_tests
    result = run_maven_tests(Path(workspace))
    result["testSuites"] = ["Maven unit tests", "Generated JUnit tests"]
    return result
