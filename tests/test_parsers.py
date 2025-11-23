"""Unit tests for Troostwatch parsers.

These tests exercise the helper functions and HTML parsers defined in the
``troostwatch.parsers`` package. They provide basic coverage to ensure
that date and currency parsing behave as expected and that the lot card
and lot detail parsers can extract key fields from simplified HTML
snippets. The tests use static HTML strings rather than relying on
network access so they run quickly and deterministically.
"""

from troostwatch.parsers.lot_card import (
    _parse_eur_to_float,
    _parse_nl_datetime,
    parse_lot_card,
)
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


def test_parse_lot_card_basic():
    """Parse a simplified lot card and verify key fields."""
    html = (
        '<li data-cy="lot-card">'
        '<a href="/lot/1234">Lot 1234</a>'
        '<h2>PowerEdge R740 Server</h2>'
        '<span class="price">€ 1.234,56</span>'
        '<span>5 bids</span>'
        '<span class="status">running</span>'
        '</li>'
    )
    card = parse_lot_card(html, auction_code="A1-39499", base_url="https://example.com")
    assert card.lot_code == "1234"
    assert card.title == "PowerEdge R740 Server"
    assert card.url == "https://example.com/lot/1234"
    assert card.bid_count == 5
    # Price should be converted to float
    assert card.price_eur == 1234.56
    # State should detect running keyword
    assert card.state == "running"


def test_parse_lot_detail_basic():
    """Parse a simplified lot detail page and verify extracted fields."""
    html = (
        '<html>'
        '<h1>Lot 1234 - PowerEdge R740 Server</h1>'
        '<p>Current bid € 2.000,00</p>'
        '<p>Opening bid € 1.000,00</p>'
        '<p>Highest bidder: John Doe</p>'
        '<p>VAT: 21%</p>'
        '<p>Auction fee: 5%</p>'
        '<p>Auction fee VAT: 21%</p>'
        '<p>Total example price € 2.500,00</p>'
        '<p>Closes: 03 dec 2023 20:20</p>'
        '<p>Original closing time: 02 dec 2023 20:00</p>'
        '<p>Opens: 01 dec 2023 10:00</p>'
        '<p>Location: Rotterdam, Netherlands</p>'
        '<p>Allocation: Seller decides</p>'
        '</html>'
    )
    detail = parse_lot_detail(html, lot_code="1234", base_url="https://example.com/auction")
    assert detail.title == "Lot 1234 - PowerEdge R740 Server"
    assert detail.current_bid_eur == 2000.0
    assert detail.opening_bid_eur == 1000.0
    assert detail.current_bidder_label == "John Doe"
    assert detail.vat_on_bid_pct == 21.0
    assert detail.auction_fee_pct == 5.0
    assert detail.auction_fee_vat_pct == 21.0
    assert detail.total_example_price_eur == 2500.0
    assert detail.closing_time_current == "2023-12-03T20:20:00"
    assert detail.closing_time_original == "2023-12-02T20:00:00"
    assert detail.opens_at == "2023-12-01T10:00:00"
    assert detail.location_city == "Rotterdam"
    assert detail.location_country == "Netherlands"
    assert detail.seller_allocation_note == "Seller decides"