# 📊 FinanceTracker — Sistema de Controlo Financeiro Pessoal

<p align="center">
  <img src="https://img.shields.io/badge/Versão-2.1.0-cyan?style=for-the-badge">
  <img src="https://img.shields.io/badge/Vercel-Serverless%20Ready-black?style=for-the-badge&logo=vercel">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/FastAPI-0.110-teal?style=for-the-badge&logo=fastapi">
  <img src="https://img.shields.io/badge/PostgreSQL-Neon%20Serverless-blue?style=for-the-badge&logo=postgresql">
  <img src="https://img.shields.io/badge/Pytest-Passing%20(10/10)-success?style=for-the-badge">
  <img src="https://img.shields.io/badge/License-MIT-purple?style=for-the-badge">
</p>

---

## 🚀 Sobre o Projeto

O **FinanceTracker** é uma aplicação web full-stack de controle financeiro pessoal desenvolvida sob uma arquitetura moderna e escalável, 100% pronta para **deploy na Vercel** com **PostgreSQL Serverless (Neon/Supabase)**.

Qualquer pessoa pode **testar instantaneamente na nuvem com 1 clique (sem necessidade de cadastro)** através do **Modo Convidado**, enquanto usuários reais contam com autenticação em **Cookies HTTP-Only**, proteção contra força bruta (*Rate Limiting*), orçamentos mensais com barras de progresso, metas de economia, simulador de cenários ("E se..."), suporte multi-moeda e alternância entre tema **Cyberpunk Neon** e **Clean Minimal**.

---

## ✨ Principais Funcionalidades

### 1. Experiência de Teste Imediato (Vercel Test Mode)
* 🧪 **Modo Convidado 1-Click:** Botão *"Testar Agora (Modo Convidado)"* na tela de login que gera automaticamente uma sessão isolada pré-povoada com transações, metas e orçamentos realistas. Permite testar criação, edição, filtros e simulações sem preencher cadastros.
* 🧹 **Auto-Cleanup / Vercel Cron:** Rotina interna (`/api/cron/cleanup-demo`) configurada no `vercel.json` para expurgar automaticamente contas de demonstração após 4 horas, mantendo o banco de dados leve.

### 2. Segurança & Infraestrutura
* 🔒 **Cookies HTTP-Only com SameSite=Lax e Secure:** Proteção total contra roubo de tokens via XSS.
* 🛡️ **Rate Limiting (SlowAPI):** Limite de requisições por IP protegendo endpoints sensíveis contra abusos e ataques de força bruta.
* 🌐 **CORS Dinâmico Rígido:** Aceita dinamicamente domínios autorizados da Vercel (`*.vercel.app`) e ambientes de desenvolvimento local.
* 🛡️ **Sanitização XSS:** Escapamento e validação estrita em todas as entradas no frontend e schemas Pydantic V2 no backend.

### 3. Alta Performance & Serverless
* ⚡ **Consultas Agregadas em SQL:** Métricas e balanços (`SUM`, `COUNT`, `AVG`) calculados diretamente no PostgreSQL, sem carregar listas pesadas na memória da função serverless.
* 📄 **Paginação Serverless:** Navegação paginada na API e no frontend com controle de limite por página e navegação rápida.
* 🔌 **Conexão Otimizada com Neon Pooler:** Gerenciamento seguro de conexões com fechamento imediato para evitar esgotamento de conexões ativas.

### 4. Gestão Financeira Completa
* 🎯 **Orçamentos Mensais por Categoria:** Defina tetos de gastos (ex: Alimentação R$ 1.000) e acompanhe barras visuais de progresso (verde, amarelo e vermelho).
* 🏆 **Metas Financeiras (Savings Goals):** Crie objetivos (ex: "Fundo de Emergência", "Viagem"), acompanhe o percentual atingido e faça aportes rápidos.
* 🔮 **Previsão Inteligente & Simulador ("E se..."):** Projeção de saldo para 30 dias com simulador interativo de corte de gastos em tempo real.
* 💵 **Suporte Multi-Moeda:** Alterne instantaneamente entre `BRL (R$)`, `USD ($)` e `EUR (€)`.
* 📥 **Exportação de Dados:** Download de relatórios em formatos **CSV** (Excel UTF-8-BOM) e **JSON**.

### 5. UI/UX Avançada
* 🎨 **Alternância de Tema:** Escolha entre a estética futurista **Cyberpunk Neon Glass** e o modo **Clean Minimal**.
* ⌨️ **Atalhos de Teclado:** Tecla `[N]` para nova movimentação, `[F]` para focar busca e `[ESC]` para fechar modais.
* 💬 **Cyber Toasts:** Notificações flutuantes com feedback visual em tempo real.

---

## 🏛️ Arquitetura do Sistema

```mermaid
graph TD
    A[Front-end SPA HTML5/JS/CSS] -->|HTTP REST + Cookies HTTP-Only| B[FastAPI Serverless /api/index.py]
    B -->|SlowAPI| R[Rate Limiting Middleware]
    R -->|Pydantic V2| S[Validação de DTOs]
    S --> C[Router Auth: Login / Registro / Demo]
    S --> D[Router Transactions: CRUD & Paginação]
    S --> E[Router Budgets: Tetos por Categoria]
    S --> F[Router Goals: Metas de Economia]
    S --> G[Router Cron: Limpeza Automática]
    C & D & E & F & G -->|psycopg2 Context Manager| H[(PostgreSQL Neon Cloud)]
```

---

## 📂 Estrutura do Projeto

```
finance-tracker/
├── api/
│   └── index.py                 # Entrypoint serverless para Vercel
├── backend/
│   ├── routers/
│   │   ├── auth.py              # Login, registro, /me, /demo e cookies HTTP-Only
│   │   ├── transactions.py      # CRUD, paginação, resumo agregado e export
│   │   ├── budgets.py           # Tetos mensais por categoria
│   │   ├── goals.py             # Metas financeiras e aportes
│   │   └── cron.py              # Rotina de limpeza agendada
│   ├── tests/
│   │   ├── conftest.py          # Fixtures do pytest
│   │   ├── test_auth.py         # Testes de autenticação e modo demo
│   │   ├── test_transactions.py # Testes de transações e paginação
│   │   └── test_features.py     # Testes de orçamentos, metas e cron
│   ├── database.py              # Gerenciador de conexões otimizado para Serverless
│   ├── models.py                # DDL relacional (users, transactions, budgets, goals)
│   ├── schemas.py               # Contratos e validações Pydantic V2
│   ├── main.py                  # Inicialização do FastAPI com rate limiting e CORS
│   └── requirements.txt         # Dependências do backend
├── frontend/
│   ├── assets/
│   │   ├── css/
│   │   │   └── style.css        # Design System (Cyberpunk Neon + Clean Minimal)
│   │   └── js/
│   │       ├── app.js           # Lógica do painel, filtros, metas, orçamentos, simulação
│   │       └── auth.js          # Fluxo de login, registro e botão Demo 1-Click
│   ├── index.html               # Dashboard completo
│   ├── login.html               # Tela de acesso com botão Modo Convidado
│   └── register.html            # Tela de criação de conta
├── vercel.json                  # Roteamento e Cron Jobs para Vercel
├── requirements.txt             # Dependências na raiz para detecção da Vercel
└── README.md                    # Documentação do projeto
```

---

## ⚡ Como Fazer Deploy na Vercel (Guia Passo a Passo)

1. **Obter uma conta gratuita no [Neon.tech](https://neon.tech):**
   - Crie um projeto no Neon e copie a string de conexão:
     `postgresql://usuario:senha@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require`

2. **Subir para o GitHub:**
   ```bash
   git add .
   git commit -m "feat: evolucao completa para Vercel com modo demo e seguranca"
   git push origin main
   ```

3. **Importar na Vercel ([vercel.com](https://vercel.com)):**
   - Clique em **"Add New Project"** e selecione este repositório.
   - Em **Environment Variables**, adicione:
     - `DATABASE_URL`: String de conexão do Neon.
     - `JWT_SECRET`: Uma chave segura (ex: `finance-tracker-cyberpunk-secret-2026`).
     - `CRON_SECRET`: *(Opcional)* Segredo para autenticar as chamadas de cron.
   - Clique em **Deploy**.

4. **Pronto para Usar:**
   - Acesse a URL gerada pela Vercel e clique em **"🧪 Testar Agora (Modo Convidado)"** para experimentar imediatamente!

---

## 🧪 Testes Automatizados (Pytest)

Execute a suíte completa de testes de integração com o comando:

```bash
pytest -v backend/tests
```

**Resultado:**
```text
backend/tests/test_auth.py::test_health_check PASSED               [ 10%]
backend/tests/test_auth.py::test_register_and_login_success PASSED [ 20%]
backend/tests/test_auth.py::test_demo_mode_session PASSED          [ 30%]
backend/tests/test_auth.py::test_logout_clears_session PASSED      [ 40%]
backend/tests/test_auth.py::test_register_duplicate_email PASSED   [ 50%]
backend/tests/test_auth.py::test_login_invalid_credentials PASSED  [ 60%]
backend/tests/test_features.py::test_budgets_lifecycle PASSED      [ 70%]
backend/tests/test_features.py::test_goals_lifecycle PASSED        [ 80%]
backend/tests/test_features.py::test_cron_demo_cleanup PASSED      [ 90%]
backend/tests/test_transactions.py::test_transaction_lifecycle PASSED [100%]
====================== 10 passed in 1.13s ======================
```

---

## 📜 Licença

Distribuído sob a licença **MIT**. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
