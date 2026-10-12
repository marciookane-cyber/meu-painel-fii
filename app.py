import datetime
import json
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from streamlit_gsheets import GSheetsConnection

# ------------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Painel de FIIs - Equalização",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

LOCAL_STORAGE_FILE = "carteira_backup_local.csv"
SALDO_STORAGE_FILE = "saldo_config.json"

# ------------------------------------------------------------------------------
# ESTILIZAÇÃO CSS CUSTOMIZADA
# ------------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b0e14 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    h1, h2, h3, h4, h5, h6, p, label, span {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    h1 {
        font-weight: 900 !important;
        letter-spacing: -0.5px;
    }
    [data-testid="stMetric"] {
        background-color: #151922 !important;
        border: 1px solid #232936 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4) !important;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #00d092 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #94a3b8 !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.65rem !important;
        font-weight: 900 !important;
        color: #ffffff !important;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid #232936;
        border-radius: 12px;
        overflow: hidden;
    }
    [data-testid="stDataFrame"] div[role="columnheader"] {
        background-color: #151922 !important;
        color: #ffffff !important;
        font-weight: 800 !important;
    }
    [data-testid="stDataFrame"] div[role="gridcell"] {
        background-color: #0b0e14 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #151922 !important;
        border-right: 1px solid #232936 !important;
    }
    [data-testid="stSidebar"] label {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 800 !important;
        border: none;
        background-color: #00d092 !important;
        color: #0b0e14 !important;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #00e6a1 !important;
        box-shadow: 0 4px 15px rgba(0, 208, 146, 0.4);
        color: #0b0e14 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #232936;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #151922;
        border-radius: 6px 6px 0px 0px;
        color: #ffffff !important;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00d092 !important;
        color: #0b0e14 !important;
        font-weight: 900 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# CONEXÃO E GERENCIAMENTO DE CARTEIRA
# ------------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

# Dados base da sua planilha para evitar que o app abra zerado
DADOS_BASE_INICIAIS = [
    {"fii": "ALZR11", "cotas": 1500, "preco_medio": 10.76, "dy_anual (%)": 8.50, "provento_mensal_cota": 0.07, "dividendo_acumulado_historico": 105.00},
    {"fii": "BTLG11", "cotas": 60, "preco_medio": 96.98, "dy_anual (%)": 9.10, "provento_mensal_cota": 0.78, "dividendo_acumulado_historico": 46.80},
    {"fii": "BRCO11", "cotas": 20, "preco_medio": 99.61, "dy_anual (%)": 8.80, "provento_mensal_cota": 0.87, "dividendo_acumulado_historico": 17.40},
    {"fii": "XPML11", "cotas": 106, "preco_medio": 110.20, "dy_anual (%)": 9.00, "provento_mensal_cota": 0.92, "dividendo_acumulado_historico": 97.52},
    {"fii": "PMLL11", "cotas": 32, "preco_medio": 103.03, "dy_anual (%)": 8.90, "provento_mensal_cota": 0.90, "dividendo_acumulado_historico": 28.80},
    {"fii": "GGRC11", "cotas": 1010, "preco_medio": 11.20, "dy_anual (%)": 10.50, "provento_mensal_cota": 0.09, "dividendo_acumulado_historico": 90.90},
    {"fii": "IRIM11", "cotas": 163, "preco_medio": 60.86, "dy_anual (%)": 16.54, "provento_mensal_cota": 0.72, "dividendo_acumulado_historico": 117.36},
]

def carregar_dados_iniciais():
    # 1. Tenta carregar da conexão remota do Google Sheets
    try:
        data = conn.read(ttl="0s")
        if not data.empty and "fii" in data.columns and len(data) > 0:
            if pd.to_numeric(data["cotas"], errors="coerce").sum() > 0:
                return data.copy()
    except Exception:
        pass

    # 2. Tenta carregar do arquivo local de backup
    if os.path.exists(LOCAL_STORAGE_FILE):
        try:
            df_local = pd.read_csv(LOCAL_STORAGE_FILE)
            if not df_local.empty and "fii" in df_local.columns and df_local["cotas"].sum() > 0:
                return df_local.copy()
        except Exception:
            pass

    # 3. Fallback: Usa os dados exatos da planilha
    return pd.DataFrame(DADOS_BASE_INICIAIS)


df_carteira = carregar_dados_iniciais()

colunas_numericas = [
    "cotas",
    "preco_medio",
    "dy_anual (%)",
    "provento_mensal_cota",
    "dividendo_acumulado_historico",
]

for col in colunas_numericas:
    if col in df_carteira.columns:
        df_carteira[col] = pd.to_numeric(
            df_carteira[col].astype(str).str.replace(",", "."),
            errors="coerce",
        ).fillna(0.0)

fiis = ["ALZR11", "XPML11", "GGRC11", "PMLL11", "BTLG11", "BRCO11", "IRIM11"]


@st.cache_data(ttl=300)
def obter_cotacoes_b3(tickers):
    dados = {}
    for t in tickers:
        try:
            ticker_b3 = f"{t}.SA"
            info = yf.Ticker(ticker_b3).fast_info
            price = float(info.get("lastPrice", 0.0))
            dados[t] = price
        except Exception:
            dados[t] = 0.0
    return dados


cotacoes_atuais = obter_cotacoes_b3(fiis)


def obter_meta(row):
    ticker = str(row["fii"]).strip().upper()
    metas_fixas = {
        "ALZR11": 1500,
        "XPML11": 150,
        "GGRC11": 1500,
        "PMLL11": 150,
        "PMALL11": 150,
        "BTLG11": 150,
        "BRCO11": 150,
    }
    if ticker in metas_fixas:
        return metas_fixas[ticker]
    elif ticker == "IRIM11":
        return row["cotas"] if row["cotas"] > 0 else 163
    return 150


df_carteira["meta"] = df_carteira.apply(obter_meta, axis=1)
df_carteira["cotacao_atual"] = df_carteira["fii"].map(cotacoes_atuais)

df_carteira["cotacao_atual"] = df_carteira.apply(
    lambda r: r["preco_medio"]
    if r["cotacao_atual"] == 0 or pd.isna(r["cotacao_atual"])
    else r["cotacao_atual"],
    axis=1,
)

# Cálculos de Métricas
df_carteira["patrimonio_atual"] = (
    df_carteira["cotas"] * df_carteira["cotacao_atual"]
)
df_carteira["total_investido"] = (
    df_carteira["cotas"] * df_carteira["preco_medio"]
)
df_carteira["lucro_ganho_capital"] = (
    df_carteira["patrimonio_atual"] - df_carteira["total_investido"]
)
df_carteira["dividendo_mensal_total"] = (
    df_carteira["cotas"] * df_carteira["provento_mensal_cota"]
)

df_carteira["dy_mensal_pct"] = df_carteira.apply(
    lambda r: (r["provento_mensal_cota"] / r["cotacao_atual"] * 100)
    if r["cotacao_atual"] > 0
    else 0.0,
    axis=1,
)

df_carteira["progresso_meta"] = df_carteira.apply(
    lambda r: (r["cotas"] / r["meta"] * 100) if r["meta"] > 0 else 100.0, axis=1
)

df_carteira["cotas_faltantes"] = (
    (df_carteira["meta"] - df_carteira["cotas"]).clip(lower=0).astype(int)
)
df_carteira["valor_restante_meta"] = (
    df_carteira["cotas_faltantes"] * df_carteira["cotacao_atual"]
)

dividendos_mes_total = float(df_carteira["dividendo_mensal_total"].sum())

# ------------------------------------------------------------------------------
# GERENCIAMENTO E PERSISTÊNCIA DO SALDO
# ------------------------------------------------------------------------------


def carregar_config_saldo():
    saldo_default = {
        "valor_bolso": 1000.0,
        "ajuste_operacoes": 0.0,
    }
    if os.path.exists(SALDO_STORAGE_FILE):
        try:
            with open(SALDO_STORAGE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return saldo_default


def salvar_config_saldo(valor_bolso, ajuste_operacoes):
    dados = {
        "valor_bolso": float(valor_bolso),
        "ajuste_operacoes": float(ajuste_operacoes),
    }
    try:
        with open(SALDO_STORAGE_FILE, "w") as f:
            json.dump(dados, f)
    except Exception:
        pass


saldo_cfg = carregar_config_saldo()

if "valor_bolso_custom" not in st.session_state:
    st.session_state.valor_bolso_custom = saldo_cfg.get("valor_bolso", 1000.0)

if "ajuste_saldo_operacoes" not in st.session_state:
    st.session_state.ajuste_saldo_operacoes = saldo_cfg.get(
        "ajuste_operacoes", 0.0
    )


def salvar_dados_permanente(df_para_salvar):
    st.session_state["df_carteira_override"] = df_para_salvar.copy()

    df_salvar = df_para_salvar[[
        "fii",
        "cotas",
        "preco_medio",
        "dy_anual (%)",
        "provento_mensal_cota",
        "dividendo_acumulado_historico",
    ]].copy()

    try:
        df_salvar.to_csv(LOCAL_STORAGE_FILE, index=False)
    except Exception:
        pass

    try:
        conn.update(data=df_salvar)
    except Exception:
        pass

    salvar_config_saldo(
        st.session_state.valor_bolso_custom,
        st.session_state.ajuste_saldo_operacoes,
    )
    return True


# ------------------------------------------------------------------------------
# CABEÇALHO DO DASHBOARD
# ------------------------------------------------------------------------------
st.title("📊 DASHBOARD DE FIIs")
st.markdown(
    "**Acompanhamento patrimonial e recomendação inteligente de aportes •"
    " Projeto Equalização**"
)
st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# MENU LATERAL - CONFIGURAÇÃO DE SALDO E OPERAÇÕES
# ------------------------------------------------------------------------------
st.sidebar.header("💵 Configuração do Aporte")

aporte_bolso = st.sidebar
