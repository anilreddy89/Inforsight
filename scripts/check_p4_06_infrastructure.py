"""Static, dependency-free checks for the P4-06 deployment baseline."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"{path} is missing required marker: {needle}")


def main() -> None:
    require(
        "infra/docker/Dockerfile.control-plane",
        "FROM maven:",
        "FROM eclipse-temurin:21-jre-alpine",
        "mvn -B -f services/control-plane/pom.xml -DskipTests package",
        "USER inforsight:inforsight",
    )
    require(
        "infra/docker/Dockerfile.inference",
        "FROM python:3.12-slim AS builder",
        "FROM python:3.12-slim AS runtime",
        "USER inforsight",
        "http://localhost:8000/health",
    )
    require(
        "infra/docker-compose.yml",
        "kafka:",
        "postgres:",
        "inference-runtime:",
        "control-plane:",
        "condition: service_healthy",
        'INFORSIGHT_EXTERNAL_EXECUTION_ENABLED: "false"',
        'INFORSIGHT_AUTHORIZED_TO_ACT: "false"',
    )
    chart = ROOT / "infra/helm/inforsight"
    for path in ("Chart.yaml", "values.yaml", "templates/control-plane-deployment.yaml", "templates/inference-deployment.yaml", "templates/postgres.yaml", "templates/hpa.yaml"):
        if not (chart / path).is_file():
            raise AssertionError(f"missing Helm chart file: {path}")
    require("infra/helm/inforsight/values.yaml", "externalExecutionEnabled: false", "authorizedToAct: false")
    require("infra/helm/inforsight/templates/hpa.yaml", "autoscaling/v2", "kind: HorizontalPodAutoscaler")
    print("P4-06 infrastructure checks passed")


if __name__ == "__main__":
    main()
