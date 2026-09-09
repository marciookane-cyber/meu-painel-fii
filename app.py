import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard FIIs - Controle & Metas",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilização CSS personalizada para o Streamlit
st.markdown(
    """
    <style>
        .stApp {
            background-color: #0b0e14;
            color: #ffffff;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #1f2937;
            border-radius: 4px;
            color: #ffffff;
            padding: 8px 16px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #00d092 !important;
            color: #000000 !important;
            font-weight: bold;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# BASE DE DADOS (DADOS DE EXEMPLO DE CARTEIRA DE FIIs)
# ------------------------------------------------------------------------------
dados_carteira = {
    "fii": [
        "MXRF11",
        "HGLG11",
        "XPML11",
        "KNCR11",
        "VISC11",
        "BBRC11",
        "CPTS11",
    ],
    "quantidade": [1500, 120, 95, 200, 110, 80, 550],
    "preco_medio": [10.20, 162.50, 108.00, 101.30, 118.20, 105.00, 8.40],
    "preco_atual": [10.45, 168.10, 115.50, 103.80, 122.00, 109.50, 8.65],
    "dividendo_ultimo_mes": [0.10, 1.10, 0.90, 1.00, 0.85, 0.95, 0.08],
    "dividendo_acumulado_historico": [
        117.36,
        105.00,
        85.50,
        200.00,
        93.50,
        76.00,
        44.00,
    ],
    "meta_cotas": [2000, 150, 100, 250, 150, 100, 1000],
}

df_carteira = pd.DataFrame(dados_carteira)

# Calculados
df_carteira["patrimonio_total"] = (
    df_carteira["quantidade"] * df_carteira["preco_atual"]
)
df_carteira["dividendo_mensal_total"] = (
    df_carteira["quantidade"] * df_carteira["dividendo_ultimo_mes"]
)
df_carteira["progresso_meta"] = (
    df_carteira["quantidade"] / df_carteira["meta_cotas"]
) * 100

# ------------------------------------------------------------------------------
# SIDEBAR / CONTROLES DE ENTRADA
# ------------------------------------------------------------------------------
st.sidebar.title("⚙️ Configurações da Carteira")
aporte_bolso = st.sidebar.number_input(
    "Aporte Mensal do Bolso (R$)",
    min_value=0.0,
    value=1500.0,
    step=100.0,
)
meta_renda_mensal = st.sidebar.number_input(
    "Meta de Renda Mensal (R$)",
    min_value=100.0,
    value=2000.0,
    step=100.0,
)

# ------------------------------------------------------------------------------
# MÉTRICAS PRINCIPAIS (KPIs)
# ------------------------------------------------------------------------------
st.title("📊 Dashboard - Acompanhamento de FIIs")

patrimonio_total = df_carteira["patrimonio_total"].sum()
dividendos_mes_total = df_carteira["dividendo_mensal_total"].sum()
yield_medio_mensal = (
    (dividendos_mes_total / patrimonio_total) * 100
    if patrimonio_total > 0
    else 0.0
)
faltante_meta_renda = max(0.0, meta_renda_mensal - dividendos_mes_total)

# Estimativa simples de tempo para a meta
if faltante_meta_renda > 0 and (aporte_bolso + dividendos_mes_total) > 0:
    meses_estimados = int(
        np.ceil(
            faltante_meta_renda
            / (
                (aporte_bolso + dividendos_mes_total)
                * (yield_medio_mensal / 100)
            )
        )
    )
else:
    meses_estimados = 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Patrimônio Total", f"R$ {patrimonio_total:,.2f}")
col2.metric("Dividendos / Mês Estimados", f"R$ {dividendos_mes_total:,.2f}")
col3.metric("Yield Médio Mensal", f"{yield_medio_mensal:.2f}%")
col4.metric(
    "Progresso Meta Renda",
    f"{(dividendos_mes_total / meta_renda_mensal) * 100:.1f}%",
    delta=f"-R$ {faltante_meta_renda:,.2f}",
)

st.markdown("---")

# ------------------------------------------------------------------------------
# LAYOUT DE GRÁFICOS ESCUROS PADRONIZADOS
# ------------------------------------------------------------------------------
layout_padrao_escuro = dict(
    paper_bgcolor="#0b0e14",
    plot_bgcolor="#0b0e14",
    font=dict(color="#ffffff", family="serif"),
    margin=dict(t=60, b=60, l=60, r=40),
    xaxis=dict(
        visible=True,
        showticklabels=True,
        type="category",
        color="#ffffff",
        tickfont=dict(color="#ffffff", size=13, family="serif", weight="bold"),
        title=dict(
            text="FII", font=dict(color="#ffffff", size=14, weight="bold")
        ),
        showgrid=False,
        zeroline=False,
    ),
    yaxis=dict(
        visible=True,
        showticklabels=True,
        color="#ffffff",
        tickfont=dict(color="#ffffff", size=12, family="serif", weight="bold"),
        title=dict(
            text="Total (R$)",
            font=dict(color="#ffffff", size=14, weight="bold"),
        ),
        gridcolor="#1f2937",
        gridwidth=1,
        zeroline=False,
    ),
)

# ------------------------------------------------------------------------------
# ABA DE GRÁFICOS INTERATIVOS
# ------------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🏆 Ranking Histórico",
        "💵 Proventos do Mês",
        "🎯 Progresso das Metas",
        "🔮 Bola de Neve",
    ]
)

with tab1:
    st.subheader("🏆 Ranking de Dividendos Acumulados")
    df_rank_div = df_carteira.sort_values(
        by="dividendo_acumulado_historico", ascending=False
    )

    fig_rank = px.bar(
        df_rank_div,
        x="fii",
        y="dividendo_acumulado_historico",
        labels={"fii": "FII", "dividendo_acumulado_historico": "Total (R$)"},
    )

    fig_rank.update_traces(
        marker_color="#00d092",
        texttemplate="R$ %{y:.2f}",
        textposition="outside",
        cliponaxis=False,
        textfont=dict(color="#ffffff", size=13, family="serif", weight="bold"),
    )

    fig_rank.update_layout(**layout_padrao_escuro)
    st.plotly_chart(fig_rank, use_container_width=True)

with tab2:
    st.subheader("💵 Rendimento Estimado no Mês")
    df_div_sorted = df_carteira.sort_values(
        by="dividendo_mensal_total", ascending=False
    )

    fig_div = px.bar(
        df_div_sorted,
        x="fii",
        y="dividendo_mensal_total",
        labels={"fii": "FII", "dividendo_mensal_total": "Rendimento (R$)"},
    )
    fig_div.update_traces(
        marker_color="#00d092",
        texttemplate="R$ %{y:.2f}",
        textposition="outside",
        cliponaxis=False,
        textfont=dict(color="#ffffff", size=13, family="serif", weight="bold"),
    )

    layout_tab2 = layout_padrao_escuro.copy()
    layout_tab2["yaxis"]["title"]["text"] = "Rendimento (R$)"

    fig_div.update_layout(**layout_tab2)
    st.plotly_chart(fig_div, use_container_width=True)

with tab3:
    st.subheader("🎯 Progresso Rumo às Metas por FII")

    df_prog = df_carteira.sort_values(
        by="progresso_meta", ascending=True
    ).copy()
    dois_menores = df_carteira["progresso_meta"].nsmallest(2).values.tolist()

    def definir_cor(row):
        if row["progresso_meta"] >= 100.0:
            return "#00d092"
        elif row["progresso_meta"] in dois_menores:
            return "#ef4444"
        return "#f59e0b"

    df_prog["cor"] = df_prog.apply(definir_cor, axis=1)

    fig_prog_plotly = go.Figure(
        go.Bar(
            x=df_prog["progresso_meta"],
            y=df_prog["fii"],
            orientation="h",
            text=[f"{p:.1f}%" for p in df_prog["progresso_meta"]],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(
                color="#ffffff", size=13, family="serif", weight="bold"
            ),
            marker=dict(color=df_prog["cor"]),
        )
    )

    fig_prog_plotly.update_layout(
        paper_bgcolor="#0b0e14",
        plot_bgcolor="#0b0e14",
        font=dict(color="#ffffff", family="serif"),
        margin=dict(t=40, b=50, l=80, r=40),
        xaxis=dict(
            visible=True,
            showticklabels=True,
            range=[0, 120],
            color="#ffffff",
            tickfont=dict(
                color="#ffffff", size=13, family="serif", weight="bold"
            ),
            title=dict(
                text="Conclusão (%)",
                font=dict(color="#ffffff", size=14, weight="bold"),
            ),
            gridcolor="#1f2937",
        ),
        yaxis=dict(
            visible=True,
            showticklabels=True,
            type="category",
            dtick=1,
            color="#ffffff",
            tickfont=dict(
                color="#ffffff", size=14, family="serif", weight="bold"
            ),
            showgrid=False,
        ),
    )
    st.plotly_chart(fig_prog_plotly, use_container_width=True)

with tab4:
    st.subheader(
        "🔮 Simulação do Efeito Bola de Neve (Renda Reinvestida)"
    )

    sim_meses = min(
        24, max(12, meses_estimados if meses_estimados > 0 else 12)
    )
    meses_proj = [f"Mês {m}" for m in range(0, sim_meses + 1)]
    renda_proj = []

    renda_atual_sim = dividendos_mes_total
    taxa_rendimento_media = (
        (dividendos_mes_total / patrimonio_total)
        if patrimonio_total > 0
        else 0.008
    )

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
            line=dict(color="#00d092", width=3),
            marker=dict(size=7, color="#00d092"),
        )
    )

    fig_sim.update_layout(
        paper_bgcolor="#0b0e14",
        plot_bgcolor="#0b0e14",
        font=dict(color="#ffffff", family="serif"),
        margin=dict(t=40, b=50, l=50, r=20),
        xaxis=dict(
            visible=True,
            showticklabels=True,
            type="category",
            color="#ffffff",
            tickfont=dict(
                color="#ffffff", size=13, family="serif", weight="bold"
            ),
            title=dict(
                text="Período",
                font=dict(color="#ffffff", size=14, weight="bold"),
            ),
            showgrid=False,
        ),
        yaxis=dict(
            visible=True,
            showticklabels=True,
            color="#ffffff",
            tickfont=dict(
                color="#ffffff", size=13, family="serif", weight="bold"
            ),
            title=dict(
                text="Provento Mensal (R$)",
                font=dict(color="#ffffff", size=14, weight="bold"),
            ),
            gridcolor="#1f2937",
        ),
    )
    st.plotly_chart(fig_sim, use_container_width=True)

# ------------------------------------------------------------------------------
# DETALHAMENTO DA CARTEIRA
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📋 Detalhamento das Posições")
st.dataframe(
    df_carteira[
        [
            "fii",
            "quantidade",
            "preco_atual",
            "patrimonio_total",
            "dividendo_ultimo_mes",
            "dividendo_mensal_total",
            "meta_cotas",
            "progresso_meta",
        ]
    ].style.format(
        {
            "preco_atual": "R$ {:.2f}",
            "patrimonio_total": "R$ {:.2f}",
            "dividendo_ultimo_mes": "R$ {:.2f}",
            "dividendo_mensal_total": "R$ {:.2f}",
            "progresso_meta": "{:.1f}%",
        }
    ),
    use_container_width=True,
)
