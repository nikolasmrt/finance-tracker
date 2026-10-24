# 🔌 Especificação da API REST — FinanceTracker v2.1

A API comunica-se por meio de requisições HTTP utilizando payloads em formato JSON, validados estritamente por DTOs do Pydantic V2, com suporte a cookies HTTP-Only, rate limiting e consultas agregadas otimizadas para ambientes Serverless.

## Módulos e Endpoints

### 1. Módulo de Autenticação & Sessão (`/api`)
- **`POST /api/demo`**
  - **Descrição:** Cria instantaneamente uma sessão temporária de demonstração (Modo Convidado), populando transações, orçamentos e metas realistas, gravando cookie HTTP-Only.
  - **Resposta de Sucesso (201 Created):** Retorna `user`, `access_token` e `is_demo: true`.
- **`POST /api/register`**
  - **Descrição:** Regista um novo utilizador no sistema com senha criptografada via Bcrypt e grava cookie de sessão.
  - **Payload (JSON):** `{ "name": "string", "email": "user@email.com", "password": "string (mínimo 6 caracteres)" }`
  - **Resposta de Sucesso (201 Created):** Retorna o utilizador cadastrado.
- **`POST /api/login`**
  - **Descrição:** Autentica as credenciais do utilizador comparando o hash Bcrypt e emite cookie HTTP-Only com Token JWT.
  - **Payload (JSON):** `{ "email": "user@email.com", "password": "string" }`
  - **Resposta de Sucesso (200 OK):** Confirmação de login e dados do perfil.
- **`POST /api/logout`**
  - **Descrição:** Encerra a sessão removendo o cookie HTTP-Only do navegador.
  - **Resposta de Sucesso (200 OK):** Confirmação de saída.
- **`GET /api/me`**
  - **Descrição:** Retorna o perfil do utilizador autenticado via Cookie HTTP-Only ou cabeçalho `Authorization: Bearer <token>`.
  - **Resposta de Sucesso (200 OK):** Perfil do utilizador com identificador de modo demo.

### 2. Módulo de Transações Financeiras (`/api`)
- **`POST /api/transactions`**
  - **Descrição:** Cria uma nova receita (`income`) ou despesa (`expense`).
  - **Payload (JSON):** `{ "user_id": int, "type": "income|expense", "amount": float, "description": "string", "category": "string", "transaction_date": "YYYY-MM-DD" }`
  - **Resposta de Sucesso (201 Created):** Retorna a transação criada.
- **`GET /api/transactions/{user_id}`**
  - **Descrição:** Lista as movimentações com suporte a **paginação** (`page`, `limit`), filtros query (`type`, `category`, `search`, `start_date`, `end_date`).
  - **Resposta de Sucesso (200 OK):** Objeto com `{ "transactions": [...], "pagination": { "page": int, "limit": int, "total_records": int, "total_pages": int } }`.
- **`GET /api/transactions/{user_id}/summary`**
  - **Descrição:** Consolida o balanço financeiro, totais por categoria e cálculo do algoritmo de **Previsão Inteligente (30 dias)** diretamente via SQL agregador no banco.
  - **Resposta de Sucesso (200 OK):** Objeto com `total_deposits`, `total_expenses`, `net_balance`, `categories` e `forecast`.
- **`PUT /api/transactions/{transaction_id}`**
  - **Descrição:** Atualiza campos de uma transação existente (`amount`, `description`, `category`, `type`, `transaction_date`).
  - **Resposta de Sucesso (200 OK):** Transação atualizada.
- **`DELETE /api/transactions/{transaction_id}`**
  - **Descrição:** Remove fisicamente o registo da base de dados com verificação de integridade e permissão.
  - **Resposta de Sucesso (200 OK):** Confirmação de exclusão.
- **`GET /api/transactions/{user_id}/export?format=csv|json`**
  - **Descrição:** Gera e faz download do histórico financeiro completo em planilha CSV ou em JSON estruturado.
  - **Resposta de Sucesso (200 OK):** Stream de download do arquivo.

### 3. Módulo de Orçamentos por Categoria (`/api/budgets`)
- **`GET /api/budgets/{user_id}`**
  - **Descrição:** Retorna os limites orçamentários mensais, cruzando com os gastos reais do mês atual para exibir percentual e status (`safe`, `warning`, `exceeded`).
  - **Resposta de Sucesso (200 OK):** Coleção de orçamentos com progresso.
- **`POST /api/budgets`**
  - **Descrição:** Cria ou atualiza (upsert) o teto de gastos mensal para uma categoria.
  - **Payload (JSON):** `{ "category": "string", "monthly_limit": float }`
  - **Resposta de Sucesso (201 Created):** Orçamento configurado.
- **`DELETE /api/budgets/{budget_id}`**
  - **Descrição:** Remove uma regra orçamentária.
  - **Resposta de Sucesso (200 OK):** Confirmação de remoção.

### 4. Módulo de Metas Financeiras (`/api/goals`)
- **`GET /api/goals/{user_id}`**
  - **Descrição:** Lista as metas de poupança cadastradas com percentual de conclusão.
  - **Resposta de Sucesso (200 OK):** Coleção de metas.
- **`POST /api/goals`**
  - **Descrição:** Cria uma nova meta com valor alvo e data opcional.
  - **Payload (JSON):** `{ "title": "string", "target_amount": float, "current_amount": float, "target_date": "YYYY-MM-DD" }`
  - **Resposta de Sucesso (201 Created):** Meta criada.
- **`PUT /api/goals/{goal_id}`**
  - **Descrição:** Atualiza campos da meta ou realiza aportes incrementais através do campo `add_amount`.
  - **Payload (JSON):** `{ "add_amount": float, ... }`
  - **Resposta de Sucesso (200 OK):** Meta atualizada.
- **`DELETE /api/goals/{goal_id}`**
  - **Descrição:** Remove uma meta financeira.
  - **Resposta de Sucesso (200 OK):** Confirmação de remoção.

### 5. Módulo de Manutenção & Cron (`/api/cron`)
- **`GET / POST /api/cron/cleanup-demo`**
  - **Descrição:** Rotina acionada periodicamente (via Vercel Cron) para expurgar perfis demo com mais de 4 horas de criação.
  - **Resposta de Sucesso (200 OK):** Relatório de exclusões efetuadas.
