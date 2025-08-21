from typing import List, Optional, Literal
from datetime import datetime

from langchain_core.tools import tool

from models import Task, SubTask, _validate_iso_date
from storage import processed_tasks, _save_tasks, _format_task, thought_log


@tool
def task_form() -> str:
    """
    Request the UI to display a task creation form for the user to fill in.

    Use this when the user asks to enter task details via a form. The frontend
    will capture user inputs and submit them back to the assistant in the
    background, which should then create the task via add_task.
    """
    # Special marker for the UI layer to detect and show the form immediately during streaming
    return "[[TASK_FORM_UI]]"


@tool
def add_task(task: Task) -> str:
    """
    Create or replace a task by ID with rich metadata.

    Args:
        task: A Task object to create or replace.
    """
    processed_tasks[task.id] = task
    _save_tasks()
    return f"Saved: {_format_task(task)}"


@tool
def process_tasks(tasks: List[Task]) -> str:
    """
    Process a list of tasks by storing or updating them by their IDs.

    Args:
        tasks: A list of Task objects to be processed.
    """
    results = []
    for task in tasks:
        processed_tasks[task.id] = task
        results.append(_format_task(task))
    _save_tasks()
    return f"Processed {len(tasks)} task(s):\n" + "\n".join(results)


@tool
def get_task(task_id: str) -> str:
    """
    Retrieve a specific task by ID.

    Args:
        task_id: The ID of the task to retrieve.
    """
    task = processed_tasks.get(task_id)
    if not task:
        return f"Task with ID '{task_id}' not found."
    return _format_task(task)


@tool
def get_tasks() -> str:
    """
    Retrieve all processed tasks.
    """
    if not processed_tasks:
        return "No tasks have been processed yet."
    return "\n".join([_format_task(task) for task in processed_tasks.values()])


@tool
def list_tasks(
    filter_status: Optional[Literal["todo", "in_progress", "done"]] = None,
    min_priority: Optional[int] = None,
    max_priority: Optional[int] = None,
    tag: Optional[str] = None,
    due_before: Optional[str] = None,
    due_after: Optional[str] = None,
    search: Optional[str] = None,
) -> str:
    """
    List tasks with optional filtering by status, priority range, tag, due date range, or search text.

    Date filters use YYYY-MM-DD.
    """
    def parse_date(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            return None

    d_before = parse_date(due_before)
    d_after = parse_date(due_after)

    def include(task: Task) -> bool:
        if filter_status and task.status != filter_status:
            return False
        if min_priority is not None and task.priority < min_priority:
            return False
        if max_priority is not None and task.priority > max_priority:
            return False
        if tag and tag not in task.tags:
            return False
        if d_before and task.due_date:
            try:
                if datetime.strptime(task.due_date, "%Y-%m-%d") >= d_before:
                    pass
            except ValueError:
                return False
        if d_after and task.due_date:
            try:
                if datetime.strptime(task.due_date, "%Y-%m-%d") <= d_after:
                    pass
            except ValueError:
                return False
        if search:
            s = search.lower()
            haystack = " ".join([
                task.id,
                task.description,
                " ".join(task.tags),
                task.notes or "",
            ]).lower()
            if s not in haystack:
                return False
        return True

    filtered = [task for task in processed_tasks.values() if include(task)]
    if not filtered:
        return "No tasks match the given filters."
    return "\n".join([_format_task(t) for t in filtered])


@tool
def update_task(
    task_id: str,
    description: Optional[str] = None,
    priority: Optional[int] = None,
    status: Optional[Literal["todo", "in_progress", "done"]] = None,
    due_date: Optional[str] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Update fields of a task by ID. Only provided fields are changed.
    """
    task = processed_tasks.get(task_id)
    if not task:
        return f"Task with ID '{task_id}' not found."

    if description is not None:
        task.description = description
    if priority is not None:
        if not (1 <= priority <= 5):
            return "priority must be between 1 and 5"
        task.priority = priority
    if status is not None:
        task.status = status
    if due_date is not None:
        # validate via helper
        try:
            _validate_iso_date(due_date)
        except Exception as e:
            return str(e)
        task.due_date = due_date or None
    if tags is not None:
        task.tags = tags
    if notes is not None:
        task.notes = notes

    processed_tasks[task_id] = task
    _save_tasks()
    return f"Updated: {_format_task(task)}"


@tool
def complete_task(task_id: str) -> str:
    """
    Mark a task as done.
    """
    task = processed_tasks.get(task_id)
    if not task:
        return f"Task with ID '{task_id}' not found."
    task.status = "done"
    processed_tasks[task_id] = task
    _save_tasks()
    return f"Completed: {_format_task(task)}"


@tool
def add_sub_task(task_id: str, name: str) -> str:
    """
    Add a sub-task to a task.
    """
    task = processed_tasks.get(task_id)
    if not task:
        return f"Task with ID '{task_id}' not found."
    task.sub_tasks.append(SubTask(name=name, is_completed=False))
    processed_tasks[task_id] = task
    _save_tasks()
    return f"Added sub-task to {task_id}: {name}"


@tool
def complete_sub_task(task_id: str, sub_task_name: str) -> str:
    """
    Mark a sub-task complete by name.
    """
    task = processed_tasks.get(task_id)
    if not task:
        return f"Task with ID '{task_id}' not found."
    for st in task.sub_tasks:
        if st.name == sub_task_name:
            st.is_completed = True
            _save_tasks()
            return f"Completed sub-task '{sub_task_name}' in {task_id}."
    return f"Sub-task '{sub_task_name}' not found in {task_id}."


@tool
def delete_task(task_id: str) -> str:
    """
    Delete a specific task by its ID.
    """
    if task_id in processed_tasks:
        deleted_task = processed_tasks.pop(task_id)
        _save_tasks()
        return f"Deleted: {task_id} ('{deleted_task.description}')"
    else:
        return f"Task with ID '{task_id}' not found."


@tool
def remove_all_tasks() -> str:
    """
    Remove all processed tasks.
    """
    count = len(processed_tasks)
    processed_tasks.clear()
    _save_tasks()
    return f"Successfully removed all {count} task(s)."


@tool
def think(thought: str) -> str:
    """
    Use this tool to think about something. It will not obtain new information or change the database, 
    but just append the thought to the log. Use it when complex reasoning or some cache memory is needed.
    """
    thought_log.append(thought)
    return f"{thought}" 