# Instruções rápidas para agentes de código (Copilot / AI)

Resumo curto
- Projeto: Painel financeiro simples em Streamlit para gerenciar bancos e investimentos.
- Estrutura principal: `app.py` (landing), `pages/` (páginas multipage), `data/db.py` (CRUD CSV), `data/db.csv` e `data/history.csv` (persistência simples).

Como executar (Windows / PowerShell)
```powershell
# crie/ative um virtualenv (opcional)
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install streamlit pandas plotly
python -m streamlit run app.py
```

Visão arquitetural (o "porquê")
- UI: `app.py` é a página inicial; arquivos em `pages/` são páginas separadas automaticamente carregadas pelo Streamlit.
- Persistência: simples CSVs em `data/`. `data/db.py` encapsula acesso a `db.csv` (colunas: ID, Tipo, Nome, Saldo, Detalhes).
- Histórico: `data/history.csv` armazena lançamentos (colunas esperadas: ID, BancoID, Tipo, Nome, Data, Operação, Valor, Categoria, Descrição).

Contratos e funções importantes (exemplos reais)
- `data.db.load_data()` → pandas.DataFrame com colunas ["ID","Tipo","Nome","Saldo","Detalhes"].
- `data.db.save_data(df)` → sobrescreve `data/db.csv`.
- `data.db.add_entry(tipo, nome, saldo, detalhes="")` → lida com duplicados (para `Banco`) e gera ID incremental.
- Padrão de `Tipo`: literalmente "Banco" ou "Investimento" (usa-se em filtros e lógica de negócio).

Padrões e convenções do projeto
- IDs são inteiros incrementais e estáveis; busca/edição prefere ID quando disponível.
- Nomes são comparados normalmente com `.str.lower()` em verificações de duplicação.
- Saldos são armazenados como números (float) na coluna `Saldo` do CSV.
- Datas no histórico são gravadas em formato `YYYY-MM-DD` (às vezes com hora `YYYY-MM-DD 00:00:00`).
- Compatibilidade retroativa: várias páginas fazem mapping quando `BancoID` está ausente — alterar esquema exige atualizar os mapeamentos em `pages/3_manage_banks.py` e `pages/4_quick_actions.py`.

Fluxos críticos que um agente deve conhecer
- Adicionar banco/investimento: UI em `pages/3_manage_banks.py` chama `data.db.add_entry`.
- Atualizar saldo + histórico: `pages/4_quick_actions.py` atualiza `data/db.csv` via `save_data()` e acrescenta linha em `data/history.csv` sem sobrescrever datas antigas.
- Renomear item: quando um `Nome` muda, o código atual atualiza também `history.csv` (prefere `BancoID` quando presente, senão faz fallback por Nome+Tipo).
- Remoção: ao remover um registro o código tenta excluir transações associadas (por `BancoID` ou por Nome+Tipo se `BancoID` ausente).

Erros e verificações que já existem (para não duplicar lógica)
- Validação de saldo negativo: operações que causariam saldo negativo são bloqueadas nas páginas (ver `pages/4_quick_actions.py`).
- Duplicados: `add_entry` impede cadastrar dois bancos com mesmo nome (case-insensitive).

Como modificar dados/estrutura com segurança
- Ao adicionar uma nova coluna ao DB/CVs: atualizar `data/db.py` (COLUMNS), revisar todas as páginas que indexam colunas por nome.
- Ao alterar formato de data ou nome de coluna em `history.csv`: certificar-se de adaptar as rotinas de compatibilidade em `pages/3_manage_banks.py` e `pages/4_quick_actions.py`.

Exemplos rápidos que ajudam a editar o projeto
- Para mostrar um novo campo na lista de bancos, edite `pages/3_manage_banks.py` na seção que renderiza `st.expander` e use `row['SeuCampo']`.
- Para adicionar validação extra ao salvar um investimento, estenda `data/db.add_entry` (retorna dict com chave `duplicado` atualmente).

Observações finais
- Não há CI/testes automáticos no repo — adicione testes unitários para `data/db.py` se desejar segurança ao refatorar IDs/CSV.
- Arquivo `requirements.txt` não existe; prefira instalar `streamlit,pandas,plotly` no ambiente.

Se algo ficar ambíguo, diga qual comportamento deseja (ex.: normalizar fuso horário das datas, forçar BancoID inteiro, mover persitência para SQLite) e eu ajusto as instruções.
