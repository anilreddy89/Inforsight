# Security Policy

Inforsight is a fictional-data portfolio project and must not receive real policyholder, customer, insurer, or payment data.

## Reporting a vulnerability

Do not open a public issue containing secrets, personal data, or exploit details. Contact the repository owner privately through the security-reporting mechanism configured on the hosting platform.

## Repository security rules

- Never commit credentials, tokens, private keys, cloud configuration containing secrets, or production connection strings.
- Use `.env.example` only for non-secret variable names and safe defaults.
- Keep generated datasets small, fictional, reproducible, and explicitly labeled.
- Pin or otherwise review third-party dependencies before release.
- Generate an SBOM and dependency/license report before the first public release.
- Treat model files and serialized objects as untrusted inputs.

## Supported versions

Until the first tagged release, security fixes apply to the default branch only.
