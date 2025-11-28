# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- **Image Pipeline Iteration 2 complete**: Full image analysis pipeline with vendor support.
  - Vendor-specific code extraction profiles for 7 manufacturers:
    HP, Lenovo, Ubiquiti, Dell, Apple, Samsung, Cisco.
  - Confidence-based auto-approve for high-confidence extracted codes (threshold 0.85).
  - UI review queue for manual code approval with bulk actions.
  - Parallel image downloads with configurable concurrency (default 10).
  - Rich progress bars for CLI batch operations.
  - Prometheus-compatible metrics for image pipeline monitoring.

- **Review Queue API endpoints**:
  - `GET /review/codes/pending` – Paginated list of codes awaiting review.
  - `POST /review/codes/{id}/approve` – Approve a single code.
  - `POST /review/codes/{id}/reject` – Reject a single code.
  - `POST /review/codes/bulk` – Bulk approve/reject multiple codes.
  - `GET /review/stats` – Review queue statistics.

- **Image pipeline metrics**:
  - `image_downloads_total` – Downloads by status (success/failed).
  - `image_download_duration_seconds` – Download latency histogram.
  - `image_analysis_total` – Analyses by backend and status.
  - `image_analysis_duration_seconds` – Analysis latency by backend.
  - `extracted_codes_total` – Codes extracted by backend.
  - `code_approvals_total` – Approvals by type and code category.

- **CLI enhancements**:
  - `troostwatch images download --parallel --concurrency N` for faster downloads.
  - `troostwatch images promote-codes` to promote approved codes to lot records.
  - Progress bars with live updates for batch operations.

- **OpenTelemetry tracing support**: Optional distributed tracing via OpenTelemetry.
  Install with `pip install troostwatch[tracing]`. Configure with `configure_tracing()`.
  - `trace_span()` context manager for creating spans
  - `@traced` decorator for functions
  - Trace context available for log correlation via `get_trace_context()`
  - Exports to OTLP endpoints (Jaeger, Tempo, etc.)

- **WebSocket message format v1**: Standardized message envelope for all WebSocket events.
  - All messages now include `version`, `type`, `timestamp`, and `payload` fields
  - New `connection_ready` message sent on WebSocket connect
  - Typed Pydantic models for all message types in `troostwatch.app.ws_messages`
  - Backwards compatible: legacy payloads automatically wrapped in v1 format

### Changed

- WebSocket endpoint `WS /ws/lots` promoted from **Experimental** to **Stable**.
- Schema version bumped to 9 (adds approval columns to `extracted_codes` table).
- `ImageAnalysisService` now records metrics for all operations.

## [0.7.1] – 2025-11-28

### Changed

- **Documentation refresh**: Updated all docs to reflect current codebase state.
  - Fixed schema version references (now correctly shows version 7).
  - Updated architecture docs to reflect Level 3 enforcement (full compliance).
  - Fixed outdated file paths in feature_status.md.
  - Expanded docs/README.md with comprehensive documentation index.
  - Updated version compatibility matrix in versioning.md.

## [0.6.3]

### Changed

- **Python 3.11+ required**: Minimum Python version bumped from 3.10 to 3.11. Python 3.14 is supported.
- **Major dependency upgrades**:
  - FastAPI 0.122+ (was 0.110)
  - uvicorn 0.38+ (was 0.20)
  - pytest 9.0+ (was 7.0)
  - aiohttp 3.13+ (was 3.9)
  - beautifulsoup4 4.14+ (was 4.10)
  - rich 14.0+ (was 13.4)
  - websockets 15.0+ (was 10.0)
  - pydantic 2.12+
- **Frontend upgrades**:
  - Next.js 16.0+ (was 15.x)
  - React 19.1+ 
  - TypeScript 5.8+
  - ESLint 9.28+

## [0.7.0] – 2025-11-27

### Added

- **Brand field for lots**: The lot detail parser now extracts the brand/manufacturer
  from lot specifications (supports `Merk`, `Brand`, `Fabricaat` keys).
- **Bid history tracking**: New `bid_history` table stores historical bids scraped
  from lot detail pages, with bidder label, amount, and timestamp.
- **Brand filter in UI**: The lots page now includes a brand filter with autocomplete
  from available brands in the database.
- **Brand query parameter**: `GET /lots` endpoint accepts a `brand` filter parameter.

### Changed

- Bumped schema version to 2 (adds `brand` column to `lots`, creates `bid_history` table).
- `LotDetailData` parser dataclass now includes `brand` and `bid_history` fields.
- `LotView` API response model now includes `brand` field.
- `LotRepository.upsert_from_parsed()` now stores brand and bid history.

### Migration

Existing databases are automatically migrated:
- `brand` column added to `lots` table via programmatic migration.
- `bid_history` table created via `_ensure_bid_history_table()`.

## [0.6.2] – 2025-11-23

### Changed

- `troostwatch.interfaces.cli.*` is now the primaire importlocatie voor CLI
  commando's. Importeren via `troostwatch.cli.*` blijft tijdelijk beschikbaar
  maar geeft een `DeprecationWarning`.

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