from __future__ import annotations

from typing import Dict, List, Optional

from ..schema import ensure_schema
from troostwatch.infrastructure.web.parsers.lot_card import LotCardData
from troostwatch.infrastructure.web.parsers.lot_detail import LotDetailData


class LotRepository:
    def __init__(self, conn) -> None:
        self.conn = conn
        ensure_schema(self.conn)

    def get_id(self, lot_code: str, auction_code: Optional[str] = None) -> Optional[int]:
        query = "SELECT l.id FROM lots l JOIN auctions a ON l.auction_id = a.id WHERE l.lot_code = ?"

        def _lookup(code: str) -> Optional[int]:
            params: List = [code]
            local_query = query
            if auction_code is not None:
                local_query += " AND a.auction_code = ?"
                params.append(auction_code)
            cur = self.conn.execute(local_query, tuple(params))
            row = cur.fetchone()
            return row[0] if row else None

        lot_id = _lookup(lot_code)
        if lot_id is None and auction_code and not lot_code.startswith(f"{auction_code}-"):
            lot_id = _lookup(f"{auction_code}-{lot_code}")
        return lot_id

    def list_lot_codes_by_auction(self, auction_code: str) -> List[str]:
        rows = self.conn.execute(
            """
            SELECT l.lot_code
            FROM lots l
            JOIN auctions a ON l.auction_id = a.id
            WHERE a.auction_code = ?
            ORDER BY l.lot_code
            """,
            (auction_code,),
        ).fetchall()
        return [r[0] for r in rows]

    def list_lots(
        self,
        *,
        auction_code: Optional[str] = None,
        state: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Optional[str]]]:
        query = """
            SELECT a.auction_code AS auction_code,
                   l.lot_code AS lot_code,
                   l.title AS title,
                   l.state AS state,
                   l.current_bid_eur AS current_bid_eur,
                   l.bid_count AS bid_count,
                   l.current_bidder_label AS current_bidder_label,
                   l.closing_time_current AS closing_time_current,
                   l.closing_time_original AS closing_time_original
            FROM lots l
            JOIN auctions a ON l.auction_id = a.id
        """

        conditions: list[str] = []
        params: list = []
        if auction_code:
            conditions.append("a.auction_code = ?")
            params.append(auction_code)
        if state:
            conditions.append("l.state = ?")
            params.append(state)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY a.auction_code, l.lot_code"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cur = self.conn.execute(query, tuple(params))
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def upsert_from_parsed(
        self,
        auction_id: int,
        card: LotCardData,
        detail: LotDetailData,
        *,
        listing_hash: str,
        detail_hash: str,
        last_seen_at: str,
        detail_last_seen_at: str,
    ) -> None:
        lot_title = detail.title or card.title
        lot_url = detail.url or card.url
        lot_state = detail.state or card.state
        lot_opens_at = detail.opens_at or card.opens_at
        lot_closing_current = detail.closing_time_current or card.closing_time_current
        lot_closing_original = detail.closing_time_original
        lot_bid_count = detail.bid_count if detail.bid_count is not None else card.bid_count
        lot_opening_bid = _choose_value(detail.opening_bid_eur, card.price_eur if card.is_price_opening_bid else None)
        lot_current_bid = _choose_value(detail.current_bid_eur, card.price_eur)
        location_city = detail.location_city or card.location_city
        location_country = detail.location_country or card.location_country

        self.conn.execute(
            """
            INSERT INTO lots (
                auction_id, lot_code, title, url, state, status, opens_at,
                closing_time_current, closing_time_original, bid_count,
                opening_bid_eur, current_bid_eur, current_bidder_label,
                buyer_fee_percent, buyer_fee_vat_percent, vat_percent,
                awarding_state, total_example_price_eur, location_city,
                location_country, seller_allocation_note,
                listing_hash, detail_hash, last_seen_at, detail_last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(auction_id, lot_code) DO UPDATE SET
                title = excluded.title,
                url = excluded.url,
                state = excluded.state,
                status = excluded.status,
                opens_at = excluded.opens_at,
                closing_time_current = excluded.closing_time_current,
                closing_time_original = excluded.closing_time_original,
                bid_count = excluded.bid_count,
                opening_bid_eur = excluded.opening_bid_eur,
                current_bid_eur = excluded.current_bid_eur,
                current_bidder_label = excluded.current_bidder_label,
                buyer_fee_percent = excluded.buyer_fee_percent,
                buyer_fee_vat_percent = excluded.buyer_fee_vat_percent,
                vat_percent = excluded.vat_percent,
                awarding_state = excluded.awarding_state,
                total_example_price_eur = excluded.total_example_price_eur,
                location_city = excluded.location_city,
                location_country = excluded.location_country,
                seller_allocation_note = excluded.seller_allocation_note,
                listing_hash = excluded.listing_hash,
                detail_hash = excluded.detail_hash,
                last_seen_at = excluded.last_seen_at,
                detail_last_seen_at = excluded.detail_last_seen_at
            """,
            (
                auction_id,
                card.lot_code,
                lot_title,
                lot_url,
                lot_state,
                lot_state,
                lot_opens_at,
                lot_closing_current,
                lot_closing_original,
                lot_bid_count,
                lot_opening_bid,
                lot_current_bid,
                detail.current_bidder_label,
                detail.auction_fee_pct,
                detail.auction_fee_vat_pct,
                detail.vat_on_bid_pct,
                detail.state,
                detail.total_example_price_eur,
                location_city,
                location_country,
                detail.seller_allocation_note,
                listing_hash,
                detail_hash,
                last_seen_at,
                detail_last_seen_at,
            ),
        )


def _choose_value(*values: Optional[str | float | int | bool]):
    for value in values:
        if value is not None:
            return value
    return None
