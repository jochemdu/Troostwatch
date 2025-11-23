# Troostwatch

This repository hosts the code for the Troostwatch project.

It provides a set of tools to scrape Troostwijk auctions, store the data in a SQLite database, analyse your bidding exposure and display a live overview via a command‑line interface.

## Project structure

The code is organised into a Python package `troostwatch` with several sub‑packages:

- `troostwatch/cli/` – entry points for the `sync`, `view` and `debug` commands.
- `troostwatch/parsers/` – HTML parsers for auction listing pages and lot detail pages.
- `troostwatch/sync/` – functions to fetch pages from the Troostwijk website and upsert data into the database.
- `troostwatch/analytics/` – helper functions to summarise your bidding exposure.
- `troostwatch/models/` – dataclasses and helpers for working with internal models.
- `troostwatch/db.py` – helper for connecting to the SQLite database.
- `troostwatch/config.py` and `troostwatch/logging_utils.py` – configuration and logging helpers.

There is also a `schema` directory containing the database schema and any migrations, a `scripts` directory for one‑off scripts such as `firstrun.py`, and a `tests` directory containing unit tests. The `examples` directory holds example configuration and data files to help new users get started.