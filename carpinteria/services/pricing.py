import sqlite3

from carpinteria.utils import money

def cheapest_supplier_labels(conn: sqlite3.Connection) -> dict[int, str]:
    rows = conn.execute(
        """
        SELECT material_id, supplier_name, price
        FROM (
            SELECT
                mp.material_id,
                s.name AS supplier_name,
                mp.price,
                ROW_NUMBER() OVER (PARTITION BY mp.material_id ORDER BY mp.price ASC, s.name ASC) AS rn
            FROM material_prices mp
            JOIN suppliers s ON s.id = mp.supplier_id
            WHERE mp.price IS NOT NULL
        )
        WHERE rn = 1
        """
    ).fetchall()
    return {row["material_id"]: f"Mas barato: {row['supplier_name']} ({money(row['price'])})" for row in rows}


def best_price(conn: sqlite3.Connection, material_id: int, preferred_supplier_id: int | None):
    if preferred_supplier_id:
        row = conn.execute(
            """
            SELECT mp.price, s.name AS supplier_name
            FROM material_prices mp
            JOIN suppliers s ON s.id = mp.supplier_id
            WHERE mp.material_id = ? AND mp.supplier_id = ?
            """,
            (material_id, preferred_supplier_id),
        ).fetchone()
        if row and row["price"] is not None:
            return row["price"], row["supplier_name"]
    row = conn.execute(
        """
        SELECT mp.price, s.name AS supplier_name
        FROM material_prices mp
        JOIN suppliers s ON s.id = mp.supplier_id
        WHERE mp.material_id = ? AND mp.price IS NOT NULL
        ORDER BY mp.price ASC
        LIMIT 1
        """,
        (material_id,),
    ).fetchone()
    if row:
        return row["price"], row["supplier_name"]
    return 0, ""
