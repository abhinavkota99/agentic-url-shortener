import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, DateTime, select, JSON, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.dialects.postgresql import JSONB
from .models import Workflow

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://app:app@localhost:5433/shortener")

class Base(DeclarativeBase):
    pass

class WorkflowRecord(Base):
    __tablename__ = "agent_workflows"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True, default="local-developer")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

_engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

def initialize_database():
    Base.metadata.create_all(_engine)
    # Upgrade databases created by earlier phases before owner_id was indexed.
    with _engine.begin() as connection:
        connection.execute(text("ALTER TABLE agent_workflows ADD COLUMN IF NOT EXISTS owner_id VARCHAR(100)"))
        connection.execute(text(
            "UPDATE agent_workflows SET owner_id = COALESCE(payload ->> 'owner_id', 'local-developer') "
            "WHERE owner_id IS NULL"
        ))
        connection.execute(text("ALTER TABLE agent_workflows ALTER COLUMN owner_id SET NOT NULL"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_agent_workflows_owner_id ON agent_workflows (owner_id)"))

class WorkflowStore:
    def save(self, workflow: Workflow):
        workflow.updated_at = datetime.now(timezone.utc)
        payload = workflow.model_dump(mode="json")
        with Session(_engine) as session, session.begin():
            record = session.get(WorkflowRecord, workflow.id)
            if record is None:
                session.add(WorkflowRecord(id=workflow.id, payload=payload, owner_id=workflow.owner_id, updated_at=workflow.updated_at))
            else:
                record.payload = payload
                record.owner_id = workflow.owner_id
                record.updated_at = workflow.updated_at

    def get(self, workflow_id: str) -> Workflow:
        with Session(_engine) as session:
            record = session.get(WorkflowRecord, workflow_id)
            if record is None:
                raise KeyError(workflow_id)
            return Workflow.model_validate(record.payload)

    def all(self, owner_id: str | None = None):
        with Session(_engine) as session:
            query = select(WorkflowRecord).order_by(WorkflowRecord.updated_at.desc())
            if owner_id is not None:
                query = query.where(WorkflowRecord.owner_id == owner_id)
            rows = session.scalars(query).all()
            return [Workflow.model_validate(row.payload) for row in rows]

store = WorkflowStore()
