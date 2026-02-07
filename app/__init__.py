from flask import Flask, redirect, url_for
from app.config import Config
from app.extensions import db, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Alembic can detect them
    from app import models  # noqa: F401

    # Register blueprints
    from app.routes.accounts import accounts_bp
    from app.routes.rules import rules_bp
    from app.routes.maintenance import maintenance_bp

    app.register_blueprint(accounts_bp)
    app.register_blueprint(rules_bp)
    app.register_blueprint(maintenance_bp)

    @app.route("/")
    def index():
        return redirect(url_for("rules.index"))

    return app
