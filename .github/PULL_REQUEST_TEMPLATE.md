<!-- Thanks for contributing! Keep this short. -->

## What this changes

<!-- One or two sentences. -->

## Type

- [ ] Catalog update (`confirmed-controls.md`)
- [ ] New / updated example screen
- [ ] SKILL.md workflow, templates, or rules
- [ ] Eval case (`tests/evals/`)
- [ ] Docs
- [ ] Packaging / CI
- [ ] Other

## Studio evidence (required for catalog / example changes)

- Power Apps Studio version:
- What you pasted and what Studio did:

<!-- Paste the minimal YAML and the exact Studio result / warning code. -->

## Eval evidence (required if this changes SKILL.md, the catalog, or the patterns)

<!-- Run at least two cases before and after, and paste the rows that changed.
     See docs/evals.md. One run per case is a sample of one -- say so if that is
     all you have. -->

## Checklist

- [ ] `python scripts/validate.py` passes
- [ ] Any catalog change cites a Studio version
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`
- [ ] `plugin.json` `version` bumped if behaviour changed (SemVer)
- [ ] No real data / secrets in example YAML
