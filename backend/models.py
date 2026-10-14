from database import get_db_connection

def init_db():
    """
    Cria automaticamente as tabelas 'users' e 'transactions' no PostgreSQL,
    garantindo a integridade referencial e o comportamento em cascata.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
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
        
        # Confirma as alterações na base de dados
        conn.commit()
        print("Esquema relacional (users e transactions) verificado/criado com sucesso no PostgreSQL!")
    except Exception as e:
        conn.rollback()
        print(f"Erro ao inicializar as tabelas no PostgreSQL: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_db()