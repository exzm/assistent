# Security Policy

## Supported versions

The `main` branch receives security fixes.

## Reporting a vulnerability

Please report security issues privately to the repository maintainer.
Do not open a public issue for credential leaks or remote exploits.

Include:

- affected version / commit
- reproduction steps
- impact assessment

## Secrets

If an API token or bot token is exposed:

1. Revoke/rotate it immediately at the provider
2. Redeploy with the new secret
3. Audit logs for unexpected usage
