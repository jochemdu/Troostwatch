# Troostwatch

This repository hosts the code for the Troostwatch project.

It provides a set of tools to scrape Troostwijk auctions, store the data in a SQLite database, analyse your bidding exposure and display a live overview via a command‑line interface.

## Project structure

- The code is organised into a Python package `troostwatch` with several sub‑packages:

    - `troostwatch/cli/` – entry points for all available commands including `buyer`, `sync`, `sync-multi`, `positions`, `report`, `debug` and `view`. The `view` command now displays lots stored in the SQLite database with optional filters for `--auction-code`, `--state` and `--limit`, and can emit structured data via `--json-output`. Under the hood it calls `list_lots` from `troostwatch.db`, so the output shows auction code, lot code, title, state, bid metrics (current bid, bid count, current bidder) and closing times.
- `troostwatch/parsers/` – HTML parsers for auction listing pages and lot detail pages.
- `troostwatch/sync/` – functions to fetch pages from the Troostwijk website and upsert data into the database.
- `troostwatch/analytics/` – helper functions to summarise your bidding exposure.
- `troostwatch/models/` – dataclasses and helpers for working with internal models.
- `troostwatch/db.py` – helper for connecting to the SQLite database.
- `troostwatch/config.py` and `troostwatch/logging_utils.py` – configuration and logging helpers.

Examples voor de vernieuwde `view` command:

```bash
# Bekijk alle lots in een lokale SQLite database
python -m troostwatch.cli view --db troostwatch.db

# Filter op een specifieke veiling en toon maximaal 20 lots als JSON
python -m troostwatch.cli view --db troostwatch.db --auction-code A1-39499 --limit 20 --json-output

# Toon alleen open lots, bijvoorbeeld na een sync run
python -m troostwatch.cli view --db troostwatch.db --state open
```

## Requirements and installation

This project depends on a small number of third‑party libraries. To use the
command‑line interface you must install these dependencies into your Python
environment. The recommended way is via `pip` and the supplied
`requirements.txt` file:

```bash
python -m venv .venv
source .venv/bin/activate  # on Windows use `.venv\Scripts\activate`
pip install -r requirements.txt
```

At minimum the CLI requires [Click](https://click.palletsprojects.com/) for
defining commands and [PyYAML](https://pyyaml.org/) for reading the YAML
configuration file used by the `sync-multi` command. Parsing HTML responses relies
on [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/), and the sync
pipeline depends on both [aiohttp](https://docs.aiohttp.org/) and
[requests](https://requests.readthedocs.io/) to support concurrent fetching with
retries and rate limiting. For richer terminal output you can also install
[Rich](https://rich.readthedocs.io/). All of these are listed in
configuration file used by the `sync-multi` command. The sync pipeline also
depends on [aiohttp](https://docs.aiohttp.org/) and [requests](https://requests.readthedocs.io/) to
support concurrent fetching with retries and rate limiting. These are listed in
`requirements.txt` for convenience.

Listing pages and lot details are hashed to detect changes between sync runs.
The `sync` and `sync-multi` CLI commands expose `--max-concurrent-requests`,
`--throttle-per-host`, retry/backoff toggles and `--skip-unchanged-details`
behaviour so you can tune performance while avoiding unnecessary requests.

With the virtual environment activated you can invoke the CLI entry points via
`python -m troostwatch.cli`. Below are some common commands:

```bash
# Add a buyer
python -m troostwatch.cli buyer add Jochem --name "Jochem" --notes "IS IT engineer"

# Track a specific lot with an optional budget
python -m troostwatch.cli positions add --db troostwatch.db Jochem A1-39499 1234 --budget 2500

# View a summary of your exposure for a buyer
python -m troostwatch.cli report buyer --db troostwatch.db Jochem
```

There is also a `schema` directory containing the database schema and any migrations, a `scripts` directory for one‑off scripts such as `firstrun.py`, and a `tests` directory containing unit tests. The `examples` directory holds example configuration and data files to help new users get started.

### New commands in version 0.6.0

Recent versions have greatly expanded the CLI. In addition to the core `sync` command, you can now:

- **buyer** – create, list and delete buyers. Each buyer represents one identity you use to bid.
- **positions** – track specific lots for a buyer, optionally with a maximum budget, and mark them active or inactive.
- **report** – generate exposure summaries for a buyer, including the number of tracked lots and your minimum/maximum exposure based on current bids and budgets.
- **sync-multi** – synchronise multiple auctions at once from a YAML file.
- **debug** – inspect your local database. Subcommands let you view row counts per table, run an integrity check, or show rows from a specific table.

These commands can be invoked via `python -m troostwatch.cli <command>`. Note that the `view` command is not yet implemented and will only print a placeholder message. For an overview of your tracked lots and exposure, use the `report buyer` command; for inspecting the underlying database tables, use the `debug view` subcommand. See the examples above and the documentation in `docs/` for more details.
