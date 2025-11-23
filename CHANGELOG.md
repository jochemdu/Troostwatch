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