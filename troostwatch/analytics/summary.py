"""Placeholder analytics module.

Defines the `get_buyer_summary` function as a stub.
"""

from __future__ import annotations


def get_buyer_summary(conn, buyer_label: str) -> dict:
    """Compute a summary of lots and exposure for a buyer.

    This stub returns an empty summary. The actual implementation should query
    the database and return a dictionary with keys such as:
        - open_tracked_lots
        - won_lots
        - open_exposure_min_eur
        - open_exposure_max_eur

    Args:
        conn: Database connection.
        buyer_label: The label of the buyer.

    Returns:
        A dictionary summarizing the buyer's position.
    """
    # TODO: implement real analytics
    return {}