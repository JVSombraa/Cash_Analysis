import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("💰 Simulador de Investimentos")

st.markdown("""
Simule o crescimento de um investimento com base no **CDI atual** e um percentual escolhido.
""")

# Entradas
col1, col2, col3 = st.columns(3)
valor_inicial = col1.number_input("💵 Valor inicial (R$)", min_value=0.0, step=100.0)
aporte_mensal = col2.number_input("📈 Aporte mensal (R$)", min_value=0.0, step=100.0)
meses = col3.number_input("🗓️ Duração (meses)", min_value=1, step=1, value=12)

col4, col5 = st.columns(2)
cdi_atual = col4.number_input("🏦 CDI atual (%)", min_value=0.0, step=0.1, value=10.65)
percentual_cdi = col5.number_input("⚙️ Percentual do CDI (%)", min_value=0.0, step=1.0, value=106.0)

if st.button("Calcular Simulação"):
    taxa_mensal = (cdi_atual / 100) * (percentual_cdi / 100) / 12
    valor_total = valor_inicial
    historico = []

    for mes in range(1, int(meses) + 1):
        valor_total = (valor_total + aporte_mensal) * (1 + taxa_mensal)
        historico.append({"Mês": mes, "Valor acumulado": valor_total})

    df = pd.DataFrame(historico)
    total_aportado = valor_inicial + aporte_mensal * meses
    rendimento = valor_total - total_aportado

    st.success(f"💵 Valor total após {meses} meses: **R$ {valor_total:,.2f}**")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Aportado", f"R$ {total_aportado:,.2f}")
    col_b.metric("Rendimento", f"R$ {rendimento:,.2f}")
    col_c.metric("Total final", f"R$ {valor_total:,.2f}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Mês"], y=df["Valor acumulado"],
        mode="lines+markers", line=dict(color="green"),
        name="Evolução"
    ))
    fig.update_layout(title="📈 Crescimento do Investimento", xaxis_title="Mês", yaxis_title="Valor (R$)")
    st.plotly_chart(fig, use_container_width=True)
