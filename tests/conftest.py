import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Set the test DB before importing the app so the app uses an isolated database.
_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from app.database import Base, engine
from app.main import app

@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True, scope="session")
def cleanup_test_db():
    yield
    try:
        os.remove(_db_path)
    except OSError:
        pass
