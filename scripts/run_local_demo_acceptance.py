"""Qualify the real Docker demo through its public HTTP gateway.

No mocked clients or expected success payloads. The optional fault probes stop
real containers belonging only to the explicitly selected Compose project.
"""
from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import sys
import subprocess
import time
import urllib.error
import urllib.request
import urllib.parse
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIGEST = "7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656"
STAGES = ["submission", "publication", "ingestion", "snapshot", "score", "rules", "allocation", "case", "agent", "decision", "audit"]


class Qualification:
    def __init__(self, base: str, *, compose_file="infra/docker-compose.yml", public=False, loopback_public=False):
        self.base = base.rstrip("/")
        self.compose_file = str(ROOT / compose_file)
        self.public = public
        self.loopback_public = loopback_public
        self.results: list[dict] = []
        self.runs: list[str] = []
        self.cookies = http.cookiejar.CookieJar()
        self.http = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))
        self.csrf = None
        self.session = None
        if public:
            parsed = urllib.parse.urlparse(self.base)
            if parsed.scheme != "https" and not (loopback_public and parsed.hostname in ("localhost", "127.0.0.1")):
                raise ValueError("Public qualification requires HTTPS; --loopback-public is only for private pre-exposure checks")
            self.session = self.request("/api/v1/demo/session")
            assert self.session["public_mode"] is True
            self.csrf = self.session["csrf_token"]
            assert len(self.csrf) >= 32
            assert len(list(self.cookies)) == 1
            cookie = next(iter(self.cookies))
            assert cookie.secure and cookie.has_nonstandard_attr("HttpOnly")

    def request(self, path: str, body=None, *, key=None, expected=(200, 201, 202), csrf=True, origin=None, extra_headers=None):
        headers = {"Accept": "application/json"}
        # The only HTTP exception is an explicitly selected loopback preflight.
        # The server still sets Secure; the public HTTPS pass uses CookieJar normally.
        if self.loopback_public:
            headers["Cookie"] = "; ".join(f"{c.name}={c.value}" for c in self.cookies)
        if body is not None and self.public:
            headers["Origin"] = origin or self.base
            if csrf and self.csrf:
                headers["X-Demo-CSRF"] = self.csrf
        if extra_headers:
            headers.update(extra_headers)
        if key:
            headers["Idempotency-Key"] = key
        data = None if body is None else json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, headers=headers)
        try:
            with self.http.open(req, timeout=30) as response:
                code, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            code, raw = error.code, error.read()
        try:
            parsed = json.loads(raw) if raw else {}
        except ValueError:
            parsed = {"gateway_message": raw.decode(errors="replace")[:256]}
        assert code in expected, (path, code, parsed)
        return parsed

    def record(self, name: str, evidence=None):
        self.results.append({"check": name, "passed": True, "evidence": evidence})
        print(f"PASS {name}", flush=True)

    def create(self, scenario="late-payment", key=None):
        run = self.request("/api/v1/demo/runs", {"scenario_id": scenario}, key=key or str(uuid.uuid4()))
        self.runs.append(run["correlation_id"])
        return run

    def get(self, rid):
        return self.request(f"/api/v1/demo/runs/{rid}")

    def wait(self, rid, predicate, timeout=90):
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            last = self.get(rid)
            if predicate(last):
                return last
            time.sleep(0.6 if self.public else 0.2)
        raise AssertionError(f"run {rid} did not reach expected state: {json.dumps(last)}")

    @staticmethod
    def stage(run, stage):
        return next((item for item in run["stages"] if item["stage"] == stage), {})

    def ready(self, rid):
        result = self.wait(rid, lambda r: self.stage(r, "agent").get("status") in ("completed", "abstained") or r["status"].upper() == "FAILED")
        assert result["status"].upper() != "FAILED", result
        return result

    def decision(self, run, decision="APPROVED", *, key=None, version=None, expected=(200, 201, 202)):
        return self.request(f"/api/v1/demo/runs/{run['correlation_id']}/decision", {
            "decision": decision,
            "expected_case_version": run["case_version"] if version is None else version,
            "idempotency_key": key or str(uuid.uuid4()),
            "rationale": "FICTIONAL_REVIEW",
            "notes": "Acceptance test: reviewed the persisted fictional evidence. No external action.",
            "reviewer_id": "fictional-acceptance-reviewer",
        }, expected=expected)

    def compose(self, *args):
        subprocess.run(["docker", "compose", "-f", self.compose_file, *args], cwd=ROOT, check=True)

    def sql(self, statement, *, succeeds=True):
        result = subprocess.run(["docker", "compose", "-f", self.compose_file, "exec", "-T", "postgres",
            "psql", "-U", "inforsight_app", "-d", "inforsight_enterprise", "-At", "-c", statement],
            cwd=ROOT, capture_output=True, text=True)
        assert (result.returncode == 0) is succeeds, result.stderr
        return result.stdout.strip() if succeeds else result.stderr.strip()

    def kafka(self, *args, records=None):
        """Use the real broker CLI; records go to stdin, never shell text."""
        result = subprocess.run(["docker", "compose", "-f", self.compose_file,
            "exec", "-T", "kafka", *args], cwd=ROOT, input=records, capture_output=True,
            text=True, timeout=45)
        assert result.returncode == 0, (args, result.stderr)
        return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:3000")
    parser.add_argument("--faults", action="store_true", help="Interrupt only the selected dedicated Compose containers")
    parser.add_argument("--compose-file", default="infra/docker-compose.yml")
    parser.add_argument("--public", action="store_true", help="Require signed visitor session and same-origin CSRF")
    parser.add_argument("--loopback-public", action="store_true", help="Allow private pre-exposure HTTP on loopback only")
    parser.add_argument("--output", default="artifacts/local-demo/acceptance.json")
    args = parser.parse_args()
    q = Qualification(args.base_url, compose_file=args.compose_file, public=args.public, loopback_public=args.loopback_public)
    report = {"local_result": "FAIL", "gcp_result": "FAIL — Planned; not deployed", "public_result": "FAIL" if args.public else "NOT_RUN", "base_url": args.base_url, "compose_file": args.compose_file, "loopback_preflight": args.loopback_public, "checks": q.results, "runs": q.runs}
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        qualify(q, args.faults, report)
        report["local_result"] = "PASS"
        if args.public:
            report["public_result"] = "PASS_PRIVATE_PREFLIGHT" if args.loopback_public else "PASS"
    finally:
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Evidence: {output}", flush=True)


def qualify(q: Qualification, faults: bool, report: dict):
    # Detailed evidence assertions are intentionally centralized here so the
    # acceptance boundary remains independent of frontend rendering.
    capabilities = q.request("/api/v1/demo/scenarios")
    report["capabilities"] = capabilities
    key = str(uuid.uuid4())
    submitted = q.create(key=key)
    rid = submitted["correlation_id"]
    report["primary_run_id"] = rid
    duplicate = q.create(key=key)
    assert duplicate["correlation_id"] == rid
    q.request("/api/v1/demo/runs", {"scenario_id": "agent-abstention"}, key=key, expected=(409,))
    q.record("submission idempotency and conflicting reuse", rid)
    ready = q.ready(rid)
    q.record("real journey reached human review", rid)
    for name in STAGES[:9]:
        step = q.stage(ready, name)
        assert step["status"] in ("completed", "abstained"), (name, step)
        assert step["started_at"] and step["completed_at"] and step["producer"]
        assert step["duration_ms"] >= 0 and step["attempt"] >= 1
        assert step["output_refs"] and step["evidence"], (name, step)
    publication = q.stage(ready, "publication")["evidence"]
    ingestion = q.stage(ready, "ingestion")["evidence"]
    for field in ("topic", "partition", "offset"):
        assert publication[field] == ingestion[field], (publication, ingestion)
    assert ingestion["event_id"] == ready["event_id"]
    q.record("broker acknowledgement matches durable consumer receipt", ingestion)
    verify_artifacts(q, ready)
    report["pre_review"] = ready
    review_key = str(uuid.uuid4())
    q.decision(ready, key=review_key)
    q.decision(ready, key=review_key)
    final = q.get(rid)
    assert final["case_version"] == ready["case_version"] + 1
    q.record("human decision idempotency", final["case_version"])
    q.decision(ready, decision="REJECTED", expected=(409,))
    q.record("stale human decision rejected")
    audit = q.request(f"/api/v1/demo/runs/{rid}/audit")
    assert audit.get("valid") is True, audit
    verify_audit(audit, rid)
    final = q.get(rid)
    for stage in final["stages"]:
        completed = [e for e in audit["entries"] if e["stage"] == stage["stage"] and e["payload"]["status"] in ("completed", "abstained")]
        assert len(completed) == 1, (stage["stage"], len(completed))
        assert completed[0]["payload"]["evidence"] == stage, stage["stage"]
    q.record("every displayed completed stage matches hash-bound persisted evidence")
    # Corrupt a copy, never the running database or its immutable journal.
    tampered = json.loads(json.dumps(audit))
    tampered["entries"][0]["canonical_payload"] += " "
    rejected = False
    try:
        verify_audit(tampered, rid)
    except AssertionError:
        rejected = True
    assert rejected
    q.record("independent verifier detects modified evidence export")
    counts = q.sql(f"SELECT (SELECT count(*) FROM demo_inbox WHERE correlation_id='{rid}'), (SELECT count(*) FROM demo_case WHERE correlation_id='{rid}'), (SELECT count(*) FROM demo_decision WHERE correlation_id='{rid}'), (SELECT version FROM demo_case WHERE correlation_id='{rid}');")
    assert counts == "1|1|1|1", counts
    q.record("PostgreSQL inbox, case and human decision persisted once", counts)
    mutation = q.sql(f"UPDATE demo_journal SET producer=producer WHERE correlation_id='{rid}';", succeeds=False)
    assert "append-only" in mutation
    q.record("PostgreSQL rejects journal row updates")
    assert q.request(f"/api/v1/demo/runs/{rid}/audit")["head_hash"] == audit["head_hash"]
    report["primary_run"] = q.get(rid)
    report["audit"] = audit
    q.record("persisted audit verified", audit)
    broker_ingress_checks(q, final)
    for scenario in ("missing-safety-evidence", "agent-abstention"):
        case = q.ready(q.create(scenario)["correlation_id"])
        assert case["artifacts"]["agent"]["status"] == "ABSTAIN"
        assert case["artifacts"]["allocation"]["selected_action"] == "abstain"
        assert case["artifacts"]["agent"]["authorized_to_act"] is False
        q.decision(case, expected=(400,))
        q.decision(case, decision="REQUEST_MORE_INFORMATION" if scenario == "missing-safety-evidence" else "REJECTED")
        receipt = q.request(f"/api/v1/demo/runs/{case['correlation_id']}/audit")
        assert receipt["valid"] is True
        verify_audit(receipt, case["correlation_id"])
        q.record(f"{scenario}: real abstention, approval blocked, human decision audited", case["correlation_id"])
    if faults:
        fault_checks(q)


def broker_ingress_checks(q: Qualification, completed: dict):
    """Prove broker redelivery and poison-record recovery with durable evidence.

    The local topic has one partition. A later quarantined record and then a
    later accepted public submission prove the consumer traversed the exact
    re-published duplicate; unchanged rows and audit checkpoint prove deduping.
    """
    rid = completed["correlation_id"]
    before = q.request(f"/api/v1/demo/runs/{rid}/audit")
    envelope = json.loads(q.sql(f"SELECT envelope::text FROM demo_outbox WHERE correlation_id='{rid}';"))
    assert envelope["event_id"] == completed["event_id"]
    assert envelope["correlation_id"] == rid
    topic = q.stage(completed, "ingestion")["evidence"]["topic"]
    offsets = q.kafka("kafka-get-offsets", "--bootstrap-server", "kafka:29092", "--topic", topic, "--time", "latest")
    partitions = [line.rsplit(":", 2) for line in offsets.splitlines() if line.startswith(topic + ":")]
    assert len(partitions) == 1 and partitions[0][:2] == [topic, "0"], offsets
    first_possible_offset = int(partitions[0][2])
    marker = "acceptance-malformed-" + uuid.uuid4().hex
    malformed = '{"fictional":true,"acceptance_marker":"' + marker + '"'
    malformed_digest = hashlib.sha256(malformed.encode()).hexdigest()
    records = (envelope["event_id"] + "\t" + json.dumps(envelope, separators=(",", ":")) + "\n"
               + marker + "\t" + malformed + "\n")
    q.kafka("kafka-console-producer", "--bootstrap-server", "kafka:29092", "--topic", topic,
            "--sync", "--property", "parse.key=true", "--property", "key.separator=\t",
            "--producer-property", "acks=all", records=records)

    deadline = time.monotonic() + 30
    quarantine = None
    while time.monotonic() < deadline:
        raw = q.sql("SELECT row_to_json(receipt)::text FROM "
                    "(SELECT topic,partition_id,record_offset,payload_sha256,error_code,rejected_at "
                    f"FROM demo_ingress_quarantine WHERE payload_sha256='{malformed_digest}') receipt;")
        if raw:
            quarantine = json.loads(raw)
            break
        time.sleep(.2)
    assert quarantine is not None, "malformed Kafka record was not durably quarantined"
    assert quarantine["topic"] == topic and quarantine["partition_id"] == 0
    assert quarantine["record_offset"] > first_possible_offset, quarantine
    assert quarantine["payload_sha256"] == malformed_digest
    assert quarantine["error_code"] == "INVALID_OR_UNBOUND_DEMO_ENVELOPE"

    following = q.ready(q.create()["correlation_id"])
    following_receipt = q.stage(following, "ingestion")["evidence"]
    assert following_receipt["topic"] == topic and following_receipt["partition"] == 0
    assert following_receipt["offset"] > quarantine["record_offset"], (following_receipt, quarantine)
    q.decision(following, decision="REJECTED")
    following_audit = q.request(f"/api/v1/demo/runs/{following['correlation_id']}/audit")
    assert following_audit["valid"] is True, following_audit
    verify_audit(following_audit, following["correlation_id"])

    after = q.request(f"/api/v1/demo/runs/{rid}/audit")
    assert after["valid"] is True and after["head_hash"] == before["head_hash"]
    assert after["verified_entries"] == before["verified_entries"]
    assert q.get(rid)["case_version"] == completed["case_version"]
    for run_id in (rid, following["correlation_id"]):
        counts = q.sql(f"SELECT (SELECT count(*) FROM demo_inbox WHERE correlation_id='{run_id}'), "
                       f"(SELECT count(*) FROM demo_case WHERE correlation_id='{run_id}'), "
                       f"(SELECT count(*) FROM demo_decision WHERE correlation_id='{run_id}');")
        assert counts == "1|1|1", (run_id, counts)
    q.record("real Kafka duplicate delivery preserves one inbox, case, decision and audit checkpoint", {
        "correlation_id": rid, "event_id": envelope["event_id"], "topic": topic, "partition": 0,
        "duplicate_offset_at_least": first_possible_offset, "duplicate_offset_before": quarantine["record_offset"],
        "unchanged_audit_head": after["head_hash"], "row_counts": "1|1|1",
    })
    q.record("malformed broker record quarantined; following public event completes and verifies", {
        "quarantine": quarantine, "following_run_id": following["correlation_id"],
        "following_ingestion": following_receipt, "following_audit_head": following_audit["head_hash"],
    })


def fault_checks(q: Qualification):
    q.compose("stop", "inference-runtime")
    try:
        run = q.create()
        rid = run["correlation_id"]
        failed = q.wait(rid, lambda r: r["status"] == "FAILED")
        assert q.stage(failed, "score")["status"] == "failed"
        assert not failed["artifacts"].get("score")
        assert all(q.stage(failed, stage)["status"] == "blocked" for stage in STAGES[5:])
        q.decision(failed, expected=(409,))
        q.record("inference outage persists failure, blocks downstream work and human approval", rid)
        before = q.request(f"/api/v1/demo/runs/{rid}/audit")["head_hash"]
        q.compose("restart", "control-plane")
        wait_gateway(q)
        recovered = q.get(rid)
        assert recovered["status"] == "FAILED"
        assert q.request(f"/api/v1/demo/runs/{rid}/audit")["head_hash"] == before
        q.record("failed run and journal survive control-plane restart", rid)
    finally:
        q.compose("start", "inference-runtime")
    wait_inference(q)
    q.request(f"/api/v1/demo/runs/{rid}/retry", {})
    ready = q.ready(rid)
    assert ready["event_id"] == run["event_id"]
    assert q.stage(ready, "score")["attempt"] == 2
    q.decision(ready, decision="REJECTED")
    receipt = q.request(f"/api/v1/demo/runs/{rid}/audit")
    verify_audit(receipt, rid)
    q.record("retry resumes same event without duplicate ingestion or case", rid)

    # Freeze the real inference process, then crash Java while an HTTP request
    # is in flight. No fake delay or test endpoint is added to application code.
    q.compose("pause", "inference-runtime")
    try:
        run = q.create()
        rid = run["correlation_id"]
        in_flight = q.wait(rid, lambda r: q.stage(r, "score").get("status") == "processing", timeout=12)
        q.compose("kill", "-s", "SIGKILL", "control-plane")
        q.compose("up", "-d", "--no-deps", "--no-build", "control-plane")
    finally:
        q.compose("unpause", "inference-runtime")
        q.compose("up", "-d", "--no-deps", "--no-build", "control-plane")
    wait_gateway(q)
    ready = q.ready(rid)
    assert ready["event_id"] == in_flight["event_id"]
    assert q.stage(ready, "score")["attempt"] >= 2
    q.decision(ready, decision="REJECTED")
    receipt = q.request(f"/api/v1/demo/runs/{rid}/audit")
    verify_audit(receipt, rid)
    completed = [e["stage"] for e in receipt["entries"] if e["payload"]["status"] in ("completed", "abstained")]
    assert len(completed) == len(set(completed)) == len(STAGES)
    q.record("in-flight crash automatically resumes; each stage commits once", rid)


def wait_gateway(q):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            q.request("/api/v1/demo/scenarios")
            return
        except (OSError, AssertionError, ValueError):
            time.sleep(.5)
    raise AssertionError("gateway did not recover")


def wait_inference(q):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        result = subprocess.run(["docker", "compose", "-f", q.compose_file, "exec", "-T", "inference-runtime",
            "python", "-c", "import json,urllib.request; assert json.load(urllib.request.urlopen('http://localhost:8000/health',timeout=2))['engine_status']=='ready'"],
            cwd=ROOT, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return
        time.sleep(.5)
    raise AssertionError("inference did not recover")


def verify_artifacts(q, run):
    sys.path[:0] = [str(ROOT), str(ROOT / "simulator/src"), str(ROOT / "inference-runtime/src")]
    from inforsight_inference import load_verified_runtime
    from serving.preprocessing import coefficient_features
    from demo_runtime.app import ProjectRequest, project
    artifacts = run["artifacts"]
    snapshot, projection, score = artifacts["snapshot"], artifacts["projection"], artifacts["score"]
    source = run["source"]
    replay = project(ProjectRequest(history=source["history"], as_of=source["as_of"], policy_id=run["policy_id"], event_id=run["event_id"]))
    replay = json.loads(json.dumps(replay))  # Normalize dataclass tuples at the HTTP serialization boundary.
    assert replay["snapshot"] == snapshot and replay["features"] == projection["features"]
    assert run["event_id"] in projection["source_event_ids"]
    assert projection["excluded_event_ids"], "fixture must demonstrate future evidence exclusion"
    q.record("point-in-time facts/features independently reconstructed; future evidence excluded", {"snapshot_id": snapshot["snapshot_id"], "excluded": projection["excluded_event_ids"]})
    assert score["bundle_digest"] == RELEASE_DIGEST
    assert score["authorized_to_act"] is False and score["top_risk_drivers"]
    model = load_verified_runtime(ROOT / "docs/experiments/phase-02-10-model-bundle.json", expected_sha256=RELEASE_DIGEST,
        expected_bundle_id="inforsight-v6-logistic-platt-20260817", expected_bundle_version="1.0.0")
    independent = model.engine.score_record(coefficient_features(projection["features"]))
    assert round(independent.calibrated_probability, 6) == score["calibrated_probability"]
    q.record("released HTTP score matches independently loaded verified bundle", {"bundle_sha256": RELEASE_DIGEST, "risk": score["calibrated_probability"]})
    rules = artifacts["rules"]["results"]
    allocation = artifacts["allocation"]
    selected = allocation["selected"]
    assert len(selected) <= 1
    allowed = {r["action_type"] for r in rules if r["eligible"]}
    for candidate in selected:
        assert candidate["action_type"] in allowed and candidate["policy_id"] == run["policy_id"]
    assert allocation["used_money_micros"] <= allocation["budget_micros"]
    assert allocation["used_personnel_seconds"] <= allocation["personnel_seconds"]
    q.record("Java eligibility and one-action allocation obey recorded capacity", allocation["selected_action"])
    agent = artifacts["agent"]
    assert agent["authorized_to_act"] is False and agent["human_review_required"] is True
    assert agent["producer"]["worker_id"] and agent["workflow_id"]
    assert agent["action_id"] == allocation["selected_action"]
    assert set(agent["evidence_source_ids"]).issubset(projection["source_event_ids"])
    assert len(agent["evidence_source_ids"]) >= 2, "payment and safety facts require distinct source citations"
    assert agent["procedure_citations"] == ["fictional-local-review@1.0.0"]
    assert run["case_version"] == 0 and artifacts["case"]["authorized_to_act"] is False
    q.record("real bounded agent cites source evidence without changing human authority", agent["producer"])


def verify_audit(audit: dict, rid: str):
    parent = "0" * 64
    entries = audit["entries"]
    assert entries and len(entries) == audit["verified_entries"]
    for sequence, entry in enumerate(entries, 1):
        assert entry["sequence"] == sequence
        assert entry["parent_hash"] == parent
        computed = hashlib.sha256((parent + "\n" + entry["canonical_payload"]).encode()).hexdigest()
        assert computed == entry["current_hash"]
        payload = json.loads(entry["canonical_payload"])
        assert payload == entry["payload"]
        assert payload["correlation_id"] == rid
        assert payload["journal_event_id"] == entry["event_id"]
        assert payload["stage"] == entry["stage"] and payload["producer"] == entry["producer"]
        parent = computed
    assert parent == audit["head_hash"]


if __name__ == "__main__":
    main()
