import subprocess
from pathlib import Path
from app import sandbox

def test_maven_runner_uses_fixed_restricted_offline_command(monkeypatch, tmp_path):
    cache = tmp_path / "m2"
    cache.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args, 0, "BUILD SUCCESS", "")

    monkeypatch.setenv("MAVEN_CACHE", str(cache))
    monkeypatch.setattr(sandbox.subprocess, "run", fake_run)
    result = sandbox.run_maven_tests(workspace)

    args = captured["args"]
    assert result["status"] == "PASSED"
    assert "--network" in args and args[args.index("--network") + 1] == "none"
    assert "--read-only" in args
    assert "--cap-drop" in args and args[args.index("--cap-drop") + 1] == "ALL"
    assert "--security-opt" in args
    assert "--mount" in args
    assert args[-1] == "test"
    assert "-o" in args
    assert captured["kwargs"]["timeout"] == 240
    assert "shell" not in captured["kwargs"]

def test_docker_unavailable_returns_blocked(monkeypatch, tmp_path):
    cache = tmp_path / "m2"
    cache.mkdir()
    monkeypatch.setenv("MAVEN_CACHE", str(cache))
    def missing(*args, **kwargs):
        raise FileNotFoundError("docker")
    monkeypatch.setattr(sandbox.subprocess, "run", missing)
    result = sandbox.run_maven_tests(tmp_path)
    assert result["status"] == "BLOCKED"
