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
# ESTILIZAÇÃO CSS CUSTOMIZADA (LAYOUT ORIGINAL ESCURO)
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
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# CONEXÃO E GERENCIAMENTO DE CARTEIRA
# ------------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)


def carregar_dados_iniciais():
    if "df_carteira_override" in st.session_state:
        return st.session_state["df_carteira_override"].copy()

    if os.path.exists(LOCAL_STORAGE_FILE):
        try:
            df_local = pd.read_csv(LOCAL_STORAGE_FILE)
            if not df_local.empty and "fii" in df_local.columns:
                st.session_state["df_carteira_override"] = df_local.copy()
                return df_local
        except Exception:
            pass

    try:
        data = conn.read(ttl="0s")
        df_carteira = data.copy()
    except Exception:
        df_carteira = pd.DataFrame(
            columns=[
                "fii",
                "cotas",
                "preco_medio",
                "dy_anual (%)",
                "provento_mensal_cota",
                "dividendo_acumulado_historico",
            ]
        )

    st.session_state["df_carteira_override"] = df_carteira.copy()
    return df_carteira


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
    ticker = row["fii"]
    metas_fixas = {
        "ALZR11": 1500,
        "XPML11": 150,
        "GGRC11": 1500,
        "PMLL11": 150,
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
df_carteira["cotas_faltantes"] = df_carteira.apply(
    lambda r: max(0, int(r["meta"] - r["cotas"])), axis=1
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

aporte_bolso = st.sidebar.number_input(
    "Aporte do Bolso (R$):",
    min_value=0.0,
    value=st.session_state.valor_bolso_custom,
    step=100.0,
    format="%.2f",
    key="input_bolso_val",
)

if aporte_bolso != st.session_state.valor_bolso_custom:
    st.session_state.valor_bolso_custom = aporte_bolso
    salvar_config_saldo(
        st.session_state.valor_bolso_custom,
        st.session_state.ajuste_saldo_operacoes,
    )

total_disponivel_inicial = (
    st.session_state.valor_bolso_custom
    + dividendos_mes_total
    + st.session_state.ajuste_saldo_operacoes
)

st.sidebar.markdown(
    f"**Saldo Disponível Atual:** R$ {total_disponivel_inicial:,.2f}"
)

if st.sidebar.button("🔄 Resetar Saldo do Mês (Novo Mês)"):
    st.session_state.ajuste_saldo_operacoes = 0.0
    salvar_config_saldo(st.session_state.valor_bolso_custom, 0.0)
    st.sidebar.success("Saldo reiniciado para o padrão do mês!")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🔁 Operações (Comprar / Vender)")

tipo_operacao = st.sidebar.radio(
    "Tipo de Operação:",
    ["Comprar", "Vender"],
    horizontal=True,
)

fii_operacao = st.sidebar.selectbox("Selecione o FII:", fiis)

df_fii_filtrado = df_carteira[df_carteira["fii"] == fii_operacao]

if not df_fii_filtrado.empty:
    row_op = df_fii_filtrado.iloc[0]
    cotacao_default = float(row_op["cotacao_atual"])
    cotas_possuidas = int(row_op["cotas"])
else:
    cotacao_default = 0.0
    cotas_possuidas = 0

valor_unidade = st.sidebar.number_input(
    "Valor da Unidade (R$):",
    min_value=0.01,
    value=max(0.01, cotacao_default),
    step=0.10,
    format="%.2f",
)

cotas_operacao = st.sidebar.number_input(
    "Quantidade de Cotas:",
    min_value=1,
    value=1,
    step=1,
)

total_operacao = valor_unidade * cotas_operacao

st.sidebar.markdown(f"**Cotas Atuais:** {cotas_possuidas}")
st.sidebar.markdown(f"**Total da Operação:** R$ {total_operacao:,.2f}")

if tipo_operacao == "Comprar":
    saldo_restante_simulado = total_disponivel_inicial - total_operacao

    if saldo_restante_simulado < 0:
        excedente = abs(saldo_restante_simulado)
        st.sidebar.info(
            f"ℹ️ Compra excede o saldo em R$ {excedente:,.2f}. Ajustando do bolso ao confirmar."
        )

    if st.sidebar.button("✅ Confirmar Compra"):
        idx_list = df_carteira[df_carteira["fii"] == fii_operacao].index
        if len(idx_list) > 0:
            idx = idx_list[0]
            pm_atual = float(df_carteira.loc[idx, "preco_medio"])

            novas_cotas = cotas_possuidas + cotas_operacao
            novo_pm = (
                (cotas_possuidas * pm_atual) + (cotas_operacao * valor_unidade)
            ) / novas_cotas

            df_carteira.at[idx, "cotas"] = novas_cotas
            df_carteira.at[idx, "preco_medio"] = novo_pm

            st.session_state.ajuste_saldo_operacoes -= total_operacao
            salvar_dados_permanente(df_carteira)

            st.sidebar.success(
                f"Compra de {cotas_operacao} cotas de {fii_operacao} SALVA COM SUCESSO!"
            )
            st.rerun()

else:  # Vender
    if cotas_operacao > cotas_possuidas:
        st.sidebar.error(
            f"⚠️ Você possui apenas {cotas_possuidas} cotas para venda."
        )

    if st.sidebar.button("🛑 Confirmar Venda"):
        if cotas_operacao > cotas_possuidas:
            st.sidebar.error("Quantidade inválida de venda.")
        else:
            idx_list = df_carteira[df_carteira["fii"] == fii_operacao].index
            if len(idx_list) > 0:
                idx = idx_list[0]
                novas_cotas = cotas_possuidas - cotas_operacao

                df_carteira.at[idx, "cotas"] = novas_cotas
                st.session_state.ajuste_saldo_operacoes += total_operacao

                salvar_dados_permanente(df_carteira)
                st.sidebar.success(
                    f"Venda de {cotas_operacao} cotas de {fii_operacao} SALVA COM SUCESSO!"
                )
                st.rerun()

# ------------------------------------------------------------------------------
# EDIÇÃO MANUAL E BACKUP
# ------------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Atualização Manual & Backup")

fii_selecionado = st.sidebar.selectbox(
    "FII para Edição Manual:", fiis, key="select_fii_manual"
)

if fii_selecionado in df_carteira["fii"].values:
    row = df_carteira[df_carteira["fii"] == fii_selecionado].iloc[0]
    cota_val = int(row["cotas"])
    pm_val = float(row["preco_medio"])
    prov_val = float(row["provento_mensal_cota"])
    acum_val = float(row["dividendo_acumulado_historico"])
else:
    cota_val, pm_val, prov_val, acum_val = 0, 0.0, 0.0, 0.0

nova_cota = st.sidebar.number_input(
    "Qtd Cotas Manual:", min_value=0, value=cota_val, step=1
)
novo_pm = st.sidebar.number_input(
    "Preço Médio (R$):",
    min_value=0.0,
    value=pm_val,
    step=0.10,
    format="%.2f",
)
novo_provento = st.sidebar.number_input(
    "Último Provento/Cota (R$):",
    min_value=0.0,
    value=prov_val,
    step=0.01,
    format="%.2f",
)
novo_acumulado = st.sidebar.number_input(
    "Total Proventos Recebidos (R$):",
    min_value=0.0,
    value=acum_val,
    step=10.0,
    format="%.2f",
)

if st.sidebar.button("💾 Salvar Edição Manual"):
    idx_list = df_carteira[df_carteira["fii"] == fii_selecionado].index
    if len(idx_list) > 0:
        idx = idx_list[0]
        df_carteira.at[idx, "cotas"] = int(nova_cota)
        df_carteira.at[idx, "preco_medio"] = float(novo_pm)
        df_carteira.at[idx, "provento_mensal_cota"] = float(novo_provento)
        df_carteira.at[idx, "dividendo_acumulado_historico"] = float(
            novo_acumulado
        )

        salvar_dados_permanente(df_carteira)
        st.sidebar.success(f"✅ {fii_selecionado} atualizado com sucesso!")
        st.rerun()

st.sidebar.markdown("---")
csv_download = df_carteira[[
    "fii",
    "cotas",
    "preco_medio",
    "dy_anual (%)",
    "provento_mensal_cota",
    "dividendo_acumulado_historico",
]].to_csv(index=False).encode("utf-8")

st.sidebar.download_button(
    label="📥 Baixar Backup Atualizado (CSV)",
    data=csv_download,
    file_name="minha_carteira_fiis.csv",
    mime="text/csv",
)

# ------------------------------------------------------------------------------
# CARDS DE PATRIMÔNIO (METRICS)
# ------------------------------------------------------------------------------
patrimonio_total = df_carteira["patrimonio_atual"].sum()
investido_total = df_carteira["total_investido"].sum()
dividendos_historico_total = df_carteira["dividendo_acumulado_historico"].sum()
lucro_total = patrimonio_total - investido_total

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("PATRIMÔNIO TOTAL", f"R$ {patrimonio_total:,.2f}")
col2.metric("TOTAL INVESTIDO", f"R$ {investido_total:,.2f}")
col3.metric("PROVENTO MENSAL", f"R$ {dividendos_mes_total:,.2f}")
col4.metric("PROVENTOS ACUMULADOS", f"R$ {dividendos_historico_total:,.2f}")
col5.metric(
    "LUCRO / VALORIZAÇÃO",
    f"R$ {lucro_total:,.2f}",
    delta=f"{(lucro_total / investido_total) * 100:.2f}%"
    if investido_total > 0
    else "0%",
)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# PAINEL DE RECOMENDAÇÃO INTELIGENTE DE APORTE
# ------------------------------------------------------------------------------
meses = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]
hoje = datetime.date.today()
mes_atual_nome = meses[hoje.month - 1]
ano_atual = hoje.year

aporte_total_disponivel = max(0.0, total_disponivel_inicial)

st.subheader(f"🎯 Sugestão de Aporte — {mes_atual_nome} / {ano_atual}")
st.info(
    f"💰 **Total Disponível para Aporte:** **R$ {aporte_total_disponivel:,.2f}** "
    f"(Base: R$ {st.session_state.valor_bolso_custom:,.2f} do bolso + R$ {dividendos_mes_total:,.2f} proventos"
    f"{f' | Ajuste de Operações: R$ {st.session_state.ajuste_saldo_operacoes:,.2f}' if st.session_state.ajuste_saldo_operacoes != 0 else ''})"
)

df_pendentes = df_carteira[
    (df_carteira["progresso_meta"] < 100.0)
    & (df_carteira["valor_restante_meta"] > 0)
].sort_values(by="valor_restante_meta", ascending=False)

if len(df_pendentes) >= 1:
    fii_1 = df_pendentes.iloc[0]
    preco_fii1 = fii_1["cotacao_atual"]

    if aporte_total_disponivel < preco_fii1:
        st.warning(
            f"⚠️ **Saldo insuficiente para comprar 1 cota de {fii_1['fii']}.**\n\n"
            f"• **Cotação atual de {fii_1['fii']}: R$ {preco_fii1:.2f}**\n"
            f"• **Saldo atual disponível: R$ {aporte_total_disponivel:.2f}**"
        )
    else:
        if len(df_pendentes) >= 2:
            fii_2 = df_pendentes.iloc[1]
            def1 = fii_1["valor_restante_meta"]
            def2 = fii_2["valor_restante_meta"]
            total_def = def1 + def2

            pct1 = def1 / total_def if total_def > 0 else 0.5
            pct2 = def2 / total_def if total_def > 0 else 0.5

            val_fii1 = aporte_total_disponivel * pct1
            val_fii2 = aporte_total_disponivel * pct2

            cotas_fii1 = (
                int(val_fii1 // fii_1["cotacao_atual"])
                if fii_1["cotacao_atual"] > 0
                else 0
            )
            cotas_fii2 = (
                int(val_fii2 // fii_2["cotacao_atual"])
                if fii_2["cotacao_atual"] > 0
                else 0
            )

            if cotas_fii1 == 0 and cotas_fii2 == 0:
                cotas_fii1 = int(
                    aporte_total_disponivel // fii_1["cotacao_atual"]
                )

            gasto_fii1 = cotas_fii1 * fii_1["cotacao_atual"]
            gasto_fii2 = cotas_fii2 * fii_2["cotacao_atual"]
            sobra_troco = aporte_total_disponivel - (gasto_fii1 + gasto_fii2)

            c_rec1, c_rec2, c_troco = st.columns(3)

            with c_rec1:
                st.error(
                    f"🎯 **1º Foco (Maior Déficit): {fii_1['fii']}**\n\n"
                    f"• **Déficit restante:** R$ {def1:,.2f} ({fii_1['cotas_faltantes']} cotas)\n"
                    f"• **Comprar:** **{cotas_fii1} cotas** (~R$ {fii_1['cotacao_atual']:.2f})\n"
                    f"• **Subtotal:** **R$ {gasto_fii1:,.2f}**"
                )

            with c_rec2:
                if cotas_fii2 > 0:
                    st.error(
                        f"🎯 **2º Foco: {fii_2['fii']}**\n\n"
                        f"• **Déficit restante:** R$ {def2:,.2f} ({fii_2['cotas_faltantes']} cotas)\n"
                        f"• **Comprar:** **{cotas_fii2} cotas** (~R$ {fii_2['cotacao_atual']:.2f})\n"
                        f"• **Subtotal:** **R$ {gasto_fii2:,.2f}**"
                    )
                else:
                    st.info(
                        f"ℹ️ **2º Foco: {fii_2['fii']}**\n\n"
                        "• Saldo insuficiente para dividir o aporte neste mês.\n"
                        f"• Todo o aporte viável foi direcionado para **{fii_1['fii']}**."
                    )

            with c_troco:
                st.metric("Sobra de Troco", f"R$ {sobra_troco:.2f}")
                st.caption("💡 **Recomenda-se acumular para o próximo mês.**")
        else:
            cotas_fii1 = int(aporte_total_disponivel // fii_1["cotacao_atual"])
            gasto_fii1 = cotas_fii1 * fii_1["cotacao_atual"]
            sobra_troco = aporte_total_disponivel - gasto_fii1

            c_rec1, c_troco = st.columns(2)
            with c_rec1:
                st.error(
                    f"🎯 **Único Foco Pendente: {fii_1['fii']}**\n\n"
                    f"• **Déficit restante:** R$ {fii_1['valor_restante_meta']:,.2f} ({fii_1['cotas_faltantes']} cotas)\n"
                    f"• **Comprar:** **{cotas_fii1} cotas** (~R$ {fii_1['cotacao_atual']:.2f})\n"
                    f"• **Subtotal:** **R$ {gasto_fii1:,.2f}**"
                )
            with c_troco:
                st.metric("Sobra de Troco", f"R$ {sobra_troco:.2f}")
else:
    st.success("🎉 Todas as metas ativas da carteira foram atingidas!")

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# GRÁFICOS INTERATIVOS DO DASHBOARD (LAYOUT ORIGINAL CONTINUO)
# ------------------------------------------------------------------------------
st.subheader("📈 Análise Gráfica da Carteira")

g_col1, g_col2 = st.columns(2)

with g_col1:
    fig_pizza = px.pie(
        df_carteira,
        names="fii",
        values="patrimonio_atual",
        title="Alocação Patrimonial por FII",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig_pizza.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Patrimônio: R$ %{value:,.2f}<br>Percentual: %{percent}",
    )
    fig_pizza.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"),
        showlegend=True,
    )
    st.plotly_chart(fig_pizza, use_container_width=True)

with g_col2:
    fig_barras = go.Figure()
    fig_barras.add_trace(
        go.Bar(
            x=df_carteira["fii"],
            y=df_carteira["preco_medio"],
            name="Preço Médio",
            marker_color="#3b82f6",
        )
    )
    fig_barras.add_trace(
        go.Bar(
            x=df_carteira["fii"],
            y=df_carteira["cotacao_atual"],
            name="Cotação Atual",
            marker_color="#00d092",
        )
    )
    fig_barras.update_layout(
        title="Preço Médio vs. Cotação Atual",
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"),
        xaxis=dict(title="FII"),
        yaxis=dict(title="Valor (R$)"),
    )
    st.plotly_chart(fig_barras, use_container_width=True)

fig_metas = px.bar(
    df_carteira,
    x="fii",
    y="progresso_meta",
    title="Progresso das Metas de Cotas (%)",
    text_auto=".1f",
    labels={"fii": "FII", "progresso_meta": "Progresso (%)"},
    color="progresso_meta",
    color_continuous_scale="Greens",
)
fig_metas.update_traces(texttemplate="%{y:.1f}%", textposition="outside")
fig_metas.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff"),
    yaxis=dict(range=[0, 120]),
)
st.plotly_chart(fig_metas, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# POSIÇÃO DETALHADA DA CARTEIRA (TABELA)
# ------------------------------------------------------------------------------
st.subheader("📋 Posição Detalhada da Carteira")

df_exibicao = df_carteira[[
    "fii",
    "cotas",
    "meta",
    "preco_medio",
    "cotacao_atual",
    "patrimonio_atual",
    "provento_mensal_cota",
    "dy_mensal_pct",
    "dividendo_mensal_total",
    "dividendo_acumulado_historico",
    "progresso_meta",
]].copy()

df_exibicao.columns = [
    "FII",
    "Cotas",
    "Meta",
    "Preço Médio (R$)",
    "Cotação Atual (R$)",
    "Patrimônio (R$)",
    "Provento/Cota (R$)",
    "Rendimento Mensal (%)",
    "Rendimento Mensal (R$)",
    "Dividendos Acumulados (R$)",
    "Progresso (%)",
]

st.dataframe(
    df_exibicao.style.format({
        "Preço Médio (R$)": "R$ {:.2f}",
        "Cotação Atual (R$)": "R$ {:.2f}",
        "Patrimônio (R$)": "R$ {:.2f}",
        "Provento/Cota (R$)": "R$ {:.2f}",
        "Rendimento Mensal (%)": "{:.2f}%",
        "Rendimento Mensal (R$)": "R$ {:.2f}",
        "Dividendos Acumulados (R$)": "R$ {:.2f}",
        "Progresso (%)": "{:.1f}%",
    }),
    use_container_width=True,
)
