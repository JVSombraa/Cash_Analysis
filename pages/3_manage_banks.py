import streamlit as st
from pathlib import Path
import pandas as pd
from data.db import load_data, save_data, add_entry, update_balance
import json

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(layout="wide")

st.title("🏦 Gerenciar Bancos e Investimentos")

st.markdown(
    "Adicione, visualize e gerencie seus **bancos** e **investimentos** registrados no sistema."
)

# --- CAMINHOS DE ARQUIVOS POR USUÁRIO ---
user = st.session_state.get("user", "default")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "data_users" / user
DATA_DIR.mkdir(parents=True, exist_ok=True)

HIST_PATH = DATA_DIR / "history.csv"
FUTURE_PATH = DATA_DIR / "future_transactions.csv"
EXCLUSIONS_PATH = DATA_DIR / "future_exclusions.json"


if "pending_action" not in st.session_state:
    st.session_state["pending_action"] = None


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

def load_future():
    """Carrega o arquivo de agendamentos futuros."""
    if FUTURE_PATH.exists():
        return pd.read_csv(FUTURE_PATH)
    return pd.DataFrame(columns=["ID","BancoID","Tipo","Nome","Data","Operação","Valor","Categoria","Descrição","Recorrencia","Duracao_meses"])

def save_future(df):
    """Salva o DataFrame de agendamentos futuros."""
    df.to_csv(FUTURE_PATH, index=False)


def load_future_exclusions():
    """Carrega IDs excluídos (opcional, usado apenas se precisar)."""
    if EXCLUSIONS_PATH.exists():
        return set(json.loads(EXCLUSIONS_PATH.read_text()))
    return set()

def save_future_exclusions(exclusions):
    """Salva exclusões de instâncias futuras."""
    EXCLUSIONS_PATH.write_text(json.dumps(list(exclusions)))

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
    detalhes_banco = st.text_area("🧾 Descrição do banco (opcional)")

    if st.button("💾 Salvar Banco"):
        if nome_banco:
            result = add_entry("Banco", nome_banco, saldo_banco, detalhes_banco)
            if result["duplicado"]:
                st.warning(f"O banco **{nome_banco}** já existe.")
                if st.button("➕ Adicionar valor ao saldo existente"):
                    update_balance(nome_banco, "Banco", saldo_banco)
                    st.success(f"Saldo atualizado para o banco '{nome_banco}'.")
                    # st.rerun()
                    st.session_state["pending_action"] = "reload"
            else:
                st.success(f"Banco '{nome_banco}' cadastrado com sucesso!")
                # st.rerun()
                st.session_state["pending_action"] = "reload"

        else:
            st.warning("Informe o nome do banco.")

    st.markdown("---")
    st.subheader("📋 Bancos cadastrados")
    bancos_df = df[df["Tipo"] == "Banco"]
    st.dataframe(bancos_df, width='stretch')

# ================================================
# ========== ABA 2 — CADASTRAR INVESTIMENTO ======
# ================================================
with tab2:
    nome_inv = st.text_input("📈 Nome do Investimento")
    valor_inv = st.number_input("💵 Valor aplicado (R$)", min_value=0.0, step=100.0)
    detalhes_inv = st.text_area("🧾 Detalhes do investimento (ex: 106% CDI, prazo, etc.)")

    if st.button("💾 Salvar Investimento"):
        if nome_inv:
            add_entry("Investimento", nome_inv, valor_inv, detalhes_inv)
            st.success(f"Investimento '{nome_inv}' cadastrado com sucesso!")
            # st.rerun()
            st.session_state["pending_action"] = "reload"
        else:
            st.warning("Informe o nome do investimento.")

    st.markdown("---")
    st.subheader("📋 Investimentos cadastrados")
    inv_df = df[df["Tipo"] == "Investimento"]
    st.dataframe(inv_df, width='stretch')

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
                    mask_id = df_full["ID"].astype(int) == int(row["ID"])
                    if not mask_id.any():
                        st.error("Registro não encontrado no DB (ID). Atualize a página e tente novamente.")
                        st.stop()

                    # exige que tanto ID quanto Nome atual correspondam ao registro antes de permitir alterações
                    mask_both = mask_id & (df_full["Nome"].astype(str).str.strip() == str(row["Nome"]).strip())
                    if not mask_both.any():
                        st.error("ID e Nome não correspondem ao registro atual. Ação cancelada.")
                        st.stop()

                    old_nome = df_full.loc[mask_both, "Nome"].iloc[0]
                    df_full.loc[mask_both, "Nome"] = new_nome
                    df_full.loc[mask_both, "Detalhes"] = new_detalhes
                    save_data(df_full)

                    # atualizar histórico por BancoID quando disponível (somente onde BancoID e Nome correspondem)
                    hist_full = load_history()
                    if "BancoID" in hist_full.columns:
                        hist_full.loc[(hist_full["BancoID"].astype(str) == str(row["ID"])) & (hist_full["Nome"].astype(str).str.strip() == str(old_nome).strip()), "Nome"] = new_nome
                    else:
                        # fallback: onde Nome+Tipo bate
                        hist_full.loc[(hist_full["Nome"] == old_nome) & (hist_full["Tipo"] == row["Tipo"]), "Nome"] = new_nome

                    hist_full.to_csv(HIST_PATH, index=False)

                    # === Atualiza também o nome no arquivo de agendamentos futuros ===
                    future_df = load_future()
                    if not future_df.empty and "BancoID" in future_df.columns:
                        mask_future = future_df["BancoID"].astype(str) == str(row["ID"])
                        future_df.loc[mask_future, "Nome"] = new_nome
                        save_future(future_df)


                    st.success(f"{old_nome} atualizado para {new_nome}.")
                    # st.rerun()
                    st.session_state["pending_action"] = "reload"

                # --- Remover ---
                # Modal: usamos uma factory para capturar o `row` atual (evita captura tardia da variável loop)
                def make_delete_dialog(row):
                    @st.dialog("Tem certeza ?")
                    def check_delete(row=row):
                        rec_id = int(row["ID"])
                        # recarrega histórico
                        hist_full = load_history()
                        # contar transações associadas por BancoID (se houver) *e* Nome correspondente
                        if "BancoID" in hist_full.columns:
                            n_transacoes = int(((hist_full["BancoID"].astype(str) == str(rec_id)) & (hist_full["Nome"].astype(str).str.strip() == str(row["Nome"]).strip())).sum())
                        else:
                            # fallback por Nome+Tipo
                            n_transacoes = int(((hist_full["Nome"].astype(str).str.strip() == str(row["Nome"]).strip()) & (hist_full["Tipo"] == row["Tipo"])).sum())

                        st.warning(f"Esta ação removerá **{row['Nome']}** e {n_transacoes} transações associadas.")

                        confirmar = st.button(f"Remover")

                        if confirmar:
                            # remove do DB por ID E Nome (exige correspondência em ambas)
                            df_full = load_data()
                            mask_main = (df_full["ID"].astype(int) == rec_id) & (df_full["Nome"].astype(str).str.strip() == str(row["Nome"]).strip())
                            if not mask_main.any():
                                st.error("Registro no DB não corresponde ao ID e Nome esperados. Ação cancelada.")
                                st.stop()

                            df_new = df_full[~mask_main].reset_index(drop=True)
                            save_data(df_new)

                            # remove do histórico por BancoID (preferível), exigindo também Nome correspondente
                            if "BancoID" in hist_full.columns:
                                hist_new = hist_full[~((hist_full["BancoID"].astype(str) == str(rec_id)) & (hist_full["Nome"].astype(str).str.strip() == str(row["Nome"]).strip()))].reset_index(drop=True)
                            else:
                                hist_new = hist_full[~((hist_full["Nome"].astype(str).str.strip() == str(row["Nome"]).strip()) & (hist_full["Tipo"] == row["Tipo"]))].reset_index(drop=True)

                            # === Remove também agendamentos futuros associados ===
                            future_df = load_future()
                            if not future_df.empty and "BancoID" in future_df.columns:
                                future_new = future_df[future_df["BancoID"].astype(str) != str(rec_id)].reset_index(drop=True)
                                removed_future = len(future_df) - len(future_new)
                                if removed_future > 0:
                                    save_future(future_new)
                            
                            hist_new.to_csv(HIST_PATH, index=False)

                            st.success(f"{row['Nome']} removido com sucesso. ({n_transacoes} transações excluídas)")
                            # st.rerun()
                            st.session_state["pending_action"] = "reload"

                    return check_delete

                if c3.button("🗑️ Remover", key=f"excluir_{row['ID']}"):
                    # cria o diálogo específico para este `row` e o executa
                    make_delete_dialog(row)()

# --- APLICA RECARREGAMENTO SE NECESSÁRIO ---
if st.session_state.get("pending_action") == "reload":
    st.session_state["pending_action"] = None
    st.rerun()