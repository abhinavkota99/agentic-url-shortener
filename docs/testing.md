# Testing Strategy

## Backend
- Unit tests: URL validation, short-code generation, expiration and service behavior.
- Integration tests: PostgreSQL uniqueness, Redis cache hit/miss and invalidation.
- API tests: create, retrieve, redirect, deactivate and analytics.
- Concurrency tests: simultaneous custom alias creation.
- Security tests: invalid schemes, malicious input, abuse/rate limiting.
- Load tests: redirect p50/p95/p99 and throughput.

## Orchestrator
- Agent contract tests: valid structured outputs.
- DAG tests: dependencies, cycle rejection and task readiness.
- Parallel execution tests: independent architecture/security and QA/docs branches.
- Governance tests: approval blocks implementation; rejection safe-stops.
- Recovery tests: retry budget, checkpoint restore and restart.
- Replanning tests: version increment and invalidation of impacted artifacts.
- End-to-end tests: all three scenarios.

Run Python tests with `pytest` after adding the test suite. Run backend tests with `mvn test`.
