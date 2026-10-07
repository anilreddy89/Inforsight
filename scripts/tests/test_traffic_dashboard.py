import importlib.util
import json
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location('traffic', Path(__file__).parents[1]/'traffic_dashboard.py')
traffic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(traffic)


class TrafficTests(unittest.TestCase):
    def test_dedup_restart_retention_and_malformed_input(self):
        now = datetime.now(timezone.utc)
        def event(identity, at):
            return traffic.PREFIX + json.dumps({'v': 1, 'id': identity*32, 'at': at.isoformat()})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'stats.sqlite3'
            lines = [event('a', now), event('a', now), event('b', now),
                     event('c', now-timedelta(days=31)), event('d', now+timedelta(days=1)),
                     traffic.PREFIX+'{"v":1}', traffic.PREFIX+'null', 'unrelated log']
            db = traffic.connect(path)
            self.assertEqual(traffic.ingest(db, lines, now), 2)
            db.close()
            db = traffic.connect(path)
            self.assertEqual(traffic.ingest(db, lines, now), 0)
            self.assertEqual(db.execute('SELECT sum(views) FROM hourly').fetchone()[0], 2)
            traffic.ingest(db, [], now+timedelta(days=31))
            self.assertEqual(db.execute('SELECT count(*) FROM seen').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT sum(views) FROM hourly').fetchone()[0], 2)
            traffic.ingest(db, [], now+timedelta(days=366))
            self.assertEqual(db.execute('SELECT count(*) FROM hourly').fetchone()[0], 0)
            db.close()

    def test_local_boundary_and_no_store(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'stats.sqlite3'
            traffic.connect(path).close()
            collector = traffic.Collector(path, 'test')
            server = ThreadingHTTPServer(('127.0.0.1', 0), traffic.handler_for(collector, ZoneInfo('America/New_York')))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for headers, target, expected in [({}, '/', 200), ({'Host': 'attacker.example'}, '/', 403),
                    ({'Sec-Fetch-Site': 'cross-site'}, '/', 403), ({}, '/api', 404)]:
                    client = HTTPConnection('127.0.0.1', server.server_port)
                    client.request('GET', target, headers=headers)
                    response = client.getresponse()
                    self.assertEqual(response.status, expected)
                    if expected == 200:
                        self.assertEqual(response.getheader('Cache-Control'), 'no-store')
                        self.assertIn("frame-ancestors 'none'", response.getheader('Content-Security-Policy'))
                        self.assertIn(b'not unique people', response.read())
                    else:
                        response.read()
                    client.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
