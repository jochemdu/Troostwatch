import click
from troostwatch.services.products_indexer import index_products_from_lots
from troostwatch.services.reference_price_fetcher import fetch_and_store_prices

@click.group()
def products():
    """Manage products and reference prices."""
    pass

@products.command()
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    show_default=True,
    help="Path to the SQLite database file.",
)
def index(db_path: str):
    """Index products from lot titles and associate them."""
    click.echo("Indexing products from lot titles...")
    inserted = index_products_from_lots(db_path)
    click.echo(f"Inserted {inserted} new products.")

@products.command()
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    show_default=True,
    help="Path to the SQLite database file.",
)
def fetch_prices(db_path: str):
    """Fetch reference prices (new and used) for indexed products."""
    click.echo("Fetching reference prices for indexed products...")
    fetch_and_store_prices(db_path)
    click.echo("Finished fetching reference prices.")
