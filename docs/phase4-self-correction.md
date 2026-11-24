# Phase 4: Evidence-based self-correction

## Workflow

After human design approval, the implementation agent generates code in the isolated Git workspace. The QA node executes the fixed Maven test command in the restricted Docker sandbox. When Maven returns `FAILED`, the diagnostics node extracts allowlisted Java compiler locations, test-failure identifiers, and test summaries. The correction agent receives only this evidence and a bounded output excerpt, proposes complete source/test files, and submits them through the same path policy and code scanner used by initial generation. QA runs again only when a patch was safely applied.

## Safety limits

- Maximum two automatic correction attempts after the initial QA run.
- Only `src/main/java/` and `src/test/java/` can be changed by the correction agent.
- Build files, runtime configuration, Docker files, scripts, and security policy remain protected.
- Agent output is strict JSON and is never executed as a shell command.
- Compiler/test output is treated as untrusted diagnostic data, not instructions.
- No correction is attempted for `BLOCKED`, `TIMED_OUT`, or unclassified failures.
- A correction that fails policy validation, has no files, or cannot be generated stops the loop.
- Release readiness still requires QA `PASSED` and zero security blockers.
- No push or deployment capability is introduced.

## Observability

Workflow artifacts retain `qa_attempts`, `correction_attempts`, structured `diagnostics`, the latest `correction`, and `correction_history`. The QA task output records the attempt counts. The existing audit log records final workflow validation status.

## Endpoints

- `GET /api/workflows/{workflow_id}/artifacts` returns QA, diagnostics, correction, and correction history.
- `GET /api/workflows/{workflow_id}/diff` returns the current staged Git diff.
- `POST /api/workflows/{workflow_id}/commit` remains restricted to successfully completed workflows.

## Operational caveat

A Docker sandbox `BLOCKED` result means the environment could not run QA. It is not evidence of a source-code defect and does not trigger self-correction. The operator must install/configure Docker and retry validation. Actual Maven/Docker integration still needs to be run in an environment with Docker available.
