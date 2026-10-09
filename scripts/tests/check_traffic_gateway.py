"""Opt-in isolated nginx integration check; never touches the deployed gateway."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('traffic', ROOT/'scripts/traffic_dashboard.py')
traffic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(traffic)

with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    (folder/'index.html').write_text('<!doctype html><title>Traffic test</title>')
    (folder/'asset.js').write_text('/* static asset */')
    container = subprocess.check_output(['docker', 'create', '-p', '127.0.0.1::80',
        '--label', 'com.docker.compose.project=inforsight-traffic-test',
        '--label', 'com.docker.compose.service=frontend', '--label', 'com.inforsight.traffic.version=1',
        'nginx:stable-alpine'], text=True).strip()
    try:
        subprocess.run(['docker', 'cp', str(ROOT/'frontend/nginx.conf'), f'{container}:/etc/nginx/conf.d/default.conf'], check=True)
        subprocess.run(['docker', 'cp', str(folder)+'/.', f'{container}:/usr/share/nginx/html'], check=True)
        subprocess.run(['docker', 'cp', str(folder), f'{container}:/var/log/inforsight'], check=True)
        subprocess.run(['docker', 'start', container], check=True, stdout=subprocess.DEVNULL)
        port = subprocess.check_output(['docker', 'port', container, '80'], text=True).strip().rsplit(':', 1)[1]
        base = f'http://127.0.0.1:{port}'
        for _ in range(30):
            try:
                urllib.request.urlopen(base+'/health', timeout=1).close()
                break
            except OSError:
                time.sleep(.1)
        def request(path, accept='text/html', method='GET', headers=None):
            req = urllib.request.Request(base+path, method=method, headers={'Accept': accept, **(headers or {})})
            try:
                with urllib.request.urlopen(req, timeout=3) as response:
                    response.read()
                    return response.headers
            except urllib.error.HTTPError as error:
                error.read()
                return error.headers
        first = request('/')
        request('/?run=PRIVATE_QUERY')
        request('/index.html')
        request('/', headers={'If-None-Match': first['ETag']})
        request('/asset.js')
        request('/health')
        request('/missing')
        request('/api/unavailable')
        request('/', accept='application/json')
        request('/', method='HEAD')
        time.sleep(.2)
        logs = subprocess.check_output(['docker', 'logs', container], text=True, stderr=subprocess.DEVNULL)
        events = [json.loads(line[len(traffic.PREFIX):]) for line in logs.splitlines() if line.startswith(traffic.PREFIX)]
        assert len(events) == 4, events
        assert all(set(event) == {'v', 'id', 'at'} for event in events)
        assert 'PRIVATE_QUERY' not in logs
        collector = traffic.Collector(folder/'traffic.sqlite3', 'inforsight-traffic-test')
        collector.collect()
        collector.collect()
        with traffic.connect(collector.path) as db:
            assert db.execute('SELECT sum(views) FROM hourly').fetchone()[0] == 4
        assert collector.last_success is not None
        print('PASS: nginx page filtering, 304s, privacy, Docker collection, and duplicate prevention')
    finally:
        subprocess.run(['docker', 'rm', '-f', container], check=True, stdout=subprocess.DEVNULL)
