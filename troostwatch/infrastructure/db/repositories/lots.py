from __future__ import annotations

import sqlite3
from typing import Any

from ..schema import ensure_schema
from .base import BaseRepository
from troostwatch.infrastructure.web.parsers.lot_card import LotCardData
from troostwatch.infrastructure.web.parsers.lot_detail import LotDetailData


class LotRepository(BaseRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__(conn)
        ensure_schema(self.conn)

    def get_id(self, lot_code: str, auction_code: str | None = None) -> int | None:
        query = "SELECT l.id FROM lots l JOIN auctions a ON l.auction_id = a.id WHERE l.lot_code = ?"

        def _lookup(code: str) -> int | None:
            params: List = [code]
            local_query = query
            if auction_code is not None:
                local_query += " AND a.auction_code = ?"
                params.append(auction_code)
            cur = self.conn.execute(local_query, tuple(params))
            row = cur.fetchone()
            return row[0] if row else None

        lot_id = _lookup(lot_code)
        if (
            lot_id is None
            and auction_code
            and not lot_code.startswith(f"{auction_code}-")
        ):
            lot_id = _lookup(f"{auction_code}-{lot_code}")
        return lot_id

    def list_lot_codes_by_auction(self, auction_code: str) -> list[str]:
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
        auction_code: str | None = None,
        state: str | None = None,
        brand: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, str | None]]:
        query = """
            SELECT a.auction_code AS auction_code,
                   l.lot_code AS lot_code,
                   l.title AS title,
                   l.state AS state,
                   l.current_bid_eur AS current_bid_eur,
                   l.bid_count AS bid_count,
                   l.current_bidder_label AS current_bidder_label,
                   l.closing_time_current AS closing_time_current,
                   l.closing_time_original AS closing_time_original,
                   l.brand AS brand
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
        if brand:
            conditions.append("l.brand = ?")
            params.append(brand)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY a.auction_code, l.lot_code"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        return self._fetch_all_as_dicts(query, tuple(params))

    def get_lot_detail(
        self, lot_code: str, auction_code: str | None = None
    ) -> dict[str, Any | None]:
        """Get detailed lot information."""
        query = """
            SELECT a.auction_code, l.lot_code, l.title, l.url, l.state,
                   l.current_bid_eur, l.bid_count, l.opening_bid_eur,
                   l.closing_time_current, l.closing_time_original, l.brand, l.ean,
                   l.location_city, l.location_country, l.notes
            FROM lots l
            JOIN auctions a ON l.auction_id = a.id
            WHERE l.lot_code = ?
        """
        params: list[object] = [lot_code]
        if auction_code:
            query += " AND a.auction_code = ?"
            params.append(auction_code)

        return self._fetch_one_as_dict(query, tuple(params))

    def get_lot_specs(
        self, lot_code: str, auction_code: str | None = None
    ) -> list[dict[str, Any]]:
        """Get specifications (product_layers) for a lot, including parent_id, ean, price for hierarchy."""
        lot_id = self.get_id(lot_code, auction_code)
        if not lot_id:
            return []
        return self._fetch_all_as_dicts(
            "SELECT id, parent_id, template_id, title AS key, value, ean, "
            "price_eur, release_date, category "
            "FROM product_layers WHERE lot_id = ? "
            "ORDER BY parent_id NULLS FIRST, layer",
            (lot_id,),
        )

    def get_reference_prices(
        self, lot_code: str, auction_code: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all reference prices for a lot."""
        lot_id = self.get_id(lot_code, auction_code)
        if not lot_id:
            return []

        return self._fetch_all_as_dicts(
            """SELECT id, condition, price_eur, source, url, notes, created_at
               FROM reference_prices WHERE lot_id = ? ORDER BY created_at DESC""",
            (lot_id,),
        )

    def get_bid_history(
        self, lot_code: str, auction_code: str | None = None
    ) -> list[dict[str, Any]]:
        """Get bid history for a lot, ordered by timestamp descending (most recent first)."""
        lot_id = self.get_id(lot_code, auction_code)
        if not lot_id:
            return []

        return self._fetch_all_as_dicts(
            """SELECT id, bidder_label, amount_eur, timestamp, created_at
               FROM bid_history WHERE lot_id = ? ORDER BY timestamp DESC, id DESC""",
            (lot_id,),
        )

    def add_reference_price(
        self,
        lot_code: str,
        price_eur: float,
        condition: str = "used",
        source: str | None = None,
        url: str | None = None,
        notes: str | None = None,
        auction_code: str | None = None,
    ) -> int:
        """Add a reference price for a lot. Returns the new id."""
        lot_id = self.get_id(lot_code, auction_code)
        if not lot_id:
            raise ValueError(f"Lot '{lot_code}' not found")

        ref_id = self._execute_insert(
            """INSERT INTO reference_prices (lot_id, condition, price_eur, source, url, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (lot_id, condition, price_eur, source, url, notes),
        )
        self.conn.commit()
        return ref_id

    def update_reference_price(
        self,
        ref_id: int,
        price_eur: float | None = None,
        condition: str | None = None,
        source: str | None = None,
        url: str | None = None,
        notes: str | None = None,
    ) -> bool:
        """Update a reference price. Returns True if updated."""
        updates = []
        params: list[object] = []

        if price_eur is not None:
            updates.append("price_eur = ?")
            params.append(price_eur)
        if condition is not None:
            updates.append("condition = ?")
            params.append(condition)
        if source is not None:
            updates.append("source = ?")
            params.append(source)
        if url is not None:
            updates.append("url = ?")
            params.append(url)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if not updates:
            return True

        updates.append("updated_at = datetime('now')")
        params.append(ref_id)

        cur = self.conn.execute(
            f"UPDATE reference_prices SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete_reference_price(self, ref_id: int) -> bool:
        """Delete a reference price. Returns True if deleted."""
        cur = self.conn.execute("DELETE FROM reference_prices WHERE id = ?", (ref_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def update_lot(
        self,
        lot_code: str,
        auction_code: str | None = None,
        *,
        notes: str | None = None,
        ean: str | None = None,
    ) -> bool:
        """Update user-editable lot fields (notes, ean). Returns True if a row was updated."""
        lot_id = self.get_id(lot_code, auction_code)
        if not lot_id:
            return False

        updates = []
        params: list[object] = []
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        if ean is not None:
            updates.append("ean = ?")
            params.append(ean)

        if updates:
            params.append(lot_id)
            self.conn.execute(
                f"UPDATE lots SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            self.conn.commit()
        return True

    def upsert_lot_spec(
        self,
        lot_code: str,
        key: str,
        value: str,
        auction_code: str | None = None,
        parent_id: int | None = None,
        ean: str | None = None,
        price_eur: float | None = None,
        template_id: int | None = None,
        release_date: str | None = None,
        category: str | None = None,
    ) -> int:
        """Add or update a specification for a lot. Returns the spec id."""
        lot_id = self.get_id(lot_code, auction_code)
        if not lot_id:
            raise ValueError(f"Lot '{lot_code}' not found")

        # Check if spec exists (matching parent_id)
        existing_id: int | None
        if parent_id is not None:
            existing_id = self._fetch_scalar(
                "SELECT id FROM product_layers WHERE lot_id = ? AND title = ? AND parent_id = ?",
                (lot_id, key, parent_id),
            )
        else:
            existing_id = self._fetch_scalar(
                "SELECT id FROM product_layers WHERE lot_id = ? AND title = ? AND parent_id IS NULL",
                (lot_id, key),
            )
        if existing_id:
            self._execute(
                "UPDATE product_layers SET value = ?, ean = ?, price_eur = ?, "
                "template_id = ?, release_date = ?, category = ? WHERE id = ?",
                (
                    value,
                    ean,
                    price_eur,
                    template_id,
                    release_date,
                    category,
                    existing_id,
                ),
            )
            self.conn.commit()
            return existing_id
        else:
            # Get max layer number for this parent
            next_layer: int
            if parent_id is not None:
                next_layer = self._fetch_scalar(
                    "SELECT COALESCE(MAX(layer), -1) + 1 FROM product_layers WHERE lot_id = ? AND parent_id = ?",
                    (lot_id, parent_id),
                )
            else:
                next_layer = self._fetch_scalar(
                    "SELECT COALESCE(MAX(layer), -1) + 1 FROM product_layers WHERE lot_id = ? AND parent_id IS NULL",
                    (lot_id,),
                )
            spec_id = self._execute_insert(
                "INSERT INTO product_layers "
                "(lot_id, parent_id, layer, title, value, ean, price_eur, "
                "template_id, release_date, category) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    lot_id,
                    parent_id,
                    next_layer,
                    key,
                    value,
                    ean,
                    price_eur,
                    template_id,
                    release_date,
                    category,
                ),
            )
            self.conn.commit()
            return spec_id

    def delete_lot_spec(self, spec_id: int) -> bool:
        """Delete a specification by id. Returns True if deleted."""
        cur = self._execute("DELETE FROM product_layers WHERE id = ?", (spec_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # -------------------------------------------------------------------------
    # Spec Templates - reusable specifications across lots
    # -------------------------------------------------------------------------

    def list_spec_templates(self, parent_id: int | None = None) -> list[dict[str, Any]]:
        """List all spec templates, optionally filtered by parent."""
        if parent_id is not None:
            return self._fetch_all_as_dicts(
                "SELECT id, parent_id, title, value, ean, price_eur, "
                "release_date, category, created_at "
                "FROM spec_templates WHERE parent_id = ? ORDER BY title",
                (parent_id,),
            )
        else:
            return self._fetch_all_as_dicts(
                "SELECT id, parent_id, title, value, ean, price_eur, "
                "release_date, category, created_at "
                "FROM spec_templates ORDER BY parent_id NULLS FIRST, title"
            )

    def get_spec_template(self, template_id: int) -> dict[str, Any | None]:
        """Get a single spec template by id."""
        return self._fetch_one_as_dict(
            "SELECT id, parent_id, title, value, ean, price_eur, "
            "release_date, category, created_at "
            "FROM spec_templates WHERE id = ?",
            (template_id,),
        )

    def create_spec_template(
        self,
        title: str,
        value: str | None = None,
        ean: str | None = None,
        price_eur: float | None = None,
        parent_id: int | None = None,
        release_date: str | None = None,
        category: str | None = None,
    ) -> int:
        """Create a new spec template. Returns the new id."""
        template_id = self._execute_insert(
            "INSERT INTO spec_templates "
            "(title, value, ean, price_eur, parent_id, release_date, category) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, value, ean, price_eur, parent_id, release_date, category),
        )
        self.conn.commit()
        return template_id

    def update_spec_template(
        self,
        template_id: int,
        title: str | None = None,
        value: str | None = None,
        ean: str | None = None,
        price_eur: float | None = None,
        release_date: str | None = None,
        category: str | None = None,
    ) -> bool:
        """Update a spec template. Returns True if updated."""
        updates = []
        params: list[object] = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if value is not None:
            updates.append("value = ?")
            params.append(value)
        if ean is not None:
            updates.append("ean = ?")
            params.append(ean)
        if price_eur is not None:
            updates.append("price_eur = ?")
            params.append(price_eur)
        if release_date is not None:
            updates.append("release_date = ?")
            params.append(release_date)
        if category is not None:
            updates.append("category = ?")
            params.append(category)

        if not updates:
            return True

        updates.append("updated_at = datetime('now')")
        params.append(template_id)

        cur = self._execute(
            f"UPDATE spec_templates SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete_spec_template(self, template_id: int) -> bool:
        """Delete a spec template. Returns True if deleted."""
        cur = self._execute("DELETE FROM spec_templates WHERE id = ?", (template_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def apply_template_to_lot(
        self,
        lot_code: str,
        template_id: int,
        auction_code: str | None = None,
        parent_id: int | None = None,
    ) -> int:
        """Apply a spec template to a lot. Creates a new product_layer linked to the template."""
        template = self.get_spec_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        return self.upsert_lot_spec(
            lot_code=lot_code,
            key=template["title"],
            value=template.get("value") or "",
            auction_code=auction_code,
            parent_id=parent_id,
            ean=template.get("ean"),
            price_eur=template.get("price_eur"),
            template_id=template_id,
            release_date=template.get("release_date"),
            category=template.get("category"),
        )

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
        lot_bid_count = (
            detail.bid_count if detail.bid_count is not None else card.bid_count
        )
        lot_opening_bid = _choose_value(
            detail.opening_bid_eur,
            card.price_eur if card.is_price_opening_bid else None,
        )
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
                location_country, seller_allocation_note, brand,
                listing_hash, detail_hash, last_seen_at, detail_last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                brand = excluded.brand,
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
                None,  # status - not currently parsed from detail page
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
                detail.brand,
                listing_hash,
                detail_hash,
                last_seen_at,
                detail_last_seen_at,
            ),
        )

        # Upsert bid history if available
        if detail.bid_history:
            self._upsert_bid_history(card.lot_code, auction_id, detail.bid_history)

    def _upsert_bid_history(
        self,
        lot_code: str,
        auction_id: int,
        bid_history: list,
    ) -> None:
        """Insert or update bid history entries for a lot."""
        from troostwatch.infrastructure.web.parsers.lot_detail import BidHistoryEntry

        # Get lot_id
        lot_id = self._fetch_scalar(
            "SELECT id FROM lots WHERE lot_code = ? AND auction_id = ?",
            (lot_code, auction_id),
        )
        if not lot_id:
            return

        # Clear existing bid history for this lot and insert fresh
        self._execute("DELETE FROM bid_history WHERE lot_id = ?", (lot_id,))

        for entry in bid_history:
            if isinstance(entry, BidHistoryEntry):
                self._execute_insert(
                    """
                    INSERT INTO bid_history (lot_id, bidder_label, amount_eur, bid_time)
                    VALUES (?, ?, ?, ?)
                    """,
                    (lot_id, entry.bidder_label, entry.amount_eur, entry.timestamp),
                )

    def delete_lot(self, lot_code: str, auction_code: str) -> bool:
        """Delete a lot and all related data (specs, bids, reference prices, positions).

        Returns True if the lot was deleted, False if not found.
        """
        # Get auction_id and lot_id
        auction_id = self._fetch_scalar(
            "SELECT id FROM auctions WHERE auction_code = ?", (auction_code,)
        )
        if not auction_id:
            return False

        lot_id = self._fetch_scalar(
            "SELECT id FROM lots WHERE lot_code = ? AND auction_id = ?",
            (lot_code, auction_id),
        )
        if not lot_id:
            return False

        # Delete related data in order (foreign key dependencies)
        self._execute("DELETE FROM bid_history WHERE lot_id = ?", (lot_id,))
        self._execute("DELETE FROM reference_prices WHERE lot_id = ?", (lot_id,))
        self._execute("DELETE FROM product_layers WHERE lot_id = ?", (lot_id,))
        self._execute("DELETE FROM my_lot_positions WHERE lot_id = ?", (lot_id,))

        # Delete the lot itself
        self._execute("DELETE FROM lots WHERE id = ?", (lot_id,))
        self.conn.commit()
        return True


def _choose_value(*values: str | float | int | bool | None):
    for value in values:
        if value is not None:
            return value
    return None
