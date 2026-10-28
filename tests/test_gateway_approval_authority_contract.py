"""Session-authority gateways (hermes-agent >= 0.21.5) only accept
{request_id, execution_generation, choice} on POST /v1/runs/{id}/approval and
name the prompt id ``prompt_id`` in the approval.request event; anything else is
HTTP 400 invalid_params."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from api.gateway_chat import _gateway_runs_approval_event
from api.runner_client import HttpRunnerClient


def _serve():
    seen = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen


def test_event_maps_prompt_id_and_generation():
    ev = _gateway_runs_approval_event({
        "event": "approval.request", "kind": "approval", "prompt_id": "p1",
        "execution_generation": 3, "command": "rm -rf x", "choices": ["once", "deny"],
    })
    assert ev["approval_id"] == "p1" and ev["_gateway_raw_approval_id_present"] is True
    assert ev["execution_generation"] == 3


def test_client_sends_exact_authority_body_else_legacy_body():
    srv, seen = _serve()
    try:
        c = HttpRunnerClient(base_url=f"http://127.0.0.1:{srv.server_port}", api_key="k")
        c.respond_approval("run_1", "p1", "deny", 3)
        c.respond_approval("run_1", "a1", "once")
    finally:
        srv.shutdown()
    assert seen[0] == ("/v1/runs/run_1/approval", {"request_id": "p1", "execution_generation": 3, "choice": "deny"})
    assert seen[1][1] == {"choice": "once", "approval_id": "a1"}
