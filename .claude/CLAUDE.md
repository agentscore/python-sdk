# agentscore-py

Python client for the AgentScore trust and reputation API.

## Identity Model

## Methods (sync + async)

- `get_reputation` / `aget_reputation` — cached reputation lookup (free)
- `assess` / `aassess` — identity gate with policy (paid). Accepts `operator_token` for non-wallet agents.
- `create_session` / `acreate_session` — create verification session
- `poll_session` / `apoll_session` — poll session status, returns credential when verified
- `create_credential` / `acreate_credential` — create operator credential (24h TTL default)
- `list_credentials` / `alist_credentials` — list active credentials
- `revoke_credential` / `arevoke_credential` — revoke a credential

## Architecture

Single-package Python library published to PyPI.

| File | Purpose |
|------|---------|
| `agentscore/` | Source code |
| `tests/` | pytest tests |

## Tooling

- **uv** — package manager. Use `uv sync`, `uv run`.
- **ruff** — linting + formatting. `uv run ruff check .` and `uv run ruff format --check .`.
- **vulture** — dead code detection.
- **pytest** — tests. `uv run pytest tests/`.
- **Lefthook** — git hooks. Pre-commit: ruff. Pre-push: vulture.

## Key Commands

```bash
uv sync --all-extras
uv run ruff check .
uv run ruff format .
uv run pytest tests/
```

## Workflow

1. Create a branch
2. Make changes
3. Lefthook runs ruff on commit, vulture on push
4. Open a PR — CI runs automatically
5. Merge (squash)

## Rules

- **No silent refactors**
- **Never commit .env files or secrets**
- **Use PRs** — never push directly to main

## Releasing

1. Update `version` in `pyproject.toml`
2. Commit: `git commit -am "chore: bump to vX.Y.Z"`
3. Tag: `git tag vX.Y.Z`
4. Push: `git push && git push origin vX.Y.Z`

The publish workflow runs on `ubuntu-latest` (required for PyPI trusted publishing), builds, publishes to PyPI via OIDC, and creates a GitHub Release.
