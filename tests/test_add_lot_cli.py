import sqlite3
import sys
from pathlib import Path

from click.testing import CliRunner

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from troostwatch.interfaces.cli.add_lot import add_lot


def test_add_lot_command_inserts_record(tmp_path):
    db_path = tmp_path / "lots.db"
    runner = CliRunner()

    result = runner.invoke(
        add_lot,
        [
            "--db",
            str(db_path),
            "--auction-code",
            "A1-TEST",
            "--auction-title",
            "Test Auction",
            "--auction-url",
            "https://example.com/a/test",
            "--lot-code",
            "A1-TEST-1",
            "--title",
            "Manual lot",
            "--current-bid",
            "12.5",
            "--city",
            "Amsterdam",
            "--country",
            "NL",
        ],
    )

    assert result.exit_code == 0, result.output

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT a.auction_code, a.title, l.lot_code, l.title, l.current_bid_eur, l.location_city, l.location_country
            FROM lots l JOIN auctions a ON l.auction_id = a.id
            """
        ).fetchone()

    assert row == (
        "A1-TEST",
        "Test Auction",
        "A1-TEST-1",
        "Manual lot",
        12.5,
        "Amsterdam",
        "NL",
    )
