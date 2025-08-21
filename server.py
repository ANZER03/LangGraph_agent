from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
import uuid
import urllib.parse
import time

from app import graph


app = FastAPI(title="Agent Chat")

# Static dir placeholder (for potential future assets). Not strictly needed for Tailwind CDN.
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def get_thread_id(request: Request) -> str:
    # Use a cookie-based thread id; generate if missing
    thread_id = request.cookies.get("thread_id")
    if not thread_id:
        thread_id = uuid.uuid4().hex
    return thread_id


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, thread_id: str = Depends(get_thread_id)):
    # Initial empty chat
    response = templates.TemplateResponse(
        "index.html",
        {"request": request, "messages": [], "thread_id": thread_id},
    )
    # Set cookie if not present
    if not request.cookies.get("thread_id"):
        response.set_cookie("thread_id", thread_id, httponly=True, samesite="lax")
    return response


@app.post("/send", response_class=HTMLResponse)
async def send_message(request: Request, thread_id: str = Depends(get_thread_id)):
    form = await request.form()
    user_text = (form.get("message") or "").strip()
    if not user_text:
        return HTMLResponse("", status_code=204)

    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [("user", user_text)]}

    # Streaming mode: return a fragment that renders the user bubble and
    # starts an EventSource connection that streams status + final assistant.
    run_id = uuid.uuid4().hex
    q_enc = urllib.parse.quote_plus(user_text)

    return templates.TemplateResponse(
        "partials/stream_init.html",
        {
            "request": request,
            "thread_id": thread_id,
            "user_content": user_text,
            "run_id": run_id,
            "q_enc": q_enc,
        },
    )


def _sse_event(event: str, data: str) -> str:
    """Format a Server-Sent Event string for StreamingResponse."""
    # Ensure each line of data is prefixed with 'data: '
    # and terminate the event with a blank line
    if data is None:
        data = ""
    # Replace CR to avoid breaking SSE framing
    data = data.replace("\r", "")
    payload_lines = [f"data: {line}" for line in data.split("\n")]
    payload = "\n".join(payload_lines)
    return f"event: {event}\n{payload}\n\n"


@app.get("/stream")
async def stream_events(request: Request):
    thread_id = request.query_params.get("thread_id") or ""
    q = request.query_params.get("q") or ""
    run_id = request.query_params.get("rid") or uuid.uuid4().hex

    async def event_generator():
        # Initial status
        yield _sse_event("status", "Queued…")

        config = {"configurable": {"thread_id": thread_id}}
        inputs = {"messages": [("user", q)]}

        final_text_any = ""
        last_non_supervisor_assistant = None
        form_injected = False
        step = 0
        try:
            for event in graph.stream(inputs, config=config, stream_mode="values"):
                step += 1
                # Try to surface meaningful status based on the newest message
                try:
                    msg = event["messages"][~0]
                    if isinstance(msg, tuple):
                        role, content = msg
                        name = None
                    else:
                        role = getattr(msg, "type", "assistant")
                        name = getattr(msg, "name", None)
                        content = getattr(msg, "content", str(msg))

                    role_lower = (role or "").lower()
                    name_lower = (name or "").lower()

                    # Track assistant output while ignoring supervisor finals
                    if role_lower in ("ai", "assistant"):
                        final_text_any = content
                        if not (name_lower and "supervisor" in name_lower):
                            last_non_supervisor_assistant = content
                        # Heuristic: if assistant says to fill a form, inject the UI form
                        if not form_injected:
                            try:
                                c = (content or "").lower()
                                if (
                                    ("form" in c and ("fill" in c or "below" in c))
                                    or ("title:" in c and "priority" in c and "due" in c)
                                ):
                                    tmpl = templates.get_template("partials/task_form.html")
                                    form_html = tmpl.render(thread_id=thread_id)
                                    yield _sse_event("ui", form_html)
                                    form_injected = True
                            except Exception:
                                pass

                    # Detect task_form either by tool name or by special marker in content
                    try:
                        should_inject_form = (
                            (role_lower == "tool" and name_lower == "task_form") or
                            (isinstance(content, str) and "[[TASK_FORM_UI]]" in content)
                        )
                    except Exception:
                        should_inject_form = False
                    if should_inject_form and not form_injected:
                        try:
                            tmpl = templates.get_template("partials/task_form.html")
                            form_html = tmpl.render(thread_id=thread_id)
                            yield _sse_event("ui", form_html)
                            form_injected = True
                        except Exception:
                            yield _sse_event("status", "UI: task form unavailable")

                    # Only show summarized, tool/step-like statuses; skip user/assistant and supervisor
                    if role_lower in ("user", "ai", "assistant"):
                        continue
                    if name_lower and "supervisor" in name_lower:
                        continue

                    if role_lower == "tool" and name:
                        status_line = f"Tool: {name}"
                    elif name:
                        status_line = f"Step: {name}"
                    else:
                        status_line = f"{role.capitalize()}"

                    yield _sse_event("status", status_line)
                except Exception:
                    # Fallback generic status
                    yield _sse_event("status", f"Processing… step {step}")
        except Exception as e:
            final_text_any = f"Error: {e}"

        # Prefer last non-supervisor assistant text; otherwise fall back to any assistant text
        final_text_to_send = last_non_supervisor_assistant or final_text_any or ""

        # Render final assistant bubble HTML and send as 'final' (skip if empty)
        if final_text_to_send:
            tmpl = templates.get_template("partials/message.html")
            final_html = tmpl.render(role="assistant", content=final_text_to_send)
            yield _sse_event("final", final_html)
        else:
            yield _sse_event("final", "")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/reset", response_class=HTMLResponse)
async def reset_chat(request: Request):
    # Drop cookie so a new thread_id will be generated
    response = HTMLResponse("")
    response.delete_cookie("thread_id")
    return response


@app.post("/submit_task_form", response_class=HTMLResponse)
async def submit_task_form(request: Request, thread_id: str = Depends(get_thread_id)):
    form = await request.form()
    # Gather fields from form
    task_id = (form.get("task_id") or "").strip()
    description = (form.get("description") or "").strip()
    priority = (form.get("priority") or "").strip()
    status = (form.get("status") or "").strip()
    due_date = (form.get("due_date") or "").strip()
    tags = (form.get("tags") or "").strip()
    notes = (form.get("notes") or "").strip()

    # Build a concise instruction for the agent to create the task via tools
    # We do not show this message in the UI; it will stream in background and append only assistant output
    instruction_lines = [
        "Create a task using the add_task tool with the following details:",
        f"id: {task_id}",
        f"description: {description}",
        f"priority: {priority or '3'}",
        f"status: {status or 'todo'}",
        f"due_date: {due_date}",
        f"tags: {tags}",
        f"notes: {notes}",
    ]
    q = "\n".join(instruction_lines)

    run_id = uuid.uuid4().hex
    return templates.TemplateResponse(
        "partials/silent_stream_init.html",
        {
            "request": request,
            "thread_id": thread_id,
            "run_id": run_id,
            "user_content": q,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)


