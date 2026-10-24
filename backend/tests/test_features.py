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

def test_timeline_and_bills_feature(client, auth_headers):
    """Testa endpoints da linha do tempo, contas a vencer e alternância de liquidação."""
    user_id = auth_headers["user_id"]
    headers = auth_headers["headers"]

    # 1. Cria uma transação com tags, data de vencimento e pendente
    tx_payload = {
        "user_id": user_id,
        "type": "expense",
        "amount": 250.00,
        "description": "Fatura Internet Fibra Teste",
        "category": "Moradia",
        "transaction_date": "2026-10-24",
        "tags": "#internet #homeoffice",
        "due_date": "2026-10-25",
        "is_paid": False
    }
    create_res = client.post("/api/transactions", json=tx_payload, headers=headers)
    assert create_res.status_code == 201
    tx_data = create_res.json()["transaction"]
    tx_id = tx_data["id"]
    assert tx_data["tags"] == "#internet #homeoffice"
    assert tx_data["is_paid"] is False

    # 2. Testa a rota de contas a vencer (bills)
    bills_res = client.get(f"/api/transactions/{user_id}/bills", headers=headers)
    assert bills_res.status_code == 200
    bills_data = bills_res.json()
    assert "bills" in bills_data
    assert any(b["id"] == tx_id for b in bills_data["bills"])

    # 3. Testa alternar status de liquidação (toggle-paid)
    toggle_res = client.patch(f"/api/transactions/{tx_id}/toggle-paid", headers=headers)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_paid"] is True

    # 4. Testa endpoint de série temporal (timeline)
    timeline_res = client.get(f"/api/transactions/{user_id}/timeline?days=30", headers=headers)
    assert timeline_res.status_code == 200
    t_data = timeline_res.json()
    assert "points" in t_data
    assert "ending_balance" in t_data
