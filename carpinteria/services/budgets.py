from datetime import datetime
import sqlite3
from urllib.parse import quote_plus

from flask import abort

from carpinteria.services.pricing import best_price
from carpinteria.utils import money


def estimate_furniture(conn: sqlite3.Connection, items, furniture_qty: float) -> list[dict]:
    lines = []
    for item in items:
        unit_price, supplier_name = best_price(conn, item["material_id"], item["preferred_supplier_id"])
        line_qty = furniture_qty * item["quantity"] * (1 + (item["waste_pct"] / 100))
        lines.append(
            {
                "material_name": item["material_name"],
                "unit": item["unit"],
                "supplier_name": supplier_name,
                "quantity": line_qty,
                "unit_price": unit_price,
                "total": line_qty * unit_price,
                "notes": item["notes"],
            }
        )
    return lines


def furniture_quote_data(conn: sqlite3.Connection, furniture_id: int):
    furniture_row = conn.execute("SELECT * FROM furniture_types WHERE id = ?", (furniture_id,)).fetchone()
    if not furniture_row:
        abort(404)
    items = conn.execute(
        """
        SELECT fi.*, m.name AS material_name, m.unit
        FROM furniture_items fi
        JOIN materials m ON m.id = fi.material_id
        WHERE fi.furniture_type_id = ?
        ORDER BY fi.id
        """,
        (furniture_id,),
    ).fetchall()
    lines = estimate_furniture(conn, items, 1)
    material_total = sum(line["total"] for line in lines)
    subtotal = material_total
    margin_amount = material_total
    grand_total = subtotal + margin_amount
    return furniture_row, lines, material_total, subtotal, margin_amount, grand_total


def budget_quote_data(conn: sqlite3.Connection, budget_id: int):
    budget = conn.execute(
        """
        SELECT b.*, ft.name AS furniture_name, ft.description AS furniture_description
        FROM budgets b
        LEFT JOIN furniture_types ft ON ft.id = b.furniture_type_id
        WHERE b.id = ?
        """,
        (budget_id,),
    ).fetchone()
    if not budget:
        abort(404)
    lines = conn.execute("SELECT * FROM budget_lines WHERE budget_id = ? ORDER BY id", (budget_id,)).fetchall()
    material_total = sum(line["total"] for line in lines)
    subtotal = material_total
    margin_amount = material_total
    grand_total = subtotal + margin_amount
    pseudo_furniture = {
        "id": budget["id"],
        "name": budget["title"],
        "description": budget["notes"] or budget["furniture_description"] or "",
        "labor_cost": 0,
        "margin_pct": 100,
    }
    return budget, pseudo_furniture, lines, material_total, subtotal, margin_amount, grand_total


def replace_budget_lines(conn: sqlite3.Connection, budget_id: int, furniture_id: int, qty: float) -> None:
    conn.execute("DELETE FROM budget_lines WHERE budget_id = ?", (budget_id,))
    items = conn.execute(
        """
        SELECT fi.*, m.name AS material_name, m.unit
        FROM furniture_items fi
        JOIN materials m ON m.id = fi.material_id
        WHERE fi.furniture_type_id = ?
        ORDER BY fi.id
        """,
        (furniture_id,),
    ).fetchall()
    for line in estimate_furniture(conn, items, qty):
        conn.execute(
            """
            INSERT INTO budget_lines
            (budget_id, material_name, unit, supplier_name, quantity, unit_price, total, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                budget_id,
                line["material_name"],
                line["unit"],
                line["supplier_name"],
                line["quantity"],
                line["unit_price"],
                line["total"],
                line["notes"],
            ),
        )


def create_budget_from_furniture(
    conn: sqlite3.Connection,
    furniture_id: int,
    title: str,
    customer: str,
    qty: float,
    labor: float,
    margin: float,
    notes: str,
) -> int:
    furniture_row = conn.execute("SELECT * FROM furniture_types WHERE id = ?", (furniture_id,)).fetchone()
    if not furniture_row:
        abort(404)
    cur = conn.execute(
        """
        INSERT INTO budgets
        (title, customer, furniture_type_id, furniture_qty, labor_cost, margin_pct, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title or furniture_row["name"],
            customer,
            furniture_id,
            qty,
            labor,
            margin,
            notes,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ),
    )
    budget_id = cur.lastrowid
    replace_budget_lines(conn, budget_id, furniture_id, qty)
    return budget_id


def whatsapp_link(settings: dict, budget, grand_total: float) -> str:
    phone = "".join(ch for ch in settings.get("whatsapp", "") if ch.isdigit())
    message = (
        f"Hola, te comparto la cotizacion {budget['title']} "
        f"por {money(grand_total)}. Folio COT-{budget['id']:04d}."
    )
    base = f"https://wa.me/{phone}" if phone else "https://wa.me/"
    return f"{base}?text={quote_plus(message)}"
