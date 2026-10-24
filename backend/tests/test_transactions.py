def test_transaction_lifecycle(client, auth_headers):
    user_id = auth_headers["user_id"]
    headers = auth_headers["headers"]

    # 1. Criação de Receita
    income_payload = {
        "user_id": user_id,
        "type": "income",
        "amount": 5000.00,
        "description": "Salário Desenvolvimento",
        "category": "Trabalho",
        "transaction_date": "2026-10-01"
    }
    res_inc = client.post("/api/transactions", json=income_payload, headers=headers)
    assert res_inc.status_code == 201
    income_tx = res_inc.json()["transaction"]
    assert income_tx["amount"] == 5000.00

    # 2. Criação de Despesa
    expense_payload = {
        "user_id": user_id,
        "type": "expense",
        "amount": 1200.00,
        "description": "Aluguel Apartamento",
        "category": "Moradia",
        "transaction_date": "2026-10-05"
    }
    res_exp = client.post("/api/transactions", json=expense_payload, headers=headers)
    assert res_exp.status_code == 201
    expense_tx = res_exp.json()["transaction"]

    # 3. Listagem com Paginação e Filtros
    list_res = client.get(f"/api/transactions/{user_id}?page=1&limit=5", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert "transactions" in data
    assert "pagination" in data
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["limit"] == 5
    assert data["pagination"]["total_records"] >= 2

    # Filtro por tipo 'expense'
    filter_exp = client.get(f"/api/transactions/{user_id}?type=expense", headers=headers)
    assert filter_exp.status_code == 200
    assert all(t["type"] == "expense" for t in filter_exp.json()["transactions"])

    # Filtro por busca textual
    filter_search = client.get(f"/api/transactions/{user_id}?search=Aluguel", headers=headers)
    assert filter_search.status_code == 200
    assert any("Aluguel" in t["description"] for t in filter_search.json()["transactions"])

    # 4. Atualização (Update)
    update_res = client.put(
        f"/api/transactions/{expense_tx['id']}",
        json={"amount": 1350.00, "description": "Aluguel Atualizado"},
        headers=headers
    )
    assert update_res.status_code == 200
    updated_tx = update_res.json()["transaction"]
    assert updated_tx["amount"] == 1350.00
    assert updated_tx["description"] == "Aluguel Atualizado"

    # 5. Resumo e Previsão Inteligente
    summary_res = client.get(f"/api/transactions/{user_id}/summary", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_deposits"] >= 5000.00
    assert summary["total_expenses"] >= 1350.00
    assert summary["net_balance"] == round(summary["total_deposits"] - summary["total_expenses"], 2)
    assert "forecast" in summary
    assert "projected_balance_30d" in summary["forecast"]
    assert summary["forecast"]["status"] in ("positive", "warning", "critical", "neutral")

    # 6. Exportação para CSV
    export_res = client.get(f"/api/transactions/{user_id}/export?format=csv", headers=headers)
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["content-type"]
    assert "Aluguel Atualizado" in export_res.text

    # 7. Exclusão (Delete)
    del_res = client.delete(f"/api/transactions/{expense_tx['id']}", headers=headers)
    assert del_res.status_code == 200

    # Tenta excluir novamente (deve dar 404)
    del_again = client.delete(f"/api/transactions/{expense_tx['id']}", headers=headers)
    assert del_again.status_code == 404

    # Limpeza do item de receita
    client.delete(f"/api/transactions/{income_tx['id']}", headers=headers)
