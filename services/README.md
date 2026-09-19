# Services

The `control-plane/` module is the P4-03 Java 21 / Spring Boot 3 control-plane
implementation. It is contract-first and local-only: deterministic rules and
allocation are implemented here, inference remains behind a bounded adapter,
and durable persistence/audit replay remain P4-04.

Run its focused checks with:

```bash
mvn -f services/control-plane/pom.xml test
```
