import streamlit as st
from pathlib import Path
import auth

st.set_page_config(page_title="Finance Manager", layout="wide")

# --- Mantém login persistente mesmo após F5 ---
if "user" not in st.session_state:
    # Verifica se há parâmetro de usuário na URL
    params = st.query_params
    if "user" in params:
        st.session_state["user"] = params["user"]

# --- Controle de login ---
user = st.session_state.get("user")

# --- DEFINIR PÁGINAS VISÍVEIS ---
def get_pages():
    user = st.session_state.get("user")

    # Se o usuário não estiver logado
    if not user:
        return {
            "Account": [
                st.Page("auth.py", title="Login / Criar Conta", icon="🔐"),
            ],
        }

    # Se o usuário estiver logado
    return {
        "Dashboard": [
            st.Page("pages/1_view_db.py", title="Acessar Contas", icon="📊"),
            st.Page("pages/3_manage_banks.py", title="Gerenciar Contas", icon="🏦"),
            st.Page("pages/4_quick_actions.py", title="Registrar Movimentações", icon="⚡"),
        ],
        "Features": [
            st.Page("pages/2_simulate_investments.py", title="Simulador de Investimentos", icon="💡"),
        ],
        "Account": [
            st.Page("pages/5_account.py", title=f"{user}", icon="👤"),
        ],
    }

# --- CONFIGURA O MENU ---
pages = get_pages()
pg = st.navigation(pages)

# --- LÓGICA DE NAVEGAÇÃO ---
if not st.session_state.get("user"):
    # sem login → mostra o auth.py (login/criação)
    import auth
    auth.login_page()
else:
    # logado → executa página selecionada
    pg.run()
