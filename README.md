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
configuration file used by the `sync-multi` command. These are listed in
`requirements.txt` for convenience.

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

### New commands in version 0.4.0

Starting with version 0.4.0, Troostwatch includes two new capabilities:

- **positions** – manage which lots a buyer is tracking and specify a maximum budget. Positions link a buyer to a lot and can be toggled between active and inactive.
- **report** – generate exposure summaries for a buyer, including counts of tracked lots and the minimum and maximum exposure based on current bids and budgets.

See the examples above for usage.