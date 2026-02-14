import sqlite3
import pandas as pd
import datetime
import hashlib

DB_NAME = "finanflow.db"

def init_db():
    """Initializes the SQLite database with users and transactions tables."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Create Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create Goals Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            category_link TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create Admin User if not exists
    admin_email = "admin@finanflow.com"
    # Note: In production, use a proper hashing library. For simplicity here demonstrating concept.
    # We will use passlib in auth.py, but for the seed we can use a simple hash or handled in auth.
    
    conn.commit()
    conn.close()

def run_query(query, params=(), return_data=False):
    """Helper function to run SQL queries."""
    conn = sqlite3.connect(DB_NAME)
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
        conn.close()
        return str(e)

def get_users_df():
    """Returns a pandas DataFrame of all users."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

def get_transactions_df(user_id):
    """Returns a pandas DataFrame of transactions for a specific user."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM transactions WHERE user_id = ?", conn, params=(user_id,))
    conn.close()
    return df

def add_transaction(user_id, date, type, category, amount, description):
    """Adds a new transaction."""
    return run_query(
        "INSERT INTO transactions (user_id, date, type, category, amount, description) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, date, type, category, amount, description)
    )

def update_transaction(transaction_id, date, type, category, amount, description):
    """Updates an existing transaction."""
    return run_query(
        "UPDATE transactions SET date=?, type=?, category=?, amount=?, description=? WHERE id=?",
        (date, type, category, amount, description, transaction_id)
    )

def delete_transaction(transaction_id):
    """Deletes a transaction."""
    return run_query("DELETE FROM transactions WHERE id = ?", (transaction_id,))

def create_goal(user_id, name, target, category):
    """Creates a new investment goal."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO goals (user_id, name, target_amount, category_link) VALUES (?, ?, ?, ?)", (user_id, name, target, category))
    conn.commit()
    conn.close()
    return True

def update_goal_target(user_id, category, new_target):
    """Updates the target amount for a specific category goal."""
    conn = sqlite3.connect(DB_NAME)
    # Check if goal exists
    exists = conn.execute("SELECT id FROM goals WHERE user_id = ? AND category_link = ?", (user_id, category)).fetchone()
    if exists:
        conn.execute("UPDATE goals SET target_amount = ? WHERE user_id = ? AND category_link = ?", (new_target, user_id, category))
    else:
        # Create if doesn't exist
        conn.execute("INSERT INTO goals (user_id, name, target_amount, category_link) VALUES (?, ?, ?, ?)", 
                     (user_id, f"Meta: {category}", new_target, category))
    conn.commit()
    conn.close()
    return True

def delete_goal(goal_id):
    return run_query("DELETE FROM goals WHERE id = ?", (goal_id,))

def get_goals(user_id):
    """Returns list of goals for user."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM goals WHERE user_id = ?", conn, params=(user_id,))
    conn.close()
    return df

def get_goal_progress(user_id, category_link):
    """Calculates total invested in a specific category."""
    conn = sqlite3.connect(DB_NAME)
    # SUM all 'Investimento' type transactions that match the category
    total = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'Investimento' AND category = ?", 
        (user_id, category_link)
    ).fetchone()[0] or 0.0
    conn.close()
    return total

def get_monthly_summary(user_id, month, year):
    """Calculates totals for a specific month."""
    # SQLite DATE is string YYYY-MM-DD
    # Filter by month/year string matching
    date_str = f"{year}-{month:02d}-%"
    conn = sqlite3.connect(DB_NAME)
    
    # Total Income
    income = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'Entrada' AND date LIKE ?", 
        (user_id, date_str)
    ).fetchone()[0] or 0.0
    
    # Total Expense
    expense = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'Saída' AND date LIKE ?", 
        (user_id, date_str)
    ).fetchone()[0] or 0.0
    
    # Total Investment
    investment = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'Investimento' AND date LIKE ?", 
        (user_id, date_str)
    ).fetchone()[0] or 0.0
    
    conn.close()
    return income, expense, investment

def get_all_categories(user_id, type_filter):
    """Returns distinct categories used by user for a specific type."""
    conn = sqlite3.connect(DB_NAME)
    rows = conn.execute("SELECT DISTINCT category FROM transactions WHERE user_id = ? AND type = ?", (user_id, type_filter)).fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_portfolio_summary(user_id):
    """Returns total accumulated investments by category."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(
        """
        SELECT category, SUM(amount) as total
        FROM transactions 
        WHERE user_id = ? AND type = 'Investimento'
        GROUP BY category
        ORDER BY total DESC
        """, 
        conn, 
        params=(user_id,)
    )
    conn.close()
    return df

def get_portfolio_evolution(user_id):
    """Returns monthly evolution of total investments."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(
        """
        SELECT 
            strftime('%Y-%m', date) as month,
            SUM(amount) as monthly_total
        FROM transactions 
        WHERE user_id = ? AND type = 'Investimento'
        GROUP BY month
        ORDER BY month
        """, 
        conn, 
        params=(user_id,)
    )
    conn.close()
    
    # Calculate cumulative sum
    if not df.empty:
        df['cumulative_total'] = df['monthly_total'].cumsum()
    
    return df

def get_total_portfolio_value(user_id):
    """Returns total value of all investments."""
    conn = sqlite3.connect(DB_NAME)
    total = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'Investimento'", 
        (user_id,)
    ).fetchone()[0] or 0.0
    conn.close()
    return total

def goal_exists_for_category(user_id, category):
    """Checks if a goal already exists for a specific category."""
    conn = sqlite3.connect(DB_NAME)
    result = conn.execute(
        "SELECT COUNT(*) FROM goals WHERE user_id = ? AND category_link = ?",
        (user_id, category)
    ).fetchone()[0]
    conn.close()
    return result > 0

def create_auto_goal(user_id, category):
    """Creates an automatic goal for an investment category."""
    # Default target amount for auto-created goals
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

    # Current vs Previous Month Summaries
    cur_inc, cur_exp, cur_inv = get_monthly_summary(user_id, cur_month, cur_year)
    pre_inc, pre_exp, pre_inv = get_monthly_summary(user_id, prev_month, prev_year)

    # Categories Breakdown (Current Month)
    conn = sqlite3.connect(DB_NAME)
    date_str = f"{cur_year}-{cur_month:02d}%"
    categories_df = pd.read_sql_query(
        "SELECT category, SUM(amount) as total FROM transactions WHERE user_id = ? AND type = 'Saída' AND date LIKE ? GROUP BY category ORDER BY total DESC",
        conn, params=(user_id, date_str)
    )
    
    # Portfolio and Goals
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
