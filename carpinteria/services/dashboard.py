import sqlite3

def fetch_dashboard(conn: sqlite3.Connection) -> dict:
    stats = {
        "materials": conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0],
        "suppliers": conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0],
        "furniture": conn.execute("SELECT COUNT(*) FROM furniture_types WHERE active = 1").fetchone()[0],
        "budgets": conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0],
    }
    cheapest = conn.execute(
        """
        SELECT
            m.name,
            m.unit,
            best.price AS min_price,
            s.name AS supplier_name
        FROM materials m
        LEFT JOIN material_prices best
          ON best.material_id = m.id
         AND best.supplier_id = (
            SELECT mp.supplier_id
            FROM material_prices mp
            JOIN suppliers ms ON ms.id = mp.supplier_id
            WHERE mp.material_id = m.id
              AND mp.price IS NOT NULL
            ORDER BY mp.price ASC, ms.name ASC
            LIMIT 1
         )
        LEFT JOIN suppliers s ON s.id = best.supplier_id
        ORDER BY m.name
        LIMIT 8
        """
    ).fetchall()
    recent = conn.execute(
        "SELECT id, title, customer, created_at FROM budgets ORDER BY id DESC LIMIT 5"
    ).fetchall()
    return {"stats": stats, "cheapest": cheapest, "recent": recent}
