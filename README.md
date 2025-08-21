# Agent Chat with Task Memory (LangGraph + FastAPI)

A small, full‑stack example of a multi‑agent assistant built with LangGraph and LangChain, featuring a streaming web UI (FastAPI + Jinja + HTMX + Tailwind) and persistent memory. The assistant manages tasks via structured tools and a planner/worker split:

- Planner agent: reasons with a lightweight "think" tool and can open a task form UI on demand.
- Task manager agent: executes concrete CRUD operations via tools on Task objects (create, list, update, complete, delete, sub‑tasks).
- Supervisor: orchestrates the two agents and emits a final answer.

State is persisted in two ways:
- Task data in `tasks.json` for simple local storage.
- Conversation/graph state via LangGraph SQLite checkpointer in `checkpoint.db` (keyed by a per‑user `thread_id` cookie in the web UI).

---

## Features

- Multi‑agent architecture (planner + task manager) supervised into a single graph
- Rich toolset for tasks: add, list/filter, update, complete, delete, sub‑tasks, batch processing
- "Think" tool to append reasoning to an in‑memory log (no external side effects)
- Streaming responses over Server‑Sent Events with live step/status updates
- Automatic UI form injection when the agent calls `task_form`
- Persistent memory per conversation thread via LangGraph SqliteSaver
- Modern, minimal UI with Tailwind, HTMX, and Hyperscript

---

## Repository Layout

- `app.py` — Constructs the LangGraph supervisor with the planner and task_manager agents, and compiles the graph with checkpointing.
- `agents.py` — Defines the two ReAct agents and assigns tools/prompts.
- `tools.py` — All task tools (`add_task`, `list_tasks`, `update_task`, `complete_task`, `add_sub_task`, `complete_sub_task`, `delete_task`, `remove_all_tasks`, `process_tasks`) plus `task_form` and `think`.
- `models.py` — Pydantic models: `Task` and `SubTask`, plus date validation.
- `storage.py` — In‑memory state, JSON persistence to `tasks.json`, and formatting helpers.
- `checkpoint.py` — Configures LangGraph SQLite checkpointer (`checkpoint.db`).
- `llm.py` — Initializes the chat model via LangChain (`init_chat_model`).
- `server.py` — FastAPI app, endpoints, and SSE streaming logic. Renders Jinja templates.
- `templates/` — Jinja templates for the chat UI and partials (message bubbles, streaming blocks, task form).
- `static/` — Static assets (CSS) used by the templates.
- `main.py` — Simple CLI loop to chat with the agent in the terminal.
- `langgraph.json` — LangGraph CLI config mapping `app.py:graph` and referencing `.env`.
- `tasks.json` — Local persisted tasks (written by the app).

---

## How It Works

1. The web server (`server.py`) serves a chat UI at `/`.
2. When a message is sent, the server returns a partial that immediately starts an SSE stream to `/stream`.
3. The compiled LangGraph (`app.py`) streams events. The server surfaces tool/step names as status lines and collects the final assistant text to render as a chat bubble.
4. If the agent invokes `task_form` (or heuristically mentions a form), the server injects a rich HTML form into the chat. Submitting that form silently streams another run that creates a task via `add_task`.
5. Tasks are stored in `tasks.json`; graph state is checkpointed in `checkpoint.db` so subsequent messages for the same `thread_id` can carry context.

---

## Requirements

- Python 3.10+
- An LLM provider key (OpenAI by default)

Python dependencies are listed in `requirements.txt`:

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
jinja2==3.1.4
langchain==0.2.14
langgraph==0.2.18
openai==1.51.2
pydantic==2.8.2
numpy==1.26.4
scipy==1.13.1
python-dotenv==1.0.1
python-multipart==0.0.9
```

---

## Setup

1. Create and activate a virtual environment
   - macOS/Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables
   - Create a `.env` file (the repo includes an example) and set at least:
     ```env
     OPENAI_API_KEY=sk-...
     LANGSMITH_PROJECT=react-agent  # optional, for tracing
     ```
   - Important: `llm.py` currently sets an API key via `os.environ[...]` in code. For security, you should remove hard‑coded keys and rely on environment variables instead.

---

## Running

### Web UI (recommended)

- Development run (auto‑reload):
  ```bash
  uvicorn server:app --reload
  # or: python server.py
  ```
- Open http://localhost:8000 in your browser.

What you’ll see:
- A chat interface that streams status updates while the agent works.
- Ask for a task form (e.g., “Open the task form”); the agent calls `task_form`, and the UI displays a form. Submitting it drives a background run that creates the task.
- Use natural language to add, list, update, or complete tasks; the agent calls the appropriate tools.

### CLI chat

```bash
python main.py
```
Type your messages; type `exit` to quit.

---

## API Endpoints

- `GET /` — Chat page with a per‑user `thread_id` cookie.
- `POST /send` — Accepts the user message and returns a partial that starts streaming.
- `GET /stream` — Server‑Sent Events stream of status lines and final assistant output.
- `POST /submit_task_form` — Handles the injected task form submission; kicks off a silent streaming run.
- `POST /reset` — Clears the `thread_id` cookie to start a new conversation thread.

---

## Data & Persistence

- `tasks.json` — JSON file storing tasks added/updated via tools.
- `checkpoint.db` — SQLite DB used by LangGraph’s `SqliteSaver` for checkpointing. This provides per‑thread conversational state.
- `.langgraph_api/` — Internal LangGraph CLI artifacts (if you use the CLI).

To clear state:
- Delete `tasks.json` to remove all tasks, or use the `remove_all_tasks` tool via chat.
- Delete `checkpoint.db` to reset conversation state across all threads.

---

## Models and Tools

- `Task` fields: `id`, `description`, `priority` (1–5), `status` (`todo|in_progress|done`), `due_date` (YYYY‑MM‑DD), `tags[]`, `notes`, optional `sub_task`, and preferred `sub_tasks[]`.
- Task filters (in `list_tasks`): status, priority range, tag, due date range, free‑text search.
- `think(thought)` appends to an in‑memory `thought_log` (no external side effects).

---

## Notes & Caveats

- Security: Do not commit API keys to source control. Move any hard‑coded keys out of `llm.py` and into `.env` or runtime environment variables.
- Encoding: If you see odd placeholder characters in rendered output, ensure your terminal and files use UTF‑8 encoding.
- The import `from langgraph_supervisor import create_supervisor` assumes the helper is available in your environment; if you don’t have it, you can replace it with LangGraph’s standard supervisor pattern or install the missing module.

---

## Acknowledgements

- [LangGraph](https://github.com/langchain-ai/langgraph)
- [LangChain](https://github.com/langchain-ai/langchain)
- [FastAPI](https://fastapi.tiangolo.com/)
- [HTMX](https://htmx.org/), [Hyperscript](https://hyperscript.org/), and [Tailwind CSS](https://tailwindcss.com/)
