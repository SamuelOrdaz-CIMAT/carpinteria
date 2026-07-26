from datetime import datetime
from flask import Response, abort, flash, redirect, render_template, request, url_for
from carpinteria.database import db, get_settings
from carpinteria.services.budgets import budget_quote_data, create_budget_from_furniture, replace_budget_lines, whatsapp_link
from carpinteria.services.pdf import build_furniture_quote_pdf


def requested_measurements(form, furniture_row):
    return (
        float(form.get("width_m") or furniture_row["width_m"] or 0),
        float(form.get("height_m") or furniture_row["height_m"] or 0),
        float(form.get("depth_m") or furniture_row["depth_m"] or 0),
    )


def register(app):
    @app.route("/budgets", methods=["GET", "POST"])
    def budgets():
        with db() as conn:
            furniture_rows = conn.execute("SELECT * FROM furniture_types WHERE active = 1 ORDER BY name").fetchall()
            if request.method == "POST":
                furniture_id = int(request.form["furniture_type_id"])
                furniture_row = conn.execute("SELECT * FROM furniture_types WHERE id = ?", (furniture_id,)).fetchone()
                qty = float(request.form.get("furniture_qty") or 1)
                width_m, height_m, depth_m = requested_measurements(request.form, furniture_row)
                budget_id = create_budget_from_furniture(
                    conn,
                    furniture_id,
                    request.form.get("title", "").strip() or furniture_row["name"],
                    request.form.get("customer", "").strip(),
                    qty,
                    width_m,
                    height_m,
                    depth_m,
                    0,
                    100,
                    request.form.get("notes", "").strip(),
                )
                flash("Presupuesto creado.")
                return redirect(url_for("budget_detail", budget_id=budget_id))

            rows = conn.execute(
                """
                SELECT b.*, ft.name AS furniture_name
                FROM budgets b
                LEFT JOIN furniture_types ft ON ft.id = b.furniture_type_id
                ORDER BY b.id DESC
                """
            ).fetchall()
        return render_template("budgets.html", budgets=rows, furniture=furniture_rows)


    @app.route("/budgets/<int:budget_id>")
    def budget_detail(budget_id: int):
        with db() as conn:
            budget = conn.execute(
                """
                SELECT b.*, ft.name AS furniture_name
                FROM budgets b
                LEFT JOIN furniture_types ft ON ft.id = b.furniture_type_id
                WHERE b.id = ?
                """,
                (budget_id,),
            ).fetchone()
            if not budget:
                abort(404)
            lines = conn.execute("SELECT * FROM budget_lines WHERE budget_id = ? ORDER BY id", (budget_id,)).fetchall()
            settings_values = get_settings(conn)
            furniture_rows = conn.execute("SELECT * FROM furniture_types WHERE active = 1 ORDER BY name").fetchall()
        material_total = sum(line["total"] for line in lines)
        subtotal = material_total
        margin_amount = material_total
        grand_total = subtotal + margin_amount
        return render_template(
            "budget_detail.html",
            budget=budget,
            lines=lines,
            material_total=material_total,
            subtotal=subtotal,
            margin_amount=margin_amount,
            grand_total=grand_total,
            whatsapp_url=whatsapp_link(settings_values, budget, grand_total),
            furniture=furniture_rows,
        )


    @app.route("/budgets/<int:budget_id>/update", methods=["POST"])
    def update_budget(budget_id: int):
        with db() as conn:
            existing = conn.execute("SELECT * FROM budgets WHERE id = ?", (budget_id,)).fetchone()
            if not existing:
                abort(404)
            furniture_id = int(request.form["furniture_type_id"])
            furniture_row = conn.execute("SELECT * FROM furniture_types WHERE id = ?", (furniture_id,)).fetchone()
            if not furniture_row:
                abort(404)
            qty = float(request.form.get("furniture_qty") or 1)
            width_m, height_m, depth_m = requested_measurements(request.form, furniture_row)
            title = request.form.get("title", "").strip() or furniture_row["name"]
            conn.execute(
                """
                UPDATE budgets
                SET title = ?, customer = ?, furniture_type_id = ?, furniture_qty = ?,
                    width_m = ?, height_m = ?, depth_m = ?,
                    labor_cost = ?, margin_pct = ?, notes = ?
                WHERE id = ?
                """,
                (
                    title,
                    request.form.get("customer", "").strip(),
                    furniture_id,
                    qty,
                    width_m,
                    height_m,
                    depth_m,
                    0,
                    100,
                    request.form.get("notes", "").strip(),
                    budget_id,
                ),
            )
            replace_budget_lines(conn, budget_id, furniture_id, qty)
        flash("Presupuesto modificado y recalculado.")
        return redirect(url_for("budget_detail", budget_id=budget_id))


    @app.route("/budgets/<int:budget_id>/delete", methods=["POST"])
    def delete_budget(budget_id: int):
        with db() as conn:
            existing = conn.execute("SELECT id FROM budgets WHERE id = ?", (budget_id,)).fetchone()
            if not existing:
                abort(404)
            conn.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
        flash("Presupuesto eliminado.")
        return redirect(url_for("budgets"))

    @app.route("/budgets/<int:budget_id>/quote.pdf")
    def budget_quote_pdf(budget_id: int):
        with db() as conn:
            budget, furniture, lines, material_total, subtotal, margin_amount, grand_total = budget_quote_data(conn, budget_id)
            workshop = get_settings(conn)
        dimensions = f"{budget['width_m']} x {budget['height_m']} x {budget['depth_m']} m"
        meta = {
            "title": budget["title"],
            "furniture_name": budget["furniture_name"] or budget["title"],
            "quantity": f"{budget['furniture_qty']:.2f}".rstrip("0").rstrip("."),
            "subtitle": budget["notes"] or dimensions,
            "folio": f"COT-{budget['id']:04d}",
            "customer": budget["customer"],
            "created_at": budget["created_at"].split(" ")[0],
        }
        pdf_bytes = build_furniture_quote_pdf(
            furniture,
            lines,
            material_total,
            subtotal,
            margin_amount,
            grand_total,
            workshop=workshop,
            meta=meta,
        )
        filename = f"cotizacion_{budget['id']:04d}_{budget['title'].replace(' ', '_')}.pdf"
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
