import pandas as pd
import streamlit as st
import yfinance as yf
from streamlit_gsheets import GSheetsConnection

# -----------------------------------------------------------------------------
# 0. CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Dashboard de FIIs & Equalização", layout="wide")

st.title("📊 Dashboard de FIIs & Projeto Equalização")

# -----------------------------------------------------------------------------
# 1. METAS FIXAS DE COTAS
# -----------------------------------------------------------------------------
METAS_COTAS = {
    "ALZR11": 1500,
    "GGRC11": 1500,
    "XPML11": 150,
    "PMALL11": 150,
    "BTLG11": 150,
    "BRCO11": 150,
    "IRIM11": 163,  # Stand-by / 100% Concluído
}

# ⚠️ INSIRA AQUI O LINK COMPLETO DA SUA PLANILHA:
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1fbj9LrGZScPGZ8mHTqsDshS01pPPFjEu0pIZFmwAUDg/edit?usp=sharing"

# -----------------------------------------------------------------------------
# 2. CONEXÃO E CARREGAMENTO DOS DADOS (STREAMLIT GSHEETS)
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=60)
def load_data():
    if "COLE_AQUI" in URL_PLANILHA:
        st.error(
            "⚠️ Cole a URL da sua planilha na variável URL_PLANILHA no código."
        )
        st.stop()

    # Lê a aba 'Carteira' preservando a estrutura exata do Google Sheets
    df = conn.read(spreadsheet=URL_PLANILHA, worksheet="Carteira")
    return df


df_carteira = load_data()

# -----------------------------------------------------------------------------
# 3. PADRONIZAÇÃO DE COLUNAS
# -----------------------------------------------------------------------------
# Limpa espaços extras nos nomes das colunas da planilha
df_carteira.columns = df_carteira.columns.astype(str).str.strip()

# Identifica a coluna do código do FII (Ticker / FII)
col_fii = next(
    (
        c
        for c in df_carteira.columns
        if c.lower() in ["fii", "ticker", "fiis", "ativo"]
    ),
    df_carteira.columns[0],
)
df_carteira["Ticker"] = (
    df_carteira[col_fii].astype(str).str.strip().str.upper()
)

# -----------------------------------------------------------------------------
# 4. BUSCA DE COTAÇÕES E P/VP EM TEMPO REAL (YFINANCE)
# -----------------------------------------------------------------------------


@st.cache_data(ttl=300)
def fetch_market_data(tickers):
    data = {}
    for ticker in tickers:
        try:
            symbol = f"{ticker}.SA"
            t = yf.Ticker(symbol)
            info = t.info
            fast_info = t.fast_info

            cotacao = fast_info.last_price if fast_info.last_price else 0.0

            # Busca P/VP diretamente ou calcula Cotação / VP
            pvp = info.get("priceToBook", None)
            if pvp is None or pvp == 0:
                book_value = info.get("bookValue", 0.0)
                if book_value and book_value > 0 and cotacao > 0:
                    pvp = cotacao / book_value
                else:
                    pvp = 0.0

            data[ticker] = {"cotacao": cotacao, "pvp": round(pvp, 2)}
        except Exception:
            data[ticker] = {"cotacao": 0.0, "pvp": 0.0}
    return data


tickers_list = list(METAS_COTAS.keys())
market_data = fetch_market_data(tickers_list)

# -----------------------------------------------------------------------------
# 5. CÁLCULOS E REGRAS DE NEGÓCIO
# -----------------------------------------------------------------------------
df_carteira["Cotação Atual (R$)"] = df_carteira["Ticker"].map(
    lambda x: market_data.get(x, {}).get("cotacao", 0.0)
)
df_carteira["P/VP"] = df_carteira["Ticker"].map(
    lambda x: market_data.get(x, {}).get("pvp", 0.0)
)
df_carteira["Meta"] = df_carteira["Ticker"].map(METAS_COTAS)

# Mapeia colunas de Cotas e Preço Médio da planilha
col_cotas = next(
    (
        c
        for c in df_carteira.columns
        if c.lower() in ["cotas", "cotas atuais", "qtd"]
    ),
    None,
)
col_pm = next(
    (
        c
        for c in df_carteira.columns
        if "preço" in c.lower() or "pm" in c.lower() or "medio" in c.lower()
    ),
    None,
)

df_carteira["Cotas"] = pd.to_numeric(
    df_carteira[col_cotas] if col_cotas else 0, errors="coerce"
).fillna(0)
df_carteira["Preço Médio (R$)"] = pd.to_numeric(
    df_carteira[col_pm] if col_pm else 0, errors="coerce"
).fillna(0)

# Cálculos Operacionais
df_carteira["Patrimônio (R$)"] = (
    df_carteira["Cotas"] * df_carteira["Cotação Atual (R$)"]
)
df_carteira["Valor Investido"] = (
    df_carteira["Cotas"] * df_carteira["Preço Médio (R$)"]
)
df_carteira["Cotas Faltantes"] = (
    df_carteira["Meta"] - df_carteira["Cotas"]
).clip(lower=0)
df_carteira["Déficit Financeiro (R$)"] = (
    df_carteira["Cotas Faltantes"] * df_carteira["Cotação Atual (R$)"]
)
df_carteira["Progresso (%)"] = (
    (df_carteira["Cotas"] / df_carteira["Meta"]) * 100
).clip(upper=100)

# Regra Especial IRIM11 (Stand-by)
df_carteira.loc[df_carteira["Ticker"] == "IRIM11", "Progresso (%)"] = 100.0
df_carteira.loc[df_carteira["Ticker"] == "IRIM11", "Cotas Faltantes"] = 0
df_carteira.loc[df_carteira["Ticker"] == "IRIM11", "Déficit Financeiro (R$)"] = (
    0.0
)

df_carteira["FII"] = df_carteira["Ticker"]

# -----------------------------------------------------------------------------
# 6. KPIS (CARDS DO TOPO)
# -----------------------------------------------------------------------------
patrimonio_total = df_carteira["Patrimônio (R$)"].sum()
total_investido = df_carteira["Valor Investido"].sum()
lucro_prejuizo = patrimonio_total - total_investido

col1, col2, col3 = st.columns(3)
col1.metric("Patrimônio Total", f"R$ {patrimonio_total:,.2f}")
col2.metric("Total Investido", f"R$ {total_investido:,.2f}")
col3.metric("Resultado (Ganho de Capital)", f"R$ {lucro_prejuizo:,.2f}")

st.divider()

# -----------------------------------------------------------------------------
# 7. RECOMENDAÇÃO INTELIGENTE DE APORTE
# -----------------------------------------------------------------------------
st.subheader("💡 Recomendação Inteligente de Aporte")

col_aporte1, col_aporte2 = st.columns(2)
with col_aporte1:
    aporte_bolso = st.number_input(
        "Aporte do Bolso (R$)", min_value=0.0, value=1000.0, step=100.0
    )
with col_aporte2:
    dividendos_mes = st.number_input(
        "Dividendos Recebidos no Mês (R$)",
        min_value=0.0,
        value=200.0,
        step=50.0,
    )

total_disponivel = aporte_bolso + dividendos_mes
st.info(f"**Total Disponível para Aporte:** R$ {total_disponivel:,.2f}")

df_deficit = df_carteira[df_carteira["Déficit Financeiro (R$)"] > 0].copy()
df_deficit = df_deficit.sort_values(
    by="Déficit Financeiro (R$)", ascending=False
)

if not df_deficit.empty and total_disponivel > 0:
    top2_fiis = df_deficit.head(2).copy()
    metade_aporte = total_disponivel / len(top2_fiis)

    top2_fiis["Aporte Sugerido (R$)"] = metade_aporte
    top2_fiis["Cotas a Comprar"] = (
        top2_fiis["Aporte Sugerido (R$)"] / top2_fiis["Cotação Atual (R$)"]
    ).astype(int)
    top2_fiis["Custo Efetivo (R$)"] = (
        top2_fiis["Cotas a Comprar"] * top2_fiis["Cotação Atual (R$)"]
    )

    st.write("**Sugestão de Aporte (Dividido entre os 2 mais atrasados):**")
    st.dataframe(
        top2_fiis[
            [
                "FII",
                "Cotação Atual (R$)",
                "Déficit Financeiro (R$)",
                "Cotas a Comprar",
                "Custo Efetivo (R$)",
            ]
        ],
        use_container_width=True,
    )
else:
    st.success("Todas as metas foram atingidas ou nenhum aporte foi informado!")

st.divider()

# -----------------------------------------------------------------------------
# 8. TABELA COMPLETA DE POSIÇÃO (VISUAL EXATO DA IMAGEM)
# -----------------------------------------------------------------------------
st.subheader("📋 Tabela Completa de Posição")

cols_exibir = [
    "FII",
    "Cotas",
    "Meta",
    "Preço Médio (R$)",
    "Cotação Atual (R$)",
    "P/VP",
    "Patrimônio (R$)",
]

# Inclui colunas adicionais da sua planilha se existirem (ex: Provento/Cota)
for c in df_carteira.columns:
    if "provento" in c.lower() or "rendimento" in c.lower():
        if c not in cols_exibir:
            cols_exibir.append(c)

st.dataframe(
    df_carteira[cols_exibir],
    use_container_width=True,
    column_config={
        "Cotas": st.column_config.NumberColumn(format="%d"),
        "Meta": st.column_config.NumberColumn(format="%d"),
        "Preço Médio (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Cotação Atual (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Patrimônio (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "P/VP": st.column_config.NumberColumn(format="%.2f"),
    },
)
