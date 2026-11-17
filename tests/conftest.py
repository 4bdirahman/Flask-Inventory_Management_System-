import pytest

from app import create_app
from app.storage import reset_inventory


@pytest.fixture
def client():
    reset_inventory()
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
    reset_inventory()
