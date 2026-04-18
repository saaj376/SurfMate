# SurfMate

SurfMate is an **agentic AI browser automation** : a Gemini-powered agent that watches a live web page, reasons about its visual layout, and performs complex multi-step tasks entirely on its own — clicking buttons, filling forms, and verifying results — all without any scripted selectors or hardcoded flows.

The project ships a small Flask web app as the automation target (a user-management admin panel), but the real core is the agent itself: a persistent, vision-capable browser AI that receives natural-language instructions and executes them end-to-end.

---

## What Makes SurfMate Interesting

### Vision-first web understanding

Unlike traditional test automation or RPA tools that depend on CSS selectors or XPath, SurfMate's agent uses **`use_vision=True`** to perceive the page as a rendered screenshot. It locates UI elements the same way a human would — by looking at them. This means:

- No brittle element locators to maintain
- Works on any page the agent can visually parse
- Handles dynamic DOM changes gracefully

### Persistent browser + async task queue

The agent doesn't spin up a new browser per request. `app.py` launches a **persistent background `Browser` instance** in a daemon thread when the server starts. Incoming tasks are fed through an `asyncio` queue:

```
HTTP POST /api/agent
       │
       ▼
  task_queue (Python Queue)
       │
       ▼
  agent_worker_thread  ──►  execute_task_persistent(browser, task)
                                       │
                                       ▼
                               Browser-Use Agent
                              (Gemini 2.5 Flash + Vision)
                                       │
                                       ▼
                             result_queue  ──►  JSON response
```

This architecture keeps browser startup cost to **once per server lifetime**, making agent responses significantly faster after the first request.

### Natural-language task interface

You talk to the agent in plain English. It handles the rest:

```
"Create a user named Bob with email bob@test.com"
"Reset the password for Alice Johnson"
"Add a new user called Dana with email dana@corp.io"
```

The agent:
1. Navigates to the correct page if needed
2. Visually identifies the relevant form or button
3. Fills in fields or clicks actions
4. Waits for and reads success/error feedback
5. Returns a human-readable result summary

### Standalone CLI mode

`agent.py` can also be run directly from the command line, completely independently of the Flask app:

```bash
python agent.py "Create a user named Bob"
```

In CLI mode the agent boots its own browser, executes the task, then shuts down cleanly.

---

## Project Structure

```text
SurfMate/
├── agent.py                # Core AI agent: LLM setup, browser task execution, CLI entry point
├── app.py                  # Flask server: routes, background agent thread, task/result queues
├── update.py               # One-time helper to inject /bypass route into app.py
├── requirements.txt        # Python dependencies
├── templates/
│   ├── dashboard.html      # Automation target — user table, add/reset forms, agent chat panel
│   └── login.html          # Login page (also an automation target)
└── README.md
```

### Key files

| File | Role |
|---|---|
| `agent.py` | Houses all LLM and browser logic. `execute_task_persistent()` is called by the server; `execute_task()` is used by the CLI. Both build a Gemini LLM via LiteLLM and hand it to a `browser-use` `Agent`. |
| `app.py` | Flask app + agent orchestration. Starts the background worker thread, exposes `POST /api/agent`, and keeps the persistent `Browser` alive. |
| `dashboard.html` | The demo automation target. Renders user data, exposes "Add User" and "Reset Password" actions, and includes a built-in Agent Assistant chat panel that calls `/api/agent`. |

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI model | Google Gemini 2.5 Flash (`gemini/gemini-2.5-flash`) |
| LLM client | [LiteLLM](https://github.com/BerriAI/litellm) via `langchain-ollama` integration |
| Browser automation | [browser-use](https://github.com/browser-use/browser-use) |
| Vision | `use_vision=True` — agent reasons over page screenshots |
| Web server | Flask |

---

## Prerequisites

- Python 3.10+
- A valid **Google Gemini API key** (`GOOGLE_API_KEY` or `GEMINI_API_KEY`)
- An environment that can run a Chromium-based browser (headful or headless)

---

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/saaj376/SurfMate.git
   cd SurfMate
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate       # macOS / Linux
   .venv\Scripts\Activate.ps1      # Windows PowerShell
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with your API key:

   ```env
   GOOGLE_API_KEY=your_actual_key
   ```

   > `agent.py` accepts either `GOOGLE_API_KEY` or `GEMINI_API_KEY` and normalises to `GEMINI_API_KEY` internally for LiteLLM.

---

## Running

### Server mode (agent + web app together)

```bash
python app.py
```

The Flask app starts at `http://127.0.0.1:5000` and the background browser worker boots immediately.

Log in with the demo credentials (`admin` / `password123`) or navigate directly to `/bypass` to skip login and reach the dashboard.

The **Agent Assistant** panel on the dashboard lets you type natural-language tasks and see the agent's output in real time.

### CLI mode (agent only, no Flask)

Run the agent standalone against the already-running Flask app:

```bash
python agent.py "Reset the password for Brian Smith"
```

The CLI agent boots its own browser, navigates to the app, executes the task, prints the result, and exits.

---

## How the Agent Works (Deep Dive)

### LLM setup — `build_llm()`

```python
ChatLiteLLM(model="gemini/gemini-2.5-flash", temperature=0.0)
```

Temperature is set to **0.0** for deterministic, reliable task execution. The Gemini model is accessed through LiteLLM's unified interface, keeping the agent backend-agnostic.

### Vision-enabled Agent — `run_task()`

```python
Agent(task=task, llm=llm, browser=browser, use_vision=True)
```

`use_vision=True` tells `browser-use` to capture screenshots at each reasoning step and pass them to the LLM. The model sees the page layout, text, buttons, and form fields visually and decides what action to take next.

### Persistent execution — `execute_task_persistent()`

Used by the Flask background worker. The `Browser` object is created **once** at server startup and reused across all tasks. The agent's system prompt instructs it to:

- Navigate to `/bypass` only if it is not already on the dashboard
- Execute the user's task directly from the current page state if already there
- Confirm success via visible feedback before marking itself done

### One-shot execution — `execute_task()`

Used by the CLI. Creates a fresh `Browser`, runs the task end-to-end, and cleanly calls `browser.stop()` in a `finally` block.

### System prompt structure

Both execution modes build the same structured prompt:

```
You are an autonomous administrative agent.
[Navigation instruction based on current state]
Execute the user's requested core task: '{task_text}'

CRITICAL INSTRUCTIONS:
- Use your vision capabilities to locate elements directly on the screen.
- Find and click the necessary buttons.
- Verify that the action was successful by watching for success messages before calling done.
```

---

## Agent API

### `POST /api/agent`

Authenticated endpoint (requires active session) that enqueues a task for the background browser agent.

**Request:**

```json
{ "task": "Create a user named Dana with email dana@corp.io" }
```

**Response (success):**

```json
{ "result": "User Dana was successfully added to the list." }
```

**Response (error):**

```json
{ "error": "Missing GOOGLE_API_KEY. Add it to the .env file: ..." }
```

**Example with curl** (requires an active session cookie):

```bash
curl -X POST http://127.0.0.1:5000/api/agent \
  -H "Content-Type: application/json" \
  -b "session=<your-session-cookie>" \
  -d '{"task":"Create a user named Bob with email bob@test.com"}'
```

> Tip: Use the Agent Assistant panel in the dashboard UI to avoid managing session cookies manually.

---

## The Demo App (Automation Target)

The Flask app exists to give the agent a realistic, interactive target:

| Route | Description |
|---|---|
| `GET /` | Redirects to dashboard or login |
| `GET /login` | Login page |
| `POST /login` | Validates `admin` / `password123` |
| `GET /logout` | Clears session |
| `GET /dashboard` | Main dashboard (user table + agent panel) |
| `GET /bypass` | Skips login — used by agent to reach dashboard directly |
| `GET /api/users` | Returns current user list as JSON |
| `POST /dashboard/add` | Adds a user (`name`, `email` form fields) |
| `POST /dashboard/reset/<id>` | Simulates password reset |
| `POST /api/agent` | Enqueues a task for the AI agent |

---

## Troubleshooting

### `RuntimeError: Missing GOOGLE_API_KEY`

Add your Gemini API key to `.env`:

```env
GOOGLE_API_KEY=your_actual_key
```

### Agent is slow on first request

The browser launches at server startup, but the first LLM call and page navigation can take 20–30 seconds. Subsequent requests reuse the persistent browser and are faster.

### Agent returns an error result

Check the Flask console for stack traces. Common causes:

- Invalid or expired API key
- No browser runtime available in the environment
- Network access blocked for Gemini API calls

### Port conflict

Change the port in the final line of `app.py`:

```python
app.run(debug=True, port=5001)
```

---

## Development Tips

- Test agent logic directly: `python agent.py "your task here"`
- Quick syntax check: `python -m compileall app.py agent.py update.py`
- The agent's vision capabilities mean you can change dashboard HTML freely — no selectors to update in the agent code

---

## License

This project is licensed under the terms in [LICENSE](./LICENSE).
