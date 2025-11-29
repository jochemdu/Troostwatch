# Contributing to Troostwatch

> **See also:** [docs/review_checklist.md](review_checklist.md) for the PR
> review checklist that reviewers use when evaluating pull requests.

## Code Review Checklist

### Architecture Compliance

Before approving any PR, verify:

- [ ] **CLI commands don't import infrastructure directly**
  - Use services from `troostwatch/services/`
  - Use context helpers from `troostwatch/interfaces/cli/context.py`
  - Exception: `context.py`, `auth.py`, `debug.py` are allowed adapters

- [ ] **API routes don't import infrastructure directly**
  - Use services from `troostwatch/services/`
  - Exception: `api.py`, `dependencies.py` for wiring

- [ ] **Domain models have no external dependencies**
  - `troostwatch/domain/` must not import from `infrastructure/`
  - Domain models should be pure Python

- [ ] **New business logic goes in services/domain**
  - Not in CLI commands
  - Not in API routes
  - Not in infrastructure

### Import Check

Run the import checker before merging:

```bash
python scripts/check_imports.py
```

This script will fail if architectural boundaries are violated.

### Testing Requirements

- [ ] All new services have unit tests
- [ ] Domain models have tests for business logic
- [ ] Existing tests still pass (`pytest tests/`)

### Code Style

- [ ] Type hints on public functions
- [ ] Docstrings on classes and public methods
- [ ] No presentation logic (print/click.echo) in services

## Where to Put New Code

| Type of Code | Location | Examples |
|-------------|----------|----------|
| Business rules | `domain/models/` | `Lot.can_bid()`, `Lot.is_active` |
| Use cases | `services/` | `SyncService.run_sync()` |
| CLI commands | `interfaces/cli/` | `sync.py`, `view.py` |
| API endpoints | `app/api.py` | GET /lots, POST /sync |
| Database access | `infrastructure/db/repositories/` | `LotRepository` |
| External APIs | `infrastructure/http/` | `TroostwatchHttpClient` |
| Parsing | `infrastructure/web/parsers/` | `parse_lot_detail()` |

## Common Patterns

### Adding a CLI Command

```python
# interfaces/cli/my_command.py
from troostwatch.interfaces.cli.context import build_cli_context
from troostwatch.services.my_service import MyService

@click.command()
def my_command(db_path: str):
    cli_context = build_cli_context(db_path)
    with cli_context.connect() as conn:
        service = MyService(...)
        result = service.do_something()
    
    # Presentation in CLI only
    console.print(f"Result: {result}")
```

### Adding Domain Logic

```python
# domain/models/lot.py
@dataclass
class Lot:
    @property
    def is_valid_for_bidding(self) -> bool:
        """Domain rule: lot must be running and have a price."""
        return self.is_running and self.effective_price is not None
```

### Adding a Service Method

```python
# services/lots.py
class LotViewService:
    def get_biddable_lots(self) -> List[Lot]:
        """Use case: get lots that can receive bids."""
        lots = self.list_domain_lots()
        return [lot for lot in lots if lot.is_valid_for_bidding]
```

## Running Tests

```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=troostwatch

# Single test file
pytest tests/domain/test_lot_model.py -v
```

## Pre-commit Checks

Before committing:

1. Run tests: `pytest tests/`
2. Check imports: `python scripts/check_imports.py`
3. Format code: `black troostwatch/ tests/`
4. Check types: `mypy troostwatch/` (optional)

