from flask import Flask

from carpinteria.database import initialize
from carpinteria.routes import auth, budgets, furniture, main, materials, prices, suppliers
from carpinteria.utils import money


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = "carpinteria-local"
    app.jinja_env.filters["money"] = money

    auth.register(app)
    main.register(app)
    materials.register(app)
    suppliers.register(app)
    prices.register(app)
    furniture.register(app)
    budgets.register(app)
    return app
