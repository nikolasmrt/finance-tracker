# 🏛️ Arquitetura e Decisões de Projeto — FinanceTracker

## 1. Visão Geral do Sistema
O **FinanceTracker** adota uma arquitetura desacoplada em **Monorepo**, dividida em duas camadas principais perfeitamente isoladas:
- **Camada de Serviço (Back-end):** Desenvolvida em Python com **FastAPI**, implementa uma API RESTful de alta performance com validação estrita de contratos via **Pydantic** e persistência relacional em **PostgreSQL**.
- **Camada de Apresentação (Front-end):** Desenvelopida como uma Single Page Application (SPA) modular em HTML5, CSS3 avançado e JavaScript Vanilla, utilizando um design system personalizado (*Cyberpunk Neon Glass*).

```mermaid
graph TD
    A[Front-end SPA HTML/JS] -->|HTTP REST / JSON Assíncrono| B[FastAPI Back-end Core]
    B -->|Router Módulo Auth| C[routers/auth.py]
    B -->|Router Módulo Transações| D[routers/transactions.py]
    C & D -->|psycopg2 Queries Parametrizadas| E[(PostgreSQL Database)]
    C -->|Passlib / Bcrypt| F[Hashing de Credenciais]