#!/usr/bin/env python3
"""Loopback-only traffic dashboard. Standard library; no application credentials."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import threading
from zoneinfo import ZoneInfo

UTC = timezone.utc
PREFIX = 'INFORSIGHT_TRAFFIC '


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS hourly (hour TEXT PRIMARY KEY, views INTEGER NOT NULL);
    ''')
    return db


def ingest(db, lines, now):
    """Atomic deduplication and aggregation, including overlap after restart."""
    cutoff = (now - timedelta(days=30)).isoformat()
    added = 0
    with db:
        for line in lines:
            if not line.startswith(PREFIX) or len(line) > 256:
                continue
            try:
                event = json.loads(line[len(PREFIX):])
                if event.get('v') != 1 or not re.fullmatch('[0-9a-f]{32}', event.get('id', '')):
                    continue
                at = datetime.fromisoformat(event['at'])
                if at.tzinfo is None:
                    continue
                at = at.astimezone(UTC)
                if not now - timedelta(days=30) <= at <= now + timedelta(minutes=1):
                    continue
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
            inserted = db.execute('INSERT OR IGNORE INTO seen VALUES (?, ?)',
                                  (event['id'], at.isoformat())).rowcount
            if inserted:
                hour = at.replace(minute=0, second=0, microsecond=0).isoformat()
                db.execute('INSERT INTO hourly VALUES (?, 1) ON CONFLICT(hour) DO UPDATE SET views=views+1', (hour,))
                added += 1
        db.execute('DELETE FROM seen WHERE at < ?', (cutoff,))
        db.execute('DELETE FROM hourly WHERE hour < ?', ((now-timedelta(days=365)).isoformat(),))
    return added


def docker(*args):
    # No shell; stderr may contain operational details and is never rendered.
    return subprocess.run(['docker', *args], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, text=True, timeout=20).stdout


class Collector:
    def __init__(self, path, project, log_dir=None):
        self.path, self.project, self.log_dir = path, project, log_dir
        self.lock = threading.Lock()
        self.status = 'Waiting for the first collection.'
        self.last_success = None
        self.stop = threading.Event()

    def collect(self):
        try:
            with closing(connect(self.path)) as db:
                if self.log_dir is not None:
                    files = sorted(self.log_dir.glob('traffic.log*'))
                    if not files:
                        raise RuntimeError('No traffic log available')
                    for path in files:
                        try:
                            with path.open() as source:
                                ingest(db, source, datetime.now(UTC))
                        except FileNotFoundError:
                            # Rotation may rename an entry after glob. Re-scan next time.
                            continue
                else:
                    ids = docker('ps', '-a', '-q', '--filter', f'label=com.docker.compose.project={self.project}',
                                 '--filter', 'label=com.docker.compose.service=frontend',
                                 '--filter', 'label=com.inforsight.traffic.version').split()
                    if not ids:
                        raise RuntimeError('No instrumented gateway')
                    for container in ids:
                        lines = docker('logs', '--since', '720h', container).splitlines()
                        ingest(db, lines, datetime.now(UTC))
            with self.lock:
                self.last_success = datetime.now(UTC)
                self.status = 'Collection successful. Refresh this page to update the display.'
        except (OSError, subprocess.SubprocessError, RuntimeError, sqlite3.Error):
            with self.lock:
                self.status = 'Collection unavailable. Check the gateway and traffic log source. Saved counts may be stale.'

    def run(self):
        while not self.stop.is_set():
            self.collect()
            self.stop.wait(30)

    def render(self, tz):
        with closing(connect(self.path)) as db:
            rows = db.execute('SELECT hour, views FROM hourly ORDER BY hour DESC').fetchall()
        daily, hourly = Counter(), Counter()
        for hour, views in rows:
            local = datetime.fromisoformat(hour).astimezone(tz)
            daily[local.date().isoformat()] += views
            hourly[local.strftime('%Y-%m-%d %H:00 %z')] += views
        today = datetime.now(tz).date()
        with self.lock:
            status = self.status
            last = self.last_success.astimezone(tz).isoformat(timespec='seconds') if self.last_success else 'Not yet collected'
        def table(items):
            peak = max((value for _, value in items), default=1)
            return ''.join(f'<tr><th scope="row">{html.escape(key)}</th><td>{value:,}</td>'
                           f'<td><meter min="0" max="{peak}" value="{value}">{value}</meter></td></tr>'
                           for key, value in items) or '<tr><td>No recorded page views yet.</td></tr>'
        days = [(str(today-timedelta(days=i)), daily[str(today-timedelta(days=i))]) for i in range(30)]
        return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Inforsight · Traffic</title>
<style>body{{font:16px system-ui;background:#101725;color:#e7edf7;max-width:1050px;margin:40px auto;padding:0 24px}}
h1{{font-size:36px}}p{{line-height:1.6;color:#bdcce0}}.cards{{display:flex;gap:20px;flex-wrap:wrap}}
.card{{background:#1b293f;padding:24px;border-radius:12px;flex:1}}strong{{display:block;font-size:36px;color:#80d8d0}}
table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #2a3a51}}
meter{{width:100%;min-width:80px}}small{{color:#bdcce0}}a{{color:#80d8d0}}</style>
<main><small>LOCAL ACCESS · NO VISITOR IDENTIFICATION</small><h1>Inforsight traffic</h1>
<p>{html.escape(status)}<br>Last collected: {html.escape(last)} · {html.escape(str(tz))}</p>
<div class="cards"><div class="card">Today<strong>{daily[str(today)]:,}</strong>page views</div>
<div class="card">Last 30 calendar days<strong>{sum(value for _,value in days):,}</strong>page views</div>
<div class="card">Retained history · up to 365 days<strong>{sum(daily.values()):,}</strong>page views</div></div>
<p>Counts successful HTML requests to / and /index.html, including refreshes and possible bots.
API polling, assets, health checks, and in-app navigation are excluded. These are not unique people.
No traffic before instrumentation is available. Missing logs cannot be reconstructed:</p>
<p>Keep this collector running. Uncollected requests can be lost when the retained log window is exceeded.
Shared Docker volumes preserve logs and counts across container replacement. Empty periods mean no recorded views, not proof of no traffic.</p>
<h2>Daily activity · last 30 days</h2><table><caption>Page views by day</caption><tbody>{table(days)}</tbody></table>
<h2>Recent active hours</h2><table><caption>Most recent 48 hours with recorded activity</caption>
<tbody>{table(sorted(hourly.items(), reverse=True)[:48])}</tbody></table></main></html>'''.encode()


def handler_for(collector, tz):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            external = os.environ.get('TRAFFIC_PUBLIC_PORT')
            if external and external.isdigit():
                allowed.update({f'127.0.0.1:{external}', f'localhost:{external}'})
            # Host validation defeats DNS rebinding; reject cross-site browser loads.
            if self.headers.get('Host') not in allowed or self.headers.get('Sec-Fetch-Site') not in (None, 'none', 'same-origin'):
                self.send_error(403)
                return
            if self.path != '/':
                self.send_error(404)
                return
            body = collector.render(tz)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='inforsight-public')
    parser.add_argument('--port', default=3111, type=int)
    parser.add_argument('--timezone', default=os.environ.get('TRAFFIC_TIMEZONE', 'America/New_York'))
    parser.add_argument('--log-dir', type=Path)
    parser.add_argument('--container', action='store_true', help='Listen inside the isolated Docker network; publish only to host loopback')
    parser.add_argument('--state-dir', type=Path, default=Path.home()/'.local/share/inforsight-traffic')
    args = parser.parse_args()
    if not re.fullmatch('[a-z0-9][a-z0-9_-]{0,62}', args.project):
        parser.error('Invalid Compose project name')
    tz = ZoneInfo(args.timezone)
    os.umask(0o077)
    args.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = args.state_dir / f'{args.project}.sqlite3'
    connect(path).close()
    if args.container and args.log_dir is None:
        parser.error("Container mode requires --log-dir; Docker socket access is not used")
    collector = Collector(path, args.project, args.log_dir)
    server = ThreadingHTTPServer(('0.0.0.0' if args.container else '127.0.0.1', args.port), handler_for(collector, tz))
    threading.Thread(target=collector.run, daemon=True).start()
    print(f'Traffic dashboard: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        collector.stop.set()
        server.server_close()


if __name__ == '__main__':
    main()
