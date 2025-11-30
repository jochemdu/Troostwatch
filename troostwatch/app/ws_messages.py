"""WebSocket message types for Troostwatch.

This module defines the standardized message format for WebSocket communication.
All messages follow a consistent structure with a `type` field and typed payloads.

Message Format (v1):
    {
        "version": "1",
        "type": "<event_type>",
        "timestamp": "<ISO8601>",
        "payload": { ... }
    }

Event Types:
    - lot_updated: Lot data changed (bid, state, etc.)
    - sync_started: Sync run beginning
    - sync_completed: Sync run finished
    - sync_error: Sync run failed
    - buyer_created: New buyer registered
    - buyer_deleted: Buyer removed
    - positions_updated: Position batch update
    - bid_placed: Bid was placed
    - connection_ready: Initial connection established
    - heartbeat: Keep-alive message

Usage:
    from troostwatch.app.ws_messages import LotUpdatedMessage, create_message

    # Create a typed message
    msg = LotUpdatedMessage(
        lot_code="LOT001",
        auction_code="ABC123",
        current_bid_eur=1500.0,
        bid_count=10,
    )

    # Convert to wire format
    await websocket.send_json(msg.to_wire())
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Message version
# ---------------------------------------------------------------------------

MESSAGE_FORMAT_VERSION = "1"


# ---------------------------------------------------------------------------
# Base message structure
# ---------------------------------------------------------------------------


class WireMessage(BaseModel):
    """Wire format for all WebSocket messages."""

    version: str = MESSAGE_FORMAT_VERSION
    type: str
    timestamp: str
    payload: dict[str, Any]


class BaseMessage(BaseModel):
    """Base class for all WebSocket message payloads."""

    def to_wire(self) -> dict[str, Any]:
        """Convert to wire format dictionary."""
        return WireMessage(
            version=MESSAGE_FORMAT_VERSION,
            type=self._message_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=self.model_dump(exclude_none=True),
        ).model_dump()

    @property
    def _message_type(self) -> str:
        """Return the message type identifier."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Lot messages
# ---------------------------------------------------------------------------


class LotUpdatedMessage(BaseMessage):
    """Sent when lot data changes (new bid, state change, etc.)."""

    lot_code: str
    auction_code: str
    title: str | None = None
    state: str | None = None
    current_bid_eur: float | None = None
    bid_count: int | None = None
    closing_time_current: str | None = None
    current_bidder_label: str | None = None

    @property
    def _message_type(self) -> str:
        return "lot_updated"


class LotClosedMessage(BaseMessage):
    """Sent when a lot closes."""

    lot_code: str
    auction_code: str
    final_bid_eur: float | None = None
    winner_label: str | None = None

    @property
    def _message_type(self) -> str:
        return "lot_closed"


# ---------------------------------------------------------------------------
# Sync messages
# ---------------------------------------------------------------------------


class SyncStartedMessage(BaseMessage):
    """Sent when a sync run begins."""

    auction_code: str
    max_pages: int | None = None
    dry_run: bool = False

    @property
    def _message_type(self) -> str:
        return "sync_started"


class SyncCompletedMessage(BaseMessage):
    """Sent when a sync run completes successfully."""

    auction_code: str
    status: Literal["success", "partial"] = "success"
    pages_scanned: int = 0
    lots_scanned: int = 0
    lots_updated: int = 0
    duration_seconds: float | None = None

    @property
    def _message_type(self) -> str:
        return "sync_completed"


class SyncErrorMessage(BaseMessage):
    """Sent when a sync run fails."""

    auction_code: str
    error: str
    error_count: int = 1

    @property
    def _message_type(self) -> str:
        return "sync_error"


# ---------------------------------------------------------------------------
# Buyer messages
# ---------------------------------------------------------------------------


class BuyerCreatedMessage(BaseMessage):
    """Sent when a new buyer is registered."""

    buyer_label: str
    name: str | None = None

    @property
    def _message_type(self) -> str:
        return "buyer_created"


class BuyerDeletedMessage(BaseMessage):
    """Sent when a buyer is removed."""

    buyer_label: str

    @property
    def _message_type(self) -> str:
        return "buyer_deleted"


# ---------------------------------------------------------------------------
# Position messages
# ---------------------------------------------------------------------------


class PositionUpdatedMessage(BaseMessage):
    """Sent when positions are updated."""

    buyer_label: str
    lot_code: str
    auction_code: str | None = None
    max_budget_total_eur: float | None = None
    track_active: bool = True

    @property
    def _message_type(self) -> str:
        return "position_updated"


class PositionsBatchUpdatedMessage(BaseMessage):
    """Sent when a batch of positions is updated."""

    updated_count: int
    created_count: int = 0
    positions: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def _message_type(self) -> str:
        return "positions_updated"


# ---------------------------------------------------------------------------
# Bid messages
# ---------------------------------------------------------------------------


class BidPlacedMessage(BaseMessage):
    """Sent when a bid is placed."""

    lot_code: str
    auction_code: str
    buyer_label: str
    amount_eur: float
    is_winning: bool | None = None

    @property
    def _message_type(self) -> str:
        return "bid_placed"


# ---------------------------------------------------------------------------
# Connection messages
# ---------------------------------------------------------------------------


class ConnectionReadyMessage(BaseMessage):
    """Sent when connection is established."""

    server_version: str
    message_format_version: str = MESSAGE_FORMAT_VERSION

    @property
    def _message_type(self) -> str:
        return "connection_ready"


class HeartbeatMessage(BaseMessage):
    """Keep-alive message."""

    @property
    def _message_type(self) -> str:
        return "heartbeat"


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def create_message(
    message_type: str,
    **payload: Any,
) -> dict[str, Any]:
    """Create a wire-format message from type and payload.

    This is a convenience function for creating messages without
    instantiating the typed classes.

    Args:
        message_type: The event type (e.g., "lot_updated").
        **payload: Message payload fields.

    Returns:
        Wire-format dictionary ready to be sent via WebSocket.
    """
    return WireMessage(
        version=MESSAGE_FORMAT_VERSION,
        type=message_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        payload=payload,
    ).model_dump()


# ---------------------------------------------------------------------------
# Message parsing (for clients/tests)
# ---------------------------------------------------------------------------


MESSAGE_TYPE_MAP: dict[str, type[BaseMessage]] = {
    "lot_updated": LotUpdatedMessage,
    "lot_closed": LotClosedMessage,
    "sync_started": SyncStartedMessage,
    "sync_completed": SyncCompletedMessage,
    "sync_error": SyncErrorMessage,
    "buyer_created": BuyerCreatedMessage,
    "buyer_deleted": BuyerDeletedMessage,
    "position_updated": PositionUpdatedMessage,
    "positions_updated": PositionsBatchUpdatedMessage,
    "bid_placed": BidPlacedMessage,
    "connection_ready": ConnectionReadyMessage,
    "heartbeat": HeartbeatMessage,
}


def parse_message(data: dict[str, Any]) -> BaseMessage | None:
    """Parse a wire-format message into a typed message object.

    Args:
        data: Wire-format dictionary from WebSocket.

    Returns:
        Typed message object, or None if parsing fails.
    """
    try:
        msg_type = data.get("type")
        payload = data.get("payload", {})

        if msg_type in MESSAGE_TYPE_MAP:
            return MESSAGE_TYPE_MAP[msg_type].model_validate(payload)
        return None
    except Exception:
        return None
