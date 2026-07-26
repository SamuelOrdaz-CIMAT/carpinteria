from datetime import datetime
from flask import Response, abort, flash, redirect, render_template, request, url_for
from carpinteria.database import db, get_settings
from carpinteria.services.budgets import create_budget_from_furniture, estimate_furniture, furniture_quote_data
from carpinteria.services.pdf import build_catalog_pdf, build_furniture_quote_pdf
from carpinteria.services.pricing import cheapest_supplier_labels


def catalog_entries(conn):
    entries = []
    furniture_rows = conn.execute(
        "SELECT * FROM furniture_types WHERE active = 1 ORDER BY name"
    ).fetchall()
    for furniture_row in furniture_rows:
        items = conn.execute(
            """
            SELECT fi.*, m.name AS material_name, m.unit
            FROM furniture_items fi
            JOIN materials m ON m.id = fi.material_id
            WHERE fi.furniture_type_id = ?
            ORDER BY fi.id
            """,
            (furniture_row["id"],),
        ).fetchall()
        lines = estimate_furniture(conn, items, 1)
        material_total = sum(line["total"] for line in lines)
        entries.append(
            {
                "id": furniture_row["id"],
                "name": furniture_row["name"],
                "description": furniture_row["description"],
                "material_count": len(lines),
                "material_total": material_total,
                "price": material_total * 2,
            }
        )
    return entries


def register(app):
    @app.route("/furniture", methods=["GET", "POST"])
    def furniture():
        with db() as conn:
            if request.method == "POST":
                conn.execute(
                    "INSERT OR IGNORE INTO furniture_types (name, description, labor_cost, margin_pct) VALUES (?, ?, ?, ?)",
                    (
                        request.form.get("name", "").strip(),
                        request.form.get("description", "").strip(),
                        0,
                        100,
                    ),
                )
                flash("Tipo de mueble guardado.")
                return redirect(url_for("furniture"))
            rows = conn.execute(
                """
                SELECT ft.*, COUNT(fi.id) AS item_count
                FROM furniture_types ft
                LEFT JOIN furniture_items fi ON fi.furniture_type_id = ft.id
                WHERE ft.active = 1
                GROUP BY ft.id
                ORDER BY ft.name
                """
            ).fetchall()
        return render_template("furniture.html", furniture=rows)


    @app.route("/catalog")
    def catalog():
        with db() as conn:
            entries = catalog_entries(conn)
        return render_template("catalog.html", entries=entries)


    @app.route("/catalog.pdf")
    def catalog_pdf():
        with db() as conn:
            entries = catalog_entries(conn)
            workshop = get_settings(conn)
        pdf_bytes = build_catalog_pdf(entries, workshop)
        filename = f"catalogo_muebles_{datetime.now().strftime('%Y%m%d')}.pdf"
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


    @app.route("/furniture/<int:furniture_id>", methods=["GET", "POST"])
    def furniture_detail(furniture_id: int):
        with db() as conn:
            furniture_row = conn.execute("SELECT * FROM furniture_types WHERE id = ?", (furniture_id,)).fetchone()
            if not furniture_row:
                abort(404)
            if request.method == "POST":
                inserted = 0
                material_ids = request.form.getlist("material_id")
                quantities = request.form.getlist("quantity")
                supplier_ids = request.form.getlist("preferred_supplier_id")
                notes_values = request.form.getlist("notes")

                for index, material_id in enumerate(material_ids):
                    if not material_id:
                        continue
                    quantity = quantities[index] if index < len(quantities) else ""
                    preferred_supplier_id = supplier_ids[index] if index < len(supplier_ids) else ""
                    notes = notes_values[index] if index < len(notes_values) else ""
                    conn.execute(
                        """
                        INSERT INTO furniture_items
                        (furniture_type_id, material_id, quantity, waste_pct, preferred_supplier_id, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            furniture_id,
                            int(material_id),
                            float(quantity or 1),
                            0,
                            int(preferred_supplier_id) if preferred_supplier_id else None,
                            notes.strip(),
                        ),
                    )
                    inserted += 1
                flash(f"{inserted} material(es) agregado(s) al mueble." if inserted else "No se agregaron materiales.")
                return redirect(url_for("furniture_detail", furniture_id=furniture_id))

            items = conn.execute(
                """
                SELECT fi.*, m.name AS material_name, m.unit, s.name AS supplier_name
                FROM furniture_items fi
                JOIN materials m ON m.id = fi.material_id
                LEFT JOIN suppliers s ON s.id = fi.preferred_supplier_id
                WHERE fi.furniture_type_id = ?
                ORDER BY fi.id
                """,
                (furniture_id,),
            ).fetchall()
            estimate_lines = estimate_furniture(conn, items, 1)
            material_rows = conn.execute("SELECT * FROM materials ORDER BY name").fetchall()
            supplier_rows = conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
            cheapest_labels = cheapest_supplier_labels(conn)
        material_total = sum(line["total"] for line in estimate_lines)
        subtotal = material_total + furniture_row["labor_cost"]
        margin_amount = material_total * (furniture_row["margin_pct"] / 100)
        grand_total = subtotal + margin_amount
        return render_template(
            "furniture_detail.html",
            furniture=furniture_row,
            items=items,
            estimate_lines=estimate_lines,
            material_total=material_total,
            subtotal=subtotal,
            margin_amount=margin_amount,
            grand_total=grand_total,
            materials=material_rows,
            suppliers=supplier_rows,
            cheapest_labels=cheapest_labels,
        )


    @app.route("/furniture/<int:furniture_id>/update", methods=["POST"])
    def update_furniture(furniture_id: int):
        with db() as conn:
            conn.execute(
                """
                UPDATE furniture_types
                SET name = ?, description = ?
                WHERE id = ?
                """,
                (
                    request.form.get("name", "").strip(),
                    request.form.get("description", "").strip(),
                    furniture_id,
                ),
            )
        flash("Tipo de mueble actualizado.")
        return redirect(url_for("furniture_detail", furniture_id=furniture_id))


    @app.route("/furniture-item/<int:item_id>/delete", methods=["POST"])
    def delete_furniture_item(item_id: int):
        with db() as conn:
            row = conn.execute("SELECT furniture_type_id FROM furniture_items WHERE id = ?", (item_id,)).fetchone()
            if not row:
                abort(404)
            conn.execute("DELETE FROM furniture_items WHERE id = ?", (item_id,))
        flash("Material retirado del mueble.")
        return redirect(url_for("furniture_detail", furniture_id=row["furniture_type_id"]))


    @app.route("/furniture-item/<int:item_id>/update", methods=["POST"])
    def update_furniture_item(item_id: int):
        with db() as conn:
            row = conn.execute("SELECT furniture_type_id FROM furniture_items WHERE id = ?", (item_id,)).fetchone()
            if not row:
                abort(404)
            conn.execute(
                """
                UPDATE furniture_items
                SET material_id = ?, quantity = ?, waste_pct = 0, preferred_supplier_id = ?, notes = ?
                WHERE id = ?
                """,
                (
                    int(request.form["material_id"]),
                    float(request.form.get("quantity") or 1),
                    int(request.form["preferred_supplier_id"]) if request.form.get("preferred_supplier_id") else None,
                    request.form.get("notes", "").strip(),
                    item_id,
                ),
            )
        flash("Material del mueble modificado.")
        return redirect(url_for("furniture_detail", furniture_id=row["furniture_type_id"]))


    @app.route("/furniture/<int:furniture_id>/quote.pdf")
    def furniture_quote_pdf(furniture_id: int):
        with db() as conn:
            quote = furniture_quote_data(conn, furniture_id)
            workshop = get_settings(conn)
        pdf_bytes = build_furniture_quote_pdf(*quote, workshop=workshop)
        filename = f"cotizacion_{quote[0]['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


    @app.route("/furniture/<int:furniture_id>/budget", methods=["POST"])
    def create_furniture_budget(furniture_id: int):
        with db() as conn:
            furniture_row = conn.execute("SELECT * FROM furniture_types WHERE id = ?", (furniture_id,)).fetchone()
            if not furniture_row:
                abort(404)
            qty = float(request.form.get("furniture_qty") or 1)
            budget_id = create_budget_from_furniture(
                conn,
                furniture_id,
                request.form.get("title", "").strip(),
                request.form.get("customer", "").strip(),
                qty,
                0,
                100,
                request.form.get("notes", "").strip(),
            )
        flash("Presupuesto creado desde el tipo de mueble.")
        return redirect(url_for("budget_detail", budget_id=budget_id))
