"""Unit tests for the health probe. No Docker."""

from __future__ import annotations

import os
import socket
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO

import smoke


class _QuietHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def _closed_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _server(handler: type[BaseHTTPRequestHandler]) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class SmokeTests(unittest.TestCase):
    def test_health_ok_does_not_call_login(self) -> None:
        seen: list[tuple[str, str]] = []

        class Handler(_QuietHandler):
            def do_GET(self) -> None:
                seen.append(("GET", self.path.split("?", 1)[0]))
                body = b"ok"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:
                seen.append(("POST", self.path))
                self.send_response(500)
                self.end_headers()

        server = _server(Handler)
        try:
            host, port = server.server_address
            self.assertTrue(smoke.check(f"http://{host}:{port}/"))
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(seen, [("GET", "/health")])

    def test_non_200_is_failure(self) -> None:
        class Handler(_QuietHandler):
            def do_GET(self) -> None:
                self.send_response(503)
                self.end_headers()

        server = _server(Handler)
        try:
            host, port = server.server_address
            self.assertFalse(smoke.check(f"http://{host}:{port}"))
        finally:
            server.shutdown()
            server.server_close()

    def test_connection_refused(self) -> None:
        self.assertFalse(smoke.check(f"http://127.0.0.1:{_closed_port()}"))

    def test_main_prints_ok(self) -> None:
        class Handler(_QuietHandler):
            def do_GET(self) -> None:
                body = b"ok"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = _server(Handler)
        previous = os.environ.get("BASE_URL")
        host, port = server.server_address
        os.environ["BASE_URL"] = f"http://{host}:{port}"
        stdout = StringIO()
        try:
            with redirect_stdout(stdout):
                code = smoke.main()
        finally:
            server.shutdown()
            server.server_close()
            if previous is None:
                os.environ.pop("BASE_URL", None)
            else:
                os.environ["BASE_URL"] = previous
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue().strip(), "ok")

    def test_main_exits_when_health_fails(self) -> None:
        previous = os.environ.get("BASE_URL")
        os.environ["BASE_URL"] = f"http://127.0.0.1:{_closed_port()}"
        stdout = StringIO()
        stderr = StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = smoke.main()
        finally:
            if previous is None:
                os.environ.pop("BASE_URL", None)
            else:
                os.environ["BASE_URL"] = previous
        self.assertEqual(code, 1)
        self.assertNotIn("ok", stdout.getvalue())
        self.assertIn("health check failed", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
