"""Placeholder analytics module.

Defines the `get_buyer_summary` function as a stub.
"""

from __future__ import annotations


def get_buyer_summary(conn, buyer_label: str) -> dict:
    """Compute a summary of lots and exposure for a buyer.

    This function queries the ``my_lot_positions`` and ``lots`` tables to
    compute how many lots a buyer is tracking, how many are still open, how
    many have closed and crude minimum and maximum exposure values.

    The minimum exposure is calculated as the sum of the current bid amounts
    for all tracked lots that are not closed. The maximum exposure is
    calculated as the sum of the configured maximum budgets; if a budget is
    not set for a lot, the current bid amount is used instead.

    Args:
        conn: Open SQLite connection.
        buyer_label: Label of the buyer whose summary should be computed.

    Returns:
        A dictionary with keys:
            - tracked_count: total number of positions for the buyer.
            - open_count: number of positions with lots not yet closed.
            - closed_count: number of positions with closed lots.
            - open_tracked_lots: list of dictionaries describing open lots.
            - won_lots: list of dictionaries describing closed lots.
            - open_exposure_min_eur: minimum exposure across open lots.
            - open_exposure_max_eur: maximum exposure across open lots.
    """
    summary = {
        "tracked_count": 0,
        "open_count": 0,
        "closed_count": 0,
        "open_tracked_lots": [],
        "won_lots": [],
        "open_exposure_min_eur": 0.0,
        "open_exposure_max_eur": 0.0,
    }
    # Look up the buyer ID
    cur = conn.execute("SELECT id FROM buyers WHERE label = ?", (buyer_label,))
    buyer_row = cur.fetchone()
    if not buyer_row:
        return summary
    buyer_id = buyer_row[0]
    # Select positions joined with lots to compute exposures
    query = """
        SELECT l.lot_code,
               l.title,
               l.state,
               l.current_bid_eur,
               p.max_budget_total_eur,
               p.track_active
        FROM my_lot_positions p
        JOIN lots l ON p.lot_id = l.id
        WHERE p.buyer_id = ?
    """
    rows = conn.execute(query, (buyer_id,)).fetchall()
    summary["tracked_count"] = len(rows)
    for lot_code, title, state, current_bid, max_budget, track_active in rows:
        item = {
            "lot_code": lot_code,
            "title": title,
            "state": state,
            "current_bid_eur": current_bid,
            "max_budget_total_eur": max_budget,
            "track_active": bool(track_active),
        }
        if state != "closed":
            summary["open_count"] += 1
            if track_active:
                summary["open_tracked_lots"].append(item)
                # Minimum exposure is current bid (or zero if None)
                if current_bid is not None:
                    summary["open_exposure_min_eur"] += float(current_bid)
                # Maximum exposure uses the configured budget if provided
                if max_budget is not None:
                    summary["open_exposure_max_eur"] += float(max_budget)
                else:
                    # Fall back to current bid
                    if current_bid is not None:
                        summary["open_exposure_max_eur"] += float(current_bid)
        else:
            summary["closed_count"] += 1
            summary["won_lots"].append(item)
    return summary