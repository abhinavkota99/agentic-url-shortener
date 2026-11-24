#!/usr/bin/env python3
"""Create local secrets and Prometheus token without overwriting existing credentials."""
from __future__ import annotations
import json
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
TOKEN_FILE = ROOT / "monitoring" / "metrics_token"

def main() -> None:
    if ENV_FILE.exists():
        raise SystemExit(".env already exists. Refusing to overwrite secrets.")
    admin = secrets.token_urlsafe(36)
    developer = secrets.token_urlsafe(36)
    reviewer = secrets.token_urlsafe(36)
    viewer = secrets.token_urlsafe(36)
    values = {
        "APP_ENV": "production",
        "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(24),
        "ORCHESTRATOR_API_KEYS": json.dumps({
            admin: "platform-admin:admin",
            developer: "team-a:developer",
            reviewer: "team-a:reviewer",
            viewer: "team-a:viewer",
        }, separators=(",", ":")),
        "RATE_LIMIT_PER_MINUTE": "120",
        "OPENAI_API_KEY": "",
        "OPENAI_MODEL": "gpt-4o-mini",
        "AGENT_WORKSPACE_ROOT": "../.agentic-workspaces",
        "DATABASE_URL": "postgresql+psycopg://app:"
            + secrets.token_urlsafe(16) + "@localhost:5433/shortener",
        "REDIS_URL": "redis://localhost:6379/1",
        "RATE_LIMIT_ENABLED": "true",
        "RATE_LIMIT_FAIL_CLOSED": "true",
    }
    # Compose interpolates POSTGRES_PASSWORD for its own services; host Python uses DATABASE_URL.
    values["DATABASE_URL"] = (
        "postgresql+psycopg://app:" + values["POSTGRES_PASSWORD"]
        + "@localhost:5433/shortener"
    )
    ENV_FILE.write_text(
        "# Generated locally by scripts/bootstrap.py. Never commit this file.\n"
        + "\n".join(f"{key}={value}" for key, value in values.items()) + "\n",
        encoding="utf-8"
    )
    try:
        ENV_FILE.chmod(0o600)
    except OSError:
        pass
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(admin, encoding="utf-8")
    try:
        TOKEN_FILE.chmod(0o600)
    except OSError:
        pass
    print("Created .env and monitoring/metrics_token.")
    print("Admin API key:     ", admin)
    print("Developer API key: ", developer)
    print("Reviewer API key:  ", reviewer)
    print("Viewer API key:    ", viewer)
    print("Grafana password:  ", values["GRAFANA_ADMIN_PASSWORD"])
    print("Save these credentials securely. They cannot be recovered from this output later.")

if __name__ == "__main__":
    main()
