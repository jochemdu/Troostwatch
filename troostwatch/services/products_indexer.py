import sqlite3
import re

def index_products_from_lots(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, title FROM lots")
    lots = cursor.fetchall()

    inserted_products = 0
    for lot in lots:
        title = lot['title']
        lot_id = lot['id']

        # Simple extraction logic: check if there's an amount like "6 items" or "10x".
        # We can extract EANs or models from title, but no image parsing directly here
        # so we'll extract items based on title parsing.

        quantity = 1
        item_title = title

        match_x = re.search(r'\((\d+)x\)', title, re.IGNORECASE)
        match_items = re.search(r'-\s+(\d+)\s+items', title, re.IGNORECASE)

        if match_x:
            quantity = int(match_x.group(1))
            item_title = title.replace(match_x.group(0), '').strip()
        elif match_items:
            quantity = int(match_items.group(1))
            item_title = title.replace(match_items.group(0), '').strip()

        cursor.execute("SELECT id FROM products WHERE title = ?", (item_title,))
        product = cursor.fetchone()

        if product:
            product_id = product['id']
        else:
            cursor.execute("INSERT INTO products (title) VALUES (?)", (item_title,))
            product_id = cursor.lastrowid
            inserted_products += 1

        try:
            cursor.execute("""
                INSERT INTO lot_items (lot_id, product_id, quantity)
                VALUES (?, ?, ?)
            """, (lot_id, product_id, quantity))
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return inserted_products
