# data/db.py
import pandas as pd
from pathlib import Path
import streamlit as st
from auth import get_current_user, ensure_user_folder

COLUMNS = ["ID", "Tipo", "Nome", "Saldo", "Detalhes"]

def get_user_data_path() -> Path:
    """Retorna o caminho da pasta de dados do usuário atual."""
    user = get_current_user()
    user_folder = ensure_user_folder(user)
    data_path = user_folder / "db.csv"
    return data_path


def load_data() -> pd.DataFrame:
    """Carrega o arquivo db.csv do usuário atual."""
    data_path = get_user_data_path()
    if not data_path.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(data_path)


def save_data(df: pd.DataFrame):
    """Salva o arquivo db.csv no diretório do usuário."""
    data_path = get_user_data_path()
    df.to_csv(data_path, index=False)


def add_entry(tipo: str, nome: str, saldo: float, detalhes: str = ""):
    """Adiciona uma nova conta ao db.csv do usuário."""
    df = load_data()

    # Evitar duplicação de bancos
    if tipo == "Banco":
        duplicado = df[(df["Tipo"] == "Banco") & (df["Nome"].str.lower() == nome.lower())]
        if not duplicado.empty:
            return {"duplicado": True, "df": df}

    new_id = 1 if df.empty else df["ID"].max() + 1
    novo = pd.DataFrame([{
        "ID": new_id,
        "Tipo": tipo,
        "Nome": nome,
        "Saldo": saldo,
        "Detalhes": detalhes
    }])

    df = pd.concat([df, novo], ignore_index=True)
    save_data(df)
    return {"duplicado": False}


def update_balance(nome: str, tipo: str, delta: float):
    """Atualiza o saldo de uma conta."""
    df = load_data()
    mask = (df["Nome"].str.lower() == nome.lower()) & (df["Tipo"] == tipo)
    if not any(mask):
        return False
    df.loc[mask, "Saldo"] += delta
    save_data(df)
    return True


def get_summary():
    """Retorna o resumo de saldos do usuário atual."""
    df = load_data()
    total_bancos = df[df["Tipo"] == "Banco"]["Saldo"].sum()
    total_invest = df[df["Tipo"] == "Investimento"]["Saldo"].sum()
    total_geral = total_bancos + total_invest
    return total_bancos, total_invest, total_geral
