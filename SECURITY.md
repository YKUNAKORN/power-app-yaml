# Security Policy

## Scope

This repository ships a Claude **skill**: Markdown instructions, a control
catalog, a bundled JSON schema, and example `.pa.yaml` files. It contains no
executable application code and no runtime service. The realistic security
concerns are:

- A bundled file that is malicious or has been tampered with
  (`skills/power-app-yaml/references/schema-v3.pa.yaml`).
- An example `.pa.yaml` that leaks real data, credentials, or internal URLs.
- Instructions that could lead a model to produce unsafe Power Fx (e.g. calling
  out to an attacker-controlled endpoint).

## Reporting a vulnerability

**Do not open a public issue for security problems.**

Report privately via GitHub:
[**Report a vulnerability**](https://github.com/YKUNAKORN/power-app-yaml/security/advisories/new)

Please include what you found, the file/line, and (if relevant) a minimal
reproduction. You can expect an initial response within **7 days**. Once a fix is
released, we will credit you in `CHANGELOG.md` unless you prefer to remain
anonymous.

## Supported versions

Only the latest tagged release (and `main`) receive fixes.
