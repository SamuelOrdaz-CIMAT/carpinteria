import shutil
from datetime import datetime
from flask import Response, flash, redirect, render_template, request, url_for
from carpinteria.database import DEFAULT_SETTINGS, db, get_settings, initialize
from carpinteria.paths import BASE_DIR, DB_PATH
from carpinteria.services.dashboard import fetch_dashboard


def register(app):
    @app.route("/")
    def index():
        with db() as conn:
            data = fetch_dashboard(conn)
        return render_template("index.html", **data)


    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        with db() as conn:
            if request.method == "POST":
                for key in DEFAULT_SETTINGS:
                    conn.execute(
                        """
                        INSERT INTO settings (key, value)
                        VALUES (?, ?)
                        ON CONFLICT(key) DO UPDATE SET value = excluded.value
                        """,
                        (key, request.form.get(key, "").strip()),
                    )
                flash("Configuracion guardada.")
                return redirect(url_for("settings"))
            values = get_settings(conn)
        return render_template("settings.html", settings=values)


    @app.route("/backup")
    def backup_database():
        initialize()
        backup_dir = BASE_DIR / "respaldos"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"carpinteria_backup_{timestamp}.db"
        shutil.copy2(DB_PATH, backup_path)
        return Response(
            backup_path.read_bytes(),
            mimetype="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{backup_path.name}"'},
        )
