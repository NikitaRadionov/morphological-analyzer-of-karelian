"""
Flask web application for the Karelian morphological analyzer.
Run: python app/app.py
Then open http://localhost:5000
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fst"))

from flask import Flask, render_template, request, jsonify
from analyzer.analyzer import KarelianAnalyzer

app = Flask(__name__)
_analyzer = None


def get_analyzer() -> KarelianAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = KarelianAnalyzer()
    return _analyzer


@app.route("/")
def index():
    stats = get_analyzer().stats()
    return render_template("index.html", stats=stats)


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)
    word = data.get("word", "").strip()
    if not word:
        return jsonify({"error": "Введите слово"}), 400
    results = get_analyzer().analyze(word)
    return jsonify({"word": word, "results": results})


@app.route("/paradigm", methods=["POST"])
def paradigm():
    data = request.get_json(force=True)
    lemma = data.get("lemma", "").strip()
    if not lemma:
        return jsonify({"error": "Введите лемму"}), 400
    forms = get_analyzer().generate(lemma)
    return jsonify({"lemma": lemma, "forms": forms})


if __name__ == "__main__":
    get_analyzer()  # preload on startup
    import fst_analyzer
    fst_analyzer.analyze("a")  # warm up WSL so the first real request isn't slow
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
