from datetime import datetime
from flask import flash, redirect, render_template, request, url_for
from carpinteria.database import db


def register(app):
    @app.route("/prices", methods=["GET", "POST"])
    def prices():
        with db() as conn:
            suppliers_rows = conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
            material_rows = conn.execute("SELECT * FROM materials ORDER BY name").fetchall()
            if request.method == "POST":
                today = datetime.now().strftime("%Y-%m-%d")
                for material in material_rows:
                    for supplier in suppliers_rows:
                        field = f"price_{material['id']}_{supplier['id']}"
                        raw = request.form.get(field, "").strip()
                        if raw == "":
                            conn.execute(
                                "DELETE FROM material_prices WHERE material_id = ? AND supplier_id = ?",
                                (material["id"], supplier["id"]),
                            )
                            continue
                        try:
                            value = float(raw)
                        except ValueError:
                            continue
                        conn.execute(
                            """
                            INSERT INTO material_prices (material_id, supplier_id, price, updated_at, source)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(material_id, supplier_id)
                            DO UPDATE SET price = excluded.price, updated_at = excluded.updated_at
                            """,
                            (material["id"], supplier["id"], value, today, "captura manual"),
                        )
                flash("Precios actualizados.")
                return redirect(url_for("prices"))

            price_rows = conn.execute("SELECT * FROM material_prices").fetchall()
            price_map = {(row["material_id"], row["supplier_id"]): row["price"] for row in price_rows}
        return render_template("prices.html", suppliers=suppliers_rows, materials=material_rows, price_map=price_map)
