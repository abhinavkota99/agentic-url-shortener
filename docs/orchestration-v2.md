# Orchestration V2

- Workflow records are stored in PostgreSQL via SQLAlchemy.
- LangGraph uses PostgreSQL checkpointing when `DATABASE_URL` is configured.
- The graph pauses at an interrupt before implementation; approve/reject endpoints resume the same graph thread.
- Architecture and security branches fan out after planning and synchronize before approval.
- QA and documentation branches fan out after implementation and synchronize before release readiness.
- `dag.py` validates task IDs, unknown dependencies, cycles and computes topological execution levels.
- Retry delay helper uses bounded exponential backoff.

## Operational note
For production, use a dedicated connection pool lifecycle for `PostgresSaver`, protect the approval endpoints with RBAC, and make replan create a new immutable workflow version while retaining a stable parent workflow ID. Configure migrations rather than `create_all`.
