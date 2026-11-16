"""Lightweight local server for Live Interactive Demo of Agentic RAG."""
import json
import os
import sys
import time
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

# Ensure starter is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "starter"))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from agentic import run_agent
from controller import GeminiController
from advanced_agent import AdvancedDocumentRetriever

PORT = 8000

print("Đang nạp dữ liệu và khởi tạo Retriever...")
chunks_file = BASE_DIR / "data/advanced/chunks.json"
chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
retriever = AdvancedDocumentRetriever(chunks)
controller = GeminiController()
print(f"Đã nạp {len(chunks)} chunks từ tài liệu 152 trang.")


class AgenticRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/" or url.path == "/demo":
            self.path = "/demo_results.html"
        return super().do_GET()

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/api/ask":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                question = data.get("question", "").strip()
                if not question:
                    raise ValueError("Câu hỏi không được để trống")

                t0 = time.time()
                print(f"\n[LIVE QUERY] {question}")
                res = run_agent(
                    question,
                    controller,
                    retriever,
                    max_searches=3,
                    top_k=5,
                    budget=4000,
                )
                elapsed = time.time() - t0
                print(f"   -> Status: {res['status']} ({elapsed:.2f}s) | Citations: {res['citations']}")

                response_data = {
                    "question": question,
                    "status": res["status"],
                    "answer": res["answer"],
                    "citations": res["citations"],
                    "events": res["events"],
                    "elapsed_seconds": elapsed,
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                print(f"❌ Lỗi: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, AgenticRequestHandler)
    url = f"http://localhost:{PORT}"
    print(f"\n🚀 Máy chủ Demo trực tiếp đang chạy tại: {url}")
    print(f"👉 Mở trình duyệt tại: {url}/demo_results.html")
    print("Nhấn Ctrl+C để dừng máy chủ.\n")
    try:
        webbrowser.open(f"{url}/demo_results.html")
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng máy chủ.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
