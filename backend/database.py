import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Carrega .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """
    Estabelece e retorna uma conexão ativa com o servidor PostgreSQL.
    Lança uma excepção caso a variável DATABASE_URL não esteja definida.
    """
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não está configurada no ficheiro .env")
    
    try:
        # Conecta ao PostgreSQL e configura o cursor para retornar dicionários
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Erro crítico ao conectar ao banco de dados PostgreSQL: {e}")
        raise e