# 📊 FinanceTracker — Sistema de Controlo Financeiro Pessoal

[![Status](https://img.shields.io/badge/Status-Conclu%C3%addo-success?style=for-the-badge)](https://github.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-teal?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Relational-blue?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)](LICENSE)

## 🚀 Sobre o Projeto
O **FinanceTracker** é uma aplicação web full-stack de controle financeiro pessoal desenvolvida sob uma arquitetura de monorepo moderno. O sistema oferece gestão de utilizadores com criptografia segura de senhas (*Bcrypt*), registro dinâmico de entradas e saídas financeiras, cálculo automático de saldos em tempo real e visualização analítica através de gráficos de colunas personalizados, tudo imerso numa interface futurista em **Cyberpunk Neon Glass**.

---

## 🏛️ Arquitetura do Sistema
O projeto adota uma arquitetura desacoplada e modular, separando a API RESTful de alta performance da interface web interativa.

```mermaid
graph TD
    A[Front-end SPA HTML/JS] -->|HTTP REST / JSON| B[FastAPI Back-end]
    B -->|Validação Pydantic| C[Routers Modulares: auth / transactions]
    C -->|psycopg2 Queries Parametrizadas| D[(PostgreSQL Database)]
    C -->|Passlib / Bcrypt| E[Hash Seguranças de Senha]
