## Summary

<!-- Brief description of what this PR does -->

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to change)
- [ ] 📝 Documentation update
- [ ] 🔧 Refactoring (no functional changes)
- [ ] 🧪 Test improvements

## Checklist

### General

- [ ] I have run `pytest -q` and all tests pass
- [ ] I have run `flake8 .` and `black .` (no lint errors)
- [ ] I have run `mypy troostwatch` (no type errors)
- [ ] I have run `lint-imports` (no architecture violations)

### API Changes (if applicable)

> Complete this section if you modified `troostwatch/app/api.py` or any Pydantic models

- [ ] I have regenerated TypeScript types: `cd ui && npm run generate:api-types`
- [ ] I have verified the UI still compiles: `cd ui && npx tsc --noEmit`
- [ ] I have committed `openapi.json` and `ui/lib/generated/api-types.ts`
- [ ] New endpoints have appropriate stability level documented in `docs/api.md`

### Breaking API Changes (if applicable)

> Complete this section if you're making backwards-incompatible changes

- [ ] I have documented the breaking change in the PR description
- [ ] I have coordinated with UI changes (merged together or migration plan)
- [ ] I have updated `docs/api.md` with migration notes
- [ ] I have considered a deprecation period before removal

### UI Changes (if applicable)

> Complete this section if you modified files in `ui/`

- [ ] I have verified TypeScript compiles: `cd ui && npx tsc --noEmit`
- [ ] I have tested the UI manually in the browser
- [ ] I am using generated types from `@/lib/generated` (not deprecated types)

### Database Changes (if applicable)

> Complete this section if you modified schema or migrations

- [ ] I have updated `schema/schema.sql`
- [ ] I have added migration code in `troostwatch/infrastructure/db/schema/`
- [ ] I have incremented `CURRENT_SCHEMA_VERSION`
- [ ] I have tested migration on existing databases

## Related Issues

<!-- Link any related issues: Fixes #123, Relates to #456 -->

## Screenshots (if applicable)

<!-- Add screenshots for UI changes -->

## Notes for Reviewers

<!-- Any additional context or areas to focus on during review -->
