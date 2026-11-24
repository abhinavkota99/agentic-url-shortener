"""Fixed-command Docker test runner. It never evaluates agent-provided shell commands."""
import os
import subprocess
from pathlib import Path

class SandboxError(RuntimeError):
    pass

def run_maven_tests(workspace: Path, timeout_seconds: int = 240) -> dict:
    docker = os.getenv("DOCKER_BIN", "docker")
    image = os.getenv("MAVEN_SANDBOX_IMAGE", "maven:3.9.9-eclipse-temurin-21")
    cache = Path(os.getenv("MAVEN_CACHE", str(Path.home() / ".m2"))).expanduser()
    uid = str(os.getuid()) if hasattr(os, "getuid") else "10001"
    gid = str(os.getgid()) if hasattr(os, "getgid") else "10001"
    args = [
        docker, "run", "--rm",
        "--network", "none",
        "--read-only",
        "--memory", "1g",
        "--cpus", "2",
        "--pids-limit", "256",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
        "--mount", f"type=bind,source={workspace.resolve()},target=/workspace",
        "--mount", f"type=bind,source={cache.resolve()},target=/root/.m2,readonly",
        "-w", "/workspace",
        "--entrypoint", "mvn",
        image,
        "-B", "-ntp", "-o", "-Dmaven.repo.local=/root/.m2/repository", "test"
    ]
    if os.name != "nt":
        args[2:2] = ["--user", f"{uid}:{gid}"]
    try:
        result = subprocess.run(
            args, text=True, capture_output=True, timeout=timeout_seconds,
            check=False, env=os.environ.copy()
        )
        return {
            "status": "PASSED" if result.returncode == 0 else "FAILED",
            "exitCode": result.returncode,
            "stdout": result.stdout[-12000:],
            "stderr": result.stderr[-12000:],
            "command": "docker run <restricted-container> mvn -B -ntp -o test",
            "sandbox": "docker-network-none-read-only-root-limited-resources"
        }
    except FileNotFoundError:
        return {
            "status": "BLOCKED",
            "reason": "Docker CLI is unavailable. Install Docker and retry.",
            "sandbox": "not-started"
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "TIMED_OUT",
            "reason": f"Maven test exceeded {timeout_seconds} seconds.",
            "stdout": (exc.stdout or "")[-8000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-8000:] if isinstance(exc.stderr, str) else "",
            "sandbox": "docker"
        }
