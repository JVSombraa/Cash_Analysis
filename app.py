import streamlit as st

pages = {
    "Dashboard": [
        st.Page("pages/1_view_db.py", title="Acessar Contas"),
        st.Page("pages/3_manage_banks.py", title="Gerenciar Contas"),
        st.Page("pages/4_quick_actions.py", title="Registrar Movimentações"),
    ],
    "Features": [
        st.Page("pages/2_simulate_investments.py", title="Simulador de Investimentos"),
    ],
}

pg = st.navigation(pages)
pg.run()