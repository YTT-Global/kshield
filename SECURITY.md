# Security Policy

KShield exists to help developers catch security issues before they ship — so a vulnerability in KShield itself gets treated as a priority, not an afterthought.

## Supported Versions

Only the latest released version is supported with security fixes. There is no long-term-support branch yet — upgrade to the newest release to get a fix.

## Reporting a Vulnerability

**Do not open a public GitHub issue for a security vulnerability.** Email `accounts@ytt.global` directly instead, with:

- A description of the vulnerability and its impact
- Steps to reproduce (exact commands, request payloads, or code samples)
- Which component is affected (Rust CLI, Python backend, React dashboard, VS Code extension, or the installers)
- Your assessment of severity, if you have one

You should receive an acknowledgement within 5 business days. We'll keep you updated as the issue is triaged, fixed, and released, and will credit you in the release notes unless you'd prefer to stay anonymous.

## Scope

In scope: the Rust CLI, the FastAPI backend, the React dashboard, the VS Code extension, and the four install paths (`install.sh`, the Homebrew formula, the npm wrapper, the PyPI package).

A few things worth knowing up front rather than reported as surprises — these are tracked, known gaps rather than undiscovered vulnerabilities:

- The backend API currently has no authentication on any endpoint. This is a reasonable default for the local-first, `127.0.0.1`-only install path, but matters if you point `KSHIELD_BACKEND` at a shared or network-reachable instance (e.g. via `docker-compose.yml`). Treat any non-localhost deployment as requiring a reverse proxy or firewall in front of it until this is addressed.
- Findings and remediation patches are generated locally from the scanned file's own content — a specially crafted source file is a more relevant threat model here than a typical web app's input validation surface. If you find a way to make the entropy/regex/AST engines misbehave (crash, hang, or produce an unsafe patch) on adversarial input, that's exactly the kind of report we want.

## What Happens After a Report

1. We confirm the issue and determine severity.
2. A fix is developed and tested against the existing test suite plus a regression test for the specific issue.
3. A new release is cut and the fix is documented in `CHANGELOG.md`.
4. Public disclosure happens after the fix is released, coordinated with you.
