"""Minimal Flask backend for YouTube->Serum UI."""
import sys
import json
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

ROOT = Path(__file__).parent


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def run_pipeline():
    """Run the YouTube->Serum pipeline and stream logs."""
    data = request.json
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL required"}), 400

    try:
        # Run main.py as subprocess and capture output
        result = subprocess.run(
            [sys.executable, str(ROOT / "main.py"), url],
            capture_output=True,
            text=True,
            timeout=300
        )

        # Parse output for final paths
        preset_path = None
        report_path = None

        for line in result.stdout.split('\n'):
            if 'Serum Preset:' in line:
                preset_path = line.split(': ', 1)[1].strip() if ': ' in line else None
            elif 'Report' in line and '.json' in line:
                report_path = line.split(': ', 1)[1].strip() if ': ' in line else None

        return jsonify({
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "preset_path": preset_path,
            "report_path": report_path,
        })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Pipeline timeout (>5min)"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<path:filepath>")
def download_file(filepath):
    """Download a file."""
    try:
        file_path = Path(filepath)
        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False, port=5000)
