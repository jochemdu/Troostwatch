from troostwatch.services.lots import LotView, LotViewService


class _StubLotRepository:
    def __init__(self, rows):
        self._rows = rows
        self.list_calls = []

    def list_lots(self, *, auction_code=None, state=None, brand=None, limit=None):
        self.list_calls.append(
            {
                "auction_code": auction_code,
                "state": state,
                "brand": brand,
                "limit": limit,
            }
        )
        return self._rows


def test_list_lots_returns_dtos_and_forwards_filters():
    rows = [
        {
            "auction_code": "A1",
            "lot_code": "L1",
            "title": "Lot 1",
            "state": "running",  # Use "running" which maps to LotState.RUNNING
            "current_bid_eur": 100.0,
            "bid_count": 2,
            "current_bidder_label": "BID123",
            "closing_time_current": "2024-01-01T00:00:00Z",
            "closing_time_original": "2023-12-31T23:00:00Z",
            "brand": None,
        }
    ]
    repository = _StubLotRepository(rows)
    service = LotViewService(repository)

    result = service.list_lots(auction_code="A1", state="running", limit=5)

    assert repository.list_calls == [
        {"auction_code": "A1", "state": "running", "brand": None, "limit": 5}
    ]
    assert result == [
        LotView(
            auction_code="A1",
            lot_code="L1",
            title="Lot 1",
            state="running",
            current_bid_eur=100.0,
            bid_count=2,
            current_bidder_label="BID123",
            closing_time_current="2024-01-01T00:00:00Z",
            closing_time_original="2023-12-31T23:00:00Z",
            brand=None,
            is_active=True,  # Domain logic: running lots are active
            effective_price=100.0,  # Domain logic: current_bid is effective price
        )
    ]


def test_list_lots_converts_non_positive_limit_to_none():
    repository = _StubLotRepository([])
    service = LotViewService(repository)

    service.list_lots(limit=0)
    service.list_lots(limit=-3)

    assert repository.list_calls == [
        {"auction_code": None, "state": None, "brand": None, "limit": None},
        {"auction_code": None, "state": None, "brand": None, "limit": None},
    ]


def test_from_record_handles_missing_optional_fields():
    minimal = {"auction_code": "A1", "lot_code": "L2"}

    view = LotView.from_record(minimal)

    assert view.auction_code == "A1"
    assert view.lot_code == "L2"
    assert view.title is None
    assert view.closing_time_current is None
    assert view.closing_time_original is None
    assert view.is_active is False  # Unknown state is not active
    assert view.effective_price is None  # No price data
