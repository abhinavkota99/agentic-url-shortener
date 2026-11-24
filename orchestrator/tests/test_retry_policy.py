from app.retry_policy import MAX_CORRECTIONS, after_qa, after_correction

def test_failed_qa_routes_to_diagnosis_with_retry_budget():
    assert after_qa({"qa":{"status":"FAILED"},"qa_attempts":1,"correction_attempts":0}) == "diagnose"

def test_passed_qa_routes_to_documentation():
    assert after_qa({"qa":{"status":"PASSED"},"qa_attempts":1,"correction_attempts":0}) == "documentation"

def test_correction_budget_is_bounded():
    assert after_qa({"qa":{"status":"FAILED"},"qa_attempts":3,"correction_attempts":MAX_CORRECTIONS}) == "documentation"

def test_only_applied_correction_reenters_qa():
    assert after_correction({"correction":{"status":"APPLIED"}}) == "qa"
    assert after_correction({"correction":{"status":"REJECTED"}}) == "documentation"
