"""Unit tests for Troostwatch parsers backed by snapshot HTML."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from troostwatch.parsers.lot_card import _parse_eur_to_float, _parse_nl_datetime, parse_lot_card
from troostwatch.parsers.lot_detail import parse_lot_detail


def test_parse_eur_to_float():
    """Ensure that European formatted currency strings are converted to floats."""
    assert _parse_eur_to_float("€ 1.234,56") == 1234.56
    assert _parse_eur_to_float("€0,99") == 0.99
    assert _parse_eur_to_float("1.000,00") == 1000.0
    assert _parse_eur_to_float("") is None
    assert _parse_eur_to_float("invalid") is None


def test_parse_nl_datetime():
    """Ensure Dutch date strings are parsed into ISO‑8601 strings."""
    assert _parse_nl_datetime("03 dec 2023 20:20") == "2023-12-03T20:20:00"
    assert _parse_nl_datetime("1 jan 2024 08:00") == "2024-01-01T08:00:00"
    # Invalid format returns None
    assert _parse_nl_datetime("03/12/2023") is None


FIXTURES = Path(__file__).parent / "snapshots"


def load_fixture(folder: str, name: str) -> str:
    return (FIXTURES / folder / f"{name}.html").read_text(encoding="utf-8")


def test_parse_lot_cards_from_snapshots():
    base_url = "https://www.troostwijkauctions.com"

    running = parse_lot_card(load_fixture("lot_cards", "running"), auction_code="A1-39478", base_url=base_url)
    assert running.auction_code == "A1-39478"
    assert running.lot_code == "03T-SMD-1"
    assert running.title.startswith("DAIMLER-BENZ")
    assert running.url == f"{base_url}/l/daimler-benz-mb-trac-1300-voorlader-03T-SMD-1"
    assert running.state == "running"
    assert running.opens_at == "2024-01-01T08:00:00"
    assert running.closing_time_current == "2024-01-05T18:00:00"
    assert running.location_city == "Berchtesgaden"
    assert running.location_country == "Germany"
    assert running.bid_count == 12
    assert running.price_eur == 12500.0
    assert running.is_price_opening_bid is False

    scheduled = parse_lot_card(load_fixture("lot_cards", "scheduled"), auction_code="A1-40000", base_url=base_url)
    assert scheduled.state == "scheduled"
    assert scheduled.opens_at == "2024-02-10T09:00:00"
    assert scheduled.closing_time_current == "2024-02-12T16:00:00"
    assert scheduled.is_price_opening_bid is True
    assert scheduled.bid_count == 0

    closed = parse_lot_card(load_fixture("lot_cards", "closed"), auction_code="A1-38000", base_url=base_url)
    assert closed.state == "closed"
    assert closed.closing_time_current == "2024-01-08T12:30:00"
    assert closed.price_eur == 8750.0
    assert closed.bid_count == 4


def test_parse_lot_details_from_snapshots():
    base_url = "https://www.troostwijkauctions.com"

    running = parse_lot_detail(load_fixture("lot_details", "running"), lot_code="ignored", base_url=base_url)
    assert running.lot_code == "03T-SMD-1"
    assert running.state == "running"
    assert running.opens_at == "2024-01-01T08:00:00"
    assert running.closing_time_current == "2024-01-05T16:00:00"
    assert running.closing_time_original == "2024-01-05T15:00:00"
    assert running.bid_count == 12
    assert running.current_bid_eur == 12500.0
    assert running.opening_bid_eur == 10000.0
    assert running.current_bidder_label == "Bidder 7"
    assert running.vat_on_bid_pct == 21.0
    assert running.auction_fee_pct == 18.0
    assert running.auction_fee_vat_pct == 21.0
    assert running.total_example_price_eur == 15000.0
    assert running.location_city == "Berchtesgaden"
    assert running.location_country == "Germany"
    assert running.seller_allocation_note == "Seller decides"
    assert running.url.endswith("/daimler-benz-mb-trac-1300-voorlader-03T-SMD-1")

    scheduled = parse_lot_detail(load_fixture("lot_details", "scheduled"), lot_code="ignored", base_url=base_url)
    assert scheduled.state == "scheduled"
    assert scheduled.opens_at == "2024-02-07T01:00:00"
    assert scheduled.closing_time_current == "2024-02-08T01:00:00"
    assert scheduled.bid_count == 0
    assert scheduled.opening_bid_eur == 5000.0
    assert scheduled.current_bid_eur is None
    assert scheduled.location_city == "Utrecht"
    assert scheduled.location_country == "Netherlands"

    closed = parse_lot_detail(load_fixture("lot_details", "closed"), lot_code="ignored", base_url=base_url)
    assert closed.state == "closed"
    assert closed.closing_time_current == "2023-12-31T18:00:00"
    assert closed.closing_time_original == "2023-12-31T17:00:00"
    assert closed.bid_count == 4
    assert closed.current_bid_eur == 8750.0
    assert closed.opening_bid_eur == 3000.0
    assert closed.current_bidder_label == "Winning bidder"
    assert closed.vat_on_bid_pct == 23.0
    assert closed.auction_fee_pct == 15.0
    assert closed.auction_fee_vat_pct == 23.0
    assert closed.total_example_price_eur == 10762.5
    assert closed.location_city == "Warsaw"
    assert closed.location_country == "Poland"