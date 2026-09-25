"""Run the non-authoritative local P4-07 latency profile."""

from __future__ import annotations

import argparse
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path


RESULT = re.compile(
    r"P4-07 combined capability smoke: accepted=(?P<accepted>\d+), "
    r"p99 ingress-to-scored-case=(?P<p99>[0-9.]+) ms"
)
STAGES = re.compile(
    r"P4-07 combined stages: ingress-to-handler p99=(?P<ingress>[0-9.]+) ms, "
    r"inference-batch p99=(?P<inference>[0-9.]+) ms, "
    r"post-inference-to-case p99=(?P<case>[0-9.]+) ms; "
    r"partitions=(?P<partitions>\d+), consumers=(?P<consumers>\d+), "
    r"fetch-min-bytes=(?P<fetch>\d+), "
    r"fetch-max-wait-ms=(?P<wait>\d+), max-poll-records=(?P<max_poll>\d+), "
    r"batches=(?P<batches>\d+), "
    r"max-batch=(?P<max_batch>\d+)"
)
PRODUCER = re.compile(
    r"P4-07 producer/consumer stages: ingress-to-ack p99=(?P<ack>[0-9.]+) ms, "
    r"ack-to-handler p99=(?P<handler>[0-9.]+) ms"
)


def linux_container_command() -> list[str]:
    repository = Path(__file__).resolve().parent.parent
    maven_repository = Path.home() / ".m2" / "repository"
    if not maven_repository.is_dir():
        raise ValueError(f"Maven dependency cache is required: {maven_repository}")
    context = os.environ.get("INFORSIGHT_P4_07_DOCKER_CONTEXT", "orbstack")
    network = os.environ.get("INFORSIGHT_P4_07_DOCKER_NETWORK", "infra_inforsight-network")
    benchmark_cpus = os.environ.get("INFORSIGHT_P4_07_BENCH_CPUS")
    environment = {
        "INFORSIGHT_RUN_P4_07_COMBINED_INTEGRATION": "1",
        "INFORSIGHT_P4_07_KAFKA_BOOTSTRAP_SERVERS": "kafka:29092",
        "INFORSIGHT_P4_07_INFERENCE_BASE_URL": "http://inference-runtime:8000",
        "INFORSIGHT_P4_07_POSTGRES_JDBC_URL": "jdbc:postgresql://postgres:5432/inforsight_enterprise",
        "INFORSIGHT_P4_07_PARTITION_COUNT": os.environ.get("INFORSIGHT_P4_07_PARTITION_COUNT", "12"),
        "INFORSIGHT_P4_07_CONSUMER_COUNT": "1",
        "INFORSIGHT_P4_07_MAX_POLL_RECORDS": os.environ.get("INFORSIGHT_P4_07_MAX_POLL_RECORDS", "500"),
        "INFORSIGHT_P4_07_FETCH_MIN_BYTES": "32768",
        "INFORSIGHT_P4_07_FETCH_MAX_WAIT_MS": "5",
        "INFORSIGHT_P4_07_PRODUCER_LINGER_MS": "2",
    }
    command = [
        "docker", "--context", context, "run", "--rm", "--network", network,
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{repository}:/workspace", "-v", f"{maven_repository}:/m2:ro",
        "-w", "/workspace",
    ]
    if benchmark_cpus:
        command.extend(("--cpuset-cpus", benchmark_cpus))
    for name, value in environment.items():
        command.extend(("-e", f"{name}={value}"))
    command.extend((
        "maven:3.9.9-eclipse-temurin-21-alpine", "mvn", "-o", "-q", "-Dmaven.repo.local=/m2",
        "-f", "services/control-plane/pom.xml", "-Dtest=P407CombinedTopologyIntegrationTest", "test",
    ))
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-container", action="store_true")
    parser.add_argument("--target-p99-ms", type=float)
    arguments = parser.parse_args()

    if arguments.linux_container:
        try:
            command = linux_container_command()
        except ValueError as error:
            print(error, file=sys.stderr)
            return 2
    else:
        required = ("INFORSIGHT_P4_07_KAFKA_BOOTSTRAP_SERVERS", "INFORSIGHT_P4_07_INFERENCE_BASE_URL")
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            print(f"Missing required local-service variables: {', '.join(missing)}", file=sys.stderr)
            return 2
        command = [
            "mvn", "-q", "-f", "services/control-plane/pom.xml",
            "-Dtest=P407CombinedTopologyIntegrationTest", "test",
        ]

    runs = int(os.environ.get("INFORSIGHT_P4_07_LOCAL_RUNS", "5"))
    if runs < 5:
        print("INFORSIGHT_P4_07_LOCAL_RUNS must be at least 5", file=sys.stderr)
        return 2

    environment = os.environ.copy()
    environment["INFORSIGHT_RUN_P4_07_COMBINED_INTEGRATION"] = "1"
    measurements: list[float] = []
    acknowledgements: list[float] = []
    handler_waits: list[float] = []
    for run in range(1, runs + 1):
        result = subprocess.run(command, text=True, capture_output=True, env=environment, check=False)
        output = result.stdout + result.stderr
        match = RESULT.search(output)
        stage_match = STAGES.search(output)
        producer_match = PRODUCER.search(output)
        if result.returncode != 0 or match is None or stage_match is None or producer_match is None:
            print(f"local P4-07 run {run}/{runs} failed or produced no scored-case measurement", file=sys.stderr)
            print(output[-4000:], file=sys.stderr)
            return 1
        accepted = int(match.group("accepted"))
        p99 = float(match.group("p99"))
        if accepted != 100:
            print(f"local P4-07 run {run}/{runs} accepted {accepted}/100", file=sys.stderr)
            return 1
        measurements.append(p99)
        ack = float(producer_match.group("ack"))
        handler = float(producer_match.group("handler"))
        acknowledgements.append(ack)
        handler_waits.append(handler)
        print(f"local P4-07 run {run}/{runs}: scored-case p99={p99:.3f} ms; "
              f"ingress-to-ack p99={ack:.3f} ms; ack-to-handler p99={handler:.3f} ms; "
              f"inference-batch p99={float(stage_match.group('inference')):.3f} ms; "
              f"partitions={stage_match.group('partitions')}; batches={stage_match.group('batches')}")

    median = statistics.median(measurements)
    worst = max(measurements)
    print(f"local P4-07 summary: median p99={median:.3f} ms, worst p99={worst:.3f} ms")
    print(f"local P4-07 producer summary: median ingress-to-ack p99={statistics.median(acknowledgements):.3f} ms, "
          f"worst ingress-to-ack p99={max(acknowledgements):.3f} ms; "
          f"worst ack-to-handler p99={max(handler_waits):.3f} ms")
    print("production E2 remains a separate controlled-environment gate at p99 <= 50 ms")
    if arguments.target_p99_ms is not None:
        if worst > arguments.target_p99_ms:
            print(f"local P4-07 {arguments.target_p99_ms:g} ms diagnostic target: FAIL")
            return 1
        print(f"local P4-07 {arguments.target_p99_ms:g} ms diagnostic target: PASS")
    if worst > 400.0:
        print("local P4-07 status: FAIL (worst run exceeds the >400 ms local regression band)")
        return 1
    if worst > 250.0:
        print("local P4-07 status: WARN (one or more runs exceed the 250 ms baseline)")
    else:
        print("local P4-07 status: PASS (local development baseline)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
