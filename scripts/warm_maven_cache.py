#!/usr/bin/env python3
"""Download Maven dependencies before the network-disabled QA sandbox is used."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
docker = os.getenv("DOCKER_BIN", "docker")
image = os.getenv("MAVEN_SANDBOX_IMAGE", "maven:3.9.9-eclipse-temurin-21")
cache = Path(os.getenv("MAVEN_CACHE", str(Path.home() / ".m2"))).expanduser()
cache.mkdir(parents=True, exist_ok=True)
command = [
    docker, "run", "--rm",
    "--mount", f"type=bind,source={cache.resolve()},target=/root/.m2",
    "--mount", f"type=bind,source={(ROOT / 'backend').resolve()},target=/workspace",
    "-w", "/workspace",
    image, "mvn", "-B", "-ntp", "dependency:go-offline"
]
print("Warming Maven cache. This step needs internet access and may take several minutes.")
result = subprocess.run(command, check=False)
if result.returncode:
    raise SystemExit(result.returncode)
print("Maven dependencies are cached. QA sandbox can now run with network disabled.")
