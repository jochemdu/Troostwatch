"""Tests for WebSocket message types."""

from troostwatch.app.ws_messages import (MESSAGE_FORMAT_VERSION,
                                         BidPlacedMessage, BuyerCreatedMessage,
                                         BuyerDeletedMessage,
                                         ConnectionReadyMessage,
                                         HeartbeatMessage, LotClosedMessage,
                                         LotUpdatedMessage,
                                         PositionsBatchUpdatedMessage,
                                         PositionUpdatedMessage,
                                         SyncCompletedMessage,
                                         SyncErrorMessage, SyncStartedMessage,
                                         WireMessage, create_message,
                                         parse_message)


class TestWireFormat:
    """Tests for the wire message format."""

    def test_wire_message_structure(self):
        """Wire messages have version, type, timestamp, and payload."""
        msg = WireMessage(
            version="1",
            type="test_event",
            timestamp="2025-11-28T12:00:00Z",
            payload={"key": "value"},
        )
        data = msg.model_dump()
        assert data["version"] == "1"
        assert data["type"] == "test_event"
        assert data["timestamp"] == "2025-11-28T12:00:00Z"
        assert data["payload"] == {"key": "value"}

    def test_message_format_version(self):
        """Current format version is 1."""
        assert MESSAGE_FORMAT_VERSION == "1"


class TestLotMessages:
    """Tests for lot-related messages."""

    def test_lot_updated_message(self):
        """LotUpdatedMessage includes lot details."""
        msg = LotUpdatedMessage(
            lot_code="LOT001",
            auction_code="ABC123",
            current_bid_eur=1500.0,
            bid_count=10,
            state="running",
        )
        wire = msg.to_wire()

        assert wire["version"] == "1"
        assert wire["type"] == "lot_updated"
        assert "timestamp" in wire
        assert wire["payload"]["lot_code"] == "LOT001"
        assert wire["payload"]["auction_code"] == "ABC123"
        assert wire["payload"]["current_bid_eur"] == 1500.0
        assert wire["payload"]["bid_count"] == 10
        assert wire["payload"]["state"] == "running"

    def test_lot_updated_excludes_none(self):
        """None values are excluded from payload."""
        msg = LotUpdatedMessage(
            lot_code="LOT001",
            auction_code="ABC123",
        )
        wire = msg.to_wire()

        assert "current_bid_eur" not in wire["payload"]
        assert "bid_count" not in wire["payload"]

    def test_lot_closed_message(self):
        """LotClosedMessage includes final state."""
        msg = LotClosedMessage(
            lot_code="LOT001",
            auction_code="ABC123",
            final_bid_eur=2000.0,
            winner_label="buyer-1",
        )
        wire = msg.to_wire()

        assert wire["type"] == "lot_closed"
        assert wire["payload"]["final_bid_eur"] == 2000.0
        assert wire["payload"]["winner_label"] == "buyer-1"


class TestSyncMessages:
    """Tests for sync-related messages."""

    def test_sync_started_message(self):
        """SyncStartedMessage includes sync parameters."""
        msg = SyncStartedMessage(
            auction_code="ABC123",
            max_pages=5,
            dry_run=True,
        )
        wire = msg.to_wire()

        assert wire["type"] == "sync_started"
        assert wire["payload"]["auction_code"] == "ABC123"
        assert wire["payload"]["max_pages"] == 5
        assert wire["payload"]["dry_run"] is True

    def test_sync_completed_message(self):
        """SyncCompletedMessage includes results."""
        msg = SyncCompletedMessage(
            auction_code="ABC123",
            status="success",
            pages_scanned=5,
            lots_scanned=150,
            lots_updated=12,
            duration_seconds=8.5,
        )
        wire = msg.to_wire()

        assert wire["type"] == "sync_completed"
        assert wire["payload"]["status"] == "success"
        assert wire["payload"]["lots_updated"] == 12

    def test_sync_error_message(self):
        """SyncErrorMessage includes error details."""
        msg = SyncErrorMessage(
            auction_code="ABC123",
            error="Connection timeout",
            error_count=3,
        )
        wire = msg.to_wire()

        assert wire["type"] == "sync_error"
        assert wire["payload"]["error"] == "Connection timeout"


class TestBuyerMessages:
    """Tests for buyer-related messages."""

    def test_buyer_created_message(self):
        """BuyerCreatedMessage includes buyer info."""
        msg = BuyerCreatedMessage(
            buyer_label="buyer-alpha",
            name="Alpha Industries",
        )
        wire = msg.to_wire()

        assert wire["type"] == "buyer_created"
        assert wire["payload"]["buyer_label"] == "buyer-alpha"
        assert wire["payload"]["name"] == "Alpha Industries"

    def test_buyer_deleted_message(self):
        """BuyerDeletedMessage includes label only."""
        msg = BuyerDeletedMessage(buyer_label="buyer-alpha")
        wire = msg.to_wire()

        assert wire["type"] == "buyer_deleted"
        assert wire["payload"]["buyer_label"] == "buyer-alpha"


class TestPositionMessages:
    """Tests for position-related messages."""

    def test_position_updated_message(self):
        """PositionUpdatedMessage includes position details."""
        msg = PositionUpdatedMessage(
            buyer_label="buyer-alpha",
            lot_code="LOT001",
            auction_code="ABC123",
            max_budget_total_eur=5000.0,
        )
        wire = msg.to_wire()

        assert wire["type"] == "position_updated"
        assert wire["payload"]["max_budget_total_eur"] == 5000.0

    def test_positions_batch_updated_message(self):
        """PositionsBatchUpdatedMessage includes counts."""
        msg = PositionsBatchUpdatedMessage(
            updated_count=5,
            created_count=2,
            positions=[{"buyer_label": "a", "lot_code": "L1"}],
        )
        wire = msg.to_wire()

        assert wire["type"] == "positions_updated"
        assert wire["payload"]["updated_count"] == 5
        assert wire["payload"]["created_count"] == 2


class TestBidMessages:
    """Tests for bid-related messages."""

    def test_bid_placed_message(self):
        """BidPlacedMessage includes bid details."""
        msg = BidPlacedMessage(
            lot_code="LOT001",
            auction_code="ABC123",
            buyer_label="buyer-alpha",
            amount_eur=1500.0,
            is_winning=True,
        )
        wire = msg.to_wire()

        assert wire["type"] == "bid_placed"
        assert wire["payload"]["amount_eur"] == 1500.0
        assert wire["payload"]["is_winning"] is True


class TestConnectionMessages:
    """Tests for connection-related messages."""

    def test_connection_ready_message(self):
        """ConnectionReadyMessage includes server info."""
        msg = ConnectionReadyMessage(
            server_version="0.7.1",
            message_format_version="1",
        )
        wire = msg.to_wire()

        assert wire["type"] == "connection_ready"
        assert wire["payload"]["server_version"] == "0.7.1"
        assert wire["payload"]["message_format_version"] == "1"

    def test_heartbeat_message(self):
        """HeartbeatMessage has empty payload."""
        msg = HeartbeatMessage()
        wire = msg.to_wire()

        assert wire["type"] == "heartbeat"
        assert wire["payload"] == {}


class TestCreateMessage:
    """Tests for the create_message factory function."""

    def test_create_message_from_type_and_payload(self):
        """create_message creates wire format from type and kwargs."""
        wire = create_message(
            "lot_updated",
            lot_code="LOT001",
            auction_code="ABC123",
            current_bid_eur=1500.0,
        )

        assert wire["version"] == "1"
        assert wire["type"] == "lot_updated"
        assert "timestamp" in wire
        assert wire["payload"]["lot_code"] == "LOT001"


class TestParseMessage:
    """Tests for parsing wire messages back to typed objects."""

    def test_parse_lot_updated(self):
        """parse_message converts wire format to typed message."""
        wire = {
            "version": "1",
            "type": "lot_updated",
            "timestamp": "2025-11-28T12:00:00Z",
            "payload": {
                "lot_code": "LOT001",
                "auction_code": "ABC123",
                "current_bid_eur": 1500.0,
            },
        }
        msg = parse_message(wire)

        assert isinstance(msg, LotUpdatedMessage)
        assert msg.lot_code == "LOT001"
        assert msg.current_bid_eur == 1500.0

    def test_parse_unknown_type_returns_none(self):
        """parse_message returns None for unknown types."""
        wire = {
            "version": "1",
            "type": "unknown_event",
            "timestamp": "2025-11-28T12:00:00Z",
            "payload": {},
        }
        msg = parse_message(wire)

        assert msg is None

    def test_parse_invalid_data_returns_none(self):
        """parse_message returns None for invalid data."""
        msg = parse_message({})
        assert msg is None

        msg = parse_message({"type": "lot_updated"})  # missing payload
        assert msg is None
