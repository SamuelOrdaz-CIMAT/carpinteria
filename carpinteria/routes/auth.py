import os
from flask import redirect, render_template, request, session, url_for


def register(app):
    @app.before_request
    def require_password():
        password = os.environ.get("CARPINTERIA_PASSWORD", "").strip()
        if not password or request.endpoint in {"login", "static"}:
            return None
        if session.get("authenticated"):
            return None
        return redirect(url_for("login", next=request.path))


    @app.route("/login", methods=["GET", "POST"])
    def login():
        password = os.environ.get("CARPINTERIA_PASSWORD", "").strip()
        if not password:
            return redirect(url_for("index"))
        error = ""
        if request.method == "POST":
            if request.form.get("password", "") == password:
                session["authenticated"] = True
                return redirect(request.args.get("next") or url_for("index"))
            error = "Contrasena incorrecta."
        return render_template("login.html", error=error)


    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))
