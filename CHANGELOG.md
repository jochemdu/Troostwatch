# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.6.0] – 2025-11-23

### Added

- A new `debug` CLI group with subcommands:
  - `stats` – show row counts for each table in the database.
  - `integrity` – run the SQLite integrity check and report any issues.
  - `view` – print a limited number of rows from a specified table.
- Support for a `--verbose` flag on the `sync` command and corresponding
  support in `sync_auction_to_db`. When enabled, sync now prints the number
  of pages discovered, indicates which page is being processed and logs
  each lot upserted.
- The CLI aggregator now exposes `positions`, `report` and `debug` commands.
- Added `debug_tools.py` providing reusable functions to inspect the database.
- Added version attribute `__version__` in the package initializer and bumped
  the version to 0.6.0.
- Added a `CHANGELOG.md` describing recent changes.

### Changed

- Updated `README.md` to reflect the expanded set of CLI commands and
  document new features.
- Adjusted `sync_auction_to_db` signature to accept a `verbose` flag.

### Fixed

- None.

### Fixed

- Applied an idempotent database migration path to add missing `lots` columns
  referenced by newer sync code. Older databases that lacked these columns
  no longer raise `sqlite3.OperationalError` during sync.

### Changed

- `sync_auction_to_db` will read runtime defaults from `config.json` under
  the `sync` key when options like `delay_seconds`, `max_pages` or `dry_run`
  are not explicitly provided. This allows project-wide tuning without
  changing invocation code.

## [0.6.1] – 2025-11-23

### Added

- Registered the `view` subcommand with the CLI aggregator. Previously, running
  `python -m troostwatch.cli view` resulted in an error because the command
  was not exposed; it now prints a stub message to remind users that the live
  viewer is not yet implemented.
- Clarified the `README.md` to indicate that `view` is a placeholder and to
  direct users toward the `report` and `debug` commands for inspecting
  their data.

### Changed

- Bumped the package version to 0.6.1 to reflect these small fixes.

## [0.6.2] – 2025-11-23

### Added

- Idempotent database migration runner applying SQL files from `migrations/`.
- Initial migration `0001_add_lots_columns.sql` to add missing `lots` columns used by sync upserts.

### Changed

- `sync_auction_to_db` now reads runtime defaults from `config.json` under the `sync` key when options are omitted (`delay_seconds`, `max_pages`, `dry_run`).
- `get_connection` accepts `None` to let `config.json` control PRAGMA defaults (`enable_wal`, `foreign_keys`).

### Fixed

- Prevent crashes on older databases by ensuring missing `lots` columns are added before upserts.