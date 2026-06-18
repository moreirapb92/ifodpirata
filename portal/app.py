import os
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from portal.models import init_db
from portal.routes import api
from portal.admin import admin_bp
from portal.loja import loja_bp

def create_app():
    app = Flask(__name__, template_folder="templates")
    app.secret_key = os.getenv("PORTAL_SECRET_KEY", "ifodpirata-dev-key-change-in-production")
    CORS(app)

    app.register_blueprint(api)
    app.register_blueprint(admin_bp)
    app.register_blueprint(loja_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/admin")
    def admin():
        return render_template("admin.html")

    @app.route("/pedidos")
    def pedidos_page():
        return render_template("pedidos.html")

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    with app.app_context():
        init_db()

    return app


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=int(os.getenv("PORTAL_PORT", "5000")), debug=debug)
