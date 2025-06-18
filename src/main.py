from flask import Flask, jsonify, current_app
from src.models.database import db
from src.routes.settings import settings_bp
import os

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///site.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)

    app.register_blueprint(settings_bp, url_prefix="/settings")

    @app.route("/")
    def home():
        return "Welcome to the Flask App!"

    @app.route("/_routes")
    def list_routes():
        output = []
        for rule in app.url_map.iter_rules():
            methods = ",".join(rule.methods)
            output.append(f"{rule.endpoint}: {rule.rule} ({methods})")
        return jsonify(output)

    return app

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=os.environ.get("PORT", 5000))
