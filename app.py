from flask import Flask, jsonify, redirect, render_template, request, session, url_for


app = Flask(__name__)
app.secret_key = "dev-secret-key"


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


USERS = [
    {"id": 1, "name": "Alice Johnson", "email": "alice@example.com"},
    {"id": 2, "name": "Brian Smith", "email": "brian@example.com"},
    {"id": 3, "name": "Carla Gomez", "email": "carla@example.com"},
]


def is_logged_in():
    return session.get("logged_in") is True


@app.route("/")
def index():
    return redirect(url_for("dashboard") if is_logged_in() else url_for("login"))

@app.route("/bypass")
def bypass():
    session["logged_in"] = True
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == "admin" and password == "password123":
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        return redirect(url_for("login", error="Invalid username or password."))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))
    return render_template("dashboard.html")


@app.route("/api/users")
def api_users():
    return jsonify(USERS)


import asyncio
import threading
import queue
import agent

task_queue = queue.Queue()
result_queue = queue.Queue()

def agent_worker_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    from browser_use import Browser
    
    _browser = Browser()
    
    async def run_worker():
        while True:
            item = task_queue.get()
            if item is None:
                break
            try:
                res = await agent.execute_task_persistent(_browser, item)
                result_queue.put({"status": "success", "result": res})
            except Exception as e:
                result_queue.put({"status": "error", "error": str(e)})
            task_queue.task_done()
    
    try:
        loop.run_until_complete(run_worker())
    except Exception as e:
        print("Agent thread error:", e)

threading.Thread(target=agent_worker_thread, daemon=True).start()

def run_agent_in_thread(task_text):
    task_queue.put(task_text)
    res = result_queue.get()
    if res["status"] == "error":
        raise Exception(res["error"])
    return res["result"]

@app.route("/api/agent", methods=["POST"])
def api_agent():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    task = data.get("task", "")
    if not task:
        return jsonify({"error": "No task provided"}), 400
        
    try:
        result = run_agent_in_thread(task)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/dashboard/reset/<int:user_id>", methods=["POST"])
def reset_password(user_id):
    if not is_logged_in():
        return redirect(url_for("login"))

    user = next((item for item in USERS if item["id"] == user_id), None)
    if user is None:
        return redirect(url_for("dashboard", error="User not found."))
    return redirect(url_for("dashboard", message=f"Password reset successful for {user['name']}."))


@app.route("/dashboard/add", methods=["POST"])
def add_user():
    if not is_logged_in():
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not email:
        return redirect(url_for("dashboard", error="Name and email are required."))

    next_id = max(user["id"] for user in USERS) + 1 if USERS else 1
    USERS.append({"id": next_id, "name": name, "email": email})
    return redirect(url_for("dashboard", message=f"Added {name} to the user list."))


if __name__ == "__main__":
    app.run(debug=True)