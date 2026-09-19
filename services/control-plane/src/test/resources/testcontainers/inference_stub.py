from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/v1/score":
            self.send_response(404)
            self.end_headers()
            return
        size = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(size))
        body = json.dumps({
            "policy_id": payload["policy_id"],
            "calibrated_probability": 0.25,
            "operational_tier": "TIER_2_ELEVATED",
            "bundle_version": "fixture-1.0.0",
            "bundle_digest": "fixture-digest",
            "authorized_to_act": False,
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass

HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
