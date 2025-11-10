import streamlit as st
import pandas as pd
import plotly.express as px
from data.db import load_data, get_summary

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

# === GRÁFICOS ===
col1, col2 = st.columns(2)
df_bancos = df[df["Tipo"] == "Banco"]
df_inv = df[df["Tipo"] == "Investimento"]

with col1:
    st.subheader("🏦 Bancos")
    st.dataframe(df_bancos, use_container_width=True)
    if not df_bancos.empty:
        fig_b = px.bar(df_bancos, x="Nome", y="Saldo", title="Saldo por Banco", text_auto=True, color="Nome")
        fig_b.update_layout(xaxis_title="", yaxis_title="R$", showlegend=False)
        st.plotly_chart(fig_b, use_container_width=True)

with col2:
    st.subheader("💰 Investimentos")
    st.dataframe(df_inv, use_container_width=True)
    if not df_inv.empty:
        fig_i = px.pie(df_inv, names="Nome", values="Saldo", title="Distribuição dos Investimentos", hole=0.4)
        st.plotly_chart(fig_i, use_container_width=True)
