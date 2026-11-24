"""Convert Maven output into bounded, structured diagnostics."""
import re
from pathlib import Path

COMPILER_RE = re.compile(
    r"\[ERROR\]\s+(?P<file>[^:\n]+\.java):\[(?P<line>\d+),(?P<column>\d+)\]\s+(?P<message>.+)"
)
TEST_RE = re.compile(r"\[ERROR\]\s+(?P<test>[\w.$#]+(?:\([^)]*\))?)\s*:\s*(?P<message>.+)")
SUMMARY_RE = re.compile(r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)")
SAFE_ROOTS = ("src/main/java/", "src/test/java/")

def parse_maven_diagnostics(result: dict, max_items: int = 30) -> dict:
    output = "\n".join((result.get("stdout") or "", result.get("stderr") or ""))
    diagnostics = []
    seen = set()
    for match in COMPILER_RE.finditer(output):
        raw_path = match.group("file").replace("\\", "/")
        marker = "/src/"
        relative = raw_path[raw_path.find(marker) + 1:] if marker in raw_path else raw_path
        if not relative.startswith(SAFE_ROOTS):
            continue
        item = {
            "kind": "COMPILATION",
            "file": relative,
            "line": int(match.group("line")),
            "column": int(match.group("column")),
            "message": match.group("message")[:500]
        }
        key = (item["kind"], item["file"], item["line"], item["message"])
        if key not in seen:
            diagnostics.append(item); seen.add(key)
    for match in TEST_RE.finditer(output):
        item = {"kind": "TEST_FAILURE", "test": match.group("test")[:200], "message": match.group("message")[:500]}
        key = (item["kind"], item["test"])
        if key not in seen:
            diagnostics.append(item); seen.add(key)
    summaries = [
        {"tests": int(m.group(1)), "failures": int(m.group(2)), "errors": int(m.group(3))}
        for m in SUMMARY_RE.finditer(output)
    ]
    actionable = bool(diagnostics)
    return {
        "status": "ACTIONABLE" if actionable else "UNCLASSIFIED",
        "diagnostics": diagnostics[:max_items],
        "testSummaries": summaries[-10:],
        "outputExcerpt": output[-10000:],
        "exitCode": result.get("exitCode")
    }
