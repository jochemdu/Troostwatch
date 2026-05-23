"""Tests for the Lot domain model."""

from datetime import datetime, timezone

import pytest

from troostwatch.domain.models import Lot, LotState


class TestLotState:
    """Tests for LotState enum."""

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ("running", LotState.RUNNING),
            ("Running", LotState.RUNNING),
            ("open", LotState.RUNNING),
            ("bidding_open", LotState.RUNNING),
            ("scheduled", LotState.SCHEDULED),
            ("published", LotState.SCHEDULED),
            ("closed", LotState.CLOSED),
            ("ended", LotState.CLOSED),
            ("bidding_closed", LotState.CLOSED),
            ("unknown_state", LotState.UNKNOWN),
            ("", LotState.UNKNOWN),
            (None, LotState.UNKNOWN),
        ],
    )
    def test_from_string(self, input_value, expected):
        assert LotState.from_string(input_value) == expected


class TestLot:
    """Tests for Lot domain model."""

    def test_is_active_when_running(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            state=LotState.RUNNING,
        )
        assert lot.is_active is True
        assert lot.is_running is True
        assert lot.is_closed is False

    def test_is_active_when_scheduled(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            state=LotState.SCHEDULED,
        )
        assert lot.is_active is True
        assert lot.is_running is False
        assert lot.is_closed is False

    def test_is_not_active_when_closed(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            state=LotState.CLOSED,
        )
        assert lot.is_active is False
        assert lot.is_running is False
        assert lot.is_closed is True

    def test_effective_price_returns_current_bid(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            opening_bid_eur=50.0,
            current_bid_eur=100.0,
        )
        assert lot.effective_price == 100.0

    def test_effective_price_falls_back_to_opening_bid(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            opening_bid_eur=50.0,
            current_bid_eur=None,
        )
        assert lot.effective_price == 50.0

    def test_effective_price_is_none_without_prices(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
        )
        assert lot.effective_price is None

    def test_has_bids_with_bid_count(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            bid_count=5,
        )
        assert lot.has_bids is True

    def test_has_bids_with_current_bid(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            current_bid_eur=100.0,
        )
        assert lot.has_bids is True

    def test_no_bids_when_zero_count(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            bid_count=0,
        )
        assert lot.has_bids is False

    def test_time_extended(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            closing_time_original=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            closing_time_current=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
        )
        assert lot.time_extended is True

    def test_time_not_extended(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            closing_time_original=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            closing_time_current=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        assert lot.time_extended is False

    def test_location_combined(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            location_city="Amsterdam",
            location_country="Netherlands",
        )
        assert lot.location == "Amsterdam, Netherlands"

    def test_location_city_only(self):
        lot = Lot(
            lot_code="L1",
            auction_code="A1",
            title="Test Lot",
            location_city="Amsterdam",
        )
        assert lot.location == "Amsterdam"
