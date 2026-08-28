import datetime
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

# ------------------------------------------------------------------------------
# ESTILIZAÇÃO CSS CUSTOMIZADA (FONTES EM NEGRITO & ALTO CONTRASTE)
# ------------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Estilo Global e Fundo */
    .main {
        background-color: #0e1117;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Títulos e Subtítulos Nítidos em Negrito */
    h1 {
        font-weight: 900 !important;
        letter-spacing: -0.5px;
        color: #ffffff !important;
        margin-bottom: 0px !important;
    }
    h2, h3, h4 {
        font-weight: 800 !important;
        letter-spacing: -0.3px;
        color: #ffffff !important;
        opacity: 1 !important;
    }

    /* Cards de Métricas (Textos e Rótulos Nítidos) */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e2638 0%, #111827 100%);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: rgba(46, 196, 182, 0.6);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #e2e8f0 !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        opacity: 1 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.65rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
    }

    /* Estilização das Abas (Tabs) - Textos em Negrito */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #161b22;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 8px;
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        border: none !important;
        opacity: 1 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #2ec4b6 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        font-weight: 800 !important;
    }

    /* Estilização Completa das Tabelas (Cabeçalhos e Linhas em Negrito) */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        overflow: hidden;
    }
    /* Estilo para células de cabeçalho da tabela */
    [data-testid="stDataFrame"] div[role="columnheader"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
    }
    /* Estilo para texto dentro da tabela */
    [data-testid="stDataFrame"] div[role="gridcell"] {
        font-weight: 600 !important;
        color: #f8fafc !important;
    }

    /* Sidebar - Rótulos e Títulos */
    [data-testid="stSidebar"] {
        background-color: #12161f;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    [data-testid="stSidebar"] label {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Botões Principais */
    .stButton > button {
        border-radius: 10px;
        font-weight: 800 !important;
        border: none;
        background: linear-gradient(135deg, #2ec4b6 0%, #208b82 100%);
        color: #ffffff !important;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #32dbcb 0%, #25a095 100%);
        box-shadow: 0 4px 12px rgba(46, 196, 182, 0.4);
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# CONEXÃO E TRATAMENTO DE DADOS
# ------------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)
data = conn.read(ttl="0s")
df_carteira = data.copy()

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

fiis = ["ALZR11", "XPML11", "GGRC11", "PMALL11", "BTLG11", "BRCO11", "IRIM11"]


@st.cache_data(ttl=300)
def obter_cotacoes_b3(tickers):
    dados = {}
    for t in tickers:
        try:
            ticker_b3 = f"{t}.SA"
            info = yf.Ticker(ticker_b3).fast_info
            price = float(info.get("lastPrice", 0.0))
            dados[t] = price
        except:
            dados[t] = 0.0
    return dados


cotacoes_atuais = obter_cotacoes_b3(fiis)


def obter_meta(row):
    ticker = row["fii"]
    metas_fixas = {
        "ALZR11": 1500,
        "XPML11": 150,
        "GGRC11": 1500,
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

# Cálculos
df_carteira["patrimonio_atual"] = df_carteira["cotas"] * df_carteira["cotacao_atual"]
df_carteira["total_investido"] = df_carteira["cotas"] * df_carteira["preco_medio"]
df_carteira["lucro_ganho_capital"] = df_carteira["patrimonio_atual"] - df_carteira["total_investido"]
df_carteira["dividendo_mensal_total"] = df_carteira["cotas"] * df_carteira["provento_mensal_cota"]

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
df_carteira["valor_restante_meta"] = df_carteira["cotas_faltantes"] * df_carteira["cotacao_atual"]

# ------------------------------------------------------------------------------
# CABEÇALHO DO DASHBOARD
# ------------------------------------------------------------------------------
st.title("📊 DASHBOARD DE FIIs")
st.markdown("**Acompanhamento patrimonial e recomendação inteligente de aportes • Projeto Equalização**")
st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# MENU LATERAL
# ------------------------------------------------------------------------------
st.sidebar.header("💵 Configuração do Aporte")
aporte_bolso = st.sidebar.number_input(
    "Aporte do Bolso (R$):",
    min_value=0.0,
    value=1000.0,
    step=100.0,
    format="%.2f",
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Atualizar Carteira")
fii_selecionado = st.sidebar.selectbox("Selecione o FII:", fiis)

if fii_selecionado in df_carteira["fii"].values:
    row = df_carteira[df_carteira["fii"] == fii_selecionado].iloc[0]
    cota_val = int(row["cotas"])
    pm_val = float(row["preco_medio"])
    prov_val = float(row["provento_mensal_cota"])
    acum_val = float(row["dividendo_acumulado_historico"])
else:
    cota_val, pm_val, prov_val, acum_val = 0, 0.0, 0.0, 0.0

nova_cota = st.sidebar.number_input("Quantidade de Cotas:", min_value=0, value=cota_val, step=1)
novo_pm = st.sidebar.number_input("Preço Médio (R$):", min_value=0.0, value=pm_val, step=0.10, format="%.2f")
novo_provento = st.sidebar.number_input("Último Provento/Cota (R$):", min_value=0.0, value=prov_val, step=0.01, format="%.2f")
novo_acumulado = st.sidebar.number_input("Total Proventos Já Recebidos (R$):", min_value=0.0, value=acum_val, step=10.0, format="%.2f")

if st.sidebar.button("📅 Virada de Mês: Somar Provento Mensal"):
    df_carteira["dividendo_acumulado_historico"] += df_carteira["dividendo_mensal_total"]
    df_salvar = df_carteira[["fii", "cotas", "preco_medio", "dy_anual (%)", "provento_mensal_cota", "dividendo_acumulado_historico"]]
    conn.update(data=df_salvar)
    st.sidebar.success("Dividendos somados ao histórico!")
    st.cache_data.clear()

if st.sidebar.button("💾 Salvar Alterações Individuais"):
    idx = df_carteira[df_carteira["fii"] == fii_selecionado].index[0]
    df_carteira.loc[idx, "cotas"] = nova_cota
    df_carteira.loc[idx, "preco_medio"] = novo_pm
    df_carteira.loc[idx, "provento_mensal_cota"] = novo_provento
    df_carteira.loc[idx, "dividendo_acumulado_historico"] = novo_acumulado

    df_salvar = df_carteira[["fii", "cotas", "preco_medio", "dy_anual (%)", "provento_mensal_cota", "dividendo_acumulado_historico"]]
    conn.update(data=df_salvar)
    st.sidebar.success(f"{fii_selecionado} atualizado!")
    st.cache_data.clear()

# ------------------------------------------------------------------------------
# CARDS DE PATRIMÔNIO (METRICS)
# ------------------------------------------------------------------------------
patrimonio_total = df_carteira["patrimonio_atual"].sum()
investido_total = df_carteira["total_investido"].sum()
dividendos_mes_total = df_carteira["dividendo_mensal_total"].sum()
dividendos_historico_total = df_carteira["dividendo_acumulado_historico"].sum()
lucro_total = patrimonio_total - investido_total

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Patrimônio Total", f"R$ {patrimonio_total:,.2f}")
col2.metric("Total Investido", f"R$ {investido_total:,.2f}")
col3.metric("Provento Mensal", f"R$ {dividendos_mes_total:,.2f}")
col4.metric("Proventos Acumulados", f"R$ {dividendos_historico_total:,.2f}")
col5.metric(
    "Lucro / Valorização",
    f"R$ {lucro_total:,.2f}",
    delta=f"{(lucro_total / investido_total) * 100:.2f}%" if investido_total > 0 else "0%",
)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# PAINEL DE RECOMENDAÇÃO INTELIGENTE DE APORTE
# ------------------------------------------------------------------------------
meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
hoje = datetime.date.today()
mes_atual_nome = meses[hoje.month - 1]
ano_atual = hoje.year

aporte_total_disponivel = aporte_bolso + dividendos_mes_total

st.subheader(f"🎯 Sugestão de Aporte — {mes_atual_nome} / {ano_atual}")
st.info(f"💰 **Total Disponível para Aporte:** **R$ {aporte_total_disponivel:,.2f}** (R$ {aporte_bolso:,.2f} do bolso + R$ {dividendos_mes_total:,.2f} em proventos)")

df_pendentes = df_carteira[
    (df_carteira["progresso_meta"] < 100.0) & (df_carteira["valor_restante_meta"] > 0)
].sort_values(by="valor_restante_meta", ascending=False)

if len(df_pendentes) >= 2:
    fii_1 = df_pendentes.iloc[0]
    fii_2 = df_pendentes.iloc[1]

    def1 = fii_1["valor_restante_meta"]
    def2 = fii_2["valor_restante_meta"]
    total_def = def1 + def2

    pct1 = def1 / total_def if total_def > 0 else 0.5
    pct2 = def2 / total_def if total_def > 0 else 0.5

    val_fii1 = aporte_total_disponivel * pct1
    val_fii2 = aporte_total_disponivel * pct2

    cotas_fii1 = int(val_fii1 // fii_1["cotacao_atual"]) if fii_1["cotacao_atual"] > 0 else 0
    cotas_fii2 = int(val_fii2 // fii_2["cotacao_atual"]) if fii_2["cotacao_atual"] > 0 else 0

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
        st.error(
            f"🎯 **2º Foco: {fii_2['fii']}**\n\n"
            f"• **Déficit restante:** R$ {def2:,.2f} ({fii_2['cotas_faltantes']} cotas)\n"
            f"• **Comprar:** **{cotas_fii2} cotas** (~R$ {fii_2['cotacao_atual']:.2f})\n"
            f"• **Subtotal:** **R$ {gasto_fii2:,.2f}**"
        )

    with c_troco:
        st.metric("Sobra de Troco", f"R$ {sobra_troco:.2f}")
        st.caption("💡 **Recomenda-se acumular ou reinvestir em FIIs de base R$ 10.**")
else:
    st.success("🎉 Todas as metas ativas da carteira foram atingidas!")

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# PROJEÇÕES FUTURAS
# ------------------------------------------------------------------------------
st.subheader("📈 Metas & Projeção Temporal")

total_valor_restante = df_carteira["valor_restante_meta"].sum()
meta_rendimento_mensal_final = (df_carteira["meta"] * df_carteira["provento_mensal_cota"]).sum()

meses_estimados = int(np.ceil(total_valor_restante / aporte_total_disponivel)) if aporte_total_disponivel > 0 else 0
anos_estimados = meses_estimados // 12
meses_sobra = meses_estimados % 12

p_col1, p_col2, p_col3 = st.columns(3)
p_col1.metric("Valor para Finalizar Metas", f"R$ {total_valor_restante:,.2f}")
p_col2.metric(
    "Prazo Estimado",
    f"{meses_estimados} meses",
    delta=f"~{anos_estimados} ano(s) e {meses_sobra} mes(es)" if anos_estimados > 0 else None,
)
p_col3.metric(
    "Renda Mensal na Conclusão",
    f"R$ {meta_rendimento_mensal_final:,.2f}",
    delta=f"+R$ {meta_rendimento_mensal_final - dividendos_mes_total:,.2f} /mês",
)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# GRÁFICOS INTERATIVOS (PLOTLY SYSTEM WITH HIGH CONTRAST)
# ------------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🏆 Ranking Histórico",
    "💵 Proventos do Mês",
    "🎯 Progresso das Metas",
    "🔮 Bola de Neve",
])

with tab1:
    st.subheader("🏆 Ranking de Dividendos Acumulados")
    df_rank_div = df_carteira.sort_values(by="dividendo_acumulado_historico", ascending=False)

    fig_rank = px.bar(
        df_rank_div,
        x="fii",
        y="dividendo_acumulado_historico",
        text_auto=".2f",
        labels={"fii": "FII", "dividendo_acumulado_historico": "Total (R$)"},
        template="plotly_dark",
    )
    fig_rank.update_traces(
        marker_color="#2ec4b6",
        texttemplate="R$ %{y:.2f}",
        textposition="outside",
        textfont=dict(color="#ffffff", size=13, family="Inter", weight="bold"),
    )
    fig_rank.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff", family="Inter", size=13, weight="bold"),
        xaxis=dict(tickfont=dict(color="#ffffff", size=13, weight="bold"), title=dict(font=dict(color="#ffffff", size=14, weight="bold"))),
        yaxis=dict(tickfont=dict(color="#ffffff", size=13, weight="bold"), title=dict(font=dict(color="#ffffff", size=14, weight="bold"))),
        margin=dict(t=30, b=0, l=0, r=0),
    )
    st.plotly_chart(fig_rank, use_container_width=True)

with tab2:
    st.subheader("💵 Rendimento Estimado no Mês")
    df_div_sorted = df_carteira.sort_values(by="dividendo_mensal_total", ascending=False)

    fig_div = px.bar(
        df_div_sorted,
        x="fii",
        y="dividendo_mensal_total",
        text_auto=".2f",
        labels={"fii": "FII", "dividendo_mensal_total": "Rendimento (R$)"},
        template="plotly_dark",
    )
    fig_div.update_traces(
        marker_color="#ff9f1c",
        texttemplate="R$ %{y:.2f}",
        textposition="outside",
        textfont=dict(color="#ffffff", size=13, family="Inter", weight="bold"),
    )
    fig_div.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff", family="Inter", size=13, weight="bold"),
        xaxis=dict(tickfont=dict(color="#ffffff", size=13, weight="bold"), title=dict(font=dict(color="#ffffff", size=14, weight="bold"))),
        yaxis=dict(tickfont=dict(color="#ffffff", size=13, weight="bold"), title=dict(font=dict(color="#ffffff", size=14, weight="bold"))),
        margin=dict(t=30, b=0, l=0, r=0),
    )
    st.plotly_chart(fig_div, use_container_width=True)

with tab3:
    st.subheader("🎯 Progresso Rumo às Metas")

    df_prog = df_carteira.sort_values(by="progresso_meta", ascending=True).copy()
    dois_menores = df_carteira["progresso_meta"].nsmallest(2).values.tolist()

    def definir_cor(row):
        if row["progresso_meta"] >= 100.0:
            return "#2ec4b6"
        elif row["progresso_meta"] in dois_menores:
            return "#e63946"
        return "#ff9f1c"

    df_prog["cor"] = df_prog.apply(definir_cor, axis=1)

    fig_prog_plotly = go.Figure(
        go.Bar(
            x=df_prog["progresso_meta"],
            y=df_prog["fii"],
            orientation="h",
            text=[f"{p:.1f}%" for p in df_prog["progresso_meta"]],
            textposition="outside",
            textfont=dict(color="#ffffff", size=13, family="Inter", weight="bold"),
            marker=dict(color=df_prog["cor"]),
        )
    )
    fig_prog_plotly.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff", family="Inter", size=13, weight="bold"),
        xaxis=dict(range=[0, 115], tickfont=dict(color="#ffffff", size=13, weight="bold"), title=dict(text="Conclusão (%)", font=dict(color="#ffffff", size=14, weight="bold"))),
        yaxis=dict(tickfont=dict(color="#ffffff", size=13, weight="bold")),
        margin=dict(t=20, b=0, l=0, r=0),
    )
    st.plotly_chart(fig_prog_plotly, use_container_width=True)

with tab4:
    st.subheader("🔮 Simulação do Efeito Bola de Neve (Renda Reinvestida)")

    sim_meses = min(24, max(12, meses_estimados))
    meses_proj = [f"Mês {m}" for m in range(0, sim_meses + 1)]
    renda_proj = []

    renda_atual_sim = dividendos_mes_total
    taxa_rendimento_media = (dividendos_mes_total / patrimonio_total) if patrimonio_total > 0 else 0.008

    for m in range(0, sim_meses + 1):
        renda_proj.append(renda_atual_sim)
        aporte_mes = aporte_bolso + renda_atual_sim
        novos_dividendos = aporte_mes * taxa_rendimento_media
        renda_atual_sim += novos_dividendos

    fig_sim = go.Figure()
    fig_sim.add_trace(
        go.Scatter(
            x=meses_proj,
            y=renda_proj,
            mode="lines+markers",
            name="Renda Mensal (R$)",
            line=dict(color="#2ec4b6", width=3),
            marker=dict(size=7, color="#2ec4b6"),
        )
    )
    fig_sim.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff", family="Inter", size=13, weight="bold"),
        xaxis=dict(tickfont=dict(color="#ffffff", size=13, weight="bold"), title=dict(text="Período", font=dict(color="#ffffff", size=14, weight="bold"))),
        yaxis=dict(tickfont=dict(color="#ffffff", size=13, weight="bold"), title=dict(text="Provento Mensal (R$)", font=dict(color="#ffffff", size=14, weight="bold"))),
        margin=dict(t=30, b=0, l=0, r=0),
    )
    st.plotly_chart(fig_sim, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TABELA COMPLETA DE POSIÇÃO
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
