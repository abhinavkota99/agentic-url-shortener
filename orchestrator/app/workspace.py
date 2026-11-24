"""Constrained Git workspace for agent-authored code changes.

Only allowlisted source/test paths can be written. No shell is invoked here.
"""
import os
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
WORKSPACE_ROOT = Path(os.getenv("AGENT_WORKSPACE_ROOT", "/var/lib/agentic/workspaces")).resolve()
ALLOWED_PREFIXES = ("src/main/java/", "src/test/java/")
ALLOWED_FILES = {"README.md"}

class WorkspaceError(RuntimeError):
    pass

def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(cwd), text=True, capture_output=True,
        timeout=30, check=False, env={**os.environ, "GIT_TERMINAL_PROMPT":"0"}
    )
    if result.returncode:
        raise WorkspaceError(result.stderr[-4000:] or "Git command failed")
    return result.stdout.strip()

def create_workspace(workflow_id: str) -> Path:
    safe_id = "".join(c for c in workflow_id if c.isalnum() or c in "-_")
    if not safe_id:
        raise WorkspaceError("Invalid workflow ID")
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    target = (WORKSPACE_ROOT / safe_id).resolve()
    if WORKSPACE_ROOT not in target.parents:
        raise WorkspaceError("Workspace path escaped root")
    if target.exists():
        return target
    shutil.copytree(
        BACKEND_ROOT, target,
        ignore=shutil.ignore_patterns("target", ".git", ".idea", ".classpath", ".project")
    )
    _git(target, "init", "-b", "agent/work-" + safe_id)
    _git(target, "config", "user.name", "Agentic Engineering Bot")
    _git(target, "config", "user.email", "agentic-bot@localhost")
    _git(target, "add", "-A")
    _git(target, "commit", "-m", "baseline: isolated repository snapshot")
    return target

def validate_relative_path(relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise WorkspaceError("Invalid relative path")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise WorkspaceError("Path traversal is not allowed")
    normalized = candidate.as_posix()
    if normalized not in ALLOWED_FILES and not normalized.startswith(ALLOWED_PREFIXES):
        raise WorkspaceError(f"Write is not allowed for path: {normalized}")
    if normalized.endswith(("pom.xml", "application.yml", ".properties", ".yaml")):
        raise WorkspaceError("Build and runtime configuration files are protected")
    return candidate

def apply_files(workspace: Path, files: list[dict]) -> list[str]:
    changed = []
    for item in files:
        if set(item) != {"path", "content"}:
            raise WorkspaceError("Each generated file must contain only path and content")
        relative = validate_relative_path(item["path"])
        content = item["content"]
        if not isinstance(content, str) or len(content.encode("utf-8")) > 200_000:
            raise WorkspaceError("Generated file content is invalid or too large")
        destination = (workspace / relative).resolve()
        if workspace.resolve() not in destination.parents:
            raise WorkspaceError("Destination escaped workspace")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        changed.append(relative.as_posix())
    if changed:
        _git(workspace, "add", "--", *changed)
    return changed

def git_diff(workspace: Path) -> str:
    return _git(workspace, "diff", "--cached", "--no-ext-diff", "--", "src", "README.md")

def git_status(workspace: Path) -> str:
    return _git(workspace, "status", "--short")

def commit_changes(workspace: Path, message: str) -> str:
    _git(workspace, "add", "--", "src", "README.md")
    status = _git(workspace, "status", "--porcelain")
    if not status:
        return _git(workspace, "rev-parse", "HEAD")
    _git(workspace, "commit", "-m", message[:120])
    return _git(workspace, "rev-parse", "HEAD")
