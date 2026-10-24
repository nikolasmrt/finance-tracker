from database import get_db_cursor

def init_db():
    """
    Inicializa automaticamente o esquema relacional no PostgreSQL,
    incluindo suporte a modo Convidado (is_demo), Orçamentos (budgets),
    Metas de Economia (goals) e índices de alta performance.
    """
    try:
        with get_db_cursor(commit=True) as cursor:
            # Tabela de Utilizadores (Autenticação)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    is_demo BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Migração suave para instâncias existentes
            cursor.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
            """)

            # Tabela de Movimentações Financeiras (Transações)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id INT NOT NULL,
                    type VARCHAR(10) NOT NULL CHECK (type IN ('income', 'expense')),
                    amount NUMERIC(10, 2) NOT NULL,
                    description VARCHAR(255) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    transaction_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # Tabela de Orçamentos Mensais por Categoria
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id SERIAL PRIMARY KEY,
                    user_id INT NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    monthly_limit NUMERIC(10, 2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_budget_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT uq_user_category UNIQUE (user_id, category)
                );
            """)

            # Tabela de Metas de Economia (Savings Goals)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id SERIAL PRIMARY KEY,
                    user_id INT NOT NULL,
                    title VARCHAR(100) NOT NULL,
                    target_amount NUMERIC(10, 2) NOT NULL,
                    current_amount NUMERIC(10, 2) DEFAULT 0.00,
                    target_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_goal_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # Índices de Performance Serverless
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_user_date 
                ON transactions(user_id, transaction_date DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_category 
                ON transactions(user_id, category);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_budgets_user 
                ON budgets(user_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_goals_user 
                ON goals(user_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_demo 
                ON users(is_demo, created_at);
            """)

        print("Esquema relacional verificado e sincronizado com sucesso no PostgreSQL!")
    except Exception as e:
        print(f"Erro ao inicializar as tabelas no PostgreSQL: {e}")
        raise e

if __name__ == "__main__":
    init_db()
