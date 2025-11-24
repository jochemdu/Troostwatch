# Agent Guidelines for Troostwatch

These instructions apply to the entire repository. Follow them when editing any file in this project.

## Code organization
- Prefer adding shared logic to centralized modules instead of duplicating code.
  - Use `troostwatch/api/` for public-facing API routes and service entry points.
  - Use `troostwatch/core/` (or create it if absent) for domain logic that should be reused across APIs, CLIs, and background jobs.
  - Place cross-cutting utilities in `troostwatch/utils/` for helpers that are broadly applicable (logging, configuration, validation, formatting, and HTTP helpers).
- Keep tests colocated with functionality under `tests/`, mirroring the package structure.

## Python best practices
- Target Python 3.11+ syntax; use type hints everywhere and prefer `dataclasses` or `pydantic` models for structured data.
- Avoid circular imports by isolating constants and interfaces in helper modules when necessary.
- Favor dependency injection for services and clients (e.g., database connections, HTTP clients). Provide sensible defaults but allow overrides for tests.
- Keep functions small and focused; extract reusable helpers when a function exceeds ~40 lines or blends unrelated concerns.

## API guidelines
- Expose public operations through clearly named functions or classes in the central API layer. Internal helpers should be private (`_`-prefixed) or live in `core/` or `utils/`.
- Validate inputs at the boundary: ensure request payloads and CLI arguments are parsed and validated before business logic runs.
- Standardize responses: use consistent result objects or dataclasses for success and error cases. Include error codes and user-friendly messages where appropriate.

## Error handling & logging
- Raise specific exceptions; avoid bare `Exception`. Translate internal errors into user-facing messages at the boundary layer.
- Log actionable context (operation, identifiers, parameters) but avoid sensitive data. Use structured logging where possible.

## Testing
- For new functionality, add unit tests that cover happy paths and edge cases. Include integration tests when touching I/O boundaries (database, external APIs).
- Use factories or fixtures for common setup. Prefer `pytest` style tests and parametrization to reduce duplication.
- Ensure tests remain deterministic; mock time, randomness, and external services as needed.

## Documentation & style
- Update relevant README or module docstrings when adding new features or behaviors.
- Follow existing lint/format tooling (e.g., `ruff`, `black`, `mypy`) where configured. Do not wrap imports in try/except.
- Keep commit messages descriptive and scoped to the change.

## PR expectations
- Summarize the change, testing performed, and any notable design choices. Link issues or tickets when available.
