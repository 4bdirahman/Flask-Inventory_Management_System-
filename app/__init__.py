"""Flask application factory for the inventory API."""

from flask import Flask

from app.inventory import inventory_bp
from app.lookup import lookup_bp


def create_app():
    """Create the app and register the inventory and lookup routes."""
    app = Flask(__name__)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(lookup_bp)
    return app


# Used by `flask --app app run`.
app = create_app()
