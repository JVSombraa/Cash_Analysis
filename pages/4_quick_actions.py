# pages/4_⚙️_Ações_Rápidas.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from data.db import load_data, save_data
from pathlib import Path

# Caminhos
HIST_PATH = Path(__file__).resolve().parent.parent / "data" / "history.csv"
HIST_PATH.parent.mkdir(exist_ok=True)

st.set_page_config(layout="wide")
st.title("⚙️ Ações Rápidas")

# --- Carregar dados principais ---
df = load_data()
if df.empty:
    st.warning("Nenhum dado encontrado. Cadastre bancos e investimentos primeiro.")
    st.stop()

# --- Garantir histórico ---
if HIST_PATH.exists():
    hist_df = pd.read_csv(HIST_PATH)
else:
    hist_df = pd.DataFrame(columns=["ID", "BancoID", "Tipo", "Nome", "Data", "Operação", "Valor", "Categoria", "Descrição"])

# Compatibilidade retroativa: se o histórico antigo não tem BancoID, tenta reconstruir
if "BancoID" not in hist_df.columns:
    hist_df["BancoID"] = None

    for i, row in hist_df.iterrows():
        # tenta achar o banco correspondente pelo nome/tipo
        match = df[(df["Nome"] == row["Nome"]) & (df["Tipo"] == row["Tipo"])]
        hist_df.at[i, "BancoID"] = int(match["ID"].iloc[0]) if not match.empty else None

    hist_df.to_csv(HIST_PATH, index=False)

# IDs e datas
if "ID" not in hist_df.columns:
    hist_df["ID"] = range(1, len(hist_df) + 1)

# Corrige datas apenas se forem nulas, sem sobrescrever as válidas
if "Data" in hist_df.columns:
    hist_df["Data"] = pd.to_datetime(hist_df["Data"], errors="coerce")
    if hist_df["Data"].isna().any():
        hist_df.loc[hist_df["Data"].isna(), "Data"] = pd.Timestamp.today()
else:
    hist_df["Data"] = pd.Timestamp.today()

# Tipos numéricos
hist_df = hist_df.astype({"ID": int, "Valor": float}, errors="ignore")

# --- Selecionar tipo e item ---
tipo = st.radio("Tipo de conta", ["Banco", "Investimento"], horizontal=True)
df_tipo = df[df["Tipo"] == tipo]
nome = st.selectbox(f"Selecione o {tipo.lower()}:", df_tipo["Nome"].unique())
item = df_tipo[df_tipo["Nome"] == nome].iloc[0]

st.markdown("### 📘 Informações do item selecionado")
col_info_1, col_info_2 = st.columns(2)
col_info_1.metric("Saldo atual", f"R$ {item['Saldo']:,.2f}")
col_info_2.write(f"**Detalhes:** {item['Detalhes'] if str(item['Detalhes']).strip() else '—'}")

st.markdown("---")

# --- Nova operação ---
operacao = st.radio("Operação", ["Depósito / Adição", "Retirada / Gasto"], horizontal=True)
valor = st.number_input("💵 Valor (R$)", min_value=0.0, step=10.0)
# data_op = st.date_input("📅 Data da operação", value=date.today(), format="DD/MM/YYYY")
data_op = st.date_input("📅 Data da operação", value=date.today())
# Categorias
if operacao == "Depósito / Adição":
    categorias_op = ["Salário", "Rendimento", "Transferência recebida", "Outros"]
else:
    categorias_op = ["Alimentação", "Transporte", "Contas", "Lazer", "Saúde", "Investimentos", "Outros"]

col_cat, col_desc = st.columns([1, 2])
categoria = col_cat.selectbox("Categoria (opcional)", ["Nenhuma"] + categorias_op)
descricao = col_desc.text_input("Descrição (opcional)")

st.markdown("---")

def new_hist_id(df_hist):
    return int(df_hist["ID"].max()) + 1 if not df_hist.empty else 1

# --- Executar operação ---
if st.button("💾 Executar operação"):
    if valor <= 0:
        st.warning("O valor deve ser maior que zero.")
    else:
        # Localizar ID do banco/investimento selecionado
        item_id = int(item["ID"])
        mask = (df["ID"] == item_id)
        current_balance = float(df.loc[mask, "Saldo"].iloc[0])

        new_effect = valor if operacao.startswith("Depósito") else -valor
        new_balance = current_balance + new_effect

        if new_balance < 0:
            st.error(f"Operação inválida: resultaria em saldo negativo (saldo atual R$ {current_balance:,.2f}).")
        else:
            # Atualizar saldo principal
            df.loc[mask, "Saldo"] = new_balance
            save_data(df)

            # Gera novo ID incremental
            new_id = int(hist_df["ID"].max()) + 1 if not hist_df.empty else 1

            # 🔹 Salva exatamente a data escolhida
            entry = {
                "ID": new_id,
                "BancoID": item_id,
                "Tipo": tipo,
                "Nome": nome,
                "Data": pd.Timestamp(data_op).strftime("%Y-%m-%d 00:00:00"),
                "Operação": "Depósito" if operacao.startswith("Depósito") else "Retirada",
                "Valor": valor,
                "Categoria": "" if categoria == "Nenhuma" else categoria,
                "Descrição": descricao or "",
            }

            cols_order = ["ID", "BancoID", "Tipo", "Nome", "Data", "Operação", "Valor", "Categoria", "Descrição"]
            hist_df = pd.concat([hist_df, pd.DataFrame([entry])], ignore_index=True)
            hist_df = hist_df[[col for col in cols_order if col in hist_df.columns]]

            # 🔹 Não reescreve datas antigas ao salvar
            hist_df.to_csv(HIST_PATH, index=False)

            st.success(f"✅ Operação registrada com sucesso para {data_op.strftime('%d/%m/%Y')}!")
            st.rerun()


# --- Histórico ---
st.markdown("---")
st.subheader("📜 Histórico de Movimentações")

col_f1, col_f2, col_f3 = st.columns(3)
filtro_tipo = col_f1.multiselect("Filtrar por tipo", hist_df["Tipo"].unique(), default=[])
filtro_op = col_f2.multiselect("Filtrar por operação", hist_df["Operação"].unique(), default=[])
filtro_data = col_f3.date_input("Filtrar por data", value=None)

filtro_df = hist_df.copy()
if filtro_tipo:
    filtro_df = filtro_df[filtro_df["Tipo"].isin(filtro_tipo)]
if filtro_op:
    filtro_df = filtro_df[filtro_df["Operação"].isin(filtro_op)]
if filtro_data:
    filtro_df = filtro_df[filtro_df["Data"].dt.date == filtro_data]

filtro_df = filtro_df.sort_values("Data", ascending=False).reset_index(drop=True)

if filtro_df.empty:
    st.info("Nenhuma movimentação encontrada.")
else:
    for _, row in filtro_df.iterrows():
        rec_id = int(row["ID"])
        header = f"[{pd.to_datetime(row['Data']).strftime('%d/%m/%Y')}] {row['Operação']} — {row['Nome']} — R$ {row['Valor']:,.2f}"
        with st.expander(header):
            edit_col1, edit_col2 = st.columns([1, 1])
            op_options = ["Depósito", "Retirada"]
            new_oper = edit_col1.selectbox("Operação", op_options, index=0 if row["Operação"] == "Depósito" else 1, key=f"op_{rec_id}")
            new_val = edit_col2.number_input("Valor (R$)", min_value=0.0, value=float(row["Valor"]), step=10.0, key=f"val_{rec_id}")
            new_date = st.date_input("Data", value=pd.to_datetime(row["Data"]).date(), key=f"date_{rec_id}")

            cat_options = ["Nenhuma"] + (["Salário", "Rendimento", "Transferência recebida", "Outros"] if new_oper == "Depósito" else ["Alimentação", "Transporte", "Contas", "Lazer", "Saúde", "Investimentos", "Outros"])
            new_cat = st.selectbox("Categoria", cat_options, index=cat_options.index(row["Categoria"]) if row["Categoria"] in cat_options else 0, key=f"cat_{rec_id}")
            new_desc = st.text_input("Descrição", value=row["Descrição"] or "", key=f"desc_{rec_id}")

            btn_col1, btn_col2 = st.columns(2)
            if btn_col1.button("💾 Salvar alterações", key=f"save_{rec_id}"):
                full_hist = pd.read_csv(HIST_PATH)
                full_hist["Data"] = pd.to_datetime(full_hist["Data"], errors="coerce").fillna(pd.Timestamp.today())
                idx = full_hist.index[full_hist["ID"] == rec_id].tolist()
                if not idx:
                    st.error("Registro não encontrado.")
                    st.stop()
                idx = idx[0]

                old_row = full_hist.loc[idx]
                old_effect = old_row["Valor"] if old_row["Operação"] == "Depósito" else -old_row["Valor"]
                new_effect = new_val if new_oper == "Depósito" else -new_val

                mask_main = (df["Nome"] == old_row["Nome"]) & (df["Tipo"] == old_row["Tipo"])
                current_balance = float(df.loc[mask_main, "Saldo"].iloc[0])
                proposed_balance = current_balance - old_effect + new_effect

                if proposed_balance < 0:
                    st.error("Alteração inválida: resultaria em saldo negativo.")
                    st.stop()

                df.loc[mask_main, "Saldo"] = proposed_balance
                save_data(df)

                full_hist.loc[idx, "Data"] = pd.to_datetime(new_date).strftime("%Y-%m-%d")
                full_hist.loc[idx, "Operação"] = new_oper
                full_hist.loc[idx, "Valor"] = new_val
                full_hist.loc[idx, "Categoria"] = "" if new_cat == "Nenhuma" else new_cat
                full_hist.loc[idx, "Descrição"] = new_desc
                full_hist.to_csv(HIST_PATH, index=False)

                st.success("✅ Registro atualizado com sucesso!")
                st.rerun()

            if btn_col2.button("❌ Excluir", key=f"del_{rec_id}"):
                full_hist = pd.read_csv(HIST_PATH)
                idx = full_hist.index[full_hist["ID"] == rec_id].tolist()
                if not idx:
                    st.error("Registro não encontrado.")
                    st.stop()
                idx = idx[0]
                old_row = full_hist.loc[idx]
                old_effect = old_row["Valor"] if old_row["Operação"] == "Depósito" else -old_row["Valor"]

                mask_main = (df["Nome"] == old_row["Nome"]) & (df["Tipo"] == old_row["Tipo"])
                current_balance = float(df.loc[mask_main, "Saldo"].iloc[0])
                proposed_balance = current_balance - old_effect

                if proposed_balance < 0:
                    st.error("Exclusão inválida: saldo negativo.")
                    st.stop()

                df.loc[mask_main, "Saldo"] = proposed_balance
                save_data(df)
                full_hist = full_hist.drop(index=idx).reset_index(drop=True)
                full_hist.to_csv(HIST_PATH, index=False)
                st.warning("🗑️ Registro excluído e saldo atualizado.")
                st.rerun()

# --- Gráficos ---
st.markdown("---")
st.subheader("📊 Análises Visuais")

if hist_df.empty:
    st.info("Ainda não há histórico suficiente para gerar gráficos.")
    st.stop()

# Filtro por intervalo de datas para os gráficos
min_date = hist_df["Data"].min()
max_date = hist_df["Data"].max()
if pd.isna(min_date) or pd.isna(max_date):
    min_date = max_date = pd.Timestamp.today()

min_date = min_date.date()
max_date = max_date.date()

col_g1, col_g2 = st.columns([1, 2])
date_range = col_g1.date_input("Período (início, fim)", value=(min_date, max_date))
show_separate = col_g2.checkbox("Mostrar linhas separadas por tipo (Bancos / Investimentos)", value=True)

gdf = hist_df.copy()
# filtrar por período selecionado
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_dt, end_dt = date_range
    gdf = gdf[(gdf["Data"].dt.date >= start_dt) & (gdf["Data"].dt.date <= end_dt)]
elif isinstance(date_range, date):
    gdf = gdf[gdf["Data"].dt.date == date_range]

if gdf.empty:
    st.info("Sem dados no período selecionado.")
else:
    col_pie, col_line = st.columns([1, 2])

    # --- Gráfico de pizza: distribuição de gastos ---
    gastos = gdf[gdf["Operação"] == "Retirada"]
    if not gastos.empty:
        fig_pie = px.pie(
            gastos,
            names="Categoria",
            values="Valor",
            title="Distribuição de Gastos por Categoria (período)",
            hole=0.4
        )
        fig_pie.update_traces(textinfo="label+percent")
        col_pie.plotly_chart(fig_pie, use_container_width=True)
    else:
        col_pie.info("Nenhum gasto no período selecionado.")

    # --- Evolução do saldo ---
    temp = gdf.copy().sort_values("Data")
    temp["Efeito"] = temp.apply(lambda r: r["Valor"] if r["Operação"] == "Depósito" else -r["Valor"], axis=1)
    grouped = temp.groupby([temp["Data"].dt.date, "Tipo"])["Efeito"].sum().reset_index()
    pivot = grouped.pivot(index="Data", columns="Tipo", values="Efeito").fillna(0).sort_index()

    # garantir colunas fixas e mesmo comprimento
    for colname in ["Banco", "Investimento"]:
        if colname not in pivot.columns:
            pivot[colname] = 0.0

    # cumsum (acumulado)
    cum = pivot.cumsum()

    if show_separate:
        cum_reset = cum.reset_index().melt(id_vars="Data", var_name="Tipo", value_name="Saldo acumulado")
        fig_line = px.line(
            cum_reset,
            x="Data", y="Saldo acumulado", color="Tipo",
            title="Evolução do Saldo por Tipo (acumulado)",
            markers=True
        )
    else:
        cum["Total"] = cum.sum(axis=1)
        fig_line = px.area(
            cum.reset_index(),
            x="Data", y="Total",
            title="Evolução do Saldo Total (acumulado)"
        )

    fig_line.update_layout(
        xaxis_title="Data",
        yaxis_title="Variação acumulada (R$)",
        template="simple_white",
        hovermode="x unified",
        height=420
    )
    col_line.plotly_chart(fig_line, use_container_width=True)