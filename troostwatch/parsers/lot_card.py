"""Parser for Troostwatch lot cards."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Iterable, Optional

from bs4 import BeautifulSoup

from troostwatch.logging_utils import get_logger
from . import utils

logger = get_logger(__name__)


@dataclass
class LotCardData:
    """Data extracted from a lot card on an auction page."""

    auction_code: str
    lot_code: str
    title: str
    url: str
    state: str | None = None
    opens_at: str | None = None
    closing_time_current: str | None = None
    location_city: str | None = None
    location_country: str | None = None
    bid_count: int | None = None
    price_eur: float | None = None
    is_price_opening_bid: bool | None = None


def parse_lot_card(html: str, auction_code: str, base_url: str | None = None) -> LotCardData:
    """Parse a lot card from HTML matching Troostwijk's card markup."""

    soup = BeautifulSoup(html, "html.parser")
    card = soup.find(attrs={"data-cy": "lot-card"}) or soup
    card_html = str(card)
    utils.log_structure_signature(logger, "lot_card.card", card_html)

    try:
        def _text(selector: str) -> str:
            return utils.extract_by_data_cy(card, selector)

        lot_code = _text("display-id-text")
        title_link = card.find(attrs={"data-cy": "title-link"})
        title = utils.extract_text(title_link)
        url = title_link.get("href", "") if title_link else ""
        if base_url and url.startswith("/"):
            url = base_url.rstrip("/") + url

        state_text = (_text("state-chip") or (card.get("data-state") or "")).strip().lower()
        state: Optional[str]
        if state_text.startswith("run"):
            state = "running"
        elif state_text.startswith("sched") or state_text.startswith("open"):
            state = "scheduled"
        elif state_text.startswith("closed"):
            state = "closed"
        else:
            state = None

        bid_count = None
        bid_count_text = _text("bid-count-text")
        match_bid = re.search(r"(\d+)", bid_count_text)
        if match_bid:
            bid_count = int(match_bid.group(1))

        price_eur = None
        is_price_opening_bid = None
        bid_text = card.find(attrs={"data-cy": "bid-text"})
        if bid_text:
            amount_text = bid_text.get_text(" ", strip=True)
            match_price = re.search(r"€[^0-9]*([\d\.,]+)", amount_text)
            if match_price:
                price_eur = utils.parse_eur_to_float(match_price.group(0))
            label = " ".join(part.lower() for part in bid_text.stripped_strings if "€" not in part)
            if label:
                is_price_opening_bid = "open" in label

        opens_at = utils.parse_datetime_from_text(_text("opening-date-text"))
        closing_time_current = utils.parse_datetime_from_text(_text("closing-date-text"))

        city, country = utils.split_location(_text("location-text"))

        return LotCardData(
            auction_code=auction_code,
            lot_code=lot_code,
            title=title,
            url=url,
            state=state,
            opens_at=opens_at,
            closing_time_current=closing_time_current,
            location_city=city,
            location_country=country,
            bid_count=bid_count,
            price_eur=price_eur,
            is_price_opening_bid=is_price_opening_bid,
        )
    except Exception as exc:
        utils.record_parsing_error(logger, "lot_card.card", card_html, exc)
        raise


def parse_auction_page(html: str, base_url: str | None = None) -> Iterable[LotCardData]:
    """Parse all lot cards from a full auction page via ``__NEXT_DATA__``."""

    data = utils.extract_next_data(html)
    utils.log_structure_signature(logger, "auction.next_data", json.dumps(data, sort_keys=True))
    page_props = data.get("props", {}).get("pageProps", {})
    auction = page_props.get("auction", {})
    auction_code = auction.get("displayId")

    results = page_props.get("lots", {}).get("results") or []
    for lot in results:
        display_id = lot.get("displayId") or ""
        lot_auction_code = auction_code or "-".join(display_id.split("-")[:2])
        url_slug = lot.get("urlSlug") or ""
        url = url_slug
        if base_url and url_slug:
            url = f"{base_url.rstrip('/')}/l/{url_slug}"

        bids = lot.get("bidsCount")
        current_bid_amount = utils.amount_from_cents_dict(lot.get("currentBidAmount"))
        is_price_opening_bid = None
        if bids is not None:
            is_price_opening_bid = bids == 0

        status = (lot.get("biddingStatus") or "").lower()
        if status.startswith("bidding_open"):
            state = "running"
        elif status.startswith("published"):
            state = "scheduled"
        elif status.startswith("bidding_closed"):
            state = "closed"
        else:
            state = None

        location = lot.get("location") or {}
        city, country = utils.split_location("{city}, {countryCode}".format(**{**{"city": "", "countryCode": ""}, **location}))
        country_code = (location.get("countryCode") or "").lower()
        country = utils.COUNTRY_CODES.get(country_code, country)

        yield LotCardData(
            auction_code=lot_auction_code,
            lot_code=display_id,
            title=lot.get("title", ""),
            url=url,
            state=state,
            opens_at=utils.epoch_to_iso(lot.get("startDate")),
            closing_time_current=utils.epoch_to_iso(lot.get("endDate")),
            location_city=city,
            location_country=country,
            bid_count=bids,
            price_eur=current_bid_amount,
            is_price_opening_bid=is_price_opening_bid,
        )
