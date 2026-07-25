# Security Policy

## Reporting a Vulnerability

If you find a security vulnerability in `promptlint`, please report it privately rather than opening a public issue.

- **Preferred:** open the repo's [Security tab -> Report a vulnerability](https://github.com/M-Ashrey/promptlint/security/advisories/new) (GitHub private advisory).
- **Alternative:** email m.ashrey122@gmail.com with subject `SECURITY: promptlint`.

Please include a description of the issue, steps to reproduce (a minimal example is ideal), and the potential impact. A suggested fix is welcome but not required.

This is a solo-maintained open-source project — there's no formal SLA, but security reports are treated as priority and acknowledged as soon as I see them, typically within a few days.

## Supported Versions

Only the latest release on PyPI and the `main` branch are supported. There are no LTS branches at this stage.

## Scope

`promptlint` only reads the files you point it at (Markdown/text prompt files) and never executes their contents. It has no network access and no eval/exec of file contents. The main thing worth reporting here is a regex or parser (`promptlint/rules.py`, `promptlint/tokens.py`) that could be driven into catastrophic backtracking or excessive resource use (ReDoS) by a crafted input file.
