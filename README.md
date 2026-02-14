# 💰 FinanFlow

Sistema completo de gestão financeira pessoal desenvolvido com Streamlit.

## 🚀 Funcionalidades

- **📝 Registros Financeiros**: Controle completo de entradas, saídas e investimentos
- **📊 Dashboard Analítico**: Visualizações interativas dos seus dados financeiros
- **🎯 Metas de Investimento**: Defina e acompanhe suas metas financeiras
- **💼 Portfólio**: Visualize a evolução e distribuição dos seus investimentos
- **🤖 Assistente IA**: Análise inteligente das suas finanças (em desenvolvimento)

## 📦 Tecnologias

- Python 3.8+
- Streamlit
- Pandas
- Plotly
- SQLite
- Bcrypt

## 🔧 Instalação Local

1. Clone o repositório:
```bash
git clone <seu-repositorio>
cd FinanFlow
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure os secrets (crie o arquivo `.streamlit/secrets.toml`):
```toml
[general]
admin_email = "admin@finanflow.com"
admin_password = "admin@123"
db_name = "finanflow.db"
```

4. Execute a aplicação:
```bash
streamlit run main.py
```

## 🌐 Deploy no Streamlit Cloud

A aplicação está configurada para deploy automático no Streamlit Community Cloud.

### Pré-requisitos:
- Conta no GitHub
- Conta no Streamlit Cloud (gratuita)

### Passos:
1. Faça push do código para um repositório GitHub
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Conecte seu repositório
4. Configure os secrets no painel do Streamlit Cloud
5. Deploy automático!

## 🔐 Segurança

- Senhas criptografadas com bcrypt
- Secrets gerenciados via Streamlit Secrets
- Banco de dados SQLite local

## 📱 Responsividade

Interface totalmente responsiva, otimizada para desktop e mobile.

## 📄 Licença

Projeto pessoal - Todos os direitos reservados.
