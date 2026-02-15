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
    # First check for regular user in DB
    try:
        result = db.run_query("SELECT id, email, password_hash, role, status, expiry_date FROM users WHERE email = %s", (email,), return_data=True)
        
        if isinstance(result, list) and len(result) > 0:
            user = result[0]
            # Check if we have password_hash (index 2)
            if len(user) >= 3:
                stored_hash = user[2]
                if verify_password(password, stored_hash):
                    # Check Expiration (index 5)
                    expiry = user[5]
                    from datetime import datetime
                    if expiry and datetime.now() > expiry:
                        # Auto-block if expired
                        db.run_query("UPDATE users SET status = 'blocked' WHERE id = %s", (user[0],))
                        return {"status": "expired"}
                    
                    return {
                        "id": user[0],
                        "email": user[1],
                        "role": user[3] if len(user) > 3 else 'user',
                        "status": user[4] if len(user) > 4 else 'active'
                    }
        elif isinstance(result, str):
            st.sidebar.error(f"Erro no Banco: {result}")
    except Exception as e:
        st.sidebar.error(f"Erro de processamento: {e}")
    
    # Check for admin (Credentials from secrets)
    try:
        admin_email = st.secrets["general"]["admin_email"]
        admin_pass = st.secrets["general"]["admin_password"]
    except Exception:
        # Fallback for local dev without secrets.toml
        admin_email = "admin@finanflow.com" 
        admin_pass = "admin@123"

    if email == admin_email and password == admin_pass:
        # Ensure admin exists in DB
        existing = db.run_query("SELECT * FROM users WHERE email = %s", (email,), return_data=True)
        if not existing or isinstance(existing, str):
             db.run_query("INSERT INTO users (email, password_hash, role, status) VALUES (%s, %s, %s, %s)", 
                          (email, hash_password(password), 'admin', 'active'))
        return {"id": 0, "email": email, "role": "admin", "status": "active"}
        
    return None

def register_user(email, password):
    """Registers a new user with 'pending' status."""
    existing = db.run_query("SELECT * FROM users WHERE email = %s", (email,), return_data=True)
    if existing and not isinstance(existing, str):
        return False, "E-mail já cadastrado."
    
    hashed = hash_password(password)
    result = db.run_query("INSERT INTO users (email, password_hash, role, status) VALUES (%s, %s, %s, %s)", 
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
    # Inject Custom CSS for Premium Login
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700&display=swap');
        
        /* Gradient Background */
        .stApp {
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%) !important;
        }

        /* Center Card Container */
        .login-card {
            background: white;
            padding: 2.5rem;
            border-radius: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            max-width: 450px;
            margin: 2rem auto;
            border: 1px solid #e2e8f0;
        }

        /* Input Styling */
        .stTextInput > div > div > input {
            padding: 12px 16px !important;
            border-radius: 10px !important;
            border: 1px solid #cbd5e1 !important;
            background-color: #f8fafc !important;
        }

        /* Full Width Buttons */
        .stButton > button {
            width: 100% !important;
            padding: 12px !important;
            border-radius: 10px !important;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            color: white !important;
            font-weight: 600 !important;
            border: none !important;
        }

        /* Branding Text */
        .brand-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: #0f172a;
            margin-top: 15px;
            letter-spacing: -1px;
        }
        
        .brand-subtitle {
            font-size: 0.9rem;
            color: #10b981;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: 700;
            margin-bottom: 25px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Centering via columns
    empty_col_l, main_col, empty_col_r = st.columns([1, 2, 1])
    
    with main_col:
        # Card Starts
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="background: #10b981; width: 60px; height: 60px; border-radius: 16px; margin: 0 auto; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);">
                    <svg width="35" height="35" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        <path d="M12 8v4"/>
                        <path d="M12 16h.01"/>
                    </svg>
                </div>
                <div class="brand-title">FinanFlow</div>
                <div class="brand-subtitle">Gestão Inteligente</div>
            </div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🔐 Entrar", "✨ Registrar"])
        
        with tab1:
            email = st.text_input("E-mail", key="login_email")
            password = st.text_input("Senha", type="password", key="login_password")
            
            if st.button("Acessar Conta", use_container_width=True):
                user = check_login(email, password)
                if user:
                    if isinstance(user, dict) and user.get("status") == "expired":
                        st.error("🚫 Seu acesso expirou. Entre em contato com o administrador.")
                    elif user['status'] != 'active':
                        st.error("Sua conta ainda não foi aprovada pelo administrador ou está bloqueada.")
                    else:
                        st.session_state.user = user
                        st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")

        with tab2:
            new_email = st.text_input("E-mail", key="reg_email")
            new_pass = st.text_input("Senha", type="password", key="reg_pass")
            confirm_pass = st.text_input("Confirmar Senha", type="password", key="reg_confirm")
            
            if st.button("Criar Minha Conta", use_container_width=True):
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
