from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question

PORT = 8501
HOST = "127.0.0.1"


class DemoHubHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/demo", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_path = ROOT_DIR / "docs" / "demo_hub.html"
            with open(html_path, "rb") as f:
                self.wfile.write(f.read())
            return

        if parsed.path in ("/slides", "/slides.html", "/docs/slides.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_path = ROOT_DIR / "docs" / "slides.html"
            with open(html_path, "rb") as f:
                self.wfile.write(f.read())
            return

        if parsed.path == "/api/status":
            self._handle_status()
            return

        if parsed.path == "/api/testset":
            self._handle_testset()
            return

        if parsed.path == "/api/reports":
            self._handle_reports()
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}

        if parsed.path == "/api/run-phase1":
            self._handle_run_script("script/run_phase1.py")
            return

        if parsed.path == "/api/run-corruption":
            self._handle_run_script("script/run_corruption_flow.py")
            return

        if parsed.path == "/api/ask":
            self._handle_ask(body.get("question", ""))
            return

        self.send_error(404, "Endpoint not found")

    def _send_json(self, data: dict, status: int = 200):
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_status(self):
        settings = load_settings(ROOT_DIR)
        has_baseline = settings.paths.baseline_metrics.exists()
        has_corrupted = settings.paths.corrupted_metrics.exists()
        has_repaired = settings.paths.repaired_metrics.exists()

        baseline_data = {}
        corrupted_data = {}
        repaired_data = {}

        if has_baseline:
            with open(settings.paths.baseline_metrics, "r", encoding="utf-8") as f:
                baseline_data = json.load(f)
        if has_corrupted:
            with open(settings.paths.corrupted_metrics, "r", encoding="utf-8") as f:
                corrupted_data = json.load(f)
        if has_repaired:
            with open(settings.paths.repaired_metrics, "r", encoding="utf-8") as f:
                repaired_data = json.load(f)

        self._send_json({
            "status": "ready",
            "has_baseline": has_baseline,
            "has_corrupted": has_corrupted,
            "has_repaired": has_repaired,
            "baseline": baseline_data,
            "corrupted": corrupted_data,
            "repaired": repaired_data,
        })

    def _handle_testset(self):
        settings = load_settings(ROOT_DIR)
        testset_path = settings.paths.eval_testset
        if testset_path.exists():
            with open(testset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._send_json({"questions": data})
        else:
            self._send_json({"questions": []})

    def _handle_reports(self):
        settings = load_settings(ROOT_DIR)
        corruption_report = ""
        phase1_report = ""
        if settings.paths.comparison_report.exists():
            with open(settings.paths.comparison_report, "r", encoding="utf-8") as f:
                corruption_report = f.read()
        if settings.paths.baseline_report.exists():
            with open(settings.paths.baseline_report, "r", encoding="utf-8") as f:
                phase1_report = f.read()

        corruption_log = []
        if settings.paths.corruption_log.exists():
            with open(settings.paths.corruption_log, "r", encoding="utf-8") as f:
                corruption_log = json.load(f)

        self._send_json({
            "corruption_report_md": corruption_report,
            "phase1_report_md": phase1_report,
            "corruption_log": corruption_log,
        })

    def _handle_run_script(self, rel_path: str):
        python_exe = sys.executable
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC_DIR)

        try:
            proc = subprocess.run(
                [python_exe, rel_path],
                cwd=str(ROOT_DIR),
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode

            # re-read status
            settings = load_settings(ROOT_DIR)
            res_metrics = {}
            if "phase1" in rel_path and settings.paths.baseline_metrics.exists():
                with open(settings.paths.baseline_metrics, "r", encoding="utf-8") as f:
                    res_metrics = json.load(f)
            elif "corruption" in rel_path and settings.paths.repaired_metrics.exists():
                with open(settings.paths.repaired_metrics, "r", encoding="utf-8") as f:
                    res_metrics = json.load(f)

            self._send_json({
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "metrics": res_metrics,
            })
        except subprocess.TimeoutExpired:
            self._send_json({"success": False, "error": "Script timed out (120s limit)"}, 500)
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    def _handle_ask(self, question: str):
        if not question:
            self._send_json({"error": "Empty question"}, 400)
            return

        settings = load_settings(ROOT_DIR)
        try:
            # Load baseline or repaired collection
            index = LocalEmbeddingIndex(settings=settings, collection_name=settings.baseline_collection_name)
            result = answer_question(question, settings=settings, index=index)
            self._send_json({
                "question": question,
                "answer": result.answer,
                "retrieved_titles": result.retrieved_titles,
                "retrieved_contexts": result.retrieved_contexts[:2],
            })
        except Exception as e:
            self._send_json({"error": f"Retrieval error: {str(e)}"}, 500)


def start_server():
    server = HTTPServer((HOST, PORT), DemoHubHandler)
    print(f"\n========================================================")
    print(f"  Team Latentia: Live Demo & Presentation Hub")
    print(f"  URL: http://{HOST}:{PORT}")
    print(f"========================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Demo Hub Server...")
        server.server_close()


if __name__ == "__main__":
    start_server()
