def test_budgets_lifecycle(client, auth_headers):
    user_id = auth_headers["user_id"]
    headers = auth_headers["headers"]

    # 1. Configura um teto orçamentário para Alimentação
    budget_payload = {
        "category": "Alimentação",
        "monthly_limit": 800.00
    }
    create_res = client.post("/api/budgets", json=budget_payload, headers=headers)
    assert create_res.status_code == 201
    b_data = create_res.json()
    assert b_data["category"] == "Alimentação"
    assert b_data["monthly_limit"] == 800.00
    budget_id = b_data["id"]

    # 2. Lista os orçamentos
    list_res = client.get(f"/api/budgets/{user_id}", headers=headers)
    assert list_res.status_code == 200
    budgets = list_res.json()
    assert any(b["id"] == budget_id for b in budgets)

    # 3. Exclui o orçamento
    del_res = client.delete(f"/api/budgets/{budget_id}", headers=headers)
    assert del_res.status_code == 200

def test_goals_lifecycle(client, auth_headers):
    user_id = auth_headers["user_id"]
    headers = auth_headers["headers"]

    # 1. Cria uma meta financeira
    goal_payload = {
        "title": "Viagem de Férias Cyberpunk",
        "target_amount": 5000.00,
        "current_amount": 1000.00,
        "target_date": "2026-12-31"
    }
    create_res = client.post("/api/goals", json=goal_payload, headers=headers)
    assert create_res.status_code == 201
    goal = create_res.json()
    assert goal["title"] == "Viagem de Férias Cyberpunk"
    assert goal["progress_percentage"] == 20.0
    goal_id = goal["id"]

    # 2. Realiza um aporte na meta
    update_res = client.put(f"/api/goals/{goal_id}", json={"add_amount": 1500.00}, headers=headers)
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["current_amount"] == 2500.00
    assert updated["progress_percentage"] == 50.0

    # 3. Lista metas
    list_res = client.get(f"/api/goals/{user_id}", headers=headers)
    assert list_res.status_code == 200
    assert any(g["id"] == goal_id for g in list_res.json())

    # 4. Remove meta
    del_res = client.delete(f"/api/goals/{goal_id}", headers=headers)
    assert del_res.status_code == 200

def test_cron_demo_cleanup(client):
    """Testa a rota de limpeza automática de sessões de demonstração."""
    res = client.post("/api/cron/cleanup-demo")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "deleted_count" in data
