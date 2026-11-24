# Phase 3: Controlled Code Generation and Validation

## Flow
1. Human approves architecture.
2. Developer agent creates an isolated workspace from the backend snapshot.
3. LLM may return strict JSON containing file paths and file contents. If no provider is configured, a deterministic Java expiration policy and JUnit tests are generated.
4. Workspace policy permits writes only beneath `src/main/java/` and `src/test/java/`, plus README. Build/runtime configuration and scripts are protected.
5. A Git baseline commit is created; generated changes are exposed as a diff.
6. QA invokes a fixed Maven test command inside Docker.
7. Docker container uses no network, read-only root, host-mapped unprivileged UID/GID where supported, dropped capabilities, no-new-privileges, memory/CPU/PID limits and a read-only local Maven cache.
8. Release readiness fails closed unless sandbox tests pass and there are no security blockers.
9. A human may create a local commit after successful validation. No push or deployment endpoint exists.

## Sandbox prerequisites
- Docker CLI and daemon.
- Maven dependencies already present in `~/.m2` (or set `MAVEN_CACHE` to a pre-populated cache).
- Set `MAVEN_SANDBOX_IMAGE` to a preloaded Maven + JDK 21 image if using an offline environment.

The test container has `--network none`; this prevents dependency downloads during the run. Prewarm the Maven cache in a separate trusted build step before running the workflow.

## Security boundaries
- Agent cannot supply a shell command.
- Agent cannot change Maven POM or runtime configuration.
- Agent cannot write outside the workspace or to protected paths.
- The only executed command is the hard-coded `mvn -B -ntp test` inside Docker.
- The container has no network, no Linux capabilities, restricted resources and read-only root.
- Generated diff must be reviewed before a human local commit.


## Deterministic fallback feature
When no LLM API key is configured, the fallback performs a concrete brownfield enhancement:
- Adds `PATCH /api/v1/urls/{code}/expiry`.
- Validates that a non-null expiry is in the future.
- Updates URL metadata and invalidates the Redis cache.
- Adds a reusable expiration policy and JUnit tests.


## Validation retry
`POST /api/workflows/{id}/retry-validation` retries a failed QA task up to its configured retry budget. It does not rerun code generation or alter the approved code artifact. A new code change requires a new workflow/approval.
