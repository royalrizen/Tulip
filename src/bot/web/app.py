import os
from threading import Thread
from flask import Flask, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "web", "templates")

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
)

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/health")
def health():
    return {"status": "ok"}, 200

def run_web():
    port = int(os.getenv("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port,
    )

def start_web():
    Thread(
        target=run_web,
        daemon=True,
    ).start()
