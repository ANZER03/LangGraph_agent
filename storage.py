import json
import os
from typing import Dict, List
from datetime import datetime

from models import Task, SubTask


# In-memory state and persistence
TASKS_PATH = os.path.join(os.path.dirname(__file__), "tasks.json")
processed_tasks: Dict[str, Task] = {}
thought_log: List[str] = []


def _task_to_dict(task: Task) -> dict:
    # Support Pydantic v1 and v2
    try:
        return task.model_dump()
    except AttributeError:
        return task.dict()


def _save_tasks() -> None:
    serializable = {task_id: _task_to_dict(task) for task_id, task in processed_tasks.items()}
    with open(TASKS_PATH, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)


def _load_tasks() -> None:
    if not os.path.exists(TASKS_PATH):
        return
    try:
        with open(TASKS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return
        for task_id, task_payload in data.items():
            # Backward-compat for old schema
            if isinstance(task_payload, dict) and "sub_tasks" not in task_payload:
                task_payload["sub_tasks"] = []
            processed_tasks[task_id] = Task(**task_payload)
    except Exception:
        # Ignore corrupted storage to avoid crashing the agent
        pass


def _format_task(task: Task) -> str:
    parts: List[str] = []
    parts.append(f"[{task.status.upper()}] {task.id}: '{task.description}' (priority {task.priority})")
    if task.due_date:
        parts.append(f"due {task.due_date}")
    if task.tags:
        parts.append("tags: " + ", ".join(task.tags))
    if task.sub_task:
        parts.append(
            f"subtask: '{task.sub_task.name}' (Completed: {task.sub_task.is_completed})"
        )
    if task.sub_tasks:
        subs = "; ".join([f"{st.name}{'✔' if st.is_completed else ''}" for st in task.sub_tasks])
        parts.append(f"subtasks: [{subs}]")
    if task.notes:
        parts.append(f"notes: {task.notes}")
    return ", ".join(parts)


# Initialize on import
_load_tasks() 