import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import sqlite3
import re
import time

def make_request(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0)",
            "Accept": "text/html",
            "Accept-Language": "en-US,en;q=0.5",
        },
    )
    return urllib.request.urlopen(req, timeout=10).read().decode("utf-8")

def fetch_marktplaats_price(query):
    clean_query = re.sub(r"[^a-zA-Z0-9\s]", "", query).strip()
    clean_query = " ".join(clean_query.split()[:4])
    url = f"https://www.marktplaats.nl/q/{urllib.parse.quote(clean_query)}/"
    try:
        html = make_request(url)
        soup = BeautifulSoup(html, "html.parser")

        prices = []
        for price_el in soup.find_all(string=re.compile(r"€\s*\d+,\d{2}")):
            match = re.search(r"€\s*(\d+,\d{2})", price_el)
            if match:
                price_str = match.group(1).replace(",", ".")
                prices.append(float(price_str))

        if prices:
            prices.sort()
            return prices[len(prices) // 2]
    except Exception as e:
        print(f"Failed to fetch Marktplaats for {clean_query}: {e}")
    return None

def fetch_coolblue_price(query):
    clean_query = re.sub(r"[^a-zA-Z0-9\s]", "", query).strip()
    clean_query = " ".join(clean_query.split()[:4])
    url = f"https://www.coolblue.nl/zoeken?query={urllib.parse.quote(clean_query)}"
    try:
        html = make_request(url)
        soup = BeautifulSoup(html, "html.parser")

        for price_el in soup.find_all(class_=re.compile("sales-price__current")):
            price_text = price_el.get_text(strip=True)
            match = re.search(r"(\d+)(?:,\-)?", price_text)
            if match:
                return float(match.group(1))
    except Exception as e:
        print(f"Failed to fetch Coolblue for {clean_query}: {e}")
    return None

def fetch_and_store_prices(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT p.id, p.title, li.lot_id FROM products p "
        "JOIN lot_items li ON p.id = li.product_id"
    )
    items = cursor.fetchall()

    for item in items[:20]:
        title = item["title"]
        lot_id = item["lot_id"]

        print(f"Fetching prices for: {title}")

        new_price = fetch_coolblue_price(title)
        if new_price:
            cursor.execute(
                """
                INSERT INTO reference_prices (lot_id, condition, price_eur, source)
                VALUES (?, ?, ?, ?)
            """,
                (lot_id, "new", new_price, "Coolblue.nl"),
            )

        used_price = fetch_marktplaats_price(title)
        if used_price:
            cursor.execute(
                """
                INSERT INTO reference_prices (lot_id, condition, price_eur, source)
                VALUES (?, ?, ?, ?)
            """,
                (lot_id, "used", used_price, "Marktplaats"),
            )

        conn.commit()
        time.sleep(2)

    conn.close()
