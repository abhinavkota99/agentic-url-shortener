"""API-key authentication, role checks, tenant ownership, and Redis rate limiting."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)
ALLOWED_ROLES = {"admin", "developer", "reviewer", "viewer"}

@dataclass(frozen=True)
class Principal:
    subject: str
    role: str

@lru_cache(maxsize=1)
def _key_index() -> dict[str, Principal]:
    raw = os.getenv("ORCHESTRATOR_API_KEYS", "")
    if not raw:
        return {}
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ORCHESTRATOR_API_KEYS must be valid JSON") from exc
    if not isinstance(config, dict):
        raise RuntimeError("ORCHESTRATOR_API_KEYS must be a JSON object")
    index = {}
    for token, identity in config.items():
        if not isinstance(token, str) or len(token) < 24:
            raise RuntimeError("Every API key must contain at least 24 characters")
        if not isinstance(identity, str) or ":" not in identity:
            raise RuntimeError("API key identity must use subject:role format")
        subject, role = identity.rsplit(":", 1)
        if not subject or role not in ALLOWED_ROLES:
            raise RuntimeError("Invalid API key subject or role")
        index[hashlib.sha256(token.encode()).hexdigest()] = Principal(subject, role)
    return index

def reset_auth_cache_for_tests():
    _key_index.cache_clear()

def authenticate_token(token: str) -> Principal | None:
    digest = hashlib.sha256(token.encode()).hexdigest()
    for expected, principal in _key_index().items():
        if hmac.compare_digest(digest, expected):
            return principal
    return None

def check_workflow_access(workflow, principal: Principal) -> None:
    if principal.role == "admin" or workflow.owner_id == principal.subject:
        return
    raise HTTPException(status_code=404, detail="Workflow not found")

def require_roles(*roles: str):
    allowed = set(roles)
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return principal
    return dependency

@lru_cache(maxsize=1)
def _redis_client():
    import redis
    return redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/1"),
        socket_connect_timeout=1, socket_timeout=1, decode_responses=True
    )

def _rate_limit(principal: Principal) -> None:
    if os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "true":
        return
    limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    try:
        window = int(__import__("time").time() // 60)
        key = f"agentic:rate:{principal.subject}:{window}"
        client = _redis_client()
        count = client.incr(key)
        if count == 1:
            client.expire(key, 70)
        if count > limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except HTTPException:
        raise
    except Exception as exc:
        if os.getenv("RATE_LIMIT_FAIL_CLOSED", "true").lower() == "true":
            raise HTTPException(status_code=503, detail="Rate limiter unavailable") from exc

def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer)
) -> Principal:
    if os.getenv("APP_ENV", "production").lower() == "development" and os.getenv("AUTH_ENABLED", "true").lower() == "false":
        principal = Principal("local-developer", "admin")
    else:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer API key required")
        principal = authenticate_token(credentials.credentials)
        if principal is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    _rate_limit(principal)
    return principal
