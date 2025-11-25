# Agent Guidelines for Troostwatch

These instructions apply to the entire repository.  Follow them when editing any
file in this project unless a more specific agent file applies.  Role‑specific
instructions live only under `.github/agents/`; duplicate copies in other
directories have been removed so each role has a single canonical file:

- `docs-agent.md` – writes and maintains project documentation.
- `test-agent.md` – writes and maintains unit and integration tests.
- `lint-agent.md` – enforces code style and static analysis rules.
- `api-agent.md` – creates and maintains FastAPI routes and related logic.
- `analytics-agent.md` – collects, models and maintains analytics pipelines and metrics logic.
- `cli-agent.md` – builds and maintains CLI entry points and supporting utilities.
- `interfaces-agent.md` – defines and evolves shared interfaces or contracts used across services.
- `migration-agent.md` – manages database migrations and schema evolution tasks.
- `observability-agent.md` – configures logging and observability utilities and patterns.
- `parser-importer-agent.md` – maintains parsers and importers for ingesting external data sources.
- `script-agent.md` – authors utility scripts and one-off maintenance tooling.
- `services-agent.md` – implements and orchestrates application service workflows.
- `ui-agent.md` – implements and refines user interface components and front-end workflows.

## Build & Test

Agents need precise commands to build, test and run the project.  Use the
commands below when performing general tasks:

- Create a virtual environment and install runtime dependencies:
  ```bash
  python -m venv .venv
  source .venv/bin/activate  # on Windows use `.venv\\Scripts\\activate`
  pip install -r requirements.txt
  ```
- Install development tools (linting, type checking, tests): ``pip install -e .[dev]``.
- Run formatting: ``black .``.
- Run linting: ``flake8 .``.
- Run type checks: ``mypy troostwatch``.
- Run the full test suite: ``pytest -q``.
- Run integration tests: ``pytest -m integration``.

## Project Layout

- `troostwatch/domain/` – Domain models, rules and reusable business logic.
- `troostwatch/infrastructure/` – Adapters for external systems (databases, HTTP, file I/O).
- `troostwatch/services/` – Application services orchestrating domain workflows.
- `troostwatch/interfaces/` and `troostwatch/cli/` – Boundary contracts and CLI entry points.
- `troostwatch/app/` – Application composition, wiring and lifecycle helpers.
- `tests/` – Unit and integration tests mirroring the package structure.
- `migrations/` and `schema/` – Database migrations and schema definitions.
- `.github/agents/` – Specialized agent instruction files.

## Git Workflow & PR expectations

1. Create branches from `main` using descriptive names (`feature/<slug>`, `bugfix/<slug>`).
2. Run the full test and lint suite locally (`flake8`, `black`, `mypy`, `pytest`) before committing.
3. Keep commits atomic and descriptive.  Use prefixes like `feat:`, `fix:`, `docs:`.
4. Force pushing is allowed only on your feature branch; **never** force‑push `main`.
5. A pull request should summarise the change, include evidence (tests passing,
   type checks clean) and link relevant issues or tickets.  Avoid broad diffs
   across unrelated files.

## Code organization

- Prefer adding shared logic to centralised modules instead of duplicating code.
- Use `troostwatch/domain/` for reusable domain logic and business rules.
- Use `troostwatch/services/` to coordinate domain operations and application workflows.
- Use `troostwatch/infrastructure/` for integrations and adapters to external systems.
- Keep boundary code and entry points in `troostwatch/interfaces/` and `troostwatch/cli/`.
- Compose application wiring and bootstrap logic in `troostwatch/app/`.
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
- Follow existing lint/format tooling (e.g., `flake8`, `black`, `mypy`) where
  configured.  Do not wrap imports in try/except.
- Keep commit messages descriptive and scoped to the change.

## Boundaries

- ✅ **Always:** Work within the designated directories (`troostwatch/domain/`,
  `troostwatch/services/`, `troostwatch/infrastructure/`, `troostwatch/interfaces/`,
  `troostwatch/cli/`, `troostwatch/app/`, `tests/`) and run tests and linters
  before committing.
- ⚠️ **Ask first:** Before modifying database migrations or schemas
  (`migrations/`, `schema/`) or introducing new dependencies.
- ⛔ **Never:** Commit secrets or API keys, edit `node_modules/` or vendor code,
  or modify files outside of the project scope without approval.
