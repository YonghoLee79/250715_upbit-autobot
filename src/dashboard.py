from flask import Flask, render_template
import json
import os

app = Flask(__name__, template_folder='templates')

@app.route('/')
def status():
    state_path = os.path.join(os.path.dirname(__file__), "coin_states.json")
    try:
        with open(state_path) as f:
            coin_states = json.load(f)
    except Exception:
        coin_states = {}
    return render_template("status.html", coin_states=coin_states)

if __name__ == '__main__':
    app.run(port=5000)