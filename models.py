from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from datetime import datetime


def _validate_iso_date(value: Optional[str]) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("due_date must be in YYYY-MM-DD format") from exc
    return value


class SubTask(BaseModel):
    """
    Represents a sub-task with a name and completion status.
    """
    name: str = Field(..., description="The name of the sub-task.")
    is_completed: bool = Field(False, description="Whether the sub-task is completed.")


class Task(BaseModel):
    """
    Represents a task with rich metadata suitable for an assistant.
    """
    id: str = Field(..., description="The unique identifier of the task.")
    description: str = Field(..., description="The description of the task.")
    priority: int = Field(3, ge=1, le=5, description="Priority from 1 (high) to 5 (low).")
    status: Literal["todo", "in_progress", "done"] = Field(
        "todo", description="The current status of the task."
    )
    due_date: Optional[str] = Field(
        None, description="Optional due date in ISO format YYYY-MM-DD."
    )
    tags: List[str] = Field(default_factory=list, description="Tags associated with the task.")
    notes: Optional[str] = Field(None, description="Optional notes for the task.")

    # Backward-compat single sub-task field
    sub_task: Optional[SubTask] = Field(
        None, description="An optional single sub-task (backward compatibility)."
    )

    # Preferred: multiple subtasks
    sub_tasks: List[SubTask] = Field(
        default_factory=list, description="List of sub-tasks for this task."
    )

    @field_validator("due_date")
    def validate_due_date(cls, value: Optional[str]) -> Optional[str]:
        return _validate_iso_date(value) 