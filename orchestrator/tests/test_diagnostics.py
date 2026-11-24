from app.diagnostics import parse_maven_diagnostics
from app.retry_policy import after_qa as _after_qa, after_correction as _after_correction

def test_extracts_only_allowlisted_compiler_diagnostics():
    result = parse_maven_diagnostics({
        "status": "FAILED",
        "exitCode": 1,
        "stdout": (
            "[ERROR] /workspace/src/main/java/com/example/Foo.java:[12,8] "
            "cannot find symbol\n"
            "[ERROR] /workspace/pom.xml:[1,1] invalid project\n"
            "[ERROR]   UrlPolicyTest.expiryAtNow:22 expected false but was true\n"
            "Tests run: 4, Failures: 1, Errors: 0\n"
        )
    })
    assert result["status"] == "ACTIONABLE"
    assert [d for d in result["diagnostics"] if d["kind"] == "COMPILATION"] == [{
        "kind": "COMPILATION",
        "file": "src/main/java/com/example/Foo.java",
        "line": 12,
        "column": 8,
        "message": "cannot find symbol"
    }]
    assert result["testSummaries"][-1] == {"tests": 4, "failures": 1, "errors": 0}
    assert any(d["kind"] == "TEST_FAILURE" for d in result["diagnostics"])

def test_unclassified_failure_does_not_enter_correction_loop():
    diagnostics = parse_maven_diagnostics({"status": "FAILED", "stdout": "network failure"})
    assert diagnostics["status"] == "UNCLASSIFIED"

def test_qa_retry_budget_stops_after_two_corrections():
    assert _after_qa({"qa":{"status":"FAILED"}, "qa_attempts":1, "correction_attempts":0}) == "diagnose"
    assert _after_qa({"qa":{"status":"FAILED"}, "qa_attempts":2, "correction_attempts":1}) == "diagnose"
    assert _after_qa({"qa":{"status":"FAILED"}, "qa_attempts":3, "correction_attempts":2}) == "documentation"
    assert _after_qa({"qa":{"status":"BLOCKED"}, "qa_attempts":1, "correction_attempts":0}) == "documentation"

def test_only_applied_correction_restarts_qa():
    assert _after_correction({"correction":{"status":"APPLIED"}}) == "qa"
    assert _after_correction({"correction":{"status":"REJECTED"}}) == "documentation"
