import streamlit as st
import pandas as pd
import plotly.express as px
from data.db import load_data, get_summary
from pathlib import Path
from datetime import date
import calendar

user = st.session_state.get("user", "default")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "data_users" / user
DATA_DIR.mkdir(parents=True, exist_ok=True)

FUTURE_PATH = DATA_DIR / "future_transactions.csv"

def generate_occurrences(start_date, recurr: str, dur_months: int):
    start = pd.to_datetime(start_date).normalize()
    today = pd.Timestamp(date.today())

    # define limite máximo (ou 12 meses, ou duração informada)
    if dur_months and dur_months > 0:
        end_limit = start + pd.DateOffset(months=dur_months)
    else:
        end_limit = start + pd.DateOffset(years=1)

    # garante que o limite nunca passe de 1 ano (proteção)
    end_limit = min(end_limit, start + pd.DateOffset(years=1))

    dates = []
    if not recurr or recurr in ("none", None, "once"):
        # se não há recorrência, só retorna a data se ainda não passou
        if start >= today:
            dates = [start]
        return dates

    # Gera recorrências
    cur = start
    while cur <= end_limit:
        if cur >= today:
            dates.append(cur)

        if recurr == "weekly":
            cur += pd.DateOffset(weeks=1)
        elif recurr == "biweekly":
            cur += pd.DateOffset(weeks=2)
        elif recurr == "monthly":
            cur += pd.DateOffset(months=1)
        elif recurr == "quarterly":
            cur += pd.DateOffset(months=3)
        elif recurr == "yearly":
            cur += pd.DateOffset(years=1)
        else:
            break  # tipo de recorrência desconhecido → interrompe
    return dates


st.set_page_config(layout="wide")
st.title("📊 Visão Geral")

df = load_data()

if df.empty:
    st.warning("⚠️ Nenhum dado encontrado. Cadastre bancos e investimentos na aba 'Gerenciar Dados'.")
    st.stop()

total_bancos, total_invest, total_geral = get_summary()

# === MÉTRICAS ===
col1, col2, col3 = st.columns(3)
col1.metric("💳 Total em Bancos", f"R$ {total_bancos:,.2f}")
col2.metric("📈 Total Investido", f"R$ {total_invest:,.2f}")
col3.metric("💰 Patrimônio Total", f"R$ {total_geral:,.2f}")

st.markdown("---")

# === LANÇAMENTOS FUTUROS DO MÊS ===
st.subheader("📅 Lançamentos Futuros do Mês")

if FUTURE_PATH.exists():
    fut_df = pd.read_csv(FUTURE_PATH)
    if not fut_df.empty:
        fut_df["Data"] = pd.to_datetime(fut_df["Data"], errors="coerce")
        hoje = date.today()
        primeiro_dia = hoje.replace(day=1)
        ultimo_dia = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
        primeiro_dia = pd.Timestamp(primeiro_dia)
        ultimo_dia = pd.Timestamp(ultimo_dia)

        linhas = []
        for _, row in fut_df.iterrows():
            rec = row.get("Recorrencia", "none")
            dur = int(row.get("Duracao_meses") or 0)
            ocorrencias = generate_occurrences(row["Data"], rec, dur)
            for d in ocorrencias:
                if primeiro_dia <= pd.Timestamp(d) <= ultimo_dia:
                    linhas.append({
                        "Data": pd.Timestamp(d),
                        "Operação": row["Operação"],
                        "Nome": row["Nome"],
                        "Valor": float(row["Valor"]),
                        "Categoria": row.get("Categoria", ""),
                        "Descrição": row.get("Descrição", ""),
                    })

        if linhas:
            fut_mes = pd.DataFrame(linhas).sort_values("Data").copy()

            # ✅ Formatações
            fut_mes["Data_formatada"] = fut_mes["Data"].dt.strftime("%d/%m/%Y")
            fut_mes["Valor_formatado"] = fut_mes["Valor"].apply(
                lambda v: f"R$ {v:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            )

            tabela = fut_mes[[
                "Data_formatada",
                "Operação",
                "Nome",
                "Valor_formatado",
                "Categoria",
                "Descrição"
            ]]

            tabela.columns = [
                "📅 Data",
                "💼 Tipo",
                "🏦 Conta",
                "💰 Valor",
                "🏷️ Categoria",
                "📝 Descrição"
            ]

            st.dataframe(
                tabela,
                width='stretch',
                hide_index=True
            )
        else:
            st.info("✅ Nenhuma movimentação futura agendada para este mês.")
    else:
        st.info("✅ Nenhuma movimentação futura cadastrada.")
else:
    st.info("✅ Nenhum arquivo de lançamentos futuros encontrado.")

# === GRÁFICOS ===
st.markdown("---")
col1, col2 = st.columns(2)
df_bancos = df[df["Tipo"] == "Banco"]
df_inv = df[df["Tipo"] == "Investimento"]

with col1:
    st.subheader("🏦 Bancos")
    st.dataframe(df_bancos, width='stretch')
    if not df_bancos.empty:
        fig_b = px.bar(df_bancos, x="Nome", y="Saldo", title="Saldo por Banco", text_auto=True, color="Nome")
        fig_b.update_layout(xaxis_title="", yaxis_title="R$", showlegend=False)
        st.plotly_chart(fig_b, width='stretch')

with col2:
    st.subheader("💰 Investimentos")
    st.dataframe(df_inv, width='stretch')
    if not df_inv.empty:
        fig_i = px.pie(df_inv, names="Nome", values="Saldo", title="Distribuição dos Investimentos", hole=0.4)
        st.plotly_chart(fig_i, width='stretch')
