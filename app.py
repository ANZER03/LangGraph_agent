from langgraph_supervisor import create_supervisor

from llm import llm
from agents import planner_agent, task_agent
from checkpoint import checkpointer

workflow = create_supervisor(
    [planner_agent, task_agent],
    model=llm,
    prompt=(
        "You are a team supervisor managing a planner and a task manager. "
        "Use planner for ambiguous requests and to capture reasoning with the think tool. "
        "Use task_manager for concrete task CRUD, listing, and updates. "
        "Provide the best final answer once the appropriate agent completes the work."
    ),
)

graph = workflow.compile(checkpointer=checkpointer) 