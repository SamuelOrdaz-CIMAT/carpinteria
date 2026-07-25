import os

from carpinteria import create_app, initialize

app = create_app()

if __name__ == "__main__":
    initialize()
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", debug=debug, port=port)
