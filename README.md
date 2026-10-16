# 📊 FinanceTracker — Sistema de Controlo Financeiro Pessoal

<p align="center">
  <img src="https://img.shields.io/badge/Versão-2.0.0-cyan?style=for-the-badge">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/FastAPI-0.110-teal?style=for-the-badge&logo=fastapi">
  <img src="https://img.shields.io/badge/PostgreSQL-15%2B-blue?style=for-the-badge&logo=postgresql">
  <img src="https://img.shields.io/badge/Pytest-Passing%20(5/5)-success?style=for-the-badge">
  <img src="https://img.shields.io/badge/License-MIT-purple?style=for-the-badge">
</p>

---

## 🚀 Sobre o Projeto

O **FinanceTracker** é uma aplicação web full-stack de controle financeiro pessoal desenvolvida sob uma arquitetura de monorepo moderno. O sistema oferece gestão de utilizadores com criptografia segura de senhas (*Bcrypt*) e tokens *JWT*, registro dinâmico e edição de entradas e saídas, cálculo automático de saldos em tempo real, **mecanismo de Previsão Inteligente para 30 dias**, filtros avançados com busca instantânea, exportação para CSV e JSON, e visualização analítica através de gráficos de colunas interativos, tudo imerso numa interface futurista em estética **Cyberpunk Neon Glassmorphism**.

---

## ✨ Principais Funcionalidades

- 🔐 **Autenticação Segura:** Cadastro e login com hash criptográfico Bcrypt e geração de tokens JWT (Bearer).
- 💰 **HUD Financeiro Reativo:** Indicadores em tempo real de Depósitos (Entradas), Gastos (Saídas) e Saldo Líquido.
- 🔮 **Previsão Inteligente (30 Dias):** Algoritmo preditivo que calcula o ritmo de gastos diários, entradas projetadas, taxa de poupança (%) e fornece recomendações financeiras dinâmicas.
- 📝 **CRUD Completo de Transações:** Criação, listagem parametrizada, atualização e remoção física com modal de confirmação.
- 🔍 **Filtros e Busca em Tempo Real:** Filtragem instantânea por texto de descrição, tipo de operação (receitas/despesas) e categorias.
- 📥 **Exportação de Dados:** Download de relatórios completos em formato **CSV** (compatível com Excel) e **JSON**.
- 📊 **Gráfico Analítico Interativo:** Gráfico proporcional por categorias com alternância de abas (*Geral*, *Despesas* e *Receitas*), exibindo percentuais e valores formatados.
- 💬 **Sistema Cyber Toasts:** Notificações flutuantes não-bloqueantes com efeitos de luz neon e feedback visual imediato.

---

## 🏛️ Arquitetura do Sistema

```mermaid
graph TD
    A[Front-end SPA HTML5/JS/CSS] -->|HTTP REST / JWT Bearer| B[FastAPI Back-end Core]
    B -->|Lifespan / DDL Automático| C[models.py]
    B -->|Validação de Schemas| D[Pydantic V2 DTOs]
    B -->|Router /api/auth| E[Autenticação & JWT]
    B -->|Router /api/transactions| F[CRUD, Filtros & Previsão 30d]
    E & F -->|Conexão Segura Context Manager| G[(PostgreSQL Database)]
```

---

## 📂 Estrutura de Diretórios

```
finance-tracker/
├── backend/
│   ├── routers/
│   │   ├── auth.py              # Endpoints de cadastro, login e /me (JWT)
│   │   └── transactions.py      # Endpoints CRUD, filtros, export e resumo 30d
│   ├── tests/
│   │   ├── conftest.py          # Fixtures e cliente de testes pytest
│   │   ├── test_auth.py         # Testes de autenticação e health check
│   │   └── test_transactions.py # Testes de ciclo de vida e projeção
│   ├── database.py              # Context manager get_db_cursor e pooling
│   ├── models.py                # DDL das tabelas e índices relacionais
│   ├── schemas.py               # Contratos e validações Pydantic V2
│   ├── main.py                  # Inicialização do FastAPI com lifespan e CORS
│   ├── requirements.txt         # Dependências do backend
│   └── Dockerfile               # Imagem Docker do backend
├── frontend/
│   ├── assets/
│   │   ├── css/
│   │   │   └── style.css        # Design System Cyberpunk Neon Glass 2.0
│   │   └── js/
│   │       ├── app.js           # Lógica do dashboard, gráficos, modais e filtros
│   │       └── auth.js          # Fluxo de login, registro e tokens
│   ├── index.html               # Dashboard principal
│   ├── login.html               # Tela de acesso
│   └── register.html            # Tela de criação de conta
├── docs/                        # Documentação técnica de arquitetura e UI
├── docker-compose.yml           # Orquestração do PostgreSQL e Backend
└── README.md                    # Este arquivo
```

---

## 🔌 Especificação da API REST

### Autenticação (`/api`)
| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/register` | Cria novo utilizador com senha Bcrypt. |
| `POST` | `/api/login` | Valida credenciais e retorna Token JWT. |
| `GET` | `/api/me` | Retorna o perfil do utilizador autenticado (Bearer). |

### Transações & Análises (`/api`)
| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/transactions` | Registra nova receita ou despesa. |
| `GET` | `/api/transactions/{user_id}` | Lista transações com filtros (`type`, `category`, `search`, `limit`). |
| `GET` | `/api/transactions/{user_id}/summary` | Retorna balanço, métricas por categoria e **Previsão Inteligente 30d**. |
| `PUT` | `/api/transactions/{transaction_id}` | Atualiza uma movimentação existente. |
| `DELETE` | `/api/transactions/{transaction_id}` | Remove uma movimentação física. |
| `GET` | `/api/transactions/{user_id}/export?format=csv\|json` | Exporta o histórico para arquivo CSV ou JSON. |

---

## ⚡ Como Executar o Projeto

### Opção 1: Deploy na Nuvem (Vercel + Neon/Supabase) 🌐

O repositório já está 100% configurado para a Vercel com Serverless Python (`/api`) e Front-end estático integrado via `vercel.json`.

1. **Obter um Banco PostgreSQL Gratuito na Nuvem:**
   - Crie uma conta gratuita no [Neon.tech](https://neon.tech) ou [Supabase](https://supabase.com).
   - Copie a string de conexão (`DATABASE_URL`), ex:
     `postgresql://usuario:senha@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require`

2. **Fazer Deploy na Vercel:**
   - Suba este repositório para o seu **GitHub**.
   - No painel da [Vercel](https://vercel.com), clique em **"Add New Project"** e selecione o repositório.
   - Na seção **Environment Variables**, adicione:
     - `DATABASE_URL`: `sua_url_do_neon_ou_supabase`
     - `JWT_SECRET`: `uma_chave_secreta_longa_e_segura`
   - Clique em **"Deploy"**.

Pronto! As tabelas do banco serão criadas automaticamente na primeira inicialização e a aplicação estará no ar no seu domínio `https://seu-projeto.vercel.app`!

---

### Opção 2: Via Docker Compose (Local)

Com o Docker instalado, execute na raiz do projeto:

```bash
docker compose up --build
```

- A API estará disponível em `http://localhost:8000` (documentação Swagger em `/docs`).
- O PostgreSQL rodará na porta `5432`.
- Abra os arquivos da pasta `frontend/index.html` em seu navegador ou sirva via Live Server / Nginx.

---

### Opção 3: Execução Local (Python Manual)

#### 1. Configurar o Banco de Dados
Certifique-se de que o serviço do PostgreSQL está ativo e crie um banco chamado `finance_tracker`.

Configure o ficheiro `backend/.env`:
```env
DATABASE_URL=postgresql://seu_usuario:sua_senha@localhost:5432/finance_tracker
JWT_SECRET=sua_chave_secreta_jwt_aqui
```

#### 2. Instalar Dependências e Iniciar o Backend
```bash
# Navegue até o diretório do backend
cd backend

# Ative o ambiente virtual
.\venv\Scripts\Activate.ps1    # No Windows PowerShell
# source venv/bin/activate     # No Linux/macOS

# Instale as dependências
pip install -r requirements.txt

# Inicie o servidor FastAPI
uvicorn main:app --reload --port 8000
```

#### 3. Abrir o Front-end
Basta abrir o arquivo `frontend/login.html` no seu navegador favorito ou servir com uma extensão como *Live Server*.

---

## 🧪 Executando os Testes Automatizados

O projeto conta com uma suíte completa de testes de integração com `pytest`:

```bash
pytest -v backend/tests
```

Saída esperada:
```
backend/tests/test_auth.py::test_health_check PASSED
backend/tests/test_auth.py::test_register_and_login_success PASSED
backend/tests/test_auth.py::test_register_duplicate_email PASSED
backend/tests/test_auth.py::test_login_invalid_credentials PASSED
backend/tests/test_transactions.py::test_transaction_lifecycle PASSED
================ 5 passed in 4.30s ================
```

---

## 📜 Licença

Distribuído sob a licença **MIT**. Consulte o arquivo [LICENSE](LICENSE) para mais informações.
