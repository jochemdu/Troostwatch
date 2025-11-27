# Versioning Policy

This document describes how versions are managed in the Troostwatch project.

## Single Source of Truth

**The application version is defined in `pyproject.toml`.**

All other version references are derived from this single source at runtime
using `importlib.metadata`. This avoids duplication and ensures consistency.

```python
# How to access the version in Python code:
from troostwatch import __version__
print(__version__)  # e.g., "0.6.2"
```

## Version Types

Troostwatch uses several distinct version numbers, each with a specific purpose:

| Version | Location | Purpose |
|---------|----------|---------|
| **Application version** | `pyproject.toml` | SemVer version of the Troostwatch package. Used in releases, User-Agent strings, and API documentation. |
| **Schema version** | `infrastructure/db/schema/migrations.py` | Database schema version. Integer that increments when the database structure changes. See [Migration Policy](migration_policy.md). |
| **Config format version** | `config.json` | Version of the configuration file format. Allows future migrations if the config structure changes. |
| **UI package version** | `ui/package.json` | npm package version for the Next.js frontend. May differ from the backend version. |

## Semantic Versioning

The application version follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.y.z): Breaking changes (API incompatibilities, database migrations requiring data transformation)
- **MINOR** (x.Y.z): New features (backward-compatible additions)
- **PATCH** (x.y.Z): Bug fixes (backward-compatible fixes)

### When to Bump Each Level

| Change Type | Version Bump | Examples |
|-------------|--------------|----------|
| **Breaking API changes** | MAJOR | Removing endpoints, renaming fields, changing response structure |
| **New API endpoints** | MINOR | Adding `/lots/export`, new query parameters |
| **Schema migrations** (externally visible) | MINOR | Adding required columns, new tables |
| **Schema migrations** (internal only) | PATCH | Adding indexes, optional columns with defaults |
| **Bug fixes** | PATCH | Fixing parsing errors, correcting calculations |
| **Internal refactoring** | PATCH | Code restructuring, AGENTS.md updates, documentation |
| **Dependency updates** | PATCH (usually) | Updating library versions (MINOR if new features exposed) |

### Decision Guide

1. **Does this break existing API consumers?** → MAJOR
2. **Does this add new functionality or externally visible schema changes?** → MINOR
3. **Is this a fix or internal change only?** → PATCH

## Where Versions Are Used

### Application Version (`pyproject.toml`)

- **Python package metadata**: Displayed by `pip show troostwatch`
- **API documentation**: OpenAPI/Swagger UI shows the API version
- **User-Agent headers**: HTTP requests include `troostwatch-client/{version}` or `troostwatch-sync/{version}`
- **CLI**: Can be accessed via `python -c "from troostwatch import __version__; print(__version__)"`

### Schema Version (`CURRENT_SCHEMA_VERSION`)

- **Database migrations**: Tracked in `schema_version` table
- **Migration checks**: `SchemaMigrator` compares stored vs. current version
- **Independent of app version**: Schema version only increments when database structure changes

### Config Format Version (`config_format_version`)

- **Configuration files**: `config.json` and `examples/config.example.json`
- **Future compatibility**: Allows config format changes without breaking old configs
- **Currently at**: `1.0` (initial structured format)

## Version Compatibility Matrix

The application version and schema version are independent but related. This
matrix documents which app versions require which minimum schema versions:

| App Version | Min Schema Version | Notes |
|-------------|-------------------|-------|
| 0.6.x | 1 | Initial versioned schema |

### Compatibility Rules

1. **Upgrading the app**: Always run migrations after updating the package.
   The app will refuse to start if the schema is outdated.

2. **Downgrading the app**: Not officially supported. Schema migrations are
   forward-only. Restore from backup if rollback is needed.

3. **Schema changes require**:
   - Increment `CURRENT_SCHEMA_VERSION` in `migrations.py`
   - Update `schema/schema.sql` (canonical schema)
   - Add migration code or SQL file in `migrations/`
   - Update this compatibility matrix

### Checking Compatibility

```python
from troostwatch.infrastructure.db.schema.migrations import CURRENT_SCHEMA_VERSION

# At startup, SchemaMigrator checks:
# - If schema_version < CURRENT_SCHEMA_VERSION → run migrations
# - If schema_version > CURRENT_SCHEMA_VERSION → error (app too old)
```

## Release Workflow

When releasing a new version:

1. **Update `pyproject.toml`**: Change `version = "X.Y.Z"` to the new version
2. **Update `CHANGELOG.md`**: Document the changes
3. **Commit and tag**: `git commit -m "release: vX.Y.Z"` then `git tag vX.Y.Z`
4. **Push**: `git push && git push --tags`

The version in `__init__.py` is automatically read from `pyproject.toml` at
runtime via `importlib.metadata.version("troostwatch")`.

## Git Tags

Release tags should use the format `vX.Y.Z` (e.g., `v0.6.2`). Tags help:

- Identify exact commit for each release
- Enable GitHub releases
- Allow `pip install git+...@vX.Y.Z` installations

## Development Versions

When running from source without installing the package, `__version__` falls
back to `"0.0.0.dev"` to indicate an uninstalled development version.

For development installations, use:

```bash
pip install -e .
```

This registers the package with pip and enables proper version detection.
