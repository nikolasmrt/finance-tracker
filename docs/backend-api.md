# 🔌 Especificação da API REST — FinanceTracker v2.0

A API comunica-se por meio de requisições HTTP utilizando payloads em formato JSON, validados estritamente por DTOs do Pydantic V2.

## Módulos e Endpoints

### 1. Módulo de Autenticação (`/api`)
- **`POST /api/register`**
  - **Descrição:** Regista um novo utilizador no sistema com senha criptografada via Bcrypt.
  - **Payload (JSON):** `{ "name": "string", "email": "user@email.com", "password": "string (mínimo 6 caracteres)" }`
  - **Resposta de Sucesso (201 Created):** Retorna o ID sequencial, nome e e-mail.
- **`POST /api/login`**
  - **Descrição:** Autentica as credenciais do utilizador comparando o hash Bcrypt e emite um Token JWT de longa duração.
  - **Payload (JSON):** `{ "email": "user@email.com", "password": "string" }`
  - **Resposta de Sucesso (200 OK):** `{ "message": "...", "access_token": "...", "token_type": "bearer", "user": { "id": int, "name": "...", "email": "..." } }`
- **`GET /api/me`**
  - **Descrição:** Retorna o perfil do utilizador autenticado via cabeçalho `Authorization: Bearer <token>`.
  - **Resposta de Sucesso (200 OK):** Perfil do utilizador.

### 2. Módulo de Transações Financeiras (`/api`)
- **`POST /api/transactions`**
  - **Descrição:** Cria uma nova receita (`income`) ou despesa (`expense`).
  - **Payload (JSON):** `{ "user_id": int, "type": "income|expense", "amount": float, "description": "string", "category": "string", "transaction_date": "YYYY-MM-DD" }`
  - **Resposta de Sucesso (201 Created):** Retorna a transação criada.
- **`GET /api/transactions/{user_id}`**
  - **Descrição:** Lista as movimentações com suporte a filtros query: `type`, `category`, `search`, `start_date`, `end_date`, `limit`.
  - **Resposta de Sucesso (200 OK):** Coleção de transações filtradas.
- **`GET /api/transactions/{user_id}/summary`**
  - **Descrição:** Consolida o balanço financeiro, totais por categoria e cálculo do algoritmo de **Previsão Inteligente (30 dias)**.
  - **Resposta de Sucesso (200 OK):** Objeto com `total_deposits`, `total_expenses`, `net_balance`, `categories` e `forecast`.
- **`PUT /api/transactions/{transaction_id}`**
  - **Descrição:** Atualiza campos de uma transação existente (`amount`, `description`, `category`, `type`, `transaction_date`).
  - **Resposta de Sucesso (200 OK):** Transação atualizada.
- **`DELETE /api/transactions/{transaction_id}`**
  - **Descrição:** Remove fisicamente o registo da base de dados com verificação de integridade e permissão.
  - **Resposta de Sucesso (200 OK):** Confirmação de exclusão.
- **`GET /api/transactions/{user_id}/export?format=csv|json`**
  - **Descrição:** Gera e faz download do histórico financeiro completo em planilha CSV (delimitada por ponto-e-vírgula com codificação UTF-8-BOM) ou em JSON estruturado.
  - **Resposta de Sucesso (200 OK):** Stream de download do arquivo.