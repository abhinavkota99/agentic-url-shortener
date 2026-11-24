from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from uuid import uuid4

class Scenario(str, Enum):
    GREENFIELD = "GREENFIELD"
    BROWNFIELD = "BROWNFIELD"
    AMBIGUOUS = "AMBIGUOUS"

class WorkflowStatus(str, Enum):
    INITIATED = "INITIATED"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    REPLANNING = "REPLANNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SAFE_STOPPED = "SAFE_STOPPED"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"

class WorkflowRequest(BaseModel):
    requirement: str = Field(min_length=10, max_length=10000)
    scenario: Scenario = Scenario.GREENFIELD
    autonomyLevel: str = "CONTROLLED"

class Task(BaseModel):
    id: str
    name: str
    agent: str
    dependencies: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    retries: int = 0
    max_retries: int = 2
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

class Workflow(BaseModel):
    id: str = Field(default_factory=lambda: f"WF-{uuid4().hex[:10]}")
    requirement: str
    scenario: Scenario
    owner_id: str = "local-developer"
    status: WorkflowStatus = WorkflowStatus.INITIATED
    current_stage: str = "REQUIREMENT_ANALYSIS"
    requirement_version: int = 1
    graph_thread_id: str | None = None
    tasks: list[Task] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    audit: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
