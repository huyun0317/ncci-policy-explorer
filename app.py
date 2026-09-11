from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ncci.answer import answer_question
from ncci.ingest import ingest_pdf
from ncci.retrieval import get_insights, search


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DEFAULT_PDF = ROOT / "data" / "2026-ncci-medicare-policy-manual-all-chapters.pdf"
DEFAULT_DB = ROOT / "data" / "ncci.db"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class NCCIRequestHandler(BaseHTTPRequestHandler):
    server_version = "NCCIPolicyExplorer/1.0"

    @property
    def app(self) -> "NCCIServer":
        return self.server  # type: ignore[return-value]

    def log_message(self, format: str, *args: object) -> None:
        sys.stdout.write(f"{self.address_string()} - {format % args}\n")

    def _headers(self, status: HTTPStatus, content_type: str, length: int) -> None:
        self.send_response(status.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store" if "json" in content_type else "public, max-age=300")
        self.end_headers()

    def _send_bytes(
        self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        self._headers(status, content_type, len(body))
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status)

    def _send_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        media_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self._send_bytes(body, media_type)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_file(STATIC / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/assets/styles.css":
            self._send_file(STATIC / "styles.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/assets/app.js":
            self._send_file(STATIC / "app.js", "text/javascript; charset=utf-8")
            return
        if parsed.path == "/manual":
            self._send_file(self.app.pdf_path, "application/pdf")
            return
        if parsed.path == "/api/health":
            self._send_json(
                {
                    "status": "ok",
                    "answer_mode": "openai" if self.app.api_key else "evidence-only",
                    "model": self.app.model if self.app.api_key else None,
                    "reasoning_effort": self.app.reasoning_effort if self.app.api_key else None,
                }
            )
            return
        if parsed.path == "/api/insights":
            self._send_json(get_insights(self.app.db_path))
            return
        if parsed.path == "/api/search":
            question = parse_qs(parsed.query).get("q", [""])[0].strip()
            if not question:
                self._send_json({"error": "Query parameter q is required."}, HTTPStatus.BAD_REQUEST)
                return
            hits = search(self.app.db_path, question, limit=8)
            self._send_json({"query": question, "sources": [hit.to_dict() for hit in hits]})
            return
        self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/chat":
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 100_000:
                raise ValueError("Request body must be between 1 byte and 100 KB.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            question = str(payload.get("question", "")).strip()
            if len(question) < 3:
                raise ValueError("Enter a more specific question.")
            if len(question) > 2_000:
                raise ValueError("Question must be 2,000 characters or fewer.")
            hits = search(self.app.db_path, question, limit=6)
            result = answer_question(
                question,
                hits,
                self.app.api_key,
                self.app.model,
                self.app.reasoning_effort,
                self.app.fallback_model,
            )
            response = result.to_dict()
            response["question"] = question
            response["sources"] = [hit.to_dict() for hit in hits]
            self._send_json(response)
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self._send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)


class NCCIServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        db_path: Path,
        pdf_path: Path,
        api_key: str | None,
        model: str,
        reasoning_effort: str,
        fallback_model: str | None,
    ) -> None:
        super().__init__(address, handler)
        self.db_path = db_path
        self.pdf_path = pdf_path
        self.api_key = api_key
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.fallback_model = fallback_model


def ensure_index(pdf_path: Path, db_path: Path) -> None:
    if db_path.exists():
        return
    print(f"Building search index from {pdf_path.name}...")
    insights = ingest_pdf(pdf_path, db_path)
    print(f"Indexed {insights['pages']} pages into {insights['chunks']} passages.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explore the 2026 CMS Medicare NCCI policy manual.")
    subparsers = parser.add_subparsers(dest="command")

    ingest_parser = subparsers.add_parser("ingest", help="Build or rebuild the local search index.")
    ingest_parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ingest_parser.add_argument("--db", type=Path, default=DEFAULT_DB)

    serve_parser = subparsers.add_parser("serve", help="Start the local web application.")
    serve_parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    serve_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    default_host = os.getenv("NCCI_HOST") or ("0.0.0.0" if os.getenv("RENDER") else "127.0.0.1")
    default_port = int(os.getenv("PORT", os.getenv("NCCI_PORT", "8000")))
    serve_parser.add_argument("--host", default=default_host)
    serve_parser.add_argument("--port", type=int, default=default_port)

    ask_parser = subparsers.add_parser("ask", help="Ask a question from the command line.")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    ask_parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser.parse_args()


def main() -> None:
    load_env_file(ROOT / ".env")
    args = parse_args()
    command = args.command or "serve"

    if command == "ingest":
        insights = ingest_pdf(args.pdf, args.db)
        print(json.dumps(insights, indent=2))
        return

    if command == "ask":
        ensure_index(args.pdf, args.db)
        hits = search(args.db, args.question, limit=6)
        result = answer_question(
            args.question,
            hits,
            os.getenv("OPENAI_API_KEY") or None,
            os.getenv("OPENAI_MODEL", "gpt-5.6"),
            os.getenv("OPENAI_REASONING_EFFORT", "low"),
            os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4.1-mini") or None,
        )
        print(result.answer)
        print("\nSources:")
        for hit in hits:
            print(f"[{hit.citation}] PDF page {hit.page} - {hit.chapter_title}")
        return

    pdf_path = args.pdf.resolve()
    db_path = args.db.resolve()
    ensure_index(pdf_path, db_path)
    server = NCCIServer(
        (args.host, args.port),
        NCCIRequestHandler,
        db_path,
        pdf_path,
        os.getenv("OPENAI_API_KEY") or None,
        os.getenv("OPENAI_MODEL", "gpt-5.6"),
        os.getenv("OPENAI_REASONING_EFFORT", "low"),
        os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4.1-mini") or None,
    )
    print(f"NCCI Policy Explorer: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
