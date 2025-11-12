# auth.py
import streamlit as st
import json
from pathlib import Path
import hashlib

USERS_FILE = Path("data/users.json")
DEFAULT_USER = "user_default"

# Garantir que o arquivo de usuários existe
USERS_FILE.parent.mkdir(exist_ok=True)
if not USERS_FILE.exists():
    USERS_FILE.write_text(json.dumps({DEFAULT_USER: {"password": "", "is_guest": True}}, indent=4))


def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


def load_users():
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)


def ensure_user_folder(username: str):
    import shutil

    base_folder = Path("data")
    user_folder = base_folder / "data_users" / username
    default_folder = base_folder / "data_users" / DEFAULT_USER

    user_folder.mkdir(parents=True, exist_ok=True)

    # Copiar arquivos padrão se não existirem
    if default_folder.exists():
        for file in default_folder.iterdir():
            dest = user_folder / file.name
            if not dest.exists():
                shutil.copy(file, dest)
    return user_folder


def login_page():
    st.title("🔐 Login")

    users = load_users()

    tab1, tab2 = st.tabs(["Entrar", "Criar conta"])

    with tab1:
        username = st.text_input("Usuário", key="login_user")
        password = st.text_input("Senha", type="password", key="login_pass")

        if st.button("Entrar"):
            if username in users and users[username]["password"] == hash_password(password):
                st.session_state["user"] = username
                ensure_user_folder(username)
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

        if st.button("Entrar como visitante"):
            st.session_state["user"] = DEFAULT_USER
            ensure_user_folder(DEFAULT_USER)
            st.rerun()

    with tab2:
        new_user = st.text_input("Novo usuário", key="new_user")
        new_pass = st.text_input("Senha", type="password", key="new_pass")
        if st.button("Criar conta"):
            if new_user in users:
                st.warning("Usuário já existe.")
            elif not new_user or not new_pass:
                st.warning("Preencha todos os campos.")
            else:
                users[new_user] = {"password": hash_password(new_pass), "is_guest": False}
                save_users(users)
                ensure_user_folder(new_user)
                st.success("Conta criada com sucesso! Faça login para continuar.")


def logout():
    """Faz logout e volta ao modo visitante"""
    st.session_state["user"] = DEFAULT_USER
    st.query_params["user"] = DEFAULT_USER  # ✅ salva na URL
    st.success("Logout realizado.")
    st.rerun()


def get_current_user():
    """Retorna o usuário logado ou 'user_default'."""
    if "user" not in st.session_state:
        st.session_state["user"] = DEFAULT_USER
        ensure_user_folder(DEFAULT_USER)
    return st.session_state["user"]
