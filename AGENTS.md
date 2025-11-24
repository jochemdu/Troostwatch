# Agent Guidelines for Troostwatch

These instructions apply to the entire repository.  Follow them when editing any
file in this project unless a more specific agent file applies.  Role‑specific
instructions live only under `.github/agents/`; duplicate copies in other
directories have been removed so each role has a single canonical file:

- `docs-agent.md` – writes and maintains project documentation.
- `test-agent.md` – writes and maintains unit and integration tests.
- `lint-agent.md` – enforces code style and static analysis rules.
- `api-agent.md` – creates and maintains FastAPI routes and related logic.

## Build & Test

Agents need precise commands to build, test and run the project.  Use the
commands below when performing general tasks:

- Install dependencies in editable mode: ``pixi run pip install -e .``
- Run static analysis and linting: ``pixi run ruff check .`` and
  ``pixi run mypy troostwatch``.
- Format code: ``pixi run black .`` and ``pixi run isort .``.
- Run the full test suite: ``pixi run pytest -q``.
- Run integration tests: ``pixi run pytest -m integration``.
- Start the development server: ``pixi run uvicorn troostwatch.api:app --reload``.

## Project Layout

- `troostwatch/api/` – Public API routes and service entry points.
- `troostwatch/core/` – Domain logic and reusable business models.
- `troostwatch/utils/` – Cross‑cutting helpers (logging, configuration, HTTP).
- `troostwatch/tests/` – Unit and integration tests mirroring the package structure.
- `troostwatch/alembic/` – Database migrations (modify only with approval).
- `deploy/` – Deployment manifests and CI/CD configuration (modify only with approval).
- `.github/agents/` – Specialized agent instruction files.

## Git Workflow & PR expectations

1. Create branches from `main` using descriptive names (`feature/<slug>`, `bugfix/<slug>`).
2. Run the full test and lint suite locally (`ruff`, `black`, `mypy`, `pytest`) before committing.
3. Keep commits atomic and descriptive.  Use prefixes like `feat:`, `fix:`, `docs:`.
4. Force pushing is allowed only on your feature branch; **never** force‑push `main`.
5. A pull request should summarise the change, include evidence (tests passing,
   type checks clean) and link relevant issues or tickets.  Avoid broad diffs
   across unrelated files.

## Code organization

- Prefer adding shared logic to centralised modules instead of duplicating code.
- Use `troostwatch/api/` for public‑facing API routes and service entry points.
- Use `troostwatch/core/` for domain logic that should be reused across APIs, CLIs,
  and background jobs.
- Place cross‑cutting utilities in `troostwatch/utils/` for helpers that are
  broadly applicable (logging, configuration, validation, formatting and
  HTTP helpers).
- Keep tests colocated with functionality under `tests/`, mirroring the package
  structure.

## Python best practices

- Target Python 3.11+; use type hints everywhere and prefer `dataclasses` or
  `pydantic` models for structured data.
- Avoid circular imports by isolating constants and interfaces in helper
  modules when necessary.
- Favour dependency injection for services and clients (e.g., database
  connections, HTTP clients).  Provide sensible defaults but allow overrides
  for tests.
- Keep functions small and focused; extract reusable helpers when a function
  exceeds ~40 lines or blends unrelated concerns.

## API guidelines

- Expose public operations through clearly named functions or classes in the
  central API layer.  Internal helpers should be private (`_` prefixed) or live
  in `core/` or `utils/`.
- Validate inputs at the boundary: ensure request payloads and CLI arguments
  are parsed and validated before business logic runs.
- Standardise responses: use consistent result objects or dataclasses for
  success and error cases.  Include error codes and user‑friendly messages
  where appropriate.

## Error handling & logging

- Raise specific exceptions; avoid bare `Exception`.  Translate internal
  errors into user‑facing messages at the boundary layer.
- Log actionable context (operation, identifiers, parameters) but avoid
  sensitive data.  Use structured logging where possible.

## Testing

- For new functionality, add unit tests covering happy paths and edge cases.
  Include integration tests when touching I/O boundaries (database,
  external APIs).
- Use factories or fixtures for common setup.  Prefer `pytest` style tests
  (simple functions) and parametrisation to reduce duplication.
- Ensure tests remain deterministic; mock time, randomness and external
  services as needed.  Do **not** create throwaway scripts; all tests
  belong under `tests/`.

## Documentation & style

- Update relevant READMEs or module docstrings when adding new features or
  behaviours.  For comprehensive documentation tasks, use the
  `docs-agent.md` under `.github/agents/`.
- Follow existing lint/format tooling (e.g., `ruff`, `black`, `mypy`) where
  configured.  Do not wrap imports in try/except.
- Keep commit messages descriptive and scoped to the change.

## Boundaries

- ✅ **Always:** Work within the designated directories (`api/`, `core/`, `tests/`)
  and run tests and linters before committing.
- ⚠️ **Ask first:** Before modifying database schemas (`alembic/`), changing
  deployment configs (`deploy/`) or introducing new dependencies.
- ⛔ **Never:** Commit secrets or API keys, edit `node_modules/` or vendor code,
  or modify files outside of the project scope without approval.