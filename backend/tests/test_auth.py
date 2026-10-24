import uuid


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["database"] == "connected"


def test_register_and_login_success(client):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "name": "Cyber User",
        "email": unique_email,
        "password": "strongPassword123",
    }

    # Registo (já abre sessão via Cookie HttpOnly)
    res = client.post("/api/register", json=payload)
    assert res.status_code == 201
    reg_data = res.json()
    assert reg_data["user"]["email"] == unique_email
    assert "id" in reg_data["user"]
    assert "access_token" in res.cookies

    # Login
    login_res = client.post(
        "/api/login",
        json={
            "email": unique_email,
            "password": "strongPassword123",
        },
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["user"]["email"] == unique_email
    assert "access_token" in login_res.cookies

    # Verificação de Perfil (/me) via Cookie HttpOnly
    me_res = client.get("/api/me")
    assert me_res.status_code == 200
    assert me_res.json()["id"] == reg_data["user"]["id"]


def test_demo_mode_session(client):
    """Testa o Modo Convidado 1-Click sem necessidade de senha nem registo."""
    res = client.post("/api/demo")
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["is_demo"] is True
    assert "guest_" in data["user"]["email"]
    assert "access_token" in res.cookies

    # Acessa /me utilizando o cookie retornado
    me_res = client.get("/api/me")
    assert me_res.status_code == 200
    assert me_res.json()["is_demo"] is True


def test_logout_clears_session(client):
    """Testa encerramento de sessão."""
    res = client.post("/api/logout")
    assert res.status_code == 200


def test_register_duplicate_email(client):
    email = f"duplicate_{uuid.uuid4().hex[:6]}@example.com"
    client.post(
        "/api/register",
        json={
            "name": "Original",
            "email": email,
            "password": "password123",
        },
    )

    # Tenta registar o mesmo e-mail novamente
    res = client.post(
        "/api/register",
        json={
            "name": "Clone",
            "email": email,
            "password": "password123",
        },
    )
    assert res.status_code == 409
    assert "já está registado" in res.json()["detail"]


def test_login_invalid_credentials(client):
    res = client.post(
        "/api/login",
        json={
            "email": "nonexistent_email_1234@domain.com",
            "password": "anypassword123",
        },
    )
    assert res.status_code == 401
