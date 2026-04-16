# SurfMate

SurfMate is a Flask-based IT admin dashboard demo with an integrated browser automation agent.
It combines a small web app for user management with an AI assistant that can execute dashboard tasks through a real browser.

## Features

- Admin login and session-based authentication
- User table view powered by `/api/users`
- Add user and reset password flows from the dashboard UI
- AI Agent Assistant panel that accepts natural-language tasks
- Persistent browser worker thread for agent task execution
- CORS headers enabled for API accessibility

## Project Structure

```text
SurfMate/
├── app.py                  # Flask web app, routes, background agent thread
├── agent.py                # Browser-Use + LLM task execution logic
├── update.py               # Helper script that injects /bypass route into app.py
├── requirements.txt        # Python dependencies
├── templates/
│   ├── login.html          # Login page template
│   └── dashboard.html      # Dashboard + agent UI template
└── README.md
```

## Tech Stack

- Python 3
- Flask
- browser-use
- litellm + langchain-ollama integration package
- Gemini API (via `GOOGLE_API_KEY` / `GEMINI_API_KEY`)

## Prerequisites

- Python 3.10+
- pip
- A valid Google Gemini API key
- Environment capable of running a browser for `browser-use`

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/saaj376/SurfMate.git
   cd SurfMate
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   On Windows (PowerShell):

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root:

   ```env
   GOOGLE_API_KEY=your_actual_key
   ```

   > `agent.py` accepts `GOOGLE_API_KEY` or `GEMINI_API_KEY` and sets `GEMINI_API_KEY` internally for LiteLLM.

## Running the App

Start the Flask app:

```bash
python app.py
```

By default, the app runs at:

- `http://127.0.0.1:5000`

## Login

Use the built-in demo credentials:

- **Username:** `admin`
- **Password:** `password123`

You can also bypass login directly (demo route):

- `http://127.0.0.1:5000/bypass`

## Dashboard Capabilities

After login, `/dashboard` provides:

- **User listing** (fetched from `/api/users`)
- **Reset Password** per user (simulated success message)
- **Add User** form (`/dashboard/add`)
- **Agent Assistant** form that sends tasks to `/api/agent`

## Agent Overview

The AI agent pipeline is split across `app.py` and `agent.py`:

1. `app.py` starts a daemon worker thread.
2. The worker owns a persistent `Browser` instance.
3. Requests to `POST /api/agent` enqueue a task.
4. The worker calls `agent.execute_task_persistent(...)`.
5. The agent uses Gemini through LiteLLM and performs browser actions with vision enabled (`use_vision=True`).
6. The final extracted result is returned as JSON.

### Example Agent Request

```bash
curl -X POST http://127.0.0.1:5000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"task":"Create a user named Bob with email bob@test.com"}'
```

## API Endpoints

### `GET /`
Redirects to `/dashboard` if logged in, otherwise `/login`.

### `GET /login`
Renders login page.

### `POST /login`
Validates credentials and sets session.

### `GET /logout`
Clears session and redirects to login.

### `GET /dashboard`
Renders dashboard (requires login).

### `POST /dashboard/add`
Adds a user from form data (`name`, `email`).

### `POST /dashboard/reset/<user_id>`
Simulates password reset and returns success/error flash message.

### `GET /api/users`
Returns current in-memory user list as JSON.

### `POST /api/agent`
Runs agent task (requires login), expects:

```json
{ "task": "..." }
```

Returns:

```json
{ "result": "..." }
```

or an error payload.

## Notes & Limitations

- User data is stored in memory (resets on app restart).
- `app.secret_key` is hardcoded for local/demo usage.
- Login credentials are hardcoded.
- `/bypass` route intentionally skips auth for convenience/testing.
- Agent response time depends on browser startup/LLM latency.

## Troubleshooting

### `Missing GOOGLE_API_KEY`
Set `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) in `.env`.

### Agent requests return errors
Check:

- API key validity
- Browser runtime availability
- Network access for model calls
- Flask console logs for stack traces

### Port already in use
Run on another port by updating `app.run(...)` in `app.py`.

## Development Tips

- Use `python -m compileall app.py agent.py update.py` for quick syntax checks.
- Keep the Flask app running while testing `/api/agent` from the dashboard or `curl`.
- Update templates in `templates/` to modify the UI.

## License

This project is licensed under the terms in [LICENSE](./LICENSE).
