#!/usr/bin/env python3
"""Operate the isolated, zero-cloud-cost visitor preview without exposing secrets.

This is an operator CLI, never an HTTP endpoint. The existing inforsight-demo
project/volumes are not touched. Secret values never enter argv or Compose env.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import plistlib
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "infra/docker-compose.public.yml"
DEFAULT_STATE = Path.home() / ".local/share/inforsight-public"
TOPIC = "inforsight.demo.events.v1"
GROUP = "inforsight-demo-journey-v1"
SERVICES = ("kafka", "postgres", "inference-runtime", "demo-runtime", "control-plane", "frontend", "traffic-dashboard")
DATA_VOLUMES = ("postgres_data", "kafka_data", "traffic_data", "traffic_logs")


def command(args, *, capture=False, check=True, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=check, text=True,
                          capture_output=capture, **kwargs)


class Preview:
    def __init__(self, state: Path):
        self.state = state.expanduser().resolve()
        self.settings_file = self.state / "settings.json"
        self.settings = json.loads(self.settings_file.read_text()) if self.settings_file.exists() else None

    def require(self):
        if not self.settings:
            raise SystemExit("Run scripts/public_demo.py init first.")
        project = self.settings["project"]
        if project == "inforsight-demo" or not re.fullmatch(r"inforsight-public(?:-[a-z0-9-]+)?", project):
            raise SystemExit("Refusing to operate on anything except an isolated inforsight-public project.")

    def services(self):
        restored = self.state / "restore-images.json"
        if restored.exists():
            return tuple(json.loads(restored.read_text())["services"])
        return SERVICES

    def data_volumes(self):
        return DATA_VOLUMES if "traffic-dashboard" in self.services() else DATA_VOLUMES[:2]

    def traffic_port(self):
        port = int(os.environ.get("INFORSIGHT_TRAFFIC_PORT", self.settings["port"] + 11))
        if not 1024 <= port <= 65535 or port == self.settings["port"]:
            raise SystemExit("Set INFORSIGHT_TRAFFIC_PORT to a distinct port in 1024..65535.")
        return port

    def env(self):
        self.require()
        return {**os.environ, "INFORSIGHT_PUBLIC_SECRET_DIR": str(self.state / "secrets"),
                "INFORSIGHT_PUBLIC_PORT": str(self.settings["port"]),
                "INFORSIGHT_TRAFFIC_PORT": str(self.traffic_port()),
                "COMPOSE_PROFILES": "traffic" if "traffic-dashboard" in self.services() else ""}

    def compose(self, *args, **kwargs):
        self.require()
        files = ["-f", COMPOSE]
        restored_images = self.state / "restore-images.json"
        if restored_images.exists():
            files += ["-f", restored_images]
        return command(["docker", "compose", "-p", self.settings["project"], *files, *args],
                       env=self.env(), cwd=ROOT, **kwargs)

    def init(self, project, port):
        if self.settings:
            self.require()
            print(f"Existing deployment preserved: {self.settings['project']} at {self.state}")
            return
        if self.state == ROOT or ROOT in self.state.parents:
            raise SystemExit("Secret/state directory must be outside the repository.")
        if not 1024 <= port <= 65535:
            raise SystemExit("Port must be in 1024..65535.")
        self.settings = {"project": project, "port": port, "secure_cookie": True, "created_at": now()}
        self.require()
        self.state.mkdir(parents=True, mode=0o700)
        self.state.chmod(0o700)
        directory = self.state / "secrets"
        directory.mkdir(mode=0o700, exist_ok=True)
        directory.chmod(0o700)
        for name in ("db_password", "demo_session_secret"):
            with (directory / name).open("x") as file:
                os.chmod(file.fileno(), 0o600)
                file.write(secrets.token_hex(32))
        self.settings_file.write_text(json.dumps(self.settings, indent=2) + "\n")
        self.settings_file.chmod(0o600)
        print(f"Initialized {project}; secret files are private in {directory}. Values were not printed.")

    def validate(self):
        config = json.loads(self.compose("config", "--format", "json", capture=True).stdout)
        assert set(config["services"]) == set(self.services())
        for name, service in config["services"].items():
            assert service["restart"] == "unless-stopped", name
            assert int(service["mem_limit"]) > 0, name
            ports = service.get("ports", [])
            if name in ("frontend", "traffic-dashboard"):
                assert len(ports) == 1 and ports[0]["host_ip"] == "127.0.0.1"
            else:
                assert not ports, f"Private service has published ports: {name}"
                assert set(service["networks"]) == {"private"}, name
        if "traffic-dashboard" in self.services():
            dashboard = config["services"]["traffic-dashboard"]
            assert set(dashboard["networks"]) == {"analytics"}
            assert dashboard["read_only"] is True and dashboard["cap_drop"] == ["ALL"]
            mounts = {v["target"]: v for v in dashboard["volumes"]}
            assert set(mounts) == {"/data", "/traffic"}
            assert mounts["/traffic"]["read_only"] is True
        assert config["networks"]["private"]["internal"] is True
        env = config["services"]["control-plane"]["environment"]
        assert env["INFORSIGHT_DEMO_PUBLIC_ENABLED"] == "true"
        assert env["INFORSIGHT_DEMO_COOKIE_SECURE"] == "true"
        assert env["INFORSIGHT_EXTERNAL_EXECUTION_ENABLED"] == "false"
        assert env["INFORSIGHT_AUTHORIZED_TO_ACT"] == "false"
        assert env["INFORSIGHT_INFERENCE_TRANSPORT"] == "http"
        assert "INFORSIGHT_DB_PASSWORD" not in env
        for secret in (self.state / "secrets").iterdir():
            assert secret.stat().st_mode & 0o077 == 0, "Secret permissions are too broad."
        print("PASS isolated topology, private service ports, authority flags, resource limits and secret permissions")
        return config

    def ensure_traffic_images(self):
        # Upgrade the gateway once to add file logging, and build the new sidecar.
        # Pinned restores must never silently substitute newer images.
        if (self.state / "restore-images.json").exists():
            return
        for service, label, version in (
                ("frontend", "com.inforsight.traffic.version", "2"),
                ("traffic-dashboard", "com.inforsight.traffic.dashboard.version", "1")):
            result = command(["docker", "image", "inspect", self.settings["project"] + "-" + service],
                             capture=True, check=False)
            images = json.loads(result.stdout) if result.returncode == 0 else []
            if not images or (images[0]["Config"].get("Labels") or {}).get(label) != version:
                self.compose("build", service)

    def up(self, build=True):
        self.validate()
        self.provision_secrets()
        if not build:
            self.ensure_traffic_images()
        args = ["up", "-d", "--wait", "--wait-timeout", "180"]
        if build and not (self.state / "restore-images.json").exists():
            # A cached tag never refreshes itself. Fetch patched service and base
            # images so a rebuild also picks up upstream security fixes.
            self.compose("pull", "--ignore-buildable", "--quiet")
            self.compose("build", "--pull")
            args.append("--build")
        else:
            args.append("--no-build")
        self.compose(*args)
        self.manifest()

    def provision_secrets(self):
        self.require()
        volume = self.settings["project"] + "_runtime_secrets"
        command(["docker", "volume", "create", "--label", "com.docker.compose.project=" + self.settings["project"],
                 "--label", "com.docker.compose.volume=runtime_secrets", volume], capture=True)
        # The image's fixed current application account is uid100/gid101. Keep
        # the source host files0600; file-backed Compose secrets cannot remap it.
        helper = """set -eu
test ! -s /target/INFORSIGHT_DB_PASSWORD || cmp -s /source/db_password /target/INFORSIGHT_DB_PASSWORD
test ! -s /target/demo_session_secret || cmp -s /source/demo_session_secret /target/demo_session_secret
cp /source/db_password /target/INFORSIGHT_DB_PASSWORD
cp /source/demo_session_secret /target/demo_session_secret
chmod 500 /target
chmod 400 /target/INFORSIGHT_DB_PASSWORD /target/demo_session_secret
chown -R 100:101 /target
"""
        command(["docker", "run", "--rm", "--network", "none", "--user", "0",
                 "-v", f"{self.state / 'secrets'}:/source:ro", "-v", f"{volume}:/target",
                 "postgres:16-alpine", "sh", "-c", helper], capture=True)
        print("Provisioned read-only runtime secret volume; host files remain private, Java remains non-root.")

    def manifest(self):
        ids = self.compose("ps", "-q", capture=True).stdout.split()
        inspected = json.loads(command(["docker", "inspect", *ids], capture=True).stdout) if ids else []
        components = []
        for item in inspected:
            original_image_id = item["Image"]
            probe = command(["docker", "image", "inspect", original_image_id], capture=True, check=False)
            if probe.returncode == 0:
                image = json.loads(probe.stdout)[0]
            else:
                # Docker's containerd image store can replace a rebuilt index
                # (new provenance attestation) while retaining the SAME runtime
                # platform manifest. Never assume its mutable tag is equivalent:
                # prove the exact platform digest before using a restorable index.
                descriptor = item.get("ImageManifestDescriptor", {})
                platform = descriptor.get("platform", {})
                image_ref = item["Config"]["Image"]
                platform_name = platform.get("os", "linux") + "/" + platform.get("architecture", "")
                platform_image = json.loads(command(["docker", "image", "inspect", "--platform", platform_name,
                                                     image_ref], capture=True).stdout)[0]
                assert descriptor.get("digest") == platform_image["Id"], "Rebuilt image differs from running platform; preserve its original image before backup."
                image = json.loads(command(["docker", "image", "inspect", image_ref], capture=True).stdout)[0]
            image_id = image["Id"]
            peak = command(["docker", "exec", item["Id"], "cat", "/sys/fs/cgroup/memory.peak"],
                           capture=True, check=False)
            components.append({"service": item["Config"]["Labels"]["com.docker.compose.service"],
                               "image_id": image_id, "architecture": image["Architecture"],
                               "container_image_reference": original_image_id,
                               "runtime_platform_digest": item.get("ImageManifestDescriptor", {}).get("digest"),
                               "healthy": item["State"].get("Health", {}).get("Status"),
                               "memory_limit_bytes": item["HostConfig"]["Memory"],
                               "memory_peak_bytes": int(peak.stdout.strip()) if peak.returncode == 0 and peak.stdout.strip().isdigit() else None,
                               "oom_killed": item["State"]["OOMKilled"], "restart_count": item["RestartCount"],
                               "started_at": item["State"]["StartedAt"],
                               "published_ports": item["HostConfig"]["PortBindings"]})
        bundle = ROOT / "docs/experiments/phase-02-10-model-bundle.json"
        manifest = {"recorded_at": now(), "project": self.settings["project"],
                    "commit": command(["git", "rev-parse", "HEAD"], cwd=ROOT, capture=True).stdout.strip(),
                    "dirty_paths": command(["git", "status", "--porcelain"], cwd=ROOT, capture=True).stdout.splitlines(),
                    "compose_sha256": hashlib.sha256(COMPOSE.read_bytes()).hexdigest(),
                    "model_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
                    "components": components,
                    "sum_of_individual_memory_peaks_bytes": sum(c["memory_peak_bytes"] or 0 for c in components),
                    "memory_peak_note": "Sum of individual cgroup peaks, not a simultaneous host-RSS measurement; excludes build/host overhead.",
                    "cloud_resources_created": False, "vendor_monthly_cost_usd": 0}
        target = self.state / "deployment-manifest.json"
        target.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"Deployment evidence: {target}")
        return manifest

    def tunnel_start(self):
        self.validate()
        self.validate_runtime()
        if not self.settings["secure_cookie"]:
            raise SystemExit("Refusing public exposure: secure_cookie must be true.")
        if not shutil.which("cloudflared"):
            raise SystemExit("Install the free client first: brew install cloudflared")
        if self.process_running("tunnel"):
            print((self.state / "public-url.txt").read_text().strip())
            return
        url = f"http://127.0.0.1:{self.settings['port']}"
        with urllib.request.urlopen(url + "/api/v1/demo/session", timeout=10) as response:
            session = json.load(response)
            cookie = response.headers.get("Set-Cookie", "")
        if "__Host-inforsight_session=" not in cookie or "Secure" not in cookie or not session.get("csrf_token"):
            raise SystemExit("Refusing exposure: gateway did not prove signed secure-session bootstrap.")
        logfile = self.state / "tunnel.log"
        with logfile.open("w") as log:
            proc = subprocess.Popen([shutil.which("cloudflared"), "tunnel", "--no-autoupdate", "--url", url,
                                     "--metrics", "127.0.0.1:49312"], stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=log, start_new_session=True)
        (self.state / "tunnel.pid").write_text(str(proc.pid))
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", logfile.read_text())
            if match:
                public_url = match.group(0)
                (self.state / "public-url.txt").write_text(public_url + "\n")
                print(public_url)
                print("Temporary HTTPS preview: available only while this Mac, Docker and tunnel are running.")
                return
            if proc.poll() is not None:
                raise SystemExit(f"Tunnel exited. Inspect the local log: {logfile}")
            time.sleep(0.25)
        raise SystemExit(f"Tunnel URL not available yet. Inspect the local log: {logfile}")

    def validate_runtime(self):
        ids = self.compose("ps", "-q", capture=True).stdout.split()
        items = json.loads(command(["docker", "inspect", *ids], capture=True).stdout) if ids else []
        assert len(items) == len(self.services()), "All configured services must be running before public exposure."
        for item in items:
            service = item["Config"]["Labels"]["com.docker.compose.service"]
            assert item["State"].get("Health", {}).get("Status") == "healthy", service
            ports = item["HostConfig"]["PortBindings"] or {}
            if service == "frontend":
                assert ports == {"80/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(self.settings["port"])}]}
            elif service == "traffic-dashboard":
                assert ports == {"3111/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(self.traffic_port())}]}
                assert set(item["NetworkSettings"]["Networks"]) == {self.settings["project"] + "_analytics"}
                assert item["HostConfig"]["ReadonlyRootfs"] is True
                assert item["Config"]["User"] == "10001:10001"
            else:
                assert not ports, f"Private runtime publishes a port: {service}"
                assert set(item["NetworkSettings"]["Networks"]) == {self.settings["project"] + "_private"}, service
            if service == "control-plane":
                env = dict(value.split("=", 1) for value in item["Config"]["Env"])
                for key, expected in (("INFORSIGHT_DEMO_PUBLIC_ENABLED", "true"), ("INFORSIGHT_DEMO_COOKIE_SECURE", "true"),
                                      ("INFORSIGHT_EXTERNAL_EXECUTION_ENABLED", "false"), ("INFORSIGHT_AUTHORIZED_TO_ACT", "false")):
                    assert env.get(key) == expected, f"Runtime configuration mismatch: {key}"
                assert env.get("INFORSIGHT_DB_PASSWORD") is None, "Database secret must not be an environment value."
                assert item["Config"]["User"] not in ("", "0", "root"), "Java must run as non-root."
                mounts = [m for m in item["Mounts"] if m["Destination"] == "/run/secrets"]
                assert len(mounts) == 1 and mounts[0]["RW"] is False
        network = json.loads(command(["docker", "network", "inspect", self.settings["project"] + "_private"], capture=True).stdout)[0]
        assert network["Internal"] is True
        print("PASS live private topology, non-root Java, secure sessions and disabled external actions")

    def process_running(self, name):
        file = self.state / f"{name}.pid"
        if not file.exists():
            return False
        pid = int(file.read_text())
        # Avoid signalling an unrelated process if the OS recycled a saved PID.
        probe = command(["ps", "-p", pid, "-o", "command="], capture=True, check=False).stdout
        expected = "cloudflared tunnel" if name == "tunnel" else str(Path(__file__).resolve())
        return expected in probe

    def tunnel_stop(self):
        if self.process_running("tunnel"):
            os.kill(int((self.state / "tunnel.pid").read_text()), signal.SIGTERM)
        (self.state / "tunnel.pid").unlink(missing_ok=True)
        print("Temporary tunnel stopped. Local service/data are preserved.")

    def maintain(self):
        """Delete broker records only behind retained evidence AND committed consumption."""
        self.require()
        query = """SELECT coalesce(min(record_offset)::text, '') FROM (
          SELECT record_offset FROM demo_inbox WHERE topic='inforsight.demo.events.v1' AND partition_id=0
          UNION ALL
          SELECT (s->'evidence'->>'offset')::bigint FROM demo_run,
            jsonb_array_elements(document->'stages') s
          WHERE s->>'stage'='publication' AND s->>'status'='completed'
            AND s->'evidence'->>'topic'='inforsight.demo.events.v1'
            AND s->'evidence'->>'partition'='0'
        ) offsets;"""
        groups = self.compose("exec", "-T", "kafka", "kafka-consumer-groups", "--bootstrap-server", "kafka:29092",
                              "--group", GROUP, "--describe", capture=True).stdout
        rows = [line.split() for line in groups.splitlines() if TOPIC in line and GROUP in line]
        matches = [row for row in rows if row[1:3] == [TOPIC, "0"] and row[3].isdigit()]
        if len(matches) != 1:
            print("No unambiguous committed consumer offset; broker deletion skipped safely.")
            return
        committed = int(matches[0][3])
        # Capture the broker fence FIRST: records published after this read have
        # offsets >= committed. A later DB read can only reduce that safe bound.
        retained = self.compose("exec", "-T", "postgres", "psql", "-U", "inforsight_app", "-d",
                                "inforsight_enterprise", "-At", "-c", query, capture=True).stdout.strip()
        cutoff = min(committed, int(retained)) if retained else committed
        if cutoff == 0:
            print("Broker cleanup waits for retained runs; cutoff is zero.")
            return
        payload = json.dumps({"partitions": [{"topic": TOPIC, "partition": 0, "offset": cutoff}], "version": 1})
        self.compose("exec", "-T", "kafka", "sh", "-c",
                     "umask 077; cat > /tmp/inforsight-delete-records.json; "
                     "kafka-delete-records --bootstrap-server kafka:29092 --offset-json-file /tmp/inforsight-delete-records.json; "
                     "result=$?; rm -f /tmp/inforsight-delete-records.json; exit $result",
                     input=payload, capture=True)
        print(f"Broker low watermark safely advanced to {cutoff}; committed={committed}, earliest retained={retained or 'none'}.")

    def maintenance_install(self):
        if sys.platform != "darwin":
            raise SystemExit("On Linux schedule 'public_demo.py maintain' with an operator-owned systemd timer every10min.")
        self.require()
        label = "com.inforsight." + self.settings["project"] + ".maintenance"
        file = Path.home() / "Library/LaunchAgents" / (label + ".plist")
        file.parent.mkdir(parents=True, exist_ok=True)
        data = {"Label": label, "ProgramArguments": [sys.executable, str(Path(__file__).resolve()),
                "--state-dir", str(self.state), "maintain"], "StartInterval": 600, "RunAtLoad": True,
                "StandardOutPath": str(self.state / "maintenance.log"),
                "StandardErrorPath": str(self.state / "maintenance-error.log"),
                "EnvironmentVariables": {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}}
        if file.exists():
            command(["launchctl", "bootout", f"gui/{os.getuid()}", file], capture=True, check=False)
        file.write_bytes(plistlib.dumps(data))
        file.chmod(0o600)
        command(["launchctl", "bootstrap", f"gui/{os.getuid()}", file])
        print(f"Installed operator-only broker maintenance every10min: {file}")

    def backup(self, destination: Path):
        """Consistent cold copy; resumes containers in finally, keeps session signing key."""
        self.require()
        destination = destination.expanduser().resolve()
        if destination == ROOT or ROOT in destination.parents:
            raise SystemExit("A backup contains signing/database secrets and must be outside the repository.")
        self.validate_runtime()
        self.provision_secrets()  # Fail if local keys no longer match the running volume.
        self.manifest()
        destination.mkdir(mode=0o700, parents=True, exist_ok=False)
        destination.chmod(0o700)
        self.compose("stop", "-t", "40")
        try:
            for name in self.data_volumes():
                volume = self.settings["project"] + "_" + name
                command(["docker", "run", "--rm", "--network", "none", "--user", "0",
                         "-v", f"{volume}:/source:ro", "-v", f"{destination}:/backup",
                         "postgres:16-alpine", "tar", "-czf", f"/backup/{name}.tgz", "-C", "/source", "."])
                (destination / f"{name}.tgz").chmod(0o600)
            shutil.copytree(self.state / "secrets", destination / "secrets")
            shutil.copy2(self.settings_file, destination / "settings.json")
            source = self.state / "deployment-manifest.json"
            if source.exists():
                shutil.copy2(source, destination / source.name)
            checksums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.glob("*.tgz")}
            (destination / "backup.json").write_text(json.dumps({"created_at": now(), "checksums": checksums}, indent=2) + "\n")
        finally:
            self.compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "180")
        print(f"Cold backup complete: {destination}. Contains sensitive session keys; keep private/offline.")

    def restore(self, source: Path):
        """Only restore into a newly initialized isolated namespace, never overwrite."""
        self.require()
        source = source.expanduser().resolve()
        info = json.loads((source / "backup.json").read_text())
        manifest = json.loads((source / "deployment-manifest.json").read_text())
        components = manifest["components"]
        recorded_services = {c["service"] for c in components}
        if recorded_services not in (set(SERVICES), set(SERVICES) - {"traffic-dashboard"}):
            raise SystemExit("Backup must record all runtime images (legacy six-service backups are supported).")
        volumes = DATA_VOLUMES if "traffic-dashboard" in recorded_services else DATA_VOLUMES[:2]
        for component in components:
            image_id = component["image_id"]
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
                raise SystemExit("Invalid recorded image identity.")
            if command(["docker", "image", "inspect", image_id], capture=True, check=False).returncode != 0:
                raise SystemExit("Load the backup's recorded Docker images before restoring its volumes.")
        if set(info["checksums"]) != {name + ".tgz" for name in volumes}:
            raise SystemExit("Backup must contain every runtime data volume archive.")
        for name, checksum in info["checksums"].items():
            if name not in {volume + ".tgz" for volume in volumes}:
                raise SystemExit("Unexpected backup member.")
            assert hashlib.sha256((source / name).read_bytes()).hexdigest() == checksum, name
            with tarfile.open(source / name, "r:gz") as archive:
                for member in archive:
                    paths = [member.name] + ([member.linkname] if member.issym() or member.islnk() else [])
                    if member.isdev() or any(Path(p).is_absolute() or ".." in Path(p).parts for p in paths):
                        raise SystemExit("Backup contains an unsafe archive path or device.")
        for name in volumes:
            volume = self.settings["project"] + "_" + name
            probe = command(["docker", "volume", "inspect", volume], capture=True, check=False)
            if probe.returncode == 0:
                raise SystemExit(f"Refusing to replace existing volume {volume}. Initialize a fresh restore project/state directory.")
        for name in volumes:
            volume = self.settings["project"] + "_" + name
            command(["docker", "volume", "create", "--label", "com.docker.compose.project=" + self.settings["project"],
                     "--label", "com.docker.compose.volume=" + name, volume], capture=True)
            command(["docker", "run", "--rm", "--network", "none", "--user", "0",
                     "-v", f"{volume}:/target", "-v", f"{source}:/backup:ro", "postgres:16-alpine",
                     "tar", "-xzf", f"/backup/{name}.tgz", "-C", "/target"])
        for name in ("db_password", "demo_session_secret"):
            shutil.copy2(source / "secrets" / name, self.state / "secrets" / name)
            (self.state / "secrets" / name).chmod(0o600)
        (self.state / "restore-images.json").write_text(json.dumps({"services": {
            c["service"]: {"image": c["image_id"]} for c in components}}, indent=2) + "\n")
        print("Restored runtime volumes and matching signing/database secrets. Start this isolated project, then verify saved audit receipts.")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    sub = parser.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init")
    init.add_argument("--project", default="inforsight-public")
    init.add_argument("--port", type=int, default=3100)
    up = sub.add_parser("up")
    up.add_argument("--no-build", action="store_true")
    for name in ("validate", "validate-runtime", "status", "manifest", "tunnel-start", "tunnel-stop", "maintain", "maintenance-install", "down"):
        sub.add_parser(name)
    backup = sub.add_parser("backup")
    backup.add_argument("directory", type=Path)
    restore = sub.add_parser("restore")
    restore.add_argument("directory", type=Path)
    compose = sub.add_parser("compose")
    compose.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    preview = Preview(args.state_dir)
    if args.action == "init": preview.init(args.project, args.port)
    elif args.action == "up": preview.up(not args.no_build)
    elif args.action == "status": preview.compose("ps")
    elif args.action == "down":
        preview.tunnel_stop()
        preview.compose("down")  # Data survives. Destructive removal is an explicit operator command.
    elif args.action == "backup": preview.backup(args.directory)
    elif args.action == "restore": preview.restore(args.directory)
    elif args.action == "compose": preview.compose(*args.arguments)
    else: getattr(preview, args.action.replace("-", "_"))()


if __name__ == "__main__":
    main()
