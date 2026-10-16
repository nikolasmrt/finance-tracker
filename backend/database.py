import os
from pathlib import Path
from contextlib import contextmanager
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Carrega .env a partir da diretoria do backend ou da raiz do projeto
env_backend = Path(__file__).resolve().parent / ".env"
if env_backend.exists():
    load_dotenv(dotenv_path=env_backend)
else:
    load_dotenv()

def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("A variável de ambiente DATABASE_URL não está configurada.")
    return url

def get_db_connection():
    """
    Estabelece e retorna uma conexão ativa com o servidor PostgreSQL.
    Lança uma exceção caso a variável DATABASE_URL não esteja definida.
    """
    database_url = get_database_url()
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Erro crítico ao conectar ao banco de dados PostgreSQL: {e}")
        raise e

@contextmanager
def get_db_cursor(commit: bool = True):
    """
    Context manager seguro para conexões e cursores no PostgreSQL.
    Garante commit automático em caso de sucesso e rollback em exceções,
    além de fechar cursores e conexões no bloco finally.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()