# Troostwatch

This repository hosts the code for the Troostwatch project.

It provides a set of tools to scrape Troostwijk auctions, store the data in a SQLite database, analyse your bidding exposure and display a live overview via a command‑line interface.

## Project structure

Troostwatch volgt een gelaagde indeling zodat domeinlogica, infrastructuur en interfaces duidelijk gescheiden blijven:

- `troostwatch/domain/` – domeinmodellen en analytische hulpfuncties die geen directe afhankelijkheid op I/O hebben.
- `troostwatch/infrastructure/` – adapters voor opslag, HTTP en HTML-parsing (`web/parsers`), logging en diagnostics.
- `troostwatch/services/` – coördinerende services zoals sync-workflows en biedlogica.
- `troostwatch/interfaces/cli/` – CLI-entrypoints en facades die de Click-commando’s beschikbaar maken.
- `troostwatch/app/` – applicatie-coördinatie, inclusief configuratie-facades voor CLI en services.

Om bestaande imports te beschermen tijdens de migratie bevat iedere nieuwe laag een alias/facade die doorverwijst naar de legacy-modules. De console scripts in `pyproject.toml` gebruiken nu de nieuwe CLI-facades, terwijl de oorspronkelijke modules bruikbaar blijven. Geleidelijke migratie is zo mogelijk: bestaande code kan blijven verwijzen naar `troostwatch.cli.*` of `troostwatch.parsers.*`, terwijl nieuwe code de gelaagde namen gebruikt.

### Mapping van legacy-modules naar de gelaagde structuur

| Legacy-pad                          | Nieuw laag-pad                                            |
| ----------------------------------- | --------------------------------------------------------- |
| `troostwatch.cli.*`                 | `troostwatch.interfaces.cli.*`                            |
| `troostwatch.parsers.*`             | `troostwatch.infrastructure.web.parsers.*`                 |
| `troostwatch.sync.*`                | `troostwatch.services.sync.*`                             |
| `troostwatch.analytics`             | `troostwatch.domain.analytics`                            |
| `troostwatch.models`                | `troostwatch.domain.models`                               |
| `troostwatch.db`                    | `troostwatch.infrastructure.persistence.db`               |
| `troostwatch.http_client`           | `troostwatch.infrastructure.http`                         |
| `troostwatch.logging_utils`         | `troostwatch.infrastructure.observability.logging`        |
| `troostwatch.debug_tools`           | `troostwatch.infrastructure.diagnostics.debug_tools`      |
| `troostwatch.config`                | `troostwatch.app.config`                                  |

Plan voor gefaseerde import-updates:

1. Nieuwe code importeert primair via de gelaagde namen uit de tabel hierboven.
2. Legacy-imports blijven beschikbaar via de facades zodat bestaande scripts blijven draaien.
3. Tijdens toekomstige refactors kunnen modules per laag verplaatst worden zonder externe breuken; pas daarna worden de legacy-paden uitgefaseerd.

Examples voor de `view` command, die opgeslagen lots laat zien met optionele filters en een JSON‑outputmodus:

```bash
# Bekijk alle lots in een lokale SQLite database
python -m troostwatch.cli view --db troostwatch.db

# Filter op een specifieke veiling en toon maximaal 20 lots als JSON
python -m troostwatch.cli view --db troostwatch.db --auction-code A1-39499 --limit 20 --json-output

# Toon alleen open lots, bijvoorbeeld na een sync run
python -m troostwatch.cli view --db troostwatch.db --state open

# Toon alle lots zonder limiet en formatteer als tekst
python -m troostwatch.cli view --db troostwatch.db --limit 0
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

These commands can be invoked via `python -m troostwatch.cli <command>`. Gebruik `view` om opgeslagen lots te bekijken (met filters voor veilingcode, status en limiet, plus een JSON‑uitvoeroptie), `report buyer` voor een overzicht van je exposure en `debug view` om tabellen rechtstreeks te inspecteren. See the examples above and the documentation in `docs/` for more details.
