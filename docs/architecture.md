# Architecture Overview

## Two bounded contexts
1. URL Shortener: Spring Boot modular monolith, PostgreSQL persistence, Redis cache.
2. Agentic SDLC Orchestrator: Python API and LangGraph workflow coordinating specialist agents.

## Orchestration lifecycle
Requirement analysis -> DAG planning -> architecture and security branches -> human approval -> implementation planning -> QA and documentation branches -> release readiness.

The workflow is stateful and stores artifacts, task statuses, approvals and audit events. The local starter store is in-memory; a production deployment must use durable PostgreSQL-backed repositories and LangGraph checkpoint storage.

## Parallelism and synchronization
Architecture and security assessment are independent after task decomposition. QA and documentation are independent after implementation. Release readiness waits for both.

## Governance
Implementation is blocked until design approval. Release agent emits a recommendation only; production deployment is never automatic in this prototype.
