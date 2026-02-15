import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import database as db
import auth
import json
import time
from streamlit_option_menu import option_menu
from streamlit_extras.metric_cards import style_metric_cards

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Page Config
st.set_page_config(
    page_title="Clan Financeiro - Gestão Inteligente",
    page_icon="🛡️",
    layout="wide"
)

# Initialize Database
if "db_initialized" not in st.session_state:
    db.init_db()
    st.session_state.db_initialized = True

# --- Styles ---
def local_css():
    st.markdown("""
    <style>
        /* Modern Fintech Theme - Premium Overhaul */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;600;700&display=swap');
        
        :root {
            --primary: #10b981; /* Emerald Green */
            --primary-dark: #059669;
            --secondary: #0f172a; /* Deep Navy */
            --bg-main: #f8fafc;
            --text-main: #0f172a;
            --text-light: #64748b;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }

        /* Essential Streamlit Overrides for Desktop */
        .main .block-container {
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        * {
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3, .metric-value {
            font-family: 'Outfit', sans-serif;
            letter-spacing: -0.02em;
        }

        .main {
            background-color: var(--background);
        }
        
        /* Modern Glass/Elevated KPI Cards */
        .metric-card {
            background: var(--surface);
            padding: 1.75rem;
            border-radius: 20px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .metric-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
            border-color: var(--primary);
        }
        
        .metric-label {
            color: var(--text-muted);
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 1rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        
        .metric-value {
            color: var(--text-main);
            font-size: 1.6rem;
            font-weight: 700;
            line-height: 1.1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .metric-delta {
            font-size: 0.8rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 4px;
            margin-top: 1rem;
            padding: 4px 10px;
            border-radius: 8px;
            width: fit-content;
        }
        
        .delta-up { background-color: #dcfce7; color: #15803d; }
        .delta-down { background-color: #fee2e2; color: #b91c1c; }
        
        /* Containers */
        .section-card {
            background-color: var(--surface);
            padding: 2.5rem;
            border-radius: 24px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
            margin-bottom: 2rem;
        }
        
        .insight-card {
            background-color: var(--surface);
            padding: 1.5rem;
            border-radius: 16px;
            border: 1px solid var(--border);
            border-left: 6px solid var(--primary);
            margin-bottom: 1.25rem;
            box-shadow: var(--shadow-sm);
            transition: transform 0.2s;
        }

        .insight-card:hover {
            transform: scale(1.01);
        }

        /* Buttons */
        .stButton>button {
            border-radius: 12px;
            padding: 0.6rem 2rem;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            border: none;
            font-weight: 600;
            box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);
            transition: all 0.2s ease;
        }
        
        .stButton>button:hover {
            box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.4);
            transform: translateY(-1px);
        }

        /* Sidebar Styling - Premium Look */
        [data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #e2e8f0 !important;
            box-shadow: 2px 0 10px rgba(0,0,0,0.02);
        }
        
        /* Ensure sidebar content is always visible */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            padding-top: 2rem;
        }

        /* Menu Link Styling */
        [data-testid="stSidebar"] .nav-link {
            color: #0f172a !important; /* Deeper navy */
            background-color: transparent !important;
        }

        [data-testid="stSidebar"] .nav-link .nav-link-text {
            color: #0f172a !important;
        }

        /* Active Item Style */
        [data-testid="stSidebar"] .nav-link.active {
            background-color: var(--primary) !important;
            color: white !important;
        }
        
        [data-testid="stSidebar"] .nav-link.active .nav-link-text {
            color: white !important;
        }

        /* Hide Streamlit components for cleaner UI */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Responsive */
        @media (max-width: 768px) {
            .main .block-container { padding-left: 1rem; padding-right: 1rem; }
            .metric-value { font-size: 1.5rem; }
            .metric-card { padding: 1.25rem; }
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- KPI Components ---
def render_kpi_card(label, value, delta=None, icon="💰", sparkline_data=None, show_delta=True, is_currency=True, color_theme="primary"):
    delta_html = ""
    # Theme colors
    colors = {
        "primary": "#10b981", # Emerald Green
        "success": "#10b981",
        "danger": "#ef4444",
        "warning": "#f59e0b",
        "info": "#0ea5e9"
    }
    card_color = colors.get(color_theme, colors["primary"])
    # Only show delta if show_delta is True and delta is non-zero
    if show_delta and delta is not None and abs(delta) > 0.001:
        delta_class = "delta-up" if delta >= 0 else "delta-down"
        delta_icon = "↑" if delta >= 0 else "↓"
        delta_html = f'<div class="metric-delta {delta_class}">{delta_icon} {abs(delta):.1f}% <span style="opacity: 0.7; font-weight: 400; font-size: 0.7rem; margin-left: 2px;">vs ant.</span></div>'
    
    value_display = f'<span style="font-size: 1rem; opacity: 0.8; margin-right: 4px;">R$</span>{value:,.2f}' if is_currency else f"{int(value)}"
    
    # Minified HTML to avoid rendering issues with whitespace
    html = (
        f'<div class="metric-card" style="border-left: 4px solid {card_color}; transition: all 0.3s ease;">'
        f'<div style="display: flex; flex-direction: column; height: 100%;">'
        f'<div class="metric-label" style="display: flex; align-items: center; gap: 8px;">'
        f'<span style="font-size: 1.2rem;">{icon}</span><span style="font-weight: 500;">{label}</span>'
        f'</div>'
        f'<div class="metric-value" style="color: {card_color if not is_currency else "#0f172a"}; font-size: 1.6rem; font-weight: 700;">{value_display}</div>'
        f'{delta_html}'
        f'</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    
    if sparkline_data is not None and not sparkline_data.empty:
        fig = px.line(sparkline_data, x=sparkline_data.index, y=sparkline_data.columns[0], 
                      color_discrete_sequence=['#3b82f6' if delta >= 0 else '#ef4444'])
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=40,
            xaxis_visible=False,
            yaxis_visible=False,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            hovermode=False
        )
        st.plotly_chart(fig, config={'displayModeBar': False}, use_container_width=True)

# --- Helper Functions ---
def get_month_year_filter(key_suffix=""):
    col1, col2 = st.columns(2)
    with col1:
        meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 
                 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
        mes_atual = datetime.datetime.now().month
        selected_mes_name = st.selectbox("Mês", list(meses.values()), index=mes_atual-1, key=f"sel_mes{key_suffix}")
        selected_mes = list(meses.keys())[list(meses.values()).index(selected_mes_name)]
    with col2:
        ano_atual = datetime.datetime.now().year
        selected_ano = st.number_input("Ano", min_value=2020, max_value=2030, value=ano_atual, key=f"sel_ano{key_suffix}")
    
    return selected_mes, selected_ano

# --- Dialogs ---
@st.dialog("Editar Transação")
def edit_transaction_dialog(row):
    # Safe date conversion
    try:
        if isinstance(row['date'], str):
            d_val = datetime.datetime.strptime(row['date'], "%Y-%m-%d").date()
        else:
            d_val = row['date'].date()
    except:
        d_val = datetime.date.today()

    new_date = st.date_input("Data", value=d_val)
    
    # Type selection
    types = ["Entrada", "Saída", "Investimento"]
    new_type = st.selectbox("Tipo", types, index=types.index(row['type']), key="edit_type")
    
    # Dynamic Categories Logic for Edit Dialog
    defaults = {
        "Entrada": ["Salário", "Freelance", "Reembolso", "Presente"],
        "Saída": ["Alimentação", "Transporte", "Moradia", "Lazer", "Saúde", "Educação"],
        "Investimento": ["Reserva de Emergência", "Ações", "Fundos Imobiliários", "CDB", "Tesouro Direto", "Crypto"]
    }
    
    # Get current categories for the selected type
    user_id = st.session_state.user['id']
    existing = db.get_all_categories(user_id, new_type)
    options = sorted(list(set(defaults.get(new_type, []) + existing)))
    
    # Ensure current category is in options if type hasn't changed
    if row['category'] not in options:
        options.append(row['category'])
    options = sorted(list(set(options)))
    options.append("➕ Nova Categoria...")
    
    # Set default index for category
    try:
        cat_index = options.index(row['category']) if new_type == row['type'] else 0
    except:
        cat_index = 0

    sel_cat = st.selectbox("Categoria", options, index=cat_index, key="edit_category")
    
    if sel_cat == "➕ Nova Categoria...":
        final_category = st.text_input("Digite o nome da categoria", key="edit_new_cat")
    else:
        final_category = sel_cat

    new_amount = st.number_input("Valor", value=float(row['amount']), min_value=0.01)
    new_desc = st.text_input("Descrição", value=row['description'])
    
    if st.button("Salvar Alterações", use_container_width=True):
        if sel_cat == "➕ Nova Categoria..." and not final_category:
            st.error("Digite o nome da categoria")
        else:
            db.update_transaction(row['id'], new_date, new_type, final_category, new_amount, new_desc)
            st.success("Atualizado!")
            st.rerun()

@st.dialog("Confirmar Exclusão")
def confirm_delete_transaction(transaction_id):
    st.warning("⚠️ Tem certeza que deseja excluir esta transação?")
    st.caption("Esta ação não pode ser desfeita.")
    
    col1, col2 = st.columns(2)
    if col1.button("✅ Sim, excluir", type="primary"):
        db.delete_transaction(transaction_id)
        st.success("Transação excluída!")
        st.rerun()
    if col2.button("❌ Cancelar"):
        st.rerun()

@st.dialog("Confirmar Exclusão")
def confirm_delete_goal(goal_id):
    st.warning("⚠️ Tem certeza que deseja excluir esta meta?")
    st.caption("Esta ação não pode ser desfeita.")
    
    col1, col2 = st.columns(2)
    if col1.button("✅ Sim, excluir", type="primary"):
        db.delete_goal(goal_id)
        st.success("Meta excluída!")
        st.rerun()
    if col2.button("❌ Cancelar"):
        st.rerun()

# --- Tab Functions ---
def tab_registros(user):
    st.subheader("📝 Registros Financeiros")
    
    # Filter
    mes, ano = get_month_year_filter()
    
    # Summary Cards
    income, expense, investment = db.get_monthly_summary(user['id'], mes, ano)
    balance = income - expense - investment
    
    # Responsive cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("Ganhos", income, icon="💰", show_delta=False)
    with c2:
        render_kpi_card("Gastos", expense, icon="📉", show_delta=False) # Delta removed as requested
    with c3:
        render_kpi_card("Investimentos", investment, icon="🏦", show_delta=False)
    with c4:
        render_kpi_card("Saldo", balance, icon="⚖️", show_delta=False)
    
    st.divider()
    
    # New Register Form
    with st.expander("➕ Novo Registro", expanded=True):
        # Type selection OUTSIDE form for dynamic filtering
        r_type = st.selectbox("Tipo", ["Selecione...", "Entrada", "Saída", "Investimento"], index=0, key="transaction_type")
        
        # Segmented Categories Logic - only show if type is selected
        defaults = {
            "Entrada": ["Salário", "Freelance", "Reembolso", "Presente"],
            "Saída": ["Alimentação", "Transporte", "Moradia", "Lazer", "Saúde", "Educação"],
            "Investimento": ["Reserva de Emergência", "Ações", "Fundos Imobiliários", "CDB", "Tesouro Direto", "Crypto"]
        }
        
        # Show category selection based on type
        if r_type != "Selecione...":
            existing = db.get_all_categories(user['id'], r_type)
            options = sorted(list(set(defaults.get(r_type, []) + existing)))
            options.insert(0, "Selecione...")  # Add default option
            options.append("➕ Nova Categoria...")
            
            sel_cat = st.selectbox("Categoria", options, key="transaction_category")
            
            if sel_cat == "➕ Nova Categoria...":
                new_category = st.text_input("Digite o nome da nova categoria", key="new_category_input")
            else:
                new_category = None
        else:
            st.info("👆 Selecione um tipo de transação para ver as categorias disponíveis")
            sel_cat = None
            new_category = None
        
        st.divider()
        
        # Rest of the form INSIDE st.form
        with st.form("new_transaction_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            
            default_date = datetime.date(ano, mes, 1)
            next_month = default_date.replace(day=28) + datetime.timedelta(days=4)
            last_day = next_month - datetime.timedelta(days=next_month.day)
            
            r_date = c1.date_input("Data", value=default_date, min_value=default_date, max_value=last_day)
            r_amount = c2.number_input("Valor (R$)", min_value=0.01, format="%.2f")
            
            r_desc = st.text_input("Descrição", placeholder="Opcional")
            
            # Form submit button
            submitted = st.form_submit_button("💾 Salvar Registro", use_container_width=True)
            
            if submitted:
                # Validate type selection
                if r_type == "Selecione...":
                    st.error("⚠️ Selecione um tipo de transação.")
                elif sel_cat == "Selecione..." or sel_cat is None:
                    st.error("⚠️ Selecione uma categoria.")
                elif sel_cat == "➕ Nova Categoria..." and not new_category:
                    st.error("⚠️ Digite o nome da nova categoria.")
                else:
                    # Determine final category
                    final_category = new_category if sel_cat == "➕ Nova Categoria..." else sel_cat
                    
                    # Add transaction
                    db.add_transaction(user['id'], r_date, r_type, final_category, r_amount, r_desc)
                    
                    # Auto-create goal if it's an investment
                    if r_type == "Investimento":
                        db.create_auto_goal(user['id'], final_category)
                        st.success(f"✅ Investimento registrado! Meta automática criada para '{final_category}'")
                    else:
                        st.success("✅ Registro salvo com sucesso!")
                    
                    st.rerun()



    # History Table
    st.subheader("Histórico do Mês")
    
    df = db.get_transactions_df(user['id'])
    
    if not df.empty:
        # CSV Export
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Relatório (CSV)",
            data=csv,
            file_name=f"finanflow_relatorio_{datetime.date.today()}.csv",
            mime="text/csv",
        )
        
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'].dt.month == mes) & (df['date'].dt.year == ano)
        filtered_df = df[mask]
        
        if filtered_df.empty:
            st.info("Nenhum registro neste mês.")
        else:
            # Responsive Card View
            for idx, row in filtered_df.iterrows():
                with st.container():
                    st.markdown('<div class="insight-card" style="border-left-width: 0; padding: 1rem; margin-bottom: 0.5rem;">', unsafe_allow_html=True)
                    # Flex-like layout using columns with specific weights
                    col_info, col_actions = st.columns([6, 1], gap="small")
                    
                    with col_info:
                        # Top row: Date and Category
                        c_date, c_cat = st.columns([1, 4])
                        c_date.caption(row['date'].strftime('%d/%m'))
                        
                        color = "green" if row['type'] == 'Entrada' else "red" if row['type'] == 'Saída' else "blue"
                        c_cat.markdown(f"**{row['category']}** :{color}[ (R$ {row['amount']:.2f})]")
                        
                        # Bottom row: Description
                        if row['description']:
                            st.caption(f"📝 {row['description']}")
                    
                    with col_actions:
                         # Buttons side by side or stacked based on mobile
                         b1, b2 = st.columns(2)
                         if b1.button("✏️", key=f"ed_{row['id']}", help="Editar"):
                             edit_transaction_dialog(row)
                         if b2.button("🗑️", key=f"del_{row['id']}", help="Excluir"):
                             confirm_delete_transaction(row['id'])
                    st.markdown('</div>', unsafe_allow_html=True)

def tab_dashboard(user):
    st.markdown("### 📊 Dashboard Estratégico")
    
    df_all = db.get_transactions_df(user['id'])
    if df_all.empty:
        st.info("Sem dados para exibir. Comece adicionando seus registros!")
        return
        
    df_all['date'] = pd.to_datetime(df_all['date'])
    
    # Período Selection
    c_filter1, c_filter2 = st.columns([1, 2])
    with c_filter1:
        time_filter = st.selectbox("Período:", ["Mês", "Todo o Período"], label_visibility="collapsed")
    
    if time_filter == "Mês":
        with c_filter2:
            mes, ano = get_month_year_filter()
        mask = (df_all['date'].dt.month == mes) & (df_all['date'].dt.year == ano)
        df_chart = df_all[mask]
        
        # Data for previous month (to calculate variation)
        prev_mes = 12 if mes == 1 else mes - 1
        prev_ano = ano - 1 if mes == 1 else ano
        mask_prev = (df_all['date'].dt.month == prev_mes) & (df_all['date'].dt.year == prev_ano)
        df_prev = df_all[mask_prev]
    else:
        df_chart = df_all
        df_prev = pd.DataFrame()

    def calc_totals(df):
        if df.empty: return 0.0, 0.0, 0.0, 0.0
        income = df[df['type'] == 'Entrada']['amount'].sum()
        expense = df[df['type'] == 'Saída']['amount'].sum()
        invest = df[df['type'] == 'Investimento']['amount'].sum()
        balance = income - expense - invest
        return income, expense, invest, balance

    cur_inc, cur_exp, cur_inv, cur_bal = calc_totals(df_chart)
    pre_inc, pre_exp, pre_inv, pre_bal = calc_totals(df_prev)
    
    def get_delta(cur, pre):
        if pre == 0: return 0.0
        return ((cur - pre) / pre) * 100
        
    # KPIs
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    with kpi_col1:
        render_kpi_card("Receita", cur_inc, get_delta(cur_inc, pre_inc), "📈")
    with kpi_col2:
        render_kpi_card("Despesas", cur_exp, get_delta(cur_exp, pre_exp), "📉")
    with kpi_col3:
        render_kpi_card("Investimentos", cur_inv, get_delta(cur_inv, pre_inv), "🏦")
    with kpi_col4:
        render_kpi_card("Saldo Líquido", cur_bal, get_delta(cur_bal, pre_bal), "⚖️")

    st.write("") 

    col_main, col_cat = st.columns([2, 1.2], gap="large")
    
    with col_main:
        st.subheader("Fluxo de Caixa e Tendência")
        
        df_daily = df_chart.copy()
        df_daily['date_day'] = df_daily['date'].dt.strftime('%d/%m')
        
        daily_pivot = df_daily.pivot_table(index='date_day', columns='type', values='amount', aggfunc='sum').fillna(0)
        for col in ['Entrada', 'Saída', 'Investimento']:
            if col not in daily_pivot.columns: daily_pivot[col] = 0
            
        daily_pivot['Saldo'] = daily_pivot['Entrada'] - daily_pivot['Saída'] - daily_pivot['Investimento']
        daily_pivot['Saldo Acumulado'] = daily_pivot['Saldo'].cumsum()
        
        import plotly.graph_objects as go
        fig_combined = go.Figure()
        fig_combined.add_trace(go.Bar(x=daily_pivot.index, y=daily_pivot['Entrada'], name='Receita', marker_color='#10b981'))
        fig_combined.add_trace(go.Bar(x=daily_pivot.index, y=daily_pivot['Saída'], name='Despesa', marker_color='#ef4444'))
        fig_combined.add_trace(go.Scatter(x=daily_pivot.index, y=daily_pivot['Saldo Acumulado'], name='Saldo Acum.', 
                                        line=dict(color='#3b82f6', width=3), yaxis='y2'))
        
        fig_combined.update_layout(
            yaxis=dict(title="Valores (R$)"),
            yaxis2=dict(title="Acumulado (R$)", overlaying='y', side='right'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=30, b=0),
            hovermode="x unified",
            height=400,
            template="plotly_white"
        )
        st.plotly_chart(fig_combined, use_container_width=True)


    with col_cat:
        st.subheader("Despesas por Categoria")
        expenses = df_chart[df_chart['type'] == 'Saída'].groupby('category')['amount'].sum().reset_index()
        if not expenses.empty:
            expenses = expenses.sort_values(by='amount', ascending=False)
            fig_donut = px.pie(expenses, values='amount', names='category', hole=0.6,
                              color_discrete_sequence=px.colors.sequential.RdBu)
            fig_donut.update_layout(
                showlegend=True,
                margin=dict(l=0, r=0, t=0, b=0),
                height=350,
                annotations=[dict(text=f'Total Gastos<br>R$ {cur_exp:,.2f}', x=0.5, y=0.5, font_size=12, showarrow=False)]
            )
        st.plotly_chart(fig_donut, use_container_width=True)


    st.markdown("### 💡 Insights Financeiros")
    i_col1, i_col2, i_col3 = st.columns(3)
    
    with i_col1:
        savings_rate = (cur_inv / cur_inc * 100) if cur_inc > 0 else 0
        st.markdown(f"""<div class="insight-card"><b>Taxa de Investimento</b><br>Você investiu {savings_rate:.1f}% da sua renda no período.</div>""", unsafe_allow_html=True)
        
    with i_col2:
        if not expenses.empty:
            top_cat = expenses.iloc[0]['category']
            top_perc = (expenses.iloc[0]['amount'] / cur_exp * 100)
            st.markdown(f"""<div class="insight-card" style="border-left-color: #ef4444;"><b>Perfil de Gasto</b><br>'{top_cat}' representa {top_perc:.1f}% das despesas.</div>""", unsafe_allow_html=True)
            
    with i_col3:
        status = "saudável" if cur_bal > 0 else "crítico"
        color = "#10b981" if cur_bal > 0 else "#ef4444"
        st.markdown(f"""<div class="insight-card" style="border-left-color: {color};"><b>Fluxo de Caixa</b><br>Seu saldo está {status}.</div>""", unsafe_allow_html=True)

@st.dialog("Resgate de Investimento")
def redemption_dialog(user_id, category, current_balance):
    st.write(f"Você está resgatando de: **{category}**")
    st.write(f"Saldo disponível: **R$ {current_balance:,.2f}**")
    
    c1, c2 = st.columns(2)
    amount_to_redeem = c1.number_input("Valor do Resgate", min_value=0.01, max_value=current_balance, value=current_balance, step=100.0)
    reason = c2.text_input("Motivo do Resgate", placeholder="Ex: Emergência, Oportunidade...")
    
    st.info("💡 O valor será abatido do investimento e voltará para seu saldo disponível.")
    
    if st.button("Confirmar Resgate Real", use_container_width=True):
        if not reason:
            st.error("⚠️ Por favor, informe o motivo do resgate.")
            return
            
        hoje = datetime.date.today()
        # The description will explicitly store the reason
        final_description = f"Resgate: {reason}"
        
        success = db.add_transaction(
            user_id, 
            hoje, 
            'Investimento', 
            category, 
            -amount_to_redeem, 
            final_description
        )
        
        if success is True:
            st.success(f"✅ Resgate de R$ {amount_to_redeem:,.2f} realizado!")
            st.balloons()
            # Adding a small sleep to ensure user sees success before rerun
            import time
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"Erro: {success}")

def tab_investimentos(user):
    st.markdown("### 🎯 Gestão de Investimentos")
    
    # 1. Filtros de Período (Igual ao Dashboard)
    c_filter1, c_filter2 = st.columns([1, 2])
    with c_filter1:
        time_filter = st.selectbox("Período Invest.:", ["Mês", "Todo o Período"], label_visibility="collapsed", key="inv_time_filter")
    
    df_all = db.get_transactions_df(user['id'])
    df_all['date'] = pd.to_datetime(df_all['date'])
    
    if time_filter == "Mês":
        with c_filter2:
            mes, ano = get_month_year_filter(key_suffix="_inv")
        mask = (df_all['date'].dt.month == mes) & (df_all['date'].dt.year == ano)
        df_filtered = df_all[mask]
        
        # Labels for comparison (if we want to add deltas later)
        prev_mes = 12 if mes == 1 else mes - 1
        prev_ano = ano - 1 if mes == 1 else ano
        mask_prev = (df_all['date'].dt.month == prev_mes) & (df_all['date'].dt.year == prev_ano)
        df_prev = df_all[mask_prev]
    else:
        df_filtered = df_all
        df_prev = pd.DataFrame()

    # Get portfolio summaries based on FILTERED data for the view, 
    # but actual balance calculation usually needs ALL data (cumulative)
    # The user asked to see "what happened in the month". 
    # Let's show KPIs of "Aportes" and "Resgates" in the month, while keeping "Total" as cumulative.
    
    def get_period_stats(df):
        if df.empty: return 0.0, 0.0
        inv_df = df[df['type'] == 'Investimento']
        aportes = inv_df[inv_df['amount'] > 0]['amount'].sum()
        resgates = abs(inv_df[inv_df['amount'] < 0]['amount'].sum())
        return aportes, resgates

    as_of_date = None
    label_patrimonio = "Patrimônio Total"
    if time_filter == "Mês":
        # Get last day of the selected month
        import calendar
        last_day = calendar.monthrange(ano, mes)[1]
        as_of_date = f"{ano}-{mes:02d}-{last_day}"
        label_patrimonio = f"Patrimônio em {calendar.month_name[mes][:3].capitalize()}/{ano % 100}"
    
    aportes_mes, resgates_mes = get_period_stats(df_filtered)
    # Get portfolio value UP TO the selected date (with fallback for sync issues)
    try:
        total_patrimonio = db.get_total_portfolio_value(user['id'], as_of_date)
    except TypeError:
        total_patrimonio = db.get_total_portfolio_value(user['id'])
    
    # Mapping for simulated liquidity profiles
    liquidity_profiles = {
        "Reserva de Emergência": {"term": "D+0", "type": "Pós-fixado", "perf": 10.5, "color": "#10b981", "status": "Disponível"},
        "CDB": {"term": "D+0", "type": "CDB Pós", "perf": 11.2, "color": "#10b981", "status": "Disponível"},
        "Tesouro Direto": {"term": "D+1", "type": "Tesouro Selic", "perf": 10.8, "color": "#3b82f6", "status": "Disponível"},
        "Ações": {"term": "D+2", "type": "Renda Variável", "perf": 14.2, "color": "#f59e0b", "status": "Disponível"},
        "Fundos Imobiliários": {"term": "D+2", "type": "FIIs", "perf": 9.5, "color": "#f59e0b", "status": "Disponível"},
        "Crypto": {"term": "D+0", "type": "Altcoins", "perf": 45.0, "color": "#10b981", "status": "Disponível"},
        "Default": {"term": "D+30+", "type": "Outros", "perf": 8.0, "color": "#ef4444", "status": "Em Carência"}
    }

    t1, t2 = st.tabs(["🛡️ Patrimônio e Liquidez", "📊 Análise de Portfólio"])
    
    # Fetch goals to display progress
    goals_df = db.get_goals(user['id'])
    # Convert goals to dictionary for easy lookup: {category: target_amount}
    goals_dict = dict(zip(goals_df['category_link'], goals_df['target_amount']))

    # For the table and category cards, we ALSO use as_of_date (with fallback)
    try:
        portfolio_df = db.get_portfolio_summary(user['id'], as_of_date)
    except TypeError:
        portfolio_df = db.get_portfolio_summary(user['id'])

    with t1:
        if total_patrimonio <= 0 and aportes_mes == 0:
            st.info("📊 Selecione um período com movimentações ou adicione novos investimentos.")
        else:
            # Prepare liquidity data from the SNAPSHOT balance
            def get_profile(cat):
                return liquidity_profiles.get(cat, liquidity_profiles["Default"])
            
            portfolio_df['term'] = portfolio_df['category'].apply(lambda x: get_profile(x)['term'])
            portfolio_df['status'] = portfolio_df['category'].apply(lambda x: get_profile(x)['status'])
            portfolio_df['color'] = portfolio_df['category'].apply(lambda x: get_profile(x)['color'])
            
            # Liquidity & Period KPIs
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                render_kpi_card(label_patrimonio, total_patrimonio, 0, "💰")
            with k2:
                render_kpi_card(f"Aportes ({time_filter})", aportes_mes, 0, "📥")
            with k3:
                render_kpi_card(f"Resgates ({time_filter})", resgates_mes, 0, "📤")
            with k4:
                # Available (D+0) as of that date
                d0_total = portfolio_df[portfolio_df['term'] == 'D+0']['total'].sum()
                render_kpi_card(f"Disponível ({'D+0'})", d0_total, 0, "⚡")

            st.write("")
            
            # Asset Availability Table (Full Width)
            st.subheader("Disponibilidade e Resgate")
            
            for _, row in portfolio_df.iterrows():
                prof = get_profile(row['category'])
                if row['total'] <= 0.01: continue
                
                target = goals_dict.get(row['category'], 0.0)
                progress = min(row['total'] / target, 1.0) if target > 0 else 0.0
                
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    
                    # Asset & Progress
                    col1.write(f"**{row['category']}**")
                    col1.caption(prof['type'])
                    if target > 0:
                        prog_color = "green" if progress >= 1.0 else "blue"
                        col1.progress(progress)
                        col1.caption(f":{prog_color}[**{progress*100:.1f}% da meta (R$ {target:,.0f})**]")
                    else:
                        col1.caption("🏁 Nenhuma meta definida")
                    
                    # Value & Liquidity
                    col2.write(f"R$ {row['total']:,.2f}")
                    badge_html = f'<span style="background-color: {prof["color"]}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem;">{prof["term"]}</span>'
                    col2.markdown(badge_html, unsafe_allow_html=True)
                    
                    # Actions: Goal & Redemption
                    with col3:
                        with st.popover("🎯 Meta"):
                            new_target = st.number_input("Definir Alvo (R$)", value=float(target), step=1000.0, key=f"target_{row['category']}")
                            if st.button("Salvar Meta", key=f"btn_target_{row['category']}", use_container_width=True):
                                db.update_goal_target(user['id'], row['category'], new_target)
                                st.success("Meta salva!")
                                st.rerun()

                    if prof['status'] == "Disponível":
                        if col4.button("Resgatar", key=f"res_{row['category']}"):
                            redemption_dialog(user['id'], row['category'], row['total'])
                    else:
                        col4.write("🔒 Bloqueado")


            # Investment History - FILTERED by period
            st.write("")
            st.subheader(f"⌛ Movimentações - {time_filter}")
            
            # Using df_filtered which respects the selected month/all period
            inv_history = df_filtered[df_filtered['type'] == 'Investimento'].sort_values('date', ascending=False)
            
            if inv_history.empty:
                st.caption(f"Nenhuma movimentação de investimento em {time_filter.lower()}.")
            else:
                for _, row in inv_history.iterrows():
                    c1, c2, c3 = st.columns([1, 3, 2])
                    date_obj = pd.to_datetime(row['date'])
                    c1.caption(date_obj.strftime('%d/%m/%y'))
                    c2.write(f"**{row['category']}**")
                    # Transparently show the reason/description
                    desc = row['description'] if row['description'] else "Aporte"
                    c2.caption(f"Nota: {desc}")
                    
                    color = "green" if row['amount'] < 0 else "blue" 
                    label = "Resgate" if row['amount'] < 0 else "Aporte"
                    c3.markdown(f":{color}[**{label}: R$ {abs(row['amount']):,.2f}**]")


    with t2:
        # Análise logic (Existing evolution + summary)
        if total_patrimonio > 0:
            st.metric("💰 Patrimônio Total", f"R$ {total_patrimonio:,.2f}")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🥧 Composição")
                fig_pie = px.pie(portfolio_df, values='total', names='category', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                evolution_df = db.get_portfolio_evolution(user['id'])
                if not evolution_df.empty:
                    st.subheader("📈 Evolução")
                    fig_line = px.line(evolution_df, x='month', y='cumulative_total', markers=True)
                    st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Sem dados para análise.")

def tab_ia(user):
    st.markdown("### 🤖 FinanBot - Consultor Estratégico")
    
    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Olá! Sou o FinanBot. Analisei seus dados e estou pronto para ajudar você a otimizar suas finanças. O que gostaria de saber?"}
        ]

    # Sidebar / Toolbar for Chat
    col_chat1, col_chat2 = st.columns([5, 1])
    with col_chat2:
        if st.button("🗑️ Limpar", use_container_width=True, help="Limpar histórico da conversa"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Histórico limpo! Como posso ajudar agora?"}
            ]
            st.rerun()

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Quick Suggestions (Auto-stacks on mobile)
    st.write("")
    q_col1, q_col2, q_col3 = st.columns([1,1,1])
    with q_col1:
        q1 = st.button("📉 Onde economizar?", use_container_width=True)
    with q_col2:
        q2 = st.button("🏦 Como investir?", use_container_width=True)
    with q_col3:
        q3 = st.button("📊 Análise do mês", use_container_width=True)
    
    selected_suggestion = None
    if q1: selected_suggestion = "Analise meus gastos deste mês e me diga onde posso economizar pelo menos 10%."
    if q2: selected_suggestion = "Com base no meu saldo e metas, qual a melhor estratégia de investimento agora?"
    if q3: selected_suggestion = "Faça um resumo executivo da minha saúde financeira comparando com o mês passado."

    # Chat input
    prompt = st.chat_input("Perqunte sobre seus gastos, investimentos ou peça uma dica...")
    if selected_suggestion:
        prompt = selected_suggestion

    if prompt:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get context
        context = db.get_ai_financial_context(user['id'])
        
        # Prepare AI response
        with st.chat_message("assistant"):
            if genai is None:
                st.error("Erro: Biblioteca 'google-generativeai' não instalada.")
                return

            try:
                # Configuration from secrets
                if "GEMINI_API_KEY" not in st.secrets:
                    st.warning("⚠️ Chave GEMINI_API_KEY não configurada nos Secrets.")
                    return
                    
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                
                # Model Fallback Logic - Favoring stable free models
                # gemini-1.5-flash-8b is the best choice for free tier quotas
                available_models = ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-pro']
                last_error = "Nenhum modelo disponível respondeu."
                success_ai = False
                
                with st.status("🤖 FinanBot está analisando seus dados...", expanded=True) as status:
                    for model_name in available_models:
                        try:
                            model = genai.GenerativeModel(model_name)
                            
                            # Context Injection
                            system_prompt = f"""
                            Você é o FinanBot, um consultor financeiro brasileiro.
                            DADOS DO USUÁRIO EM JSON:
                            {json.dumps(context, indent=2, ensure_ascii=False)}
                            
                            REGRAS:
                            1. Analise os gastos e identifique categorias críticas.
                            2. Sugira economia onde houver aumento no mês.
                            3. Responda em Português (Brasil) com tom profissional.
                            4. Use Markdown (listas, negrito).
                            """
                            
                            # Simple completion instead of chat for faster response
                            response = model.generate_content(f"{system_prompt}\n\nPERGUNTA: {prompt}")
                            
                            if response and response.text:
                                full_response = response.text
                                status.update(label="✅ Análise concluída!", state="complete", expanded=False)
                                st.markdown(full_response)
                                # Add assistant response to history
                                st.session_state.messages.append({"role": "assistant", "content": full_response})
                                success_ai = True
                                break 
                        except Exception as inner_e:
                            last_error = str(inner_e)
                            # Silently continue to next model to avoid cluterring the UI with quote errors
                            continue 
                    
                    if not success_ai:
                        status.update(label="❌ Falha na análise", state="error", expanded=True)
                        st.error(f"Não foi possível obter resposta de nenhum modelo da IA.\n\nÚltimo erro: {last_error}")
                        st.session_state.messages.append({"role": "assistant", "content": f"Erro técnico: {last_error}"})
                    # st.rerun() removed to avoid flashing/reset issues

            except Exception as e:
                error_msg = f"Ocorreu um erro na IA: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})


# --- Main App Logic ---
def main():
    if not auth.require_auth():
        return

    user = st.session_state.user
    
    # Sidebar
    with st.sidebar:
        # User ID for uniqueness
        user_email = user['email']
        
        # New Logo: Clan Financeiro
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 25px; border-radius: 16px; margin-bottom: 1.5rem; text-align: center; border: 1px solid rgba(16, 185, 129, 0.2);">
                <div style="background: #10b981; width: 50px; height: 50px; border-radius: 12px; margin: 0 auto 15px auto; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(16, 185, 129, 0.4);">
                    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        <path d="M12 8v4"/>
                        <path d="M12 16h.01"/>
                    </svg>
                </div>
                <div style="color: white; font-family: 'Outfit', sans-serif; font-weight: 700; font-size: 1.4rem; letter-spacing: -0.5px;">Clan Financeiro</div>
                <div style="color: #10b981; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; margin-top: 4px;">Gestão de Elite</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.write(f"💼 **Membro:** {user_email}")
        st.markdown("---")
            
        # Navigation
        if user['role'] == 'admin':
            menu_options = ["Dashboard Admin"]
            icons = ["speedometer2"]
        else:
            menu_options = ["Registros", "Dashboard", "Investimentos", "Assistente IA"]
            icons = ["list-task", "graph-up", "piggy-bank", "robot"]
            
        selected = option_menu(
            menu_title=None,
            options=menu_options,
            icons=icons,
            menu_icon="cast",
            default_index=0,
            styles={
                "nav-link-selected": {"background-color": "#10b981"},
                "nav-link": {"font-family": "Inter", "font-weight": "500"}
            }
        )

        # Logout at bottom
        st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
        if st.button("🚪 Encerrar Sessão", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Routing
    if user['role'] == 'admin':
        if selected == "Dashboard Admin":
            admin_dashboard()
        elif selected == "Gestão de Usuários":
            admin_users()
    else:
        if selected == "Registros":
            tab_registros(user)
        elif selected == "Dashboard":
            tab_dashboard(user)
        elif selected == "Investimentos":
            tab_investimentos(user)
        elif selected == "Assistente IA":
            tab_ia(user)

# --- Admin Pages ---
def admin_dashboard():
    # Hero Section
    st.markdown("""
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 2rem; border-radius: 20px; color: white; margin-bottom: 2rem; box-shadow: var(--shadow-lg);">
            <div style="display: flex; align-items: center; gap: 15px;">
                <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 12px;">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                </div>
                <div>
                    <h1 style="margin: 0; color: white; font-family: 'Outfit', sans-serif; font-size: 1.8rem;">Central do Administrador</h1>
                    <p style="opacity: 0.8; margin: 5px 0 0 0;">Gestão de segurança e controle de acessos da plataforma.</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    users = db.get_users_df()
    
    if users.empty:
        st.error("📊 Nenhum usuário encontrado no banco de dados.")
        st.info("Isso acontece quando o aplicativo não consegue se conectar ao banco Neon.")
        return

    # Tabs for Organization
    tab_overview, tab_management = st.tabs(["🌍 Visão Geral", "👤 Gestão de Usuários"])

    with tab_overview:
        c1, c2, c3 = st.columns(3)
        with c1:
            render_kpi_card("Total Usuários", len(users), icon="👥", is_currency=False, color_theme="info")
        with c2:
            active_count = len(users[users['status'] == 'active']) if 'status' in users.columns else 0
            render_kpi_card("Ativos", active_count, icon="✅", is_currency=False, color_theme="success")
        with c3:
            pending_count = len(users[users['status'] == 'pending']) if 'status' in users.columns else 0
            render_kpi_card("Pendentes", pending_count, icon="⏳", is_currency=False, color_theme="warning")

        st.markdown("---")
        st.subheader("📊 Atividade Recente")
        
        try:
            # Fetch last 5 transactions across all users for admin
            recent_tx = db.run_query("""
                SELECT t.date, u.email, t.description, t.amount, t.type 
                FROM transactions t 
                JOIN users u ON t.user_id = u.id 
                ORDER BY t.date DESC LIMIT 5
            """, return_data=True)
            
            if recent_tx and isinstance(recent_tx, list):
                for tx in recent_tx:
                    color = "#10b981" if tx[4] == 'Receita' else "#ef4444"
                    st.markdown(f"""
                        <div style="padding: 10px; border-radius: 8px; border-left: 4px solid {color}; background: white; margin-bottom: 5px; font-size: 0.9rem;">
                            <span style="color: #64748b;">{tx[0]}</span> | 
                            <b>{tx[1]}</b>: {tx[2]} - 
                            <span style="color: {color}; font-weight: 600;">R$ {tx[3]:,.2f}</span>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma atividade recente registrada no clã.")
        except Exception as e:
            st.warning(f"Não foi possível carregar as atividades: {e}")

    with tab_management:
        # Filters Section
        st.markdown("#### 🔍 Filtros de Busca")
        cf1, cf2 = st.columns([2, 1])
        with cf1:
            search = st.text_input("Buscar por e-mail", placeholder="ex: usuario@gmail.com", key="search_user")
        with cf2:
            status_filter = st.selectbox("Filtrar por Status", ["Todos", "active", "pending", "blocked"], index=0)

        # Apply Filters
        filtered_users = users.copy()
        if search:
            filtered_users = filtered_users[filtered_users['email'].str.contains(search, case=False)]
        if status_filter != "Todos":
            filtered_users = filtered_users[filtered_users['status'] == status_filter]

        # Display Dataframe
        st.markdown(f"Exibindo **{len(filtered_users)}** usuários")
        
        for index, row in filtered_users.iterrows():
            with st.container():
                # Premium User Row
                status_color = "#10b981" if row['status'] == 'active' else "#f59e0b" if row['status'] == 'pending' else "#ef4444"
                
                c_data, c_actions = st.columns([3, 2])
                with c_data:
                    st.markdown(f"""
                        <div style="padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; background: white; margin-bottom: 10px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 10px; height: 10px; border-radius: 50%; background: {status_color};"></div>
                                <span style="font-weight: 600; color: #0f172a;">{row['email']}</span>
                                <span style="font-size: 0.75rem; background: #f1f5f9; padding: 2px 8px; border-radius: 10px; color: #64748b;">{row['role'].upper()}</span>
                            </div>
                            <div style="font-size: 0.8rem; color: #64748b; margin-top: 5px; margin-left: 20px;">
                                ID: {row['id']} • Criado em: {row['created_at']}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with c_actions:
                    btn_cols = st.columns([1, 1, 1])
                    
                    # Access Period Input
                    with st.popover("📅 Acesso", use_container_width=True):
                        dias = st.number_input("Dias de Acesso", min_value=1, max_value=365, value=30, key=f"days_{row['id']}")
                        if st.button("Confirmar Prazo", key=f"set_exp_{row['id']}"):
                            from datetime import datetime, timedelta
                            new_expiry = datetime.now() + timedelta(days=dias)
                            db.run_query("UPDATE users SET expiry_date = %s WHERE id = %s", (new_expiry, row['id']))
                            st.success(f"Expira em: {new_expiry.strftime('%d/%m/%Y')}")
                            st.rerun()

                    with btn_cols[0]:
                        if row['status'] == 'pending':
                            if st.button("✅", key=f"app_{row['id']}", help="Aprovar"):
                                db.run_query("UPDATE users SET status = 'active' WHERE id = %s", (row['id'],))
                                st.rerun()
                        elif row['status'] == 'active':
                            if st.button("🚫", key=f"blk_{row['id']}", help="Bloquear"):
                                db.run_query("UPDATE users SET status = 'blocked' WHERE id = %s", (row['id'],))
                                st.rerun()
                        else:
                            if st.button("🔓", key=f"unblk_{row['id']}", help="Ativar"):
                                db.run_query("UPDATE users SET status = 'active' WHERE id = %s", (row['id'],))
                                st.rerun()
                    
                    with btn_cols[1]:
                        if row['role'] != 'admin':
                            if st.button("⭐", key=f"promo_{row['id']}", help="Promover"):
                                db.run_query("UPDATE users SET role = 'admin' WHERE id = %s", (row['id'],))
                                st.rerun()
                    
                    with btn_cols[2]:
                        if st.button("🗑️", key=f"del_{row['id']}", help="Excluir"):
                            if row['email'] != st.session_state.user['email']:
                                db.run_query("DELETE FROM users WHERE id = %s", (row['id'],))
                                st.rerun()

if __name__ == "__main__":
    main()
