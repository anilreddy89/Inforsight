# Services

The `control-plane/` module is the P4-03 Java 21 / Spring Boot 3 control-plane
implementation. It is contract-first and local-only: deterministic rules and
allocation are implemented here, inference remains behind a bounded adapter,
and durable persistence/audit replay remain P4-04.

Run its focused checks with:

```bash
mvn -f services/control-plane/pom.xml test
```

The Docker-backed inference boundary test is opt-in:

```bash
make p4-03-integration-check
```

It requires a working Docker daemon and runs the Testcontainers test guarded
by `INFORSIGHT_RUN_JAVA_INTEGRATION=1`. Docker Desktop 4.91 currently needs
the Maven `-Dapi.version=1.44` compatibility setting used by the Make target.
