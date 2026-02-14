import streamlit as st
import database as db
import bcrypt

def hash_password(password):
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verifies a password against a hash."""
    try:
        # Ensure hashed is bytes
        if isinstance(hashed, str):
            hashed = hashed.encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    except Exception:
        return False

def check_login(email, password):
    """Verifies email and password. Returns user dict if successful, None otherwise."""
    users = db.run_query("SELECT id, email, password_hash, role, status FROM users WHERE email = ?", (email,), return_data=True)
    
    if users:
        user = users[0]
        # user structure: (id, email, password_hash, role, status)
        stored_hash = user[2]
        
        if verify_password(password, stored_hash):
            return {
                "id": user[0],
                "email": user[1],
                "role": user[3],
                "status": user[4]
            }
    
    # Check for admin (Credentials from secrets)
    try:
        admin_email = st.secrets["general"]["admin_email"]
        admin_pass = st.secrets["general"]["admin_password"]
    except FileNotFoundError:
        # Fallback for local dev without secrets.toml (though we just created it)
        admin_email = "admin@finanflow.com" 
        admin_pass = "admin@123"

    if email == admin_email and password == admin_pass:
        # Ensure admin exists in DB
        existing = db.run_query("SELECT * FROM users WHERE email = ?", (email,), return_data=True)
        if not existing:
             db.run_query("INSERT INTO users (email, password_hash, role, status) VALUES (?, ?, ?, ?)", 
                          (email, hash_password(password), 'admin', 'active'))
        return {"id": 0, "email": email, "role": "admin", "status": "active"}
        
    return None

def register_user(email, password):
    """Registers a new user with 'pending' status."""
    existing = db.run_query("SELECT * FROM users WHERE email = ?", (email,), return_data=True)
    if existing:
        return False, "E-mail já cadastrado."
    
    hashed = hash_password(password)
    result = db.run_query("INSERT INTO users (email, password_hash, role, status) VALUES (?, ?, ?, ?)", 
                          (email, hashed, 'user', 'pending'))
    
    if result is True:
        return True, "Cadastro realizado! Aguarde aprovação do administrador."
    else:
        return False, f"Erro ao cadastrar: {result}"

def require_auth():
    """Checks if user is logged in, else shows login screen."""
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        login_page()
        return False
    return True

def login_page():
    st.title("🔐 FinanFlow - Login")
    
    tab1, tab2 = st.tabs(["Login", "Registrar"])
    
    with tab1:
        email = st.text_input("E-mail", key="login_email")
        password = st.text_input("Senha", type="password", key="login_password")
        
        if st.button("Entrar"):
            user = check_login(email, password)
            if user:
                if user['status'] != 'active':
                    st.error("Sua conta ainda não foi aprovada pelo administrador.")
                else:
                    st.session_state.user = user
                    st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")

    with tab2:
        new_email = st.text_input("E-mail", key="reg_email")
        new_pass = st.text_input("Senha", type="password", key="reg_pass")
        confirm_pass = st.text_input("Confirmar Senha", type="password", key="reg_confirm")
        
        if st.button("Criar Conta"):
            if new_pass != confirm_pass:
                st.error("As senhas não coincidem.")
            elif len(new_pass) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                success, msg = register_user(new_email, new_pass)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
