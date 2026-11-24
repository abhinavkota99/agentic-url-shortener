# Limitations, Risks and Next Steps

1. Orchestrator workflow state is in-memory in this increment. Use PostgreSQL and LangGraph persistent checkpointer for restart-safe production operation.
2. Agent implementation currently generates structured plans/artifacts; it does not autonomously write arbitrary repository code. Add isolated Git worktrees and sandboxed code tools as a separately governed capability.
3. Retry and rollback policies are represented in task models and governance design; robust transient-failure orchestration and compensating actions need additional integration tests.
4. Analytics persistence is synchronous in this increment. Use a durable event broker and idempotent consumers for high-volume analytics.
5. The URL service has basic URL scheme validation, but public production deployment needs authentication, authorization, abuse prevention, domain reputation checks and stronger rate limiting.
6. `ddl-auto: update` is for local prototyping. Use Flyway/Liquibase migrations in production.
7. No performance figures are claimed until load tests are executed.
