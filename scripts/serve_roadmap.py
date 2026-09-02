#!/usr/bin/env python3
"""
Lightweight development server for previewing the Inforsight Roadmap Web UI.
Usage: python3 scripts/serve_roadmap.py [--port 8080] [--no-browser]
"""

import argparse
import http.server
import os
import socketserver
import webbrowser
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Inforsight Roadmap Web UI locally.")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    web_dir = repo_root / "docs" / "roadmap"

    if not web_dir.exists():
        raise FileNotFoundError(f"Roadmap web directory not found: {web_dir}")

    os.chdir(web_dir)
    handler = http.server.SimpleHTTPRequestHandler

    print(f"\n=======================================================")
    print(f"🚀 Serving Inforsight Roadmap Web UI")
    print(f"📁 Directory: {web_dir}")
    print(f"🌐 URL:       http://localhost:{args.port}")
    print(f"=======================================================\n")

    if not args.no_browser:
        webbrowser.open(f"http://localhost:{args.port}")

    socketserver.TCPServer.allow_reuse_address = True
    port = args.port
    while True:
        try:
            with socketserver.TCPServer(("", port), handler) as httpd:
                print(f"Server active on http://localhost:{port}")
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    print("\nShutting down server.")
                break
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"Port {port} in use, trying {port + 1}...")
                port += 1
            else:
                raise e


if __name__ == "__main__":
    main()

