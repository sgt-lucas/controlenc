# database.py - Versão Completa e Funcional
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": "localhost", "port": "5432", "database": "controlenc_db",
    "user": "postgres", "password": "Luca$8575" # Sua senha
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def execute_query(query, params=None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        if cur.description: return cur.fetchall()
        return None
    except Exception as e:
        if conn: conn.rollback()
        raise e
    finally:
        if cur: cur.close()
        if conn: conn.close()

def execute_transaction(queries_with_params):
    """Executa várias operações em uma transação única (resolve o erro de atributo)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        results = []
        for query, params in queries_with_params:
            cur.execute(query, params)
            results.append(cur.fetchall() if cur.description else None)
        conn.commit()
        return results
    except Exception as e:
        if conn: conn.rollback()
        raise e
    finally:
        cur.close(); conn.close()

def registrar_log(user_id, acao, tabela, registro_id, detalhes):
    sql = "INSERT INTO audit_logs (user_id, action, target_table, record_id, detalhes) VALUES (%s,%s,%s,%s,%s)"
    try: execute_query(sql, (user_id, acao, tabela, registro_id, detalhes))
    except: pass