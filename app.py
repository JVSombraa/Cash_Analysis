import streamlit as st

st.set_page_config(
    page_title="Meu Painel Financeiro",
    page_icon="💵",
    layout="wide"
)

st.title("💵 Meu Painel Financeiro")

st.markdown("""
Bem-vindo ao **Painel Financeiro Pessoal**!  
Aqui você pode:
- Gerenciar suas **contas bancárias e investimentos**
- Acompanhar seus **saldos e distribuição**
- Simular **rendimentos futuros** com base no CDI atual
""")

st.info("👉 Use o menu lateral para navegar entre as páginas.")
