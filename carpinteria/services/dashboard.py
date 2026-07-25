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
        SELECT m.name, m.unit, MIN(mp.price) AS min_price
        FROM materials m
        LEFT JOIN material_prices mp ON mp.material_id = m.id AND mp.price IS NOT NULL
        GROUP BY m.id
        ORDER BY m.name
        LIMIT 8
        """
    ).fetchall()
    recent = conn.execute(
        "SELECT id, title, customer, created_at FROM budgets ORDER BY id DESC LIMIT 5"
    ).fetchall()
    return {"stats": stats, "cheapest": cheapest, "recent": recent}
