import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Adiciona backend ao sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from database import get_db_cursor
from models import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()
    yield

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers(client):
    """
    Cria ou reutiliza um utilizador de testes e retorna os headers de autenticação Bearer.
    """
    test_email = "tester_ci@example.com"
    test_password = "password123"

    # Tenta registrar
    client.post("/api/register", json={
        "name": "Tester CI",
        "email": test_email,
        "password": test_password
    })

    # Faz login
    login_res = client.post("/api/login", json={
        "email": test_email,
        "password": test_password
    })
    data = login_res.json()
    token = data["access_token"]
    user_id = data["user"]["id"]

    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": user_id,
        "email": test_email
    }
