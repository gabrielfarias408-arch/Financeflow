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
    page_title="FinanFlow",
    page_icon="💰",
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
        /* Modern Fintech Theme */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {
            font-family: 'Inter', sans-serif;
        }

        .main {
            background-color: #f8fafc;
        }
        
        /* KPI Cards */
        .metric-card {
            background-color: white;
            padding: 1.25rem;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .metric-label {
            color: #64748b;
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        
        .metric-value {
            color: #1e293b;
            font-size: 1.5rem;
            font-weight: 700;
        }
        
        .metric-delta {
            font-size: 0.75rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 4px;
            margin-top: 0.25rem;
        }
        
        .delta-up { color: #10b981; }
        .delta-down { color: #ef4444; }
        
        /* Section Containers */
        .section-card {
            background-color: white;
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            margin-bottom: 1rem;
        }
        
        .insight-card {
            background-color: #f1f5f9;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
            margin-bottom: 0.75rem;
        }

        .stButton>button {
            width: 100%;
            border-radius: 8px;
            height: 3em;
            background-color: #3b82f6;
            color: white;
            border: none;
            font-weight: 600;
            transition: 0.3s;
        }
        
        .stButton>button:hover {
            background-color: #2563eb;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }

        /* Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 16px;
            background-color: #f1f5f9;
            border: none;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important;
            color: white !important;
        }

        /* --- Responsiveness & Mobile Tweaks --- */
        @media (max-width: 768px) {
            .metric-value {
                font-size: 1.1rem;
            }
            .metric-card {
                padding: 0.75rem;
                min-height: 100px;
            }
            .section-card {
                padding: 1rem;
            }
            /* Make plotly charts shorter on mobile */
            iframe {
                max-height: 250px !important;
            }
            /* Chat icons adjustments for mobile */
            [data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {
                width: 32px !important;
                height: 32px !important;
            }
        }

        /* Optimization for better touch targets */
        button {
            min-height: 44px;
        }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- KPI Components ---
def render_kpi_card(label, value, delta, icon, sparkline_data=None):
    delta_class = "delta-up" if delta >= 0 else "delta-down"
    delta_icon = "↑" if delta >= 0 else "↓"
    
    html = f"""
    <div class="metric-card">
        <div style="display: flex; flex-direction: column; gap: 4px;">
            <div class="metric-label" style="display: flex; align-items: center; gap: 4px;">
                <span>{icon}</span> <span>{label}</span>
            </div>
            <div class="metric-value">R$ {value:,.2f}</div>
            <div class="metric-delta {delta_class}" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {delta_icon} {abs(delta):.1f}% <span style="color: #94a3b8; font-weight: 400; font-size: 0.7rem;">vs ant.</span>
            </div>
        </div>
    </div>
    """
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
    c1.metric("Ganhos", f"R$ {income:,.2f}")
    c2.metric("Gastos", f"R$ {expense:,.2f}", delta=-expense if expense > 0 else 0)
    c3.metric("Investimentos", f"R$ {investment:,.2f}")
    c4.metric("Saldo", f"R$ {balance:,.2f}")
    style_metric_cards()
    
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
                with st.container(border=True):
                    # Flex-like layout using columns with specific weights
                    col_info, col_actions = st.columns([4, 1])
                    
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

    col_main, col_cat = st.columns([2, 1])
    
    with col_main:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)

    with col_cat:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
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
        else:
            st.info("Nenhuma despesa para exibir.")
        st.markdown('</div>', unsafe_allow_html=True)

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

    aportes_mes, resgates_mes = get_period_stats(df_filtered)
    total_patrimonio = db.get_total_portfolio_value(user['id']) # Always cumulative
    
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

    # For the table and category cards, we use actual current balance (cumulative)
    portfolio_df = db.get_portfolio_summary(user['id'])

    with t1:
        if total_patrimonio <= 0 and aportes_mes == 0:
            st.info("📊 Selecione um período com movimentações ou adicione novos investimentos.")
        else:
            # Prepare liquidity data from CURRENT balance
            def get_profile(cat):
                return liquidity_profiles.get(cat, liquidity_profiles["Default"])
            
            portfolio_df['term'] = portfolio_df['category'].apply(lambda x: get_profile(x)['term'])
            portfolio_df['status'] = portfolio_df['category'].apply(lambda x: get_profile(x)['status'])
            portfolio_df['color'] = portfolio_df['category'].apply(lambda x: get_profile(x)['color'])
            
            # Liquidity & Period KPIs
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                render_kpi_card("Patrimônio Total", total_patrimonio, 0, "💰")
            with k2:
                render_kpi_card(f"Aportes {time_filter}", aportes_mes, 0, "📥")
            with k3:
                render_kpi_card(f"Resgates {time_filter}", resgates_mes, 0, "📤")
            with k4:
                # Available (D+0) is always current
                d0_total = portfolio_df[portfolio_df['term'] == 'D+0']['total'].sum()
                render_kpi_card("Disponível (D+0)", d0_total, 0, "⚡")

            st.write("")
            
            # Asset Availability Table (Full Width)
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

            # Investment History - FILTERED by period
            st.write("")
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

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
                
                # Model Fallback Logic - Using validated models from diagnostic
                available_models = ['gemini-2.0-flash', 'gemini-flash-latest', 'gemini-pro-latest', 'gemini-2.0-flash-lite']
                last_error = "Nenhum modelo disponível respondeu."
                success_ai = False
                
                with st.status("🤖 FinanBot está analisando seus dados...", expanded=True) as status:
                    for model_name in available_models:
                        try:
                            st.write(f"Tentando conexão com {model_name}...")
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
                            st.warning(f"Erro com {model_name}: {last_error[:100]}...")
                            continue # Try next model
                    
                    if not success_ai:
                        status.update(label="❌ Falha na análise", state="error", expanded=True)
                        st.error(f"Não foi possível obter resposta de nenhum modelo da IA.\n\nÚltimo erro: {last_error}")
                        st.session_state.messages.append({"role": "assistant", "content": f"Erro técnico: {last_error}"})
                    else:
                        st.rerun()

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
        st.image("https://cdn-icons-png.flaticon.com/512/2482/2482522.png", width=100)
        st.write(f"Olá, **{user['email']}**")
        if st.button("Sair"):
            st.session_state.user = None
            st.rerun()
            
        # Navigation
        if user['role'] == 'admin':
            menu_options = ["Dashboard Admin", "Gestão de Usuários"]
            icons = ["speedometer2", "people"]
        else:
            menu_options = ["Registros", "Dashboard", "Investimentos", "Assistente IA"]
            icons = ["list-task", "graph-up", "piggy-bank", "robot"]
            
        selected = option_menu(
            menu_title="Menu Principal",
            options=menu_options,
            icons=icons,
            menu_icon="cast",
            default_index=0,
            styles={
                "nav-link-selected": {"background-color": "#0099ff"},
            }
        )

    # Routing
    if user['role'] == 'admin':
        if selected == "Dashboard Admin":
            admin_dashboard()
        elif selected == "Gestão de Usuários":
            admin_users()
    else:
        if selected == "Dashboard":
            tab_dashboard(user)
        elif selected == "Registros":
            tab_registros(user)
        elif selected == "Investimentos":
            tab_investimentos(user)
        elif selected == "Assistente IA":
            tab_ia(user)

# --- Admin Pages ---
def admin_dashboard():
    st.title("Painel do Administrador")
    users = db.get_users_df()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Usuários", len(users))
    c2.metric("Ativos", len(users[users['status'] == 'active']))
    c3.metric("Pendentes", len(users[users['status'] == 'pending']))
    style_metric_cards()

def admin_users():
    st.title("Gestão de Licenças")
    users = db.get_users_df()
    
    for index, row in users.iterrows():
        with st.expander(f"{row['email']} - STATUS: {row['status'].upper()}", expanded=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"**ID:** {row['id']} | **Role:** {row['role']} | **Criado em:** {row['created_at']}")
            with c2:
                if row['status'] == 'pending':
                    if st.button("✅ Aprovar", key=f"app_{row['id']}"):
                        db.run_query("UPDATE users SET status = 'active' WHERE id = ?", (row['id'],))
                        st.rerun()
                elif row['status'] == 'active':
                    if st.button("🚫 Bloquear", key=f"blk_{row['id']}"):
                        db.run_query("UPDATE users SET status = 'blocked' WHERE id = ?", (row['id'],))
                        st.rerun()
                elif row['status'] == 'blocked':
                    if st.button("🔓 Desbloquear", key=f"unblk_{row['id']}"):
                        db.run_query("UPDATE users SET status = 'active' WHERE id = ?", (row['id'],))
                        st.rerun()

if __name__ == "__main__":
    main()
