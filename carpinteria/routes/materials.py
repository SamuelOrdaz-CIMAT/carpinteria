from flask import abort, flash, redirect, render_template, request, url_for
from carpinteria.database import db


def register(app):
    @app.route("/materials", methods=["GET", "POST"])
    def materials():
        with db() as conn:
            if request.method == "POST":
                name = request.form.get("name", "").strip()
                if name:
                    conn.execute(
                        "INSERT OR IGNORE INTO materials (name, unit, category, notes) VALUES (?, ?, ?, ?)",
                        (
                            name,
                            request.form.get("unit", "pieza").strip() or "pieza",
                            request.form.get("category", "").strip(),
                            request.form.get("notes", "").strip(),
                        ),
                    )
                    flash("Material guardado.")
                return redirect(url_for("materials"))
            rows = conn.execute("SELECT * FROM materials ORDER BY name").fetchall()
        return render_template("materials.html", materials=rows)


    @app.route("/materials/<int:material_id>/update", methods=["POST"])
    def update_material(material_id: int):
        with db() as conn:
            conn.execute(
                "UPDATE materials SET name = ?, unit = ?, category = ?, notes = ? WHERE id = ?",
                (
                    request.form.get("name", "").strip(),
                    request.form.get("unit", "pieza").strip() or "pieza",
                    request.form.get("category", "").strip(),
                    request.form.get("notes", "").strip(),
                    material_id,
                ),
            )
        flash("Material actualizado.")
        return redirect(url_for("materials"))


    @app.route("/materials/update-all", methods=["POST"])
    def update_all_materials():
        with db() as conn:
            material_ids = request.form.getlist("material_ids")
            for raw_id in material_ids:
                material_id = int(raw_id)
                name = request.form.get(f"name_{material_id}", "").strip()
                if not name:
                    continue
                conn.execute(
                    "UPDATE materials SET name = ?, unit = ?, category = ?, notes = ? WHERE id = ?",
                    (
                        name,
                        request.form.get(f"unit_{material_id}", "pieza").strip() or "pieza",
                        request.form.get(f"category_{material_id}", "").strip(),
                        request.form.get(f"notes_{material_id}", "").strip(),
                        material_id,
                    ),
                )
        flash("Materiales actualizados.")
        return redirect(url_for("materials"))


    @app.route("/materials/<int:material_id>/delete", methods=["POST"])
    def delete_material(material_id: int):
        with db() as conn:
            existing = conn.execute("SELECT id FROM materials WHERE id = ?", (material_id,)).fetchone()
            if not existing:
                abort(404)
            conn.execute("DELETE FROM furniture_items WHERE material_id = ?", (material_id,))
            conn.execute("DELETE FROM material_prices WHERE material_id = ?", (material_id,))
            conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        flash("Material eliminado.")
        return redirect(url_for("materials"))
