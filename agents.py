from langgraph.prebuilt import create_react_agent

from llm import llm, ASSISTANT_SYSTEM_PROMPT
from tools import (
    think,
    task_form,
    add_task,
    process_tasks,
    get_task,
    get_tasks,
    list_tasks,
    update_task,
    complete_task,
    add_sub_task,
    complete_sub_task,
    delete_task,
    remove_all_tasks,
)


planner_agent = create_react_agent(
    model=llm,
    tools=[
        think,
        task_form,
    ],
    name="planner",
    prompt=(
        "You are a planning specialist. Use the think tool to reason step-by-step and outline an approach. "
        "If the user requests to enter task details via a form or a UI, immediately call the task_form tool to open the form. "
        "When planning is sufficient, delegate to task_manager to execute the plan."
    ),
)


task_agent = create_react_agent(
    model=llm,
    tools=[
        task_form,
        add_task,
        process_tasks,
        get_task,
        get_tasks,
        list_tasks,
        update_task,
        complete_task,
        add_sub_task,
        complete_sub_task,
        delete_task,
        remove_all_tasks,
    ],
    name="task_manager",
    prompt=ASSISTANT_SYSTEM_PROMPT,
) 