"""Buyer analytics helpers built on repositories."""

from __future__ import annotations

from troostwatch.domain.analytics.summary import BuyerSummary
from troostwatch.infrastructure.db.repositories import BuyerRepository, PositionRepository


def get_buyer_summary(conn, buyer_label: str) -> dict:
    """Compute a summary of lots and exposure for a buyer."""

    buyer_repo = BuyerRepository(conn)
    buyer_id = buyer_repo.get_id(buyer_label)
    if buyer_id is None:
        return BuyerSummary().to_dict()

    position_repo = PositionRepository(conn, buyers=buyer_repo)
    positions = position_repo.list(buyer_label)
    return BuyerSummary.from_positions(positions).to_dict()