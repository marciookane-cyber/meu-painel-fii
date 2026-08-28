import re
import pandas as pd
import streamlit as st
import yfinance as yf

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

# ⚠️ INSIRA AQUI O LINK DA SUA PLANILHA:
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1fbj9LrGZScPGZ8mHTqsDshS01pPPFjEu0pIZFmwAUDg/edit?usp=sharing"

# -----------------------------------------------------------------------------
# 2. CARREGAMENTO DOS DADOS VIA DOWNLOAD DIRETO EM CSV
# -----------------------------------------------------------------------------


def extrair_sheet_id(url):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    return match.group(1) if match else None


@st.cache_data(ttl=60)
def load_data(url):
    sheet_id = extrair_sheet_id(url)
    if not sheet_id or "COLE_AQUI" in url:
        st.error(
            "⚠️ Por favor, cole a URL válida da sua planilha na variável URL_PLANILHA no código."
        )
        st.stop()

    # Monta a URL direta para exportar a aba "Carteira" em formato CSV
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Carteira"

    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(
            "❌ Erro ao acessar a planilha. Certifique-se de que o acesso da planilha está configurado para 'Qualquer pessoa com o link'."
        )
        st.stop()


df_carteira = load_data(URL_PLANILHA)


# -----------------------------------------------------------------------------
# 3. BUSCA DE COTAÇÕES E P/VP EM TEMPO REAL (YFINANCE)
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

            # Tenta pegar o P/VP direto ou calcula (Cotação / VP)
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
# 4. TRATAMENTO E CÁLCULOS DOS DADOS
# -----------------------------------------------------------------------------
# Trata nome da coluna principal
if "FII" in df_carteira.columns and "Ticker" not in df_carteira.columns:
    df_carteira["Ticker"] = df_carteira["FII"]

df_carteira["Cotação Atual (R$)"] = df_carteira["Ticker"].map(
    lambda x: market_data.get(x, {}).get("cotacao", 0.0)
)
df_carteira["P/VP"] = df_carteira["Ticker"].map(
    lambda x: market_data.get(x, {}).get("pvp", 0.0)
)
df_carteira["Meta"] = df_carteira["Ticker"].map(METAS_COTAS)

# Mapeia dinamicamente os nomes das colunas de Cotas e Preço Médio
col_cotas = "Cotas" if "Cotas" in df_carteira.columns else "Cotas Atuais"
col_pm = (
    "Preço Médio (R$)"
    if "Preço Médio (R$)" in df_carteira.columns
    else "Preço Médio"
)

df_carteira["Cotas"] = pd.to_numeric(
    df_carteira[col_cotas], errors="coerce"
).fillna(0)
df_carteira["Preço Médio (R$)"] = pd.to_numeric(
    df_carteira[col_pm], errors="coerce"
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

# Regra IRIM11 (Stand-by)
df_carteira.loc[df_carteira["Ticker"] == "IRIM11", "Progresso (%)"] = 100.0
df_carteira.loc[df_carteira["Ticker"] == "IRIM11", "Cotas Faltantes"] = 0
df_carteira.loc[df_carteira["Ticker"] == "IRIM11", "Déficit Financeiro (R$)"] = (
    0.0
)

df_carteira["FII"] = df_carteira["Ticker"]

# -----------------------------------------------------------------------------
# 5. CARDS DE RESUMO (KPIS)
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
# 6. RECOMENDAÇÃO INTELIGENTE DE APORTE
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
# 7. TABELA COMPLETA DE POSIÇÃO
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
if "Provento/Cota (R$)" in df_carteira.columns:
    cols_exibir.append("Provento/Cota (R$)")

st.dataframe(
    df_carteira[cols_exibir],
    use_container_width=True,
    column_config={
        "Preço Médio (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Cotação Atual (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Patrimônio (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "P/VP": st.column_config.NumberColumn(format="%.2f"),
    },
)
