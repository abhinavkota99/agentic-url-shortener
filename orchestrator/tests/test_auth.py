import json
import pytest
from fastapi import HTTPException
from app.auth import authenticate_token, check_workflow_access, reset_auth_cache_for_tests, Principal

def test_api_key_authentication_and_role_mapping(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_API_KEYS", json.dumps({"a"*32: "alice:developer"}))
    reset_auth_cache_for_tests()
    assert authenticate_token("a"*32) == Principal("alice", "developer")
    assert authenticate_token("b"*32) is None
    reset_auth_cache_for_tests()

def test_invalid_short_api_key_rejected(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_API_KEYS", json.dumps({"short": "alice:developer"}))
    reset_auth_cache_for_tests()
    with pytest.raises(RuntimeError):
        authenticate_token("short")
    reset_auth_cache_for_tests()

def test_workflow_tenant_isolation_and_admin_override():
    class Workflow:
        owner_id = "alice"
    with pytest.raises(HTTPException) as error:
        check_workflow_access(Workflow(), Principal("bob", "viewer"))
    assert error.value.status_code == 404
    check_workflow_access(Workflow(), Principal("platform-admin", "admin"))
    check_workflow_access(Workflow(), Principal("alice", "reviewer"))

def test_invalid_role_rejected(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_API_KEYS", json.dumps({"c"*32: "alice:superuser"}))
    reset_auth_cache_for_tests()
    with pytest.raises(RuntimeError):
        authenticate_token("c"*32)
    reset_auth_cache_for_tests()


def test_workflow_model_defaults_owner_to_local_identity():
    from app.models import Workflow, Scenario
    workflow = Workflow(requirement="Add URL expiration support", scenario=Scenario.BROWNFIELD)
    assert workflow.owner_id == "local-developer"
