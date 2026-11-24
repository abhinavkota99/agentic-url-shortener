# Architecture Decision Records

## ADR-001: Modular monolith for URL shortener
Decision: Start with a modular Spring Boot application.
Reason: The assignment has a short delivery window; module boundaries preserve maintainability without distributed-system overhead.
Trade-off: Independent scaling of analytics and redirects is deferred.

## ADR-002: PostgreSQL for URL metadata
Decision: Use PostgreSQL with a unique constraint on short_code.
Reason: Transactional persistence and uniqueness are central to URL creation.
Trade-off: Very large analytics workloads may require partitioning or a separate analytical store.

## ADR-003: Redis cache-aside for redirects
Decision: Cache code-to-destination mapping.
Reason: Redirect is the high-read path.
Trade-off: Cache invalidation is required on deactivation and updates.

## ADR-004: LangGraph orchestration
Decision: Represent SDLC execution as a state graph.
Reason: Conditional routing, parallel branches and stateful workflow composition are first-class requirements.
Trade-off: Requires explicit state schemas and operational checkpoint management.

## ADR-005: Human approval before implementation
Decision: Pause before implementation and require explicit approval.
Reason: Demonstrates controlled autonomy and change governance.
Trade-off: Human wait time increases workflow latency.
