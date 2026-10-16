import uuid

def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["database"] == "connected"

def test_register_and_login_success(client):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "name": "Cyber User",
        "email": unique_email,
        "password": "strongPassword123"
    }

    # Registro
    res = client.post("/api/register", json=payload)
    assert res.status_code == 201
    user_data = res.json()
    assert user_data["email"] == unique_email
    assert "id" in user_data

    # Login
    login_res = client.post("/api/login", json={
        "email": unique_email,
        "password": "strongPassword123"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == unique_email

    # Verificação de Perfil (/me)
    token = login_data["access_token"]
    me_res = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["id"] == user_data["id"]

def test_register_duplicate_email(client):
    email = "duplicate@example.com"
    client.post("/api/register", json={
        "name": "Original",
        "email": email,
        "password": "password123"
    })

    # Tenta registrar o mesmo e-mail novamente
    res = client.post("/api/register", json={
        "name": "Clone",
        "email": email,
        "password": "password123"
    })
    assert res.status_code == 400
    assert "já está registado" in res.json()["detail"]

def test_login_invalid_credentials(client):
    res = client.post("/api/login", json={
        "email": "nonexistent_email_1234@domain.com",
        "password": "anypassword"
    })
    assert res.status_code == 401
