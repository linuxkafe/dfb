# Common Errors

## General

### Secrets Committed to Git
- Symptom: GitHub alerts; credentials exposed
- Fix: Remove from git history; rotate secrets
- Prevention: Pre-merge hook checks for .env, *.key, *.pem

### TODO Left in Source
- Symptom: make check fails with "Found TODO: in source"
- Fix: Resolve or move to docs/ROADMAP.md
- Prevention: pre-build hook checks for TODOs

Add project-specific errors below:
