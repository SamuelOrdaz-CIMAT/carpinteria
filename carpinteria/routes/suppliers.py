from flask import abort, flash, redirect, render_template, request, url_for
from carpinteria.database import db


def register(app):
    @app.route("/suppliers", methods=["GET", "POST"])
    def suppliers():
        with db() as conn:
            if request.method == "POST":
                name = request.form.get("name", "").strip()
                if name:
                    conn.execute(
                        "INSERT OR IGNORE INTO suppliers (name, contact, address, notes) VALUES (?, ?, ?, ?)",
                        (
                            name,
                            request.form.get("contact", "").strip(),
                            request.form.get("address", "").strip(),
                            request.form.get("notes", "").strip(),
                        ),
                    )
                    flash("Proveedor guardado.")
                return redirect(url_for("suppliers"))
            rows = conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
        return render_template("suppliers.html", suppliers=rows)


    @app.route("/suppliers/<int:supplier_id>/update", methods=["POST"])
    def update_supplier(supplier_id: int):
        with db() as conn:
            conn.execute(
                "UPDATE suppliers SET name = ?, contact = ?, address = ?, notes = ? WHERE id = ?",
                (
                    request.form.get("name", "").strip(),
                    request.form.get("contact", "").strip(),
                    request.form.get("address", "").strip(),
                    request.form.get("notes", "").strip(),
                    supplier_id,
                ),
            )
        flash("Proveedor actualizado.")
        return redirect(url_for("suppliers"))


    @app.route("/suppliers/update-all", methods=["POST"])
    def update_all_suppliers():
        with db() as conn:
            supplier_ids = request.form.getlist("supplier_ids")
            for raw_id in supplier_ids:
                supplier_id = int(raw_id)
                name = request.form.get(f"name_{supplier_id}", "").strip()
                if not name:
                    continue
                conn.execute(
                    "UPDATE suppliers SET name = ?, contact = ?, address = ?, notes = ? WHERE id = ?",
                    (
                        name,
                        request.form.get(f"contact_{supplier_id}", "").strip(),
                        request.form.get(f"address_{supplier_id}", "").strip(),
                        request.form.get(f"notes_{supplier_id}", "").strip(),
                        supplier_id,
                    ),
                )
        flash("Proveedores actualizados.")
        return redirect(url_for("suppliers"))


    @app.route("/suppliers/<int:supplier_id>/delete", methods=["POST"])
    def delete_supplier(supplier_id: int):
        with db() as conn:
            existing = conn.execute("SELECT id FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
            if not existing:
                abort(404)
            conn.execute("UPDATE furniture_items SET preferred_supplier_id = NULL WHERE preferred_supplier_id = ?", (supplier_id,))
            conn.execute("DELETE FROM material_prices WHERE supplier_id = ?", (supplier_id,))
            conn.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
        flash("Proveedor eliminado.")
        return redirect(url_for("suppliers"))
