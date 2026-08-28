import datetime
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf
from streamlit_gsheets import GSheetsConnection

# Configuração da página
st.set_page_config(
    page_title="Painel de FIIs - Projeto Equalização",
    page_icon="💰",
    layout="wide",
)

st.title("📊 DASHBOARD DE FIIs & PROJETO EQUALIZAÇÃO")
st.markdown(
    "Acompanhe patrimônio, dividendos mensais, acumulado histórico, preço"
    " médio, cotação em tempo real e recomendação de aportes."
)

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
data = conn.read(ttl="0s")

# Copiar dados da planilha
df_carteira = data.copy()

# Tratamento para converter textos/vírgulas em números automaticamente
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

# Metas fixas da carteira
metas_dict = {
    "ALZR11": 1500,
    "XPML11": 150,
    "GGRC11": 1500,
    "MALL11": 150,
    "BTLG11": 150,
    "BRCO11": 150,
}

fiis = ["ALZR11", "XPML11", "GGRC11", "MALL11", "BTLG11", "BRCO11"]


# Busca Cotações Atuais via Yahoo Finance (B3)
@st.cache_data(ttl=300)
def obter_cotacoes(tickers):
    precos = {}
    for t in tickers:
        try:
            ticker_b3 = f"{t}.SA"
            info = yf.Ticker(ticker_b3).fast_info
            precos[t] = float(info["lastPrice"])
        except:
            precos[t] = 0.0
    return precos


cotacoes_atuais = obter_cotacoes(fiis)

# Mapear metas e cotações
df_carteira["meta"] = df_carteira["fii"].map(metas_dict)
df_carteira["cotacao_atual"] = df_carteira["fii"].map(cotacoes_atuais)

# Usar preço médio caso a cotação em tempo real venha zerada
df_carteira["cotacao_atual"] = df_carteira.apply(
    lambda r: r["preco_medio"]
    if r["cotacao_atual"] == 0 or pd.isna(r["cotacao_atual"])
    else r["cotacao_atual"],
    axis=1,
)

# Cálculos da Carteira
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

# Cálculo do Dividend Yield Mensal (%) com base no Preço Médio ou Cotação
df_carteira["dy_mensal_pct"] = df_carteira.apply(
    lambda r: (r["provento_mensal_cota"] / r["cotacao_atual"] * 100)
    if r["cotacao_atual"] > 0
    else 0.0,
    axis=1,
)

df_carteira["progresso_meta"] = (
    df_carteira["cotas"] / df_carteira["meta"]
) * 100

# ------------------------------------------------------------------------------
# MENU LATERAL - CONFIGURAÇÃO E EDIÇÃO DE DADOS
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

nova_cota = st.sidebar.number_input(
    "Quantidade de Cotas:", min_value=0, value=cota_val, step=1
)
novo_pm = st.sidebar.number_input(
    "Preço Médio (R$):", min_value=0.0, value=pm_val, step=0.10, format="%.2f"
)
novo_provento = st.sidebar.number_input(
    "Último Provento por Cota (R$):",
    min_value=0.0,
    value=prov_val,
    step=0.01,
    format="%.2f",
)
novo_acumulado = st.sidebar.number_input(
    "Total de Dividendos Já Recebidos (R$):",
    min_value=0.0,
    value=acum_val,
    step=10.0,
    format="%.2f",
)

if st.sidebar.button("📅 Virada de Mês: Somar Provento Mensal no Acumulado"):
    df_carteira["dividendo_acumulado_historico"] += df_carteira[
        "dividendo_mensal_total"
    ]
    df_salvar = df_carteira[[
        "fii",
        "cotas",
        "preco_medio",
        "dy_anual (%)",
        "provento_mensal_cota",
        "dividendo_acumulado_historico",
    ]]
    conn.update(data=df_salvar)
    st.sidebar.success("Dividendos do mês somados ao acumulado com sucesso!")
    st.cache_data.clear()

st.sidebar.markdown("---")

if st.sidebar.button("💾 Salvar Alterações Individuais"):
    idx = df_carteira[df_carteira["fii"] == fii_selecionado].index[0]
    df_carteira.loc[idx, "cotas"] = nova_cota
    df_carteira.loc[idx, "preco_medio"] = novo_pm
    df_carteira.loc[idx, "provento_mensal_cota"] = novo_provento
    df_carteira.loc[idx, "dividendo_acumulado_historico"] = novo_acumulado

    df_salvar = df_carteira[[
        "fii",
        "cotas",
        "preco_medio",
        "dy_anual (%)",
        "provento_mensal_cota",
        "dividendo_acumulado_historico",
    ]]
    conn.update(data=df_salvar)
    st.sidebar.success(f"{fii_selecionado} atualizado com sucesso!")
    st.cache_data.clear()

# ------------------------------------------------------------------------------
# VISÃO GERAL DA CARTEIRA (CARDS)
# ------------------------------------------------------------------------------
patrimonio_total = df_carteira["patrimonio_atual"].sum()
investido_total = df_carteira["total_investido"].sum()
dividendos_mes_total = df_carteira["dividendo_mensal_total"].sum()
dividendos_historico_total = df_carteira[
    "dividendo_acumulado_historico"
].sum()
lucro_total = patrimonio_total - investido_total

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Patrimônio Total", f"R$ {patrimonio_total:,.2f}")
col2.metric("Total Investido", f"R$ {investido_total:,.2f}")
col3.metric("Provento Mensal Estimado", f"R$ {dividendos_mes_total:,.2f}")
col4.metric(
    "Total Dividendos Recebidos", f"R$ {dividendos_historico_total:,.2f}"
)
col5.metric(
    "Lucro / Valorização",
    f"R$ {lucro_total:,.2f}",
    delta=f"{(lucro_total / investido_total) * 100:.2f}%"
    if investido_total > 0
    else "0%",
)

st.markdown("---")

# ------------------------------------------------------------------------------
# PAINEL DE RECOMENDAÇÃO DE APORTE DO MÊS
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

aporte_total_disponivel = aporte_bolso + dividendos_mes_total

st.subheader(
    f"🎯 RECOMENDAÇÃO DE APORTE DO MÊS - {mes_atual_nome.upper()} / {ano_atual}"
)
st.info(
    f"💰 **Aporte Total Disponível:** **R$ {aporte_total_disponivel:,.2f}** "
    f"(R$ {aporte_bolso:,.2f} do bolso + R$ {dividendos_mes_total:,.2f} de"
    " dividendos do mês)"
)

df_pendentes = df_carteira[df_carteira["progresso_meta"] < 100.0].sort_values(
    by="progresso_meta", ascending=True
)

if len(df_pendentes) >= 2:
    fii_1 = df_pendentes.iloc[0]
    fii_2 = df_pendentes.iloc[1]

    val_fii1 = aporte_total_disponivel * 0.60
    val_fii2 = aporte_total_disponivel * 0.40

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

    gasto_fii1 = cotas_fii1 * fii_1["cotacao_atual"]
    gasto_fii2 = cotas_fii2 * fii_2["cotacao_atual"]
    sobra_troco = aporte_total_disponivel - (gasto_fii1 + gasto_fii2)

    c_rec1, c_rec2, c_troco = st.columns(3)

    with c_rec1:
        st.success(
            f"🥇 **1º Foco: {fii_1['fii']}** (Progresso:"
            f" {fii_1['progresso_meta']:.1f}%)"
        )
        st.write(f"• Comprar: **{cotas_fii1} cotas**")
        st.write(f"• Preço Estimado: R$ {fii_1['cotacao_atual']:.2f}")
        st.write(f"• Total a investir: **R$ {gasto_fii1:,.2f}**")

    with c_rec2:
        st.warning(
            f"🥈 **2º Foco: {fii_2['fii']}** (Progresso:"
            f" {fii_2['progresso_meta']:.1f}%)"
        )
        st.write(f"• Comprar: **{cotas_fii2} cotas**")
        st.write(f"• Preço Estimado: R$ {fii_2['cotacao_atual']:.2f}")
        st.write(f"• Total a investir: **R$ {gasto_fii2:,.2f}**")

    with c_troco:
        st.metric("Sobra de Troco", f"R$ {sobra_troco:.2f}")
        st.caption(
            "💡 *O troco pode ser acumulado ou aplicado em FIIs de base R$ 10"
            " (ex: GGRC11).* "
        )
else:
    st.success("🎉 Parabéns! Todos os seus FIIs atingiram as metas estipuladas!")

st.markdown("---")

# ------------------------------------------------------------------------------
# GRÁFICOS INTERATIVOS
# ------------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "🏆 Ranking de Dividendos Acumulados",
    "💵 Provento do Mês (R$)",
    "🎯 Progresso das Metas",
])

with tab1:
    st.subheader(
        "🏆 Ranking dos FIIs que Mais Pagaram Dividendos (Desde o Início)"
    )
    df_rank_div = df_carteira.sort_values(
        by="dividendo_acumulado_historico", ascending=False
    )

    fig_rank = px.bar(
        df_rank_div,
        x="fii",
        y="dividendo_acumulado_historico",
        text_auto=".2f",
        labels={
            "fii": "Fundo Imobiliário",
            "dividendo_acumulado_historico": "Total Acumulado (R$)",
        },
        title="Ranking de Pagadores de Dividendos da Carteira",
    )
    fig_rank.update_traces(
        texttemplate="R$ %{y:.2f}", textposition="outside", hovertemplate="%{x}"
    )
    st.plotly_chart(fig_rank, use_container_width=True)

with tab2:
    st.subheader("💵 Rendimento Mensal Estimado por FII (Mês Atual)")
    df_div_sorted = df_carteira.sort_values(
        by="dividendo_mensal_total", ascending=False
    )

    fig_div = px.bar(
        df_div_sorted,
        x="fii",
        y="dividendo_mensal_total",
        text_auto=".2f",
        labels={
            "fii": "Fundo Imobiliário",
            "dividendo_mensal_total": "Rendimento Mensal (R$)",
        },
        title="Rendimento do Mês Atual por FII",
    )
    fig_div.update_traces(
        texttemplate="R$ %{y:.2f}", textposition="outside", hovertemplate="%{x}"
    )
    st.plotly_chart(fig_div, use_container_width=True)

with tab3:
    st.subheader("🎯 Progresso rumo às Metas (150 / 1.500 cotas)")
    fig_prog, ax = plt.subplots(figsize=(10, 4))

    # Descobrir os 2 menores progressos para pintar de vermelho
    dois_menores_valores = (
        df_carteira["progresso_meta"].nsmallest(2).values.tolist()
    )

    cores = []
    for p in df_carteira["progresso_meta"]:
        if p >= 100.0:
            cores.append("#2ec4b6")  # Verde para meta atingida
        elif p in dois_menores_valores:
            cores.append("#e63946")  # Vermelho para os 2 mais atrasados
        else:
            cores.append("#ff9f1c")  # Amarelo para os demais

    bars = ax.barh(
        df_carteira["fii"], df_carteira["progresso_meta"], color=cores
    )
    ax.set_xlim(0, 115)
    for bar, p in zip(bars, df_carteira["progresso_meta"]):
        ax.text(
            bar.get_width() + 2,
            bar.get_y() + bar.get_height() / 2,
            f"{p:.1f}%",
            va="center",
            ha="left",
            fontweight="bold",
        )
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle="--", alpha=0.5)
    st.pyplot(fig_prog)

# ------------------------------------------------------------------------------
# TABELA DETALHADA
# ------------------------------------------------------------------------------
st.markdown("### 📋 Tabela Completa de Posição")

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
