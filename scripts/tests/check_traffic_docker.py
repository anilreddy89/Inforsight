"""Exercise the actual Compose service definitions in an isolated two-service project."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
PROJECT = 'inforsight-public-traffic-check'
ENV = {**os.environ, 'COMPOSE_PROFILES': 'traffic'}


def command(*args):
    return subprocess.check_output(list(args), text=True, env=ENV, stderr=subprocess.STDOUT)


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


with tempfile.TemporaryDirectory() as directory:
    config = json.loads(command('docker', 'compose', '-p', PROJECT, '-f', str(ROOT/'infra/docker-compose.public.yml'),
                                'config', '--format', 'json'))
    config['services'] = {key: value for key, value in config['services'].items() if key in ('frontend', 'traffic-dashboard')}
    config['volumes'] = {key: value for key, value in config['volumes'].items() if key in ('traffic_data', 'traffic_logs')}
    front, stats = config['services']['frontend'], config['services']['traffic-dashboard']
    front.pop('depends_on')
    front['image'] = 'inforsight-traffic-test-frontend'
    stats['image'] = 'inforsight-traffic-test-dashboard'
    front['ports'][0]['published'] = str(free_port())
    stats['ports'][0]['published'] = str(free_port())
    stats['environment']['TRAFFIC_PUBLIC_PORT'] = stats['ports'][0]['published']
    path = Path(directory)/'compose.json'
    path.write_text(json.dumps(config))
    def compose(*args):
        return command('docker', 'compose', '-p', PROJECT, '-f', str(path), *args)
    def views():
        return int(compose('exec', '-T', 'traffic-dashboard', 'python', '-c',
            "import sqlite3; print(sqlite3.connect('/data/inforsight-public.sqlite3').execute('select coalesce(sum(views),0) from hourly').fetchone()[0])").strip())
    def wait_views(count):
        for _ in range(40):
            if views() == count:
                return
            time.sleep(1)
        raise AssertionError(f'Expected {count} views, got {views()}')
    def visit():
        request = urllib.request.Request('http://127.0.0.1:'+front['ports'][0]['published']+'/?run=PRIVATE', headers={'Accept': 'text/html'})
        urllib.request.urlopen(request, timeout=5).close()
    try:
        compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '60')
        visit()
        wait_views(1)
        compose('exec', '-T', 'frontend', 'logrotate', '-f', '-s', '/var/log/inforsight/rotation.state', '/etc/traffic-logrotate.conf')
        visit()
        wait_views(2)
        # Leave a view uncollected; recreate both containers with their volumes intact.
        compose('stop', 'traffic-dashboard')
        visit()
        compose('down')
        compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '60')
        wait_views(3)
        ids = compose('ps', '-q').split()
        containers = json.loads(command('docker', 'inspect', *ids))
        dashboard = next(c for c in containers if c['Config']['Labels']['com.docker.compose.service'] == 'traffic-dashboard')
        assert dashboard['Config']['User'] == '10001:10001'
        assert dashboard['HostConfig']['ReadonlyRootfs']
        assert set(dashboard['NetworkSettings']['Networks']) == {PROJECT+'_analytics'}
        assert all(m['Destination'] in ('/data', '/traffic') for m in dashboard['Mounts'])
        assert next(m for m in dashboard['Mounts'] if m['Destination'] == '/traffic')['RW'] is False
        assert dashboard['HostConfig']['PortBindings']['3111/tcp'][0]['HostIp'] == '127.0.0.1'
        address = 'http://127.0.0.1:'+stats['ports'][0]['published']+'/'
        with urllib.request.urlopen(address, timeout=5) as response:
            assert b'Inforsight traffic' in response.read()
            assert response.headers['Cache-Control'] == 'no-store'
        for headers in ({'Host': 'attacker.example'}, {'Sec-Fetch-Site': 'cross-site'}):
            try:
                urllib.request.urlopen(urllib.request.Request(address, headers=headers), timeout=5)
                raise AssertionError('Untrusted request accepted')
            except urllib.error.HTTPError as error:
                assert error.code == 403
        print('PASS: Compose startup, rotation, deduplication, persistent logs/counts after recreation, loopback publishing, non-root/read-only isolation, and HTTP access boundary')
    finally:
        compose('down', '--volumes')
