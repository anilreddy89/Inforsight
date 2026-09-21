"""Run the non-authoritative local P4-07 latency profile."""

from __future__ import annotations

import os
import re
import statistics
import subprocess
import sys


RESULT = re.compile(
    r"P4-07 combined capability smoke: accepted=(?P<accepted>\d+), "
    r"p99 ingress-to-scored-case=(?P<p99>[0-9.]+) ms"
)


def main() -> int:
    required = ("INFORSIGHT_P4_07_KAFKA_BOOTSTRAP_SERVERS", "INFORSIGHT_P4_07_INFERENCE_BASE_URL")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print(f"Missing required local-service variables: {', '.join(missing)}", file=sys.stderr)
        return 2

    runs = int(os.environ.get("INFORSIGHT_P4_07_LOCAL_RUNS", "5"))
    if runs < 5:
        print("INFORSIGHT_P4_07_LOCAL_RUNS must be at least 5", file=sys.stderr)
        return 2

    environment = os.environ.copy()
    environment["INFORSIGHT_RUN_P4_07_COMBINED_INTEGRATION"] = "1"
    command = [
        "mvn", "-q", "-f", "services/control-plane/pom.xml",
        "-Dtest=P407CombinedTopologyIntegrationTest", "test",
    ]
    measurements: list[float] = []
    for run in range(1, runs + 1):
        result = subprocess.run(command, text=True, capture_output=True, env=environment, check=False)
        output = result.stdout + result.stderr
        match = RESULT.search(output)
        if result.returncode != 0 or match is None:
            print(f"local P4-07 run {run}/{runs} failed or produced no scored-case measurement", file=sys.stderr)
            print(output[-4000:], file=sys.stderr)
            return 1
        accepted = int(match.group("accepted"))
        p99 = float(match.group("p99"))
        if accepted != 100:
            print(f"local P4-07 run {run}/{runs} accepted {accepted}/100", file=sys.stderr)
            return 1
        measurements.append(p99)
        print(f"local P4-07 run {run}/{runs}: scored-case p99={p99:.3f} ms")

    median = statistics.median(measurements)
    worst = max(measurements)
    print(f"local P4-07 summary: median p99={median:.3f} ms, worst p99={worst:.3f} ms")
    print("production E2 remains a separate controlled-environment gate at p99 <= 50 ms")
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
