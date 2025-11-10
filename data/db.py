import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "db.csv"
DATA_PATH.parent.mkdir(exist_ok=True)

COLUMNS = ["ID", "Tipo", "Nome", "Saldo", "Detalhes"]

def load_data():
    if not DATA_PATH.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(DATA_PATH)

def save_data(df: pd.DataFrame):
    df.to_csv(DATA_PATH, index=False)

def add_entry(tipo: str, nome: str, saldo: float, detalhes: str = ""):
    df = load_data()

    # Verifica duplicação (caso seja Banco)
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
    df = load_data()
    mask = (df["Nome"].str.lower() == nome.lower()) & (df["Tipo"] == tipo)
    if not any(mask):
        return False
    df.loc[mask, "Saldo"] += delta
    save_data(df)
    return True

def get_summary():
    df = load_data()
    total_bancos = df[df["Tipo"] == "Banco"]["Saldo"].sum()
    total_invest = df[df["Tipo"] == "Investimento"]["Saldo"].sum()
    total_geral = total_bancos + total_invest
    return total_bancos, total_invest, total_geral
