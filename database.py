import psycopg2
import pandas as pd
import datetime
import streamlit as st
import time

def get_connection():
    """Establishes a connection to the PostgreSQL database using secrets with retries."""
    if "DATABASE_URL" not in st.secrets:
        return None

    max_retries = 3
    retry_delay = 2 # seconds
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(st.secrets["DATABASE_URL"])
            return conn
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            st.error(f"Erro ao conectar ao banco de dados: {e}")
            return None

def init_db():
    """Initializes the PostgreSQL database with necessary tables."""
    conn = get_connection()
    if not conn: return
    
    c = conn.cursor()
    
    # Create Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            status TEXT NOT NULL DEFAULT 'pending', 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Transactions Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create Goals Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            target_amount DECIMAL(15,2) NOT NULL,
            category_link TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_user_goal FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def run_query(query, params=(), return_data=False):
    """Helper function to run SQL queries in PostgreSQL."""
    conn = get_connection()
    if not conn: return False
    
    c = conn.cursor()
    try:
        c.execute(query, params)
        if return_data:
            data = c.fetchall()
            conn.close()
            return data
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        if conn: conn.close()
        return str(e)

def get_users_df():
    """Returns a pandas DataFrame of all users."""
    conn = get_connection()
    if not conn: return pd.DataFrame()
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

def get_transactions_df(user_id):
    """Returns a pandas DataFrame of transactions for a specific user."""
    conn = get_connection()
    if not conn: return pd.DataFrame()
    df = pd.read_sql_query("SELECT * FROM transactions WHERE user_id = %s", conn, params=(user_id,))
    conn.close()
    return df

def add_transaction(user_id, date, type, category, amount, description):
    """Adds a new transaction."""
    return run_query(
        "INSERT INTO transactions (user_id, date, type, category, amount, description) VALUES (%s, %s, %s, %s, %s, %s)",
        (user_id, date, type, category, amount, description)
    )

def update_transaction(transaction_id, date, type, category, amount, description):
    """Updates an existing transaction."""
    return run_query(
        "UPDATE transactions SET date=%s, type=%s, category=%s, amount=%s, description=%s WHERE id=%s",
        (date, type, category, amount, description, transaction_id)
    )

def delete_transaction(transaction_id):
    """Deletes a transaction."""
    return run_query("DELETE FROM transactions WHERE id = %s", (transaction_id,))

def create_goal(user_id, name, target, category):
    """Creates a new investment goal."""
    return run_query(
        "INSERT INTO goals (user_id, name, target_amount, category_link) VALUES (%s, %s, %s, %s)", 
        (user_id, name, target, category)
    )

def update_goal_target(user_id, category, new_target):
    """Updates the target amount for a specific category goal."""
    conn = get_connection()
    if not conn: return False
    c = conn.cursor()
    # Check if goal exists
    c.execute("SELECT id FROM goals WHERE user_id = %s AND category_link = %s", (user_id, category))
    exists = c.fetchone()
    if exists:
        c.execute("UPDATE goals SET target_amount = %s WHERE user_id = %s AND category_link = %s", (new_target, user_id, category))
    else:
        # Create if doesn't exist
        c.execute("INSERT INTO goals (user_id, name, target_amount, category_link) VALUES (%s, %s, %s, %s)", 
                     (user_id, f"Meta: {category}", new_target, category))
    conn.commit()
    conn.close()
    return True

def delete_goal(goal_id):
    return run_query("DELETE FROM goals WHERE id = %s", (goal_id,))

def get_goals(user_id):
    """Returns list of goals for user."""
    conn = get_connection()
    if not conn: return pd.DataFrame()
    df = pd.read_sql_query("SELECT * FROM goals WHERE user_id = %s", conn, params=(user_id,))
    conn.close()
    return df

def get_goal_progress(user_id, category_link):
    """Calculates total invested in a specific category."""
    conn = get_connection()
    if not conn: return 0.0
    c = conn.cursor()
    c.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = %s AND type = 'Investimento' AND category = %s", 
        (user_id, category_link)
    )
    res = c.fetchone()
    total = float(res[0]) if res and res[0] is not None else 0.0
    conn.close()
    return total

def get_monthly_summary(user_id, month, year):
    """Calculates totals for a specific month."""
    conn = get_connection()
    if not conn: return 0.0, 0.0, 0.0
    c = conn.cursor()
    
    # Income
    c.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = %s AND type = 'Entrada' AND EXTRACT(MONTH FROM date) = %s AND EXTRACT(YEAR FROM date) = %s", 
        (user_id, month, year)
    )
    res = c.fetchone()
    income = float(res[0]) if res and res[0] is not None else 0.0
    
    # Expense
    c.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = %s AND type = 'Saída' AND EXTRACT(MONTH FROM date) = %s AND EXTRACT(YEAR FROM date) = %s", 
        (user_id, month, year)
    )
    res = c.fetchone()
    expense = float(res[0]) if res and res[0] is not None else 0.0
    
    # Investment
    c.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = %s AND type = 'Investimento' AND EXTRACT(MONTH FROM date) = %s AND EXTRACT(YEAR FROM date) = %s", 
        (user_id, month, year)
    )
    res = c.fetchone()
    investment = float(res[0]) if res and res[0] is not None else 0.0
    
    conn.close()
    return income, expense, investment

def get_all_categories(user_id, type_filter):
    """Returns distinct categories used by user for a specific type."""
    conn = get_connection()
    if not conn: return []
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM transactions WHERE user_id = %s AND type = %s", (user_id, type_filter))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_portfolio_summary(user_id, as_of_date=None):
    """Returns total accumulated investments by category, optionally up to a specific date."""
    conn = get_connection()
    if not conn: return pd.DataFrame()
    
    query = """
        SELECT category, SUM(amount) as total
        FROM transactions 
        WHERE user_id = %s AND type = 'Investimento'
    """
    params = [user_id]
    
    if as_of_date:
        query += " AND date <= %s"
        params.append(as_of_date)
        
    query += " GROUP BY category ORDER BY total DESC"
    
    df = pd.read_sql_query(query, conn, params=tuple(params))
    conn.close()
    return df

def get_portfolio_evolution(user_id):
    """Returns monthly evolution of total investments."""
    conn = get_connection()
    if not conn: return pd.DataFrame()
    # Postgres TO_CHAR for date formatting
    df = pd.read_sql_query(
        """
        SELECT 
            TO_CHAR(date, 'YYYY-MM') as month,
            SUM(amount) as monthly_total
        FROM transactions 
        WHERE user_id = %s AND type = 'Investimento'
        GROUP BY month
        ORDER BY month
        """, 
        conn, 
        params=(user_id,)
    )
    conn.close()
    
    if not df.empty:
        df['cumulative_total'] = df['monthly_total'].cumsum()
    return df

def get_total_portfolio_value(user_id, as_of_date=None):
    """Returns total value of all investments, optionally up to a specific date."""
    conn = get_connection()
    if not conn: return 0.0
    c = conn.cursor()
    
    query = "SELECT SUM(amount) FROM transactions WHERE user_id = %s AND type = 'Investimento'"
    params = [user_id]
    
    if as_of_date:
        query += " AND date <= %s"
        params.append(as_of_date)
        
    c.execute(query, tuple(params))
    res = c.fetchone()
    total = float(res[0]) if res and res[0] is not None else 0.0
    conn.close()
    return total

def goal_exists_for_category(user_id, category):
    """Checks if a goal already exists for a specific category."""
    conn = get_connection()
    if not conn: return False
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM goals WHERE user_id = %s AND category_link = %s", (user_id, category))
    res = c.fetchone()
    conn.close()
    return res[0] > 0 if res else False

def create_auto_goal(user_id, category):
    """Creates an automatic goal for an investment category."""
    default_target = 10000.0
    goal_name = f"Meta: {category}"
    if not goal_exists_for_category(user_id, category):
        return create_goal(user_id, goal_name, default_target, category)
    return True

def get_ai_financial_context(user_id):
    """Consolidates complete financial data into a JSON-ready dictionary for AI analysis."""
    now = datetime.datetime.now()
    cur_month, cur_year = now.month, now.year
    prev_month = 12 if cur_month == 1 else cur_month - 1
    prev_year = cur_year - 1 if cur_month == 1 else cur_year

    cur_inc, cur_exp, cur_inv = get_monthly_summary(user_id, cur_month, cur_year)
    pre_inc, pre_exp, pre_inv = get_monthly_summary(user_id, prev_month, prev_year)

    conn = get_connection()
    if not conn: return {}
    
    # Postgres syntax for month/year filter
    categories_df = pd.read_sql_query(
        """
        SELECT category, SUM(amount) as total 
        FROM transactions 
        WHERE user_id = %s AND type = 'Saída' 
        AND EXTRACT(MONTH FROM date) = %s AND EXTRACT(YEAR FROM date) = %s
        GROUP BY category 
        ORDER BY total DESC
        """,
        conn, params=(user_id, cur_month, cur_year)
    )
    
    portfolio_df = get_portfolio_summary(user_id)
    goals_df = get_goals(user_id)
    conn.close()

    context = {
        "resumo_mensal_atual": {
            "mes": cur_month, "ano": cur_year,
            "receita_total": cur_inc,
            "despesa_total": cur_exp,
            "investimento_total": cur_inv,
            "saldo_liquido": cur_inc - cur_exp - cur_inv
        },
        "comparativo_mes_anterior": {
            "receita_variacao_pct": ((cur_inc / pre_inc - 1) * 100) if pre_inc > 0 else 0,
            "despesa_variacao_pct": ((cur_exp / pre_exp - 1) * 100) if pre_exp > 0 else 0
        },
        "maiores_gastos_categoria": categories_df.to_dict(orient='records'),
        "patrimonio": {
            "valor_total": get_total_portfolio_value(user_id),
            "composicao": portfolio_df.to_dict(orient='records')
        },
        "metas_ativas": goals_df.to_dict(orient='records')
    }
    return context
