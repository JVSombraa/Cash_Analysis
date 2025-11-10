import streamlit as st
from pathlib import Path
import pandas as pd
from data.db import load_data, save_data, add_entry, update_balance

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(layout="wide")
st.title("🏦 Gerenciar Bancos e Investimentos")

st.markdown(
    "Adicione, visualize e gerencie seus **bancos** e **investimentos** registrados no sistema."
)

# --- CAMINHOS DE ARQUIVOS ---
HIST_PATH = Path(__file__).resolve().parent.parent / "data" / "history.csv"

# --- FUNÇÕES AUXILIARES ---
def load_history():
    """Carrega history.csv e garante a coluna BancoID (compatibilidade retroativa)."""
    if HIST_PATH.exists():
        h = pd.read_csv(HIST_PATH)
    else:
        h = pd.DataFrame(columns=["ID", "BancoID", "Tipo", "Nome", "Data", "Operação", "Valor", "Categoria", "Descrição"])

    # Normaliza colunas mínimas
    if "BancoID" not in h.columns:
        h["BancoID"] = None
    # garante ordem de colunas desejada quando possível
    cols_pref = ["ID", "BancoID", "Tipo", "Nome", "Data", "Operação", "Valor", "Categoria", "Descrição"]
    h = h[[c for c in cols_pref if c in h.columns] + [c for c in h.columns if c not in cols_pref]]
    return h

# --- CARREGA DADOS PRINCIPAIS ---
df = load_data()
hist_df = load_history()

# --- Compatibilidade retroativa: se BancoID ausente tente recuperar por Nome+Tipo ---
if "BancoID" in hist_df.columns and hist_df["BancoID"].isnull().all():
    # tenta mapear nomes -> IDs do DB atual
    if not df.empty and "ID" in df.columns:
        name_map = df.set_index(["Tipo", "Nome"])["ID"].to_dict()
        def map_bankid(row):
            key = (row.get("Tipo"), row.get("Nome"))
            return name_map.get(key)
        hist_df["BancoID"] = hist_df.apply(map_bankid, axis=1)
        hist_df.to_csv(HIST_PATH, index=False)

# === TABS PRINCIPAIS ===
tab1, tab2, tab3 = st.tabs(
    ["🏦 Cadastrar Banco", "💰 Cadastrar Investimento", "⚙️ Gerenciar Registros"]
)

# ========================================
# ========== ABA 1 — CADASTRAR BANCO =====
# ========================================
with tab1:
    nome_banco = st.text_input("🏦 Nome do Banco")
    saldo_banco = st.number_input("💰 Saldo inicial (R$)", min_value=0.0, step=100.0)

    if st.button("💾 Salvar Banco"):
        if nome_banco:
            result = add_entry("Banco", nome_banco, saldo_banco)
            if result["duplicado"]:
                st.warning(f"O banco **{nome_banco}** já existe.")
                if st.button("➕ Adicionar valor ao saldo existente"):
                    update_balance(nome_banco, "Banco", saldo_banco)
                    st.success(f"Saldo atualizado para o banco '{nome_banco}'.")
                    st.rerun()
            else:
                st.success(f"Banco '{nome_banco}' cadastrado com sucesso!")
                st.rerun()
        else:
            st.warning("Informe o nome do banco.")

    st.markdown("---")
    st.subheader("📋 Bancos cadastrados")
    bancos_df = df[df["Tipo"] == "Banco"]
    st.dataframe(bancos_df, use_container_width=True)

# ================================================
# ========== ABA 2 — CADASTRAR INVESTIMENTO ======
# ================================================
with tab2:
    nome_inv = st.text_input("📈 Nome do Investimento")
    valor_inv = st.number_input("💵 Valor aplicado (R$)", min_value=0.0, step=100.0)
    detalhes = st.text_area("🧾 Detalhes do investimento (ex: 106% CDI, prazo, etc.)")

    if st.button("💾 Salvar Investimento"):
        if nome_inv:
            add_entry("Investimento", nome_inv, valor_inv, detalhes)
            st.success(f"Investimento '{nome_inv}' cadastrado com sucesso!")
            st.rerun()
        else:
            st.warning("Informe o nome do investimento.")

    st.markdown("---")
    st.subheader("📋 Investimentos cadastrados")
    inv_df = df[df["Tipo"] == "Investimento"]
    st.dataframe(inv_df, use_container_width=True)

# ========================================
# ========== ABA 3 — GERENCIAMENTO =======
# ========================================
with tab3:
    st.markdown("### ⚙️ Gerenciar Bancos e Investimentos")

    if df.empty:
        st.info("Nenhum banco ou investimento cadastrado ainda.")
    else:
        # recarrega histórico (fresh) para garantir sincronia
        hist_df = load_history()

        # filtro opcional: por padrão mostra todos (opcional)
        tipo_opcoes = ["Todos", "Banco", "Investimento"]
        tipo_filtro = st.selectbox("Filtrar por tipo (opcional)", tipo_opcoes, index=0)
        if tipo_filtro == "Todos":
            df_iter = df.copy()
        else:
            df_iter = df[df["Tipo"] == tipo_filtro].copy()

        # Ícones visuais por tipo
        tipo_icone = {"Banco": "🏦", "Investimento": "📈"}

        # mostra contador de registros
        st.markdown(f"**{len(df_iter)}** registros exibidos.")

        for idx, row in df_iter.reset_index(drop=True).iterrows():
            icone = tipo_icone.get(row["Tipo"], "💼")
            with st.expander(f"{icone} {row['Tipo']} — {row['Nome']}"):
                st.markdown(
                    f"""
                    💰 **Saldo:** R$ {row['Saldo']:,.2f}  
                    🗒️ **Detalhes:** {row['Detalhes'] if str(row['Detalhes']).strip() else '—'}
                    """
                )

                st.divider()
                st.markdown("#### ✏️ Editar informações")

                # campos de edição
                new_nome = st.text_input("Novo nome", value=row["Nome"], key=f"nome_{row['ID']}")
                new_detalhes = st.text_area("Detalhes", value=row["Detalhes"], key=f"det_{row['ID']}")

                c1, c2, c3 = st.columns([1, 0.5, 1])

                # --- Atualizar ---
                if c1.button("💾 Salvar alterações", key=f"atualizar_{row['ID']}"):
                    df_full = load_data()  # recarrega DB atual
                    # localizar por ID no db (ID é estável)
                    mask = df_full["ID"].astype(int) == int(row["ID"])
                    if not mask.any():
                        st.error("Registro não encontrado no DB (ID). Atualize a página e tente novamente.")
                        st.stop()

                    old_nome = df_full.loc[mask, "Nome"].iloc[0]
                    df_full.loc[mask, "Nome"] = new_nome
                    df_full.loc[mask, "Detalhes"] = new_detalhes
                    save_data(df_full)

                    # atualizar histórico por BancoID quando disponível
                    hist_full = load_history()
                    if "BancoID" in hist_full.columns:
                        hist_full.loc[hist_full["BancoID"].astype(str) == str(row["ID"]), "Nome"] = new_nome
                    else:
                        # fallback: onde Nome+Tipo bate
                        hist_full.loc[(hist_full["Nome"] == old_nome) & (hist_full["Tipo"] == row["Tipo"]), "Nome"] = new_nome

                    hist_full.to_csv(HIST_PATH, index=False)
                    st.success(f"{old_nome} atualizado para {new_nome}.")
                    st.rerun()

                # --- Remover ---

                    # --- Modal ---
                    ##################
                @st.dialog("Tem certeza ?")
                def check_delete():
                    rec_id = int(row["ID"])
                    # recarrega histórico
                    hist_full = load_history()
                    # contar transações associadas por BancoID (se houver)
                    if "BancoID" in hist_full.columns:
                        n_transacoes = int((hist_full["BancoID"].astype(str) == str(rec_id)).sum())
                    else:
                        # fallback por Nome+Tipo
                        n_transacoes = int(((hist_full["Nome"].astype(str).str.strip() == str(row["Nome"]).strip()) & (hist_full["Tipo"] == row["Tipo"])).sum())

                    st.warning(f"Esta ação removerá **{row['Nome']}** e {n_transacoes} transações associadas.")

                    confirmar = st.button(f"Remover")

                    if confirmar:
                        # remove do DB por ID
                        df_full = load_data()
                        df_new = df_full[df_full["ID"].astype(int) != rec_id].reset_index(drop=True)
                        save_data(df_new)

                        # remove do histórico por BancoID (preferível)
                        if "BancoID" in hist_full.columns:
                            hist_new = hist_full[hist_full["BancoID"].astype(str) != str(rec_id)].reset_index(drop=True)
                        else:
                            hist_new = hist_full[~((hist_full["Nome"].astype(str).str.strip() == str(row["Nome"]).strip()) & (hist_full["Tipo"] == row["Tipo"]))].reset_index(drop=True)

                        hist_new.to_csv(HIST_PATH, index=False)

                        st.success(f"{row['Nome']} removido com sucesso. ({n_transacoes} transações excluídas)")
                        st.rerun()
                    ##################

                if c3.button("🗑️ Remover", key=f"excluir_{row['ID']}"):
                    check_delete()