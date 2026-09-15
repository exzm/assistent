# Contributing

Thanks for contributing to Helper Bot.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quality bar

- Keep changes focused and typed
- Prefer dependency injection for external I/O (LLM, DB, filesystem)
- Extract pure helpers when logic is non-trivial
- Add/adjust tests for every behavior change
- Keep coverage at **100%**

```bash
ruff check bot tests
pytest --cov=app --cov-report=term-missing
```

## Pull requests

1. Describe the problem and the approach
2. Include test plan notes
3. Do not commit secrets (`.env`, tokens, API keys)

## Code style

- Python 3.12+
- `ruff` for linting
- Explicit names over clever abstractions
