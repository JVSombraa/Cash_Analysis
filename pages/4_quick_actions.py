import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
from data.db import load_data, save_data
from pathlib import Path
import json
from pathlib import Path

# -----------------------------
# Load files
# -----------------------------

user = st.session_state.get("user", "default")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "data_users" / user
DATA_DIR.mkdir(parents=True, exist_ok=True)

HIST_PATH = DATA_DIR / "history.csv"
HIST_PATH.parent.mkdir(exist_ok=True)

FUTURE_TRANS_PATH = DATA_DIR / "future_transactions.csv"
if not FUTURE_TRANS_PATH.exists():
    pd.DataFrame(columns=[
        "ID", "BancoID", "Tipo", "Nome", "Data", "Operação", "Valor",
        "Categoria", "Descrição", "Recorrencia", "Duracao_meses"
    ]).to_csv(FUTURE_TRANS_PATH, index=False)

EXCLUSIONS_FILE = DATA_DIR / "future_exclusions.json"

# -----------------------------
# Defs
# -----------------------------
def load_future():
    if FUTURE_TRANS_PATH.exists():
        f = pd.read_csv(FUTURE_TRANS_PATH)
    else:
        f = pd.DataFrame(columns=[
            "ID", "BancoID", "Tipo", "Nome", "Data", "Operação", "Valor",
            "Categoria", "Descrição", "Recorrencia", "Duracao_meses"
        ])
    for c in ["Recorrencia", "Duracao_meses"]:
        if c not in f.columns:
            f[c] = None
    return f

def save_future(df_):
    df_.to_csv(FUTURE_TRANS_PATH, index=False)

def generate_occurrences(start_date, recurr: str, dur_months: int):
    start = pd.to_datetime(start_date).normalize()
    today = pd.Timestamp(date.today())
    
    if dur_months and dur_months > 0:
        end_limit = start + pd.DateOffset(months=min(dur_months, 12))
    else:
        end_limit = start + pd.DateOffset(years=1)
    
    end_cap = start + pd.DateOffset(years=1)
    if end_limit > end_cap:
        end_limit = end_cap

    dates = []
    if not recurr or recurr in ("none", None):
        if start >= today:
            dates = [start]
        else:
            dates = []
        return dates

    cur = start
    while cur <= end_limit:
        if cur >= today:
            dates.append(cur)
        if recurr == "weekly":
            cur = cur + pd.DateOffset(weeks=1)
        elif recurr == "biweekly":
            cur = cur + pd.DateOffset(weeks=2)
        elif recurr == "monthly":
            cur = cur + pd.DateOffset(months=1)
        else:
            break
    return dates

def load_future_exclusions():
    if EXCLUSIONS_FILE.exists():
        with open(EXCLUSIONS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_future_exclusions(exclusions):
    with open(EXCLUSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(exclusions), f, ensure_ascii=False, indent=2)

# -----------------------------
# Pages
# -----------------------------
st.set_page_config(layout="wide", page_title="Registrar Movimentações", page_icon="⚙️")
st.title("⚙️ Registrar Movimentações")

# Carrega DB principal e históricos
df = load_data()
if df.empty:
    st.warning("Nenhum banco ou investimento cadastrado. Cadastre nas páginas de cadastro antes de registrar transações.")
    st.stop()

# Carregar HIST
hist_df = pd.read_csv(HIST_PATH) if HIST_PATH.exists() else pd.DataFrame(columns=[
    "ID", "BancoID", "Tipo", "Nome", "Data", "Operação", "Valor", "Categoria", "Descrição"
])

# Normalizar dados
if "BancoID" not in hist_df.columns:
    hist_df["BancoID"] = None
if "ID" not in hist_df.columns:
    hist_df["ID"] = range(1, len(hist_df) + 1)

if "Data" in hist_df.columns:
    hist_df["Data"] = pd.to_datetime(hist_df["Data"], errors="coerce")
else:
    hist_df["Data"] = pd.NaT

future_df = load_future()
future_exclusions = load_future_exclusions()
df_future = future_df[~future_df["ID"].isin(future_exclusions)]


# -----------------------------
# Abas e descrições curtas
# -----------------------------
tab_reg, tab_edit, tab_vis, tab_future = st.tabs([
    "📥 Registrar transações",
    "✏️ Editar / Remover",
    "📊 Visualização",
    "⏳ Agendar transações"
])

# -----------------------------
# Aba Registrar
# -----------------------------
with tab_reg:
    st.subheader("🏦 Selecionar conta")

    tipo = st.radio("Tipo de conta", ["Banco", "Investimento"], horizontal=True)
    df_tipo = df[df["Tipo"] == tipo]
    nome = st.selectbox(f"Selecione o {tipo.lower()}:", df_tipo["Nome"].unique())
    item = df_tipo[df_tipo["Nome"] == nome].iloc[0]

    col_info_1, col_info_2 = st.columns(2)
    col_info_1.metric("Saldo atual", f"R$ {item['Saldo']:,.2f}")
    col_info_2.write(f"**Detalhes:** {item['Detalhes'] if str(item['Detalhes']).strip() else '—'}")

    st.divider()
    st.subheader("🗒️ Dados da transação")
    operacao = st.radio("Operação", ["Depósito / Adição", "Retirada / Gasto"], horizontal=True)
    valor = st.number_input("💵 Valor (R$)", min_value=0.0, step=10.0)
    data_op = st.date_input("📅 Data da operação", value=date.today())

    if data_op > date.today():
        st.info("Se deseja agendar uma transação, use a aba 'Transações Futuras'.")

    categorias_op = ["Salário", "Rendimento", "Transferência recebida", "Outros"] if operacao.startswith("Depósito") else ["Alimentação", "Transporte", "Contas", "Lazer", "Saúde", "Investimentos", "Outros"]
    col_cat, col_desc = st.columns([1, 2])
    categoria = col_cat.selectbox("Categoria (opcional)", ["Nenhuma"] + categorias_op)
    descricao = col_desc.text_input("Descrição (opcional)")

    if st.button("💾 Executar operação"):
        if valor <= 0:
            st.warning("O valor deve ser maior que zero.")
        elif data_op > date.today():
            st.error("Operação inválida: para o futuro utilize a aba 'Transações Futuras'.")
        else:
            item_id = int(item["ID"])
            mask = (df["ID"] == item_id)
            current_balance = float(df.loc[mask, "Saldo"].iloc[0])
            new_effect = valor if operacao.startswith("Depósito") else -valor
            new_balance = current_balance + new_effect

            if new_balance < 0:
                st.error(f"Operação inválida: resultaria em saldo negativo (saldo atual R$ {current_balance:,.2f}).")
            else:
                df.loc[mask, "Saldo"] = new_balance
                save_data(df)

                new_id = int(hist_df["ID"].max()) + 1 if not hist_df.empty else 1
                entry = {
                    "ID": new_id,
                    "BancoID": item_id,
                    "Tipo": tipo,
                    "Nome": nome,
                    "Data": pd.Timestamp(data_op).strftime("%Y-%m-%d 00:00:00"),
                    "Operação": "Depósito" if operacao.startswith("Depósito") else "Retirada",
                    "Valor": float(valor),
                    "Categoria": "" if categoria == "Nenhuma" else categoria,
                    "Descrição": descricao or ""
                }
                hist_df = pd.concat([hist_df, pd.DataFrame([entry])], ignore_index=True)
                hist_df.to_csv(HIST_PATH, index=False)
                st.success(f"✅ Operação registrada para {data_op.strftime('%d/%m/%Y')}.")
                st.rerun()

    st.markdown("---")
    st.subheader("📜 Histórico recente")

    recent = hist_df.sort_values("Data", ascending=False).head(12).copy()
    if recent.empty:
        st.info("Nenhuma movimentação registrada ainda.")
    else:
        recent["Data"] = pd.to_datetime(recent["Data"], errors="coerce").dt.strftime("%d/%m/%Y")
        st.dataframe(recent[["Data", "Operação", "Nome", "Tipo", "Valor", "Categoria", "Descrição"]], use_container_width=True)

# -----------------------------
# Aba Editar / Remover
# -----------------------------
with tab_edit:
    st.subheader("🔍 Aplicar filtros (opcional)")

    col_f1, col_f2, col_f3 = st.columns(3)
    filtro_tipo = col_f1.multiselect("Filtrar por tipo", hist_df["Tipo"].dropna().unique(), default=[])
    filtro_op = col_f2.multiselect("Filtrar por operação", hist_df["Operação"].dropna().unique(), default=[])
    filtro_data = col_f3.date_input("Filtrar por data", value=None)

    filtro_df = hist_df.copy()
    if filtro_tipo:
        filtro_df = filtro_df[filtro_df["Tipo"].isin(filtro_tipo)]
    if filtro_op:
        filtro_df = filtro_df[filtro_df["Operação"].isin(filtro_op)]
    if filtro_data:
        filtro_df = filtro_df[pd.to_datetime(filtro_df["Data"]).dt.date == filtro_data]

    filtro_df = filtro_df.sort_values("Data", ascending=False).reset_index(drop=True)

    st.markdown("---")
    st.subheader("📜 Movimentações")

    if filtro_df.empty:
        st.info("Nenhuma movimentação encontrada com os filtros atuais.")
    else:
        for _, row in filtro_df.iterrows():
            rec_id = int(row["ID"])
            date_str = pd.to_datetime(row["Data"]).strftime("%d/%m/%Y") if pd.notna(row["Data"]) else "Sem data"
            header = f"[{date_str}] {row['Operação']} — {row['Nome']} — R$ {row['Valor']:,.2f}"
            with st.expander(header):

                left, right = st.columns([2, 1])
                left.markdown(f"**Descrição:** {row['Descrição'] or '—'}")
                left.markdown(f"**Categoria:** {row['Categoria'] or '—'}")
                right.write(f"**Tipo:** {row['Tipo']}")
                right.write(f"**BancoID:** {row['BancoID']}")

                st.divider()
                e1, e2 = st.columns([1,1])
                op_options = ["Depósito", "Retirada"]
                new_oper = e1.selectbox("Operação", op_options, index=0 if row["Operação"] == "Depósito" else 1, key=f"op_{rec_id}")
                new_val = e2.number_input("Valor (R$)", min_value=0.0, value=float(row["Valor"]), step=10.0, key=f"val_{rec_id}")
                new_date = st.date_input("Data", value=pd.to_datetime(row["Data"]).date(), key=f"date_{rec_id}")

                cat_options = ["Nenhuma"] + (["Salário", "Rendimento", "Transferência recebida", "Outros"] if new_oper == "Depósito" else ["Alimentação", "Transporte", "Contas", "Lazer", "Saúde", "Investimentos", "Outros"])
                new_cat = st.selectbox("Categoria", cat_options, index=cat_options.index(row["Categoria"]) if row["Categoria"] in cat_options else 0, key=f"cat_{rec_id}")
                new_desc = st.text_input("Descrição", value=row["Descrição"] or "", key=f"desc_{rec_id}")

                b1, b2 = st.columns([1,1])
                if b1.button("💾 Salvar alterações", key=f"save_{rec_id}"):
                    full_hist = pd.read_csv(HIST_PATH)
                    full_hist["Data"] = pd.to_datetime(full_hist["Data"], errors="coerce")
                    idx = full_hist.index[full_hist["ID"] == rec_id].tolist()
                    if not idx:
                        st.error("Registro não encontrado.")
                        st.stop()
                    idx = idx[0]

                    old_row = full_hist.loc[idx]
                    old_effect = old_row["Valor"] if old_row["Operação"] == "Depósito" else -old_row["Valor"]
                    new_effect = new_val if new_oper == "Depósito" else -new_val

                    mask_main = (df["Nome"] == old_row["Nome"]) & (df["Tipo"] == old_row["Tipo"])
                    if not any(mask_main):
                        st.error("Conta associada não encontrada no banco de dados.")
                        st.stop()
                    current_balance = float(df.loc[mask_main, "Saldo"].iloc[0])
                    proposed_balance = current_balance - old_effect + new_effect

                    if proposed_balance < 0:
                        st.error("Alteração inválida: resultaria em saldo negativo.")
                        st.stop()

                    df.loc[mask_main, "Saldo"] = proposed_balance
                    save_data(df)

                    full_hist.loc[idx, "Data"] = pd.to_datetime(new_date).strftime("%Y-%m-%d 00:00:00")
                    full_hist.loc[idx, "Operação"] = new_oper
                    full_hist.loc[idx, "Valor"] = float(new_val)
                    full_hist.loc[idx, "Categoria"] = "" if new_cat == "Nenhuma" else new_cat
                    full_hist.loc[idx, "Descrição"] = new_desc
                    full_hist.to_csv(HIST_PATH, index=False)

                    st.success("✅ Registro atualizado com sucesso!")
                    st.rerun()

                if b2.button("❌ Excluir", key=f"del_{rec_id}"):
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

# -----------------------------
# Aba Visualização (Dashboard)
# -----------------------------
with tab_vis:
    st.subheader("📊 Dashboard e Relatórios")

    # Prepare data
    if hist_df.empty:
        st.info("Ainda não há histórico suficiente para gerar gráficos.")
    else:
        # Filtros
        col_k1, col_k2, col_k3 = st.columns([1,1,2])
        date_range = col_k1.date_input("Intervalo de tempo", value=(pd.to_datetime(hist_df["Data"].min()).date() if not pd.isna(hist_df["Data"].min()) else date.today(), pd.to_datetime(hist_df["Data"].max()).date() if not pd.isna(hist_df["Data"].max()) else date.today()))
        tipo_filter = col_k2.selectbox("Tipo", options=["Todos","Banco","Investimento"], index=0)
        cat_list = sorted(hist_df["Categoria"].dropna().unique().tolist())
        cat_sel = col_k3.multiselect("Categorias", options=cat_list, default=[])

        gdf = hist_df.copy()
        gdf["Data"] = pd.to_datetime(gdf["Data"], errors="coerce")

        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            start_dt, end_dt = date_range
            gdf = gdf[(gdf["Data"].dt.date >= pd.to_datetime(start_dt).date()) & (gdf["Data"].dt.date <= pd.to_datetime(end_dt).date())]
        if tipo_filter != "Todos":
            gdf = gdf[gdf["Tipo"] == tipo_filter]
        if cat_sel:
            gdf = gdf[gdf["Categoria"].isin(cat_sel)]

        if gdf.empty:
            st.info("Sem dados no período/combinação selecionada.")
        else:
            # KPIs
            total_deposit = gdf[gdf["Operação"] == "Depósito"]["Valor"].sum()
            total_withdraw = gdf[gdf["Operação"] == "Retirada"]["Valor"].sum()
            net_flow = total_deposit - total_withdraw
            total_banks = df[df["Tipo"]=="Banco"]["Saldo"].sum()
            total_invest = df[df["Tipo"]=="Investimento"]["Saldo"].sum()

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("💵 Saldo em Bancos", f"R$ {total_banks:,.2f}")
            k2.metric("📈 Saldo em Investimentos", f"R$ {total_invest:,.2f}")
            k3.metric("🔁 Fluxo líquido (período)", f"R$ {net_flow:,.2f}", delta=f"Entradas: R$ {total_deposit:,.2f} | Saídas: R$ {total_withdraw:,.2f}")
            last_date = gdf["Data"].max()
            k4.metric("📅 Última movimentação no filtro", last_date.strftime("%d/%m/%Y") if pd.notna(last_date) else "—")

            # Evolution line
            temp = gdf.sort_values("Data").copy()
            temp["Efeito"] = temp.apply(lambda r: r["Valor"] if r["Operação"] == "Depósito" else -r["Valor"], axis=1)
            grouped = temp.groupby([temp["Data"].dt.date, "Tipo"])["Efeito"].sum().reset_index()
            pivot = grouped.pivot(index="Data", columns="Tipo", values="Efeito").fillna(0).sort_index()
            for colname in ["Banco", "Investimento"]:
                if colname not in pivot.columns:
                    pivot[colname] = 0.0
            cum = pivot.cumsum().reset_index().rename(columns={"index":"Data"})
            if cum.empty:
                st.info("Sem dados válidos para gráficos de evolução.")
            else:
                fig_line = px.line(cum.melt(id_vars="Data", value_vars=[c for c in ["Banco","Investimento"] if c in cum.columns], var_name="Tipo", value_name="Saldo acumulado"),
                                   x="Data", y="Saldo acumulado", color="Tipo", title="Evolução do saldo acumulado")
                fig_line.update_layout(hovermode="x unified", template="simple_white", height=360)
                st.plotly_chart(fig_line, use_container_width=True)

            
            graph1, graph2 = st.columns([1,1])
            # Monthly cash flow
            gdf_month = gdf.copy()
            gdf_month["Mes"] = gdf_month["Data"].dt.to_period("M").dt.to_timestamp()
            monthly = gdf_month.groupby([gdf_month["Mes"], "Operação"])["Valor"].sum().unstack(fill_value=0).reset_index()
            if not monthly.empty:
                monthly = monthly.sort_values("Mes")
                fig_bar = px.bar(monthly, x="Mes", y=[c for c in monthly.columns if c!="Mes"], barmode="group", title="Fluxo mensal (Entradas vs Saídas)")
                fig_bar.update_layout(xaxis_title="Mês", yaxis_title="Valor (R$)", template="simple_white", height=360)
                graph1.plotly_chart(fig_bar, use_container_width=True)

            # Distribution by category
            gastos = gdf[gdf["Operação"] == "Retirada"]
            if not gastos.empty:
                fig_pie = px.pie(gastos, names="Categoria", values="Valor", hole=0.4, title="Distribuição de gastos por categoria")
                fig_pie.update_traces(textinfo="label+percent")
                graph2.plotly_chart(fig_pie, use_container_width=True)

            # Detailed table
            st.markdown("### 📋 Tabela detalhada")
            table = gdf.copy()
            table["Data"] = table["Data"].dt.strftime("%d/%m/%Y")
            st.dataframe(table[["Data","Operação","Nome","Tipo","Valor","Categoria","Descrição"]].sort_values("Data", ascending=False), use_container_width=True)

# -----------------------------
# Aba Transações Futuras
# -----------------------------
with tab_future:
    st.subheader("🔮 Agendar transações futuras")

    with st.form("form_future", clear_on_submit=False):
        tipo_fut = st.radio("Tipo de conta:", ["Banco", "Investimento"], horizontal=True)
        df_tipo_fut = df[df["Tipo"] == tipo_fut]
        nome_fut = st.selectbox(f"Selecione o {tipo_fut.lower()}:", df_tipo_fut["Nome"].unique())
        item_fut = df_tipo_fut[df_tipo_fut["Nome"] == nome_fut].iloc[0]

        operacao_fut = st.radio("Operação:", ["Depósito / Adição", "Retirada / Gasto"], horizontal=True)
        valor_fut = st.number_input("💵 Valor (R$):", min_value=0.0, step=10.0)
        data_fut = st.date_input("📅 Data inicial:", value=date.today())

        # Recorrência
        recorr_opts = {"Nenhuma":"none", "Semanal":"weekly", "Quinzenal":"biweekly", "Mensal":"monthly"}
        recorr_display = st.selectbox("Recorrência:", options=list(recorr_opts.keys()), index=0, help="Escolha 'Nenhuma' para agendamento único.")
        recorr = recorr_opts[recorr_display]

        dur_meses = st.number_input("Duração (em meses):", min_value=1, max_value=12, value=1, step=1, help="Limite máximo: 12 meses (Apenas para recorrência).")

        categorias_fut = ["Salário", "Rendimento", "Transferência recebida", "Outros"] if operacao_fut.startswith("Depósito") else ["Alimentação", "Transporte", "Contas", "Lazer", "Saúde", "Investimentos", "Outros"]
        categoria_fut = st.selectbox("Categoria (opcional):", ["Nenhuma"] + categorias_fut)
        descricao_fut = st.text_input("Descrição (opcional):")

        submit_fut = st.form_submit_button("💾 Agendar")
        if submit_fut:
            if valor_fut <= 0:
                st.error("Valor deve ser maior que zero.")
            elif pd.to_datetime(data_fut).date() < date.today():
                st.error("Data inicial não pode ser no passado.")
            else:
                future_df = load_future()
                new_id = int(future_df["ID"].max()) + 1 if not future_df.empty else 1
                entry = {
                    "ID": new_id,
                    "BancoID": int(item_fut["ID"]),
                    "Tipo": tipo_fut,
                    "Nome": nome_fut,
                    "Data": pd.Timestamp(data_fut).strftime("%Y-%m-%d"),
                    "Operação": "Depósito" if operacao_fut.startswith("Depósito") else "Retirada",
                    "Valor": float(valor_fut),
                    "Categoria": "" if categoria_fut == "Nenhuma" else categoria_fut,
                    "Descrição": descricao_fut or "",
                    "Recorrencia": recorr,
                    "Duracao_meses": int(dur_meses) if recorr != "none" else 0
                }
                future_df = pd.concat([future_df, pd.DataFrame([entry])], ignore_index=True)
                save_future(future_df)
                st.success("Agendamento salvo com sucesso.")
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Agendamentos Ativos")

    future_df = load_future()
    # -----------------------------
    # Visualização de movimentações futuras
    # -----------------------------
    if future_df.empty:
        st.info("Nenhum agendamento futuro cadastrado.")
    else:
        for _, sched in future_df.sort_values("Data").iterrows():
            sched_id = int(sched["ID"])
            sched_name = f"{pd.to_datetime(sched['Data']).strftime('%d/%m/%Y')} — {sched['Operação']} — {sched['Nome']} — R$ {float(sched['Valor']):,.2f}"
            with st.expander(sched_name):

                aa_c1, aa_c2 = st.columns(2)
                aa_c1.write(f"**Conta:** {sched['Nome']}")
                aa_c2.write(f"**Tipo:** {sched['Tipo']}")
                aa_c1.write(f"**Descrição:** {sched.get('Descrição','—')}")
                aa_c2.write(f"**Categoria:** {sched.get('Categoria','—')}")
                rec_display = sched.get("Recorrencia", "none")
                rec_readable = {"none":"Nenhuma", "weekly":"Semanal", "biweekly":"Quinzenal", "monthly":"Mensal"}.get(rec_display, "Nenhuma")
                aa_c1.write(f"**Recorrência:** {rec_readable}")
                aa_c2.write(f"**Duração (meses):** {int(sched.get('Duracao_meses') or 0)}")

                st.divider()

                # Calcula instâncias a partir do agendamento
                occs_all = generate_occurrences(
                    sched["Data"],
                    sched.get("Recorrencia", "none"),
                    int(sched.get("Duracao_meses") or 0)
                )

                # Remove da lista as que estão em future_exclusions
                occs = [
                    d for d in occs_all
                    if f"{sched_id}_{pd.to_datetime(d).strftime('%Y-%m-%d')}" not in future_exclusions
                ]

                if not occs:
                    st.success("Todas as transações foram realizadas.")
                else:
                    for d in occs:
                        d_str = pd.to_datetime(d).strftime("%d/%m/%Y")
                        cols = st.columns([2, 1, 1])
                        cols[0].write(f"📅 {d_str} — R$ {float(sched['Valor']):,.2f}")

                        # REGISTRAR MOVIMENTAÇÃO
                        if cols[1].button("✔️ Realizar", key=f"exec_{sched_id}_{d_str}"):
                            df_full = load_data()
                            hist_full = pd.read_csv(HIST_PATH) if HIST_PATH.exists() else pd.DataFrame(columns=["ID","BancoID","Tipo","Nome","Data","Operação","Valor","Categoria","Descrição"])

                            mask_bank = (df_full["ID"].astype(int) == int(sched["BancoID"])) & (df_full["Nome"] == sched["Nome"])

                            if not mask_bank.any():
                                st.error("Conta não encontrada (ID). Atualize a página.")
                                st.stop()
                            current_balance_fut = float(df_full.loc[mask_bank, "Saldo"].iloc[0])
                            new_effect_fut = float(sched["Valor"]) if sched["Operação"] == "Depósito" else -float(sched["Valor"])
                            new_balance_fut = current_balance_fut + new_effect_fut
                            if new_balance_fut < 0:
                                st.error("Saldo insuficiente para realizar a transação.")
                            else:
                                df_full.loc[mask_bank, "Saldo"] = new_balance_fut
                                save_data(df_full)

                                new_hist_id = int(hist_full["ID"].max()) + 1 if not hist_full.empty else 1
                                hist_entry = {
                                    "ID": new_hist_id,
                                    "BancoID": int(sched["BancoID"]),
                                    "Tipo": sched["Tipo"],
                                    "Nome": sched["Nome"],
                                    "Data": pd.to_datetime(d).strftime("%Y-%m-%d"),
                                    "Operação": sched["Operação"],
                                    "Valor": float(sched["Valor"]),
                                    "Categoria": sched.get("Categoria",""),
                                    "Descrição": sched.get("Descrição","")
                                }
                                hist_full = pd.concat([hist_full, pd.DataFrame([hist_entry])], ignore_index=True)
                                hist_full.to_csv(HIST_PATH, index=False)

                                exclusion_key = f"{sched_id}_{pd.to_datetime(d).strftime('%Y-%m-%d')}"
                                future_exclusions.add(exclusion_key)
                                save_future_exclusions(future_exclusions)

                                st.success(f"Transação realizada para {d_str} (salvo no histórico).")
                                st.rerun()

                        if cols[2].button("🗑️ Remover instância", key=f"reminst_{sched_id}_{d_str}"):
                            exclusion_key = f"{sched_id}_{pd.to_datetime(d).strftime('%Y-%m-%d')}"

                            future_exclusions.add(exclusion_key)
                            save_future_exclusions(future_exclusions)

                            st.success(f"Instância de {sched['Operação']} em {d_str} foi ignorada com sucesso.")
                            st.rerun()

                st.markdown("---")

                col_a, col_b = st.columns([1,1])
                if col_a.button("✔️ Realizar todas as movimentações futuras", key=f"exec_all_{sched_id}"):
                    df_full = load_data()
                    hist_full = pd.read_csv(HIST_PATH) if HIST_PATH.exists() else pd.DataFrame(columns=["ID","BancoID","Tipo","Nome","Data","Operação","Valor","Categoria","Descrição"])
                    executed = 0
                    skipped = 0
                    for d in occs:
                        mask_bank = (df_full["ID"].astype(int) == int(sched["BancoID"])) & (df_full["Nome"] == sched["Nome"])
                        current_balance_fut = float(df_full.loc[mask_bank, "Saldo"].iloc[0])
                        new_effect_fut = float(sched["Valor"]) if sched["Operação"] == "Depósito" else -float(sched["Valor"])
                        new_balance_fut = current_balance_fut + new_effect_fut
                        if new_balance_fut < 0:
                            skipped += 1
                            continue
                        df_full.loc[mask_bank, "Saldo"] = new_balance_fut
                        new_hist_id = int(hist_full["ID"].max()) + 1 if not hist_full.empty else 1
                        hist_entry = {
                            "ID": new_hist_id,
                            "BancoID": int(sched["BancoID"]),
                            "Tipo": sched["Tipo"],
                            "Nome": sched["Nome"],
                            "Data": pd.to_datetime(d).strftime("%Y-%m-%d"),
                            "Operação": sched["Operação"],
                            "Valor": float(sched["Valor"]),
                            "Categoria": sched.get("Categoria",""),
                            "Descrição": sched.get("Descrição","")
                        }
                        hist_full = pd.concat([hist_full, pd.DataFrame([hist_entry])], ignore_index=True)
                        executed += 1

                        exclusion_key = f"{sched_id}_{pd.to_datetime(d).strftime('%Y-%m-%d')}"
                        future_exclusions.add(exclusion_key)


                    save_data(df_full)
                    hist_full.to_csv(HIST_PATH, index=False)
                    st.success(f"Executadas {executed} instâncias. {skipped} foram puladas por saldo insuficiente.")
                    st.rerun()

                if col_b.button("🗑️ Remover agendamento", key=f"del_sched_{sched_id}"):
                        future_df = future_df[future_df["ID"] != sched_id].reset_index(drop=True)
                        save_future(future_df)
                        st.warning("Agendamento removido.")
                        st.rerun()

    st.markdown("---")
    if st.button("🧹 Limpar agendamentos concluídos"):
        future_df = load_future()
        future_exclusions = load_future_exclusions()

        keep = []
        removed = 0

        for _, s in future_df.iterrows():
            sched_id = int(s["ID"])
            rec = s.get("Recorrencia", "none")
            dur = int(s.get("Duracao_meses") or 0)
            occs = generate_occurrences(s["Data"], rec, dur)

            exclusion_keys = {f"{sched_id}_{pd.to_datetime(d).strftime('%Y-%m-%d')}" for d in occs}
            all_done = all(k in future_exclusions for k in exclusion_keys)

            if not all_done:
                keep.append(s)
            else:
                removed += 1

        newf = pd.DataFrame(keep)
        save_future(newf)

        st.success(f"Limpeza concluída. {removed} agendamento(s) concluído(s) foram removidos.")
        st.rerun()
