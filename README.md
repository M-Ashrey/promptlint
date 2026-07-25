# promptlint

A linter for prompt and agent-instruction files.

`promptlint` checks the Markdown files that steer LLM agents — system prompts,
`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `*.prompt` — for the mistakes that
quietly degrade instruction quality: token-budget overruns, hedging language,
leftover placeholders, and broken structure. It runs in CI or as a pre-commit
hook, needs no configuration to start, and has zero required dependencies.

## Why it exists

Prompt files have become source code: they are versioned, reviewed, and shipped.
But unlike source code, they usually have no linter. Two failure modes are
common and expensive:

- **Silent budget creep.** A `CLAUDE.md` grows over months until it eats a large
  slice of every request's context window, slowing responses and crowding out
  the actual task.
- **Weak or broken instructions.** Hedging phrases ("try to", "if possible")
  turn directives into suggestions, and unresolved placeholders (`{{TODO}}`,
  `<PLACEHOLDER>`) ship straight into production prompts.

`promptlint` catches both, plus structural issues, before they reach an agent.

## Install

```bash
pip install promptlint
```

For exact token counts, install the optional tokenizer backend:

```bash
pip install "promptlint[accurate]"   # pulls in tiktoken
```

Without `tiktoken`, promptlint uses a dependency-free heuristic that is close
enough for budgeting decisions.

## Usage

Lint the current directory (auto-discovers known prompt filenames):

```bash
promptlint .
```

Enforce a per-file token budget and fail CI on any warning or worse:

```bash
promptlint CLAUDE.md --budget 4000
```

Show token totals per file:

```bash
promptlint prompts/ --stats
```

Machine-readable output for tooling:

```bash
promptlint . --format json
```

Run a subset of rules, or skip some:

```bash
promptlint . --select token-budget,placeholder
promptlint . --ignore trailing-whitespace
```

List every rule:

```bash
promptlint --list-rules
```

### Example output

Running promptlint on a prompt file with real issues:

```
$ promptlint examples/bad.CLAUDE.md --max-severity error
examples/bad.CLAUDE.md
     3  warning  heading jumps from h1 to h3  heading-jump
     4  warning  hedging phrase 'maybe' weakens the instruction  hedging
     6  warning  hedging phrase 'sort of' weakens the instruction  hedging
     8    error  unresolved placeholder 'TODO'  placeholder
     9    error  unresolved placeholder '<INSERT_ERROR_POLICY>'  placeholder
    10  warning  hedging phrase 'possibly' weakens the instruction  hedging
    10    error  unresolved placeholder '{{API_KEY}}'  placeholder
    10     info  trailing whitespace  trailing-whitespace
    12  warning  hedging phrase 'perhaps' weakens the instruction  hedging
9 finding(s) across 1 file(s)
$ echo $?
1
```

A well-written prompt file (`examples/good.CLAUDE.md`) lints clean and exits `0` — this pair is exactly what CI runs as a regression check on every push.

### Exit codes

`promptlint` exits non-zero when a finding reaches `--max-severity` (default
`warning`), which makes it drop-in for CI. Use `--max-severity error` to only
fail on hard errors.

### Configuration

Optional. Add a `[tool.promptlint]` table to `pyproject.toml` or a standalone
`.promptlint.toml`:

```toml
[tool.promptlint]
token_budget = 4000
model = "cl100k_base"
ignore = ["trailing-whitespace"]
patterns = ["*.prompt", "CLAUDE.md", "AGENTS.md"]
```

CLI flags always override file config.

## Rules

| Rule | Severity | What it catches |
|------|----------|-----------------|
| `token-budget` | error | File exceeds the configured token budget |
| `placeholder` | error | Unresolved `TODO`/`FIXME`/`{{...}}`/`<PLACEHOLDER>` markers |
| `empty-file` | error | Empty or whitespace-only file |
| `hedging` | warning | Phrases that soften directives ("try to", "if possible") |
| `heading-jump` | warning | Heading levels that skip (h1 -> h3) |
| `trailing-whitespace` | info | Trailing whitespace that inflates token counts |
| `long-line` | info | Very long unbroken lines that are hard to review |

## How it works

1. **Discovery** — expands the given paths. Files are linted directly;
   directories are walked recursively for known prompt filenames (vendor and
   VCS directories are skipped); globs are supported.
2. **Tokenization** — uses `tiktoken` when installed for exact counts, and
   otherwise a sub-word heuristic (`~4 chars/token`, punctuation counted
   separately) so budgeting works with no dependencies.
3. **Rules** — each rule is an independent function over a `LintContext`,
   yielding `Finding` objects with a rule name, severity, message, and line.
   Rules can be selected or ignored individually.
4. **Reporting** — human-readable colored text (auto-disabled off a TTY and via
   `NO_COLOR`) or structured JSON. The process exit code reflects the worst
   finding relative to `--max-severity`.

## Pre-commit hook

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: promptlint
      name: promptlint
      entry: promptlint
      language: system
      files: '(CLAUDE\.md|AGENTS\.md|.*\.prompt(\.md)?)$'
```

## Related work

Building an agent from scratch? My [claude-mcp-starter-kit](https://github.com/M-Ashrey/claude-mcp-starter-kit)
is a free, minimal starting point for Claude/MCP projects — promptlint pairs
well with it for keeping instruction files healthy.

## Contributing

Bug reports and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md)
for how to add a rule and the project's guidelines, or open an issue at
[github.com/M-Ashrey/promptlint/issues](https://github.com/M-Ashrey/promptlint/issues).
See [SECURITY.md](SECURITY.md) to report a vulnerability privately.

## License

MIT (c) Mohamed Ashrey. See [LICENSE](LICENSE).
