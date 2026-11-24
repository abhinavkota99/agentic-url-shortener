-- Phase 5 migration for databases created by Phases 1-4.
ALTER TABLE agent_workflows
    ADD COLUMN IF NOT EXISTS owner_id VARCHAR(100);

UPDATE agent_workflows
SET owner_id = COALESCE(payload ->> 'owner_id', 'local-developer')
WHERE owner_id IS NULL;

ALTER TABLE agent_workflows
    ALTER COLUMN owner_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_agent_workflows_owner_id
    ON agent_workflows (owner_id);
