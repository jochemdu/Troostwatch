# PR Review Checklist

This checklist helps reviewers verify that pull requests follow Troostwatch's
architectural guidelines.  These are **soft guidelines**—PRs may be merged with
documented exceptions, but deviations should be explicitly noted in the PR
description or review comments.

---

## Quick Reference

| Layer | May Import | Must NOT Import |
|-------|------------|-----------------|
| `domain/` | standard library only | `services/`, `infrastructure/`, `app/`, external libs |
| `services/` | `domain/`, `infrastructure/` | `app/`, `interfaces/`, `cli/` |
| `app/` / `interfaces/` | `services/`, `domain/` | `infrastructure/` (except wiring files) |
| `infrastructure/` | `domain/` only | `services/`, `app/`, `interfaces/` |

---

## Architecture Questions

Ask these questions for every PR:

### 1. Does CLI/API code stay thin?

- [ ] **CLI commands** (`interfaces/cli/`) call services, not infrastructure directly
- [ ] **API routes** (`app/api.py`) call services, not infrastructure directly
- [ ] Presentation logic (printing, formatting) stays in CLI/API, not in services

**Allowed exceptions:**
- `app/dependencies.py` and `interfaces/cli/context.py` may wire infrastructure
- `interfaces/cli/debug.py` may access infrastructure for diagnostics

### 2. Does domain remain pure?

- [ ] `troostwatch/domain/` has no imports from `infrastructure/`
- [ ] Domain models use only standard library and typing
- [ ] Business rules live in domain models, not scattered across CLI/services

### 3. Do services coordinate correctly?

- [ ] Services import from `domain/` and `infrastructure/`
- [ ] Services do NOT import from `app/` or `interfaces/`
- [ ] New business logic is added to services or domain, not CLI/API

### 4. Does infrastructure stay isolated?

- [ ] `infrastructure/` modules import only from `domain/` (if needed)
- [ ] No circular dependencies with `services/`
- [ ] Adapters (repositories, HTTP clients) don't contain business logic

---

## Automated Check

Run the import checker before approving:

```bash
# Primary check (used by CI)
lint-imports

# Legacy check script
python scripts/check_imports.py
```

Both tools scan for architectural boundary violations. CI will **fail** if any
contract is broken.

---

## No New Violations Policy

The codebase currently has **zero architecture violations**. CI will **block**
PRs that introduce new violations.

### What this means for PRs:

1. **New code must follow layer rules** – No exceptions for new modules.
2. **Run `lint-imports` locally** before pushing.
3. **If CI fails on arch-check**, fix the violation before merging.

### If you believe a violation is justified:

1. Add an `ignore_imports` entry to `.importlinter` with a comment explaining why.
2. Document the exception in the PR description.
3. Get explicit approval from a maintainer.

---

## Testing Checklist

- [ ] New services have unit tests in `tests/services/`
- [ ] Domain model changes have tests in `tests/domain/`
- [ ] All existing tests pass: `pytest tests/`

---

## Full-Stack Changes Checklist

For PRs that touch both backend API and frontend UI:

### API Contract Sync

- [ ] TypeScript types regenerated: `cd ui && npm run generate:api-types`
- [ ] `openapi.json` committed with changes
- [ ] `ui/lib/generated/api-types.ts` committed with changes
- [ ] UI compiles without errors: `cd ui && npx tsc --noEmit`

### Breaking API Changes

- [ ] Change documented in PR description with migration notes
- [ ] Endpoint stability level reviewed (see [API stability policy](api.md#api-stability-policy))
- [ ] UI and API changes merged together (not separately)
- [ ] Deprecation period considered for stable endpoints

### New Endpoints

- [ ] Response model defined as Pydantic class in `app/api.py`
- [ ] Type re-exported in `ui/lib/generated/index.ts`
- [ ] Stability level documented in `docs/api.md`
- [ ] API client function added in `ui/lib/api.ts`

---

## Code Style Checklist

- [ ] Type hints on public functions and methods
- [ ] Docstrings on classes and public methods
- [ ] No `print()` or `click.echo()` in services or domain
- [ ] Formatting passes: `black --check .`

---

## Soft Guidelines Policy

These rules exist to keep the codebase maintainable, but pragmatism wins:

1. **Document exceptions** – If a PR violates a rule intentionally, note why in
   the PR description.
2. **Incremental improvement** – Legacy code may not follow all rules; new code
   should.
3. **No blocking on style alone** – Architectural violations are more important
   than formatting nits.
4. **Discuss before enforcing** – If a rule seems wrong, propose changing the
   rule rather than silently ignoring it.

---

## Related Documentation

- [Architecture](architecture.md) – full layer rules and import constraints
- [Contributing](contributing.md) – code patterns and where to put new code
- [AGENTS.md](../AGENTS.md) – project-wide guidelines and agent roles
- Agent-specific docs in `.github/agents/`:
  - `api-agent.md` – API route guidelines
  - `cli-agent.md` – CLI command guidelines
  - `services-agent.md` – service layer guidelines
  - `migration-agent.md` – database migration rules
