import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Adiciona backend ao sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client):
    """
    Cria ou reutiliza um utilizador de testes e retorna os headers Bearer + cookies HttpOnly.
    """
    test_email = "tester_ci@example.com"
    test_password = "password123"

    # Tenta registar (ignora se já existir)
    client.post(
        "/api/register",
        json={
            "name": "Tester CI",
            "email": test_email,
            "password": test_password,
        },
    )

    # Faz login
    login_res = client.post(
        "/api/login",
        json={
            "email": test_email,
            "password": test_password,
        },
    )
    assert login_res.status_code == 200
    data = login_res.json()
    token = login_res.cookies.get("access_token")
    user_id = data["user"]["id"]

    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": user_id,
        "email": test_email,
    }
