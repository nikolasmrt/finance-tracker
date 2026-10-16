from database import get_db_cursor

def init_db():
    """
    Cria automaticamente as tabelas 'users' e 'transactions' no PostgreSQL,
    além de índices estratégicos para acelerar consultas e relatórios.
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
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

            # Índices de performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_user_date 
                ON transactions(user_id, transaction_date DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_category 
                ON transactions(user_id, category);
            """)

        print("Esquema relacional (users e transactions) verificado/criado com sucesso no PostgreSQL!")
    except Exception as e:
        print(f"Erro ao inicializar as tabelas no PostgreSQL: {e}")
        raise e

if __name__ == "__main__":
    init_db()