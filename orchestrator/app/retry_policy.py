"""Pure routing policy for the bounded self-correction loop."""
MAX_CORRECTIONS = 2

def after_qa(state: dict) -> str:
    qa = state.get("qa", {})
    if (qa.get("status") == "FAILED"
            and state.get("correction_attempts", 0) < MAX_CORRECTIONS
            and state.get("qa_attempts", 0) <= MAX_CORRECTIONS):
        return "diagnose"
    return "documentation"

def after_correction(state: dict) -> str:
    return "qa" if state.get("correction", {}).get("status") == "APPLIED" else "documentation"
