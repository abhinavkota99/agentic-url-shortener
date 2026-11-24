#!/usr/bin/env python3
"""Static validation and focused unit test runner."""
from __future__ import annotations
import ast
import os
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "orchestrator"

def run(command, cwd=ROOT, env=None):
    print("+", " ".join(map(str, command)))
    return subprocess.run(command, cwd=cwd, env=env, check=False).returncode

def main():
    errors=[]
    py_files=list((ORCH/"app").glob("*.py"))+list((ORCH/"tests").glob("*.py"))+list((ROOT/"scripts").glob("*.py"))
    for file in py_files:
        try: ast.parse(file.read_text(encoding="utf-8"))
        except Exception as exc: errors.append(f"{file.relative_to(ROOT)}: {exc}")
    if errors:
        print("\n".join(errors),file=sys.stderr)
        return 1
    print(f"Python syntax: {len(py_files)} files passed")
    compose=yaml.safe_load((ROOT/"docker-compose.yml").read_text(encoding="utf-8"))
    required={"postgres","redis","backend","orchestrator","prometheus","grafana"}
    if not required.issubset(compose.get("services",{})):
        print("Missing Compose services",file=sys.stderr); return 1
    req_lines=(ORCH/"requirements.txt").read_text(encoding="utf-8").splitlines()
    if any("\\n" in line or not line.strip() for line in req_lines):
        print("Malformed requirements.txt entry",file=sys.stderr); return 1
    print("Docker Compose YAML and service inventory: passed")
    tests=[
        "orchestrator/tests/test_auth.py",
        "orchestrator/tests/test_diagnostics.py",
        "orchestrator/tests/test_dag.py",
        "orchestrator/tests/test_workspace_policy.py",
        "orchestrator/tests/test_codegen_policy.py",
        "orchestrator/tests/test_retry_policy.py",
        "orchestrator/tests/test_sandbox_policy.py",
    ]
    env=os.environ.copy()
    env.setdefault("PYTHONPATH",str(ORCH))
    env.setdefault("APP_ENV","development")
    env.setdefault("AUTH_ENABLED","false")
    env.setdefault("RATE_LIMIT_ENABLED","false")
    return run([sys.executable,"-m","pytest","-q",*tests],cwd=ROOT,env=env) if not errors else 1

if __name__=="__main__":
    raise SystemExit(main())
