# Contributing

Thanks for your interest in improving promptlint.

## Development setup

```bash
git clone https://github.com/M-Ashrey/promptlint
cd promptlint
python -m pip install -e ".[dev]"
pytest
```

## Adding a rule

1. Write a `rule_*` function in `promptlint/rules.py` that takes a
   `LintContext` and yields `Finding` objects.
2. Register it in the `ALL_RULES` dict with a short, hyphenated name.
3. Add a test in `tests/` covering a positive and negative case.

Keep rules independent and opinionated but low-noise: a rule that fires on
well-written prompts is worse than no rule at all.

## Guidelines

- The core must stay dependency-free; `tiktoken` and `tomli` are optional.
- Run `pytest` before opening a PR.
- Keep findings actionable and concise.
