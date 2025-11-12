import streamlit as st
import json
from pathlib import Path
import hashlib
import shutil
import pandas as pd

# === Caminhos base ===
DATA_USERS_DIR = Path("data/data_users")
USERS_FILE = Path("data/users.json")

# --- Redireciona para login se a página for recarregada sem sessão ---
if "user" not in st.session_state or st.session_state["user"] is None:
    params = st.query_params
    if "user" in params:
        st.session_state["user"] = params["user"]
    else:
        st.switch_page("auth.py")  # substitua pelo caminho real da sua página de login

# === Funções auxiliares ===
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if USERS_FILE.exists():
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def load_user_data(username: str):
    """Carrega dados do db.csv do usuário logado."""
    user_dir = DATA_USERS_DIR / username
    db_path = user_dir / "db.csv"
    if db_path.exists():
        return pd.read_csv(db_path)
    return pd.DataFrame(columns=["ID", "Tipo", "Nome", "Saldo", "Detalhes"])

def logout():
    st.session_state["user"] = None
    st.success("Você saiu da conta com sucesso!")
    st.query_params.clear()  # ✅ limpa a URL com o novo método
    st.rerun()

# === Config inicial ===
st.set_page_config(page_title="Perfil", layout="centered")
st.markdown("<style>.stButton>button { width: 100%; }</style>", unsafe_allow_html=True)

user = st.session_state.get("user")

# --- login persistente (atualizado para API moderna) ---
# --- Persistência de login ---
params = st.query_params

# 1️⃣ Tentamos recuperar da sessão
user = st.session_state.get("user")

# 2️⃣ Se não tiver na sessão, buscamos na URL (query_params)
if not user and "user" in params:
    user = params["user"]
    st.session_state["user"] = user

# 3️⃣ Se ainda não tiver, buscamos no cache local
if not user:
    user = st.session_state.get("cached_user")
    if user:
        st.session_state["user"] = user

# 4️⃣ Sempre que houver usuário logado, salvamos no cache
if user:
    st.session_state["cached_user"] = user
    st.query_params["user"] = user


# === Título e avatar ===
st.title("👤 Meu Perfil")

if not user:
    st.error("Nenhum usuário logado.")
    st.stop()

st.markdown(f"### Bem-vindo, **{user}** 👋")

# === Resumo do usuário ===
st.divider()
st.subheader("📊 Resumo Financeiro")

df = load_user_data(user)
if not df.empty:
    total_bancos = df[df["Tipo"] == "Banco"]["Saldo"].sum()
    total_inv = df[df["Tipo"] == "Investimento"]["Saldo"].sum()
    total = total_bancos + total_inv

    col1, col2, col3 = st.columns(3)
    col1.metric("💳 Bancos", f"R$ {total_bancos:,.2f}")
    col2.metric("📈 Investimentos", f"R$ {total_inv:,.2f}")
    col3.metric("💰 Total", f"R$ {total:,.2f}")
else:
    st.info("Nenhum dado financeiro encontrado.")

# === Alterar credenciais ===
st.divider()
st.subheader("🔐 Alterar login e senha")

users = load_users()
current_user = users.get(user, {})

with st.form("form_alterar"):
    new_username = st.text_input("Novo nome de usuário", value=user)
    new_password = st.text_input("Nova senha", type="password", placeholder="Deixe em branco para manter")
    confirm_password = st.text_input("Confirmar nova senha", type="password", placeholder="Repita a senha (se alterou)")
    submitted = st.form_submit_button("Salvar alterações")

    if submitted:
        if new_password and new_password != confirm_password:
            st.error("As senhas não coincidem.")
        else:
            # Atualiza credenciais
            users.pop(user, None)
            users[new_username] = {
                "password": hash_password(new_password or current_user.get("password", "")),
                "is_guest": "false",
            }

            # Renomeia a pasta de dados, se o nome mudou
            old_path = DATA_USERS_DIR / user
            new_path = DATA_USERS_DIR / new_username
            if old_path.exists() and user != new_username:
                old_path.rename(new_path)

            save_users(users)
            st.session_state["user"] = new_username
            st.query_params["user"] = new_username
            st.success("✅ Dados atualizados com sucesso! Recarregue a página para aplicar.")
            logout()

# === Excluir conta ===
st.divider()
st.subheader("🗑️ Excluir conta")

if st.button("Excluir minha conta", type="secondary"):
    st.warning("⚠️ Esta ação é irreversível. Deseja realmente excluir?")
    if st.button("❌ Confirmar exclusão", type="primary"):
        users.pop(user, None)
        save_users(users)
        user_path = DATA_USERS_DIR / user
        if user_path.exists():
            shutil.rmtree(user_path)
        st.session_state["user"] = None
        st.query_params.clear()  # ✅ limpa a URL
        st.success("Conta excluída com sucesso.")
        st.rerun()

# === Logout ===
st.divider()
st.subheader("🚪 Logout")

if st.button("Sair da conta"):
    logout()
