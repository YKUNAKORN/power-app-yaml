# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-27

### Added
- Initial public release of the `power-app-yaml` Claude skill.
- Workflow, control picker, fill-in templates, and pre-send checklist in
  `skills/power-app-yaml/SKILL.md`.
- Empirical control catalog `skills/power-app-yaml/references/confirmed-controls.md`,
  built from real Power Apps Studio paste tests.
- Bundled Microsoft `pa.yaml` v3.0 schema for offline reference (see `NOTICE`).
- Three real, paste-tested example screens under
  `skills/power-app-yaml/assets/examples/` (app shell, form, card grid).
- Claude Code plugin packaging: `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`.
- Repository documentation: `README`, `docs/quickstart.md`,
  `docs/troubleshooting.md`.
- Community health files: `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`,
  `SUPPORT`, GitHub issue/PR templates.
- CI: `scripts/validate.py` and `.github/workflows/validate.yml`.

[Unreleased]: https://github.com/YKUNAKORN/power-app-yaml/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YKUNAKORN/power-app-yaml/releases/tag/v0.1.0
