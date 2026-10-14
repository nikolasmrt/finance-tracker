# 🔌 Especificação da API REST — FinanceTracker

A API comunica-se por meio de requisições HTTP utilizando payloads em formato JSON, validados estritamente por DTOs do Pydantic.

## Módulos e Endpoints

### 1. Módulo de Autenticação (`/api`)
- **`POST /api/register`**
  - **Descrição:** Regista um novo utilizador no sistema.
  - **Payload (JSON):** `{ "name": "string", "email": "user@email.com", "password": "string" }`
  - **Resposta de Sucesso (201 Created):** Retorna o ID sequencial, nome e e-mail.
- **`POST /api/login`**
  - **Descrição:** Autentica as credenciais do utilizador comparando o hash do Bcrypt.
  - **Payload (JSON):** `{ "email": "user@email.com", "password": "string" }`
  - **Resposta de Sucesso (200 OK):** Confirmação de login e dados básicos do perfil.

### 2. Módulo de Transações Financeiras (`/api`)
- **`POST /api/transactions`**
  - **Descrição:** Cria uma nova receita (`income`) ou despesa (`expense`).
  - **Payload (JSON):** `{ "user_id": int, "type": "income|expense", "amount": float, "description": "string", "category": "string", "transaction_date": "YYYY-MM-DD" }`
  - **Resposta de Sucesso (201 Created):** Retorna a transação criada.
- **`GET /api/transactions/{user_id}`**
  - **Descrição:** Lista todas as movimentações financeiras de um utilizador específico ordenadas por data descendente.
  - **Resposta de Sucesso (200 OK):** Coleção de transações em formato JSON.
- **`DELETE /api/transactions/{transaction_id}`**
  - **Descrição:** Remove fisicamente um registo de transação da base de dados PostgreSQL pelo seu ID.
  - **Resposta de Sucesso (200 OK):** Confirmação de exclusão.