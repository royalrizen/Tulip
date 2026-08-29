import os
from threading import Thread
from flask import Flask, render_template

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../..")
)

app = Flask(
    __name__,
    template_folder=os.path.join(
        BASE_DIR,
        "templates",
    ),
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
