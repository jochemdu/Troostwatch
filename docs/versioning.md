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

- **MAJOR**: Breaking changes (API incompatibilities, database migrations requiring data transformation)
- **MINOR**: New features (backward-compatible additions)
- **PATCH**: Bug fixes (backward-compatible fixes)

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
