#!/usr/bin/env python3
"""Local service smoke test for the URL API and orchestrator security/health endpoints."""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

def request(url: str, method="GET", data=None, token=None, follow_redirects=True, timeout=10):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None
    opener = urllib.request.build_opener() if follow_redirects else urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with opener.open(req, timeout=timeout) as response:
            raw = response.read()
            return response.status, dict(response.headers), json.loads(raw) if raw and "json" in response.headers.get("Content-Type","") else raw.decode(errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try: parsed = json.loads(raw)
        except Exception: parsed = raw.decode(errors="replace")
        return exc.code, dict(exc.headers), parsed

def require(condition, message):
    if not condition:
        raise RuntimeError(message)
    print("PASS:", message)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--backend",default="http://localhost:8080")
    parser.add_argument("--orchestrator",default="http://localhost:8000")
    parser.add_argument("--workflow",action="store_true",help="Run a complete approval, code-generation and sandbox-QA workflow")
    parser.add_argument("--workflow-timeout",type=int,default=900)
    args=parser.parse_args()
    keys=json.loads(os.environ["ORCHESTRATOR_API_KEYS"])
    admin=next(k for k,v in keys.items() if v.endswith(":admin"))
    developer=next(k for k,v in keys.items() if v.endswith(":developer"))
    reviewer=next(k for k,v in keys.items() if v.endswith(":reviewer"))

    code="smk"+uuid.uuid4().hex[:8]
    status,_,health=request(args.backend+"/actuator/health")
    require(status==200 and health.get("status")=="UP","Spring Boot health endpoint")
    status,_,created=request(args.backend+"/api/v1/urls","POST",{
        "originalUrl":"https://example.com/phase6-smoke-test",
        "customAlias":code
    })
    require(status==201 and created.get("shortCode")==code,"Create short URL")
    status,headers,_=request(args.backend+"/"+code,follow_redirects=False)
    require(status==302 and headers.get("Location")=="https://example.com/phase6-smoke-test","Redirect resolves to destination")
    status,_,analytics=request(args.backend+f"/api/v1/urls/{code}/analytics")
    require(status==200 and analytics.get("totalClicks",0)>=1,"Click analytics recorded")

    status,_,health=request(args.orchestrator+"/health")
    require(status==200 and health.get("status")=="UP","Orchestrator liveness")
    status,_,ready=request(args.orchestrator+"/ready")
    require(status==200 and ready.get("status")=="READY","Orchestrator PostgreSQL and Redis readiness")
    status,_,_=request(args.orchestrator+"/api/workflows")
    require(status==401,"Unauthenticated workflow request rejected")
    status,_,_=request(args.orchestrator+"/api/workflows",token=developer)
    require(status==200,"Developer authentication and workflow listing")
    status,_,metrics=request(args.orchestrator+"/metrics",token=admin)
    require(status==200 and "agentic_http_requests_total" in metrics,"Admin-only Prometheus metrics")
    status,_,_=request(args.orchestrator+"/metrics",token=developer)
    require(status==403,"Developer cannot access admin-only metrics")
    if args.workflow:
        status,_,workflow=request(args.orchestrator+"/api/workflows","POST",{
            "requirement":"Add URL expiration update support with validation and unit tests",
            "scenario":"GREENFIELD",
            "autonomyLevel":"CONTROLLED"
        },token=developer,timeout=30)
        require(status==202 and workflow.get("status")=="WAITING_FOR_APPROVAL","Workflow pauses for human approval")
        workflow_id=workflow["id"]
        status,_,approved=request(
            args.orchestrator+f"/api/workflows/{workflow_id}/approve",
            "POST",token=reviewer,timeout=args.workflow_timeout
        )
        require(status==200 and approved.get("status")=="COMPLETED","Approval resumes implementation and QA to completion")
        status,_,artifacts=request(args.orchestrator+f"/api/workflows/{workflow_id}/artifacts",token=developer)
        require(status==200 and artifacts.get("qa",{}).get("status")=="PASSED","Sandbox Maven test gate passed")
        status,_,diff=request(args.orchestrator+f"/api/workflows/{workflow_id}/diff",token=developer)
        require(status==200 and len(diff.get("changedFiles",[]))>0,"Generated Git diff is available")
        status,_,audit=request(args.orchestrator+f"/api/workflows/{workflow_id}/audit",token=developer)
        require(status==200 and any(e.get("action")=="APPROVAL_GRANTED" for e in audit),"Approval is recorded in workflow audit")
    print("\nAll Phase 6 smoke checks passed.")

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print("SMOKE TEST FAILED:",exc,file=sys.stderr)
        raise SystemExit(1)
