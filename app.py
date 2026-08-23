import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Configuração da página
st.set_page_config(
    page_title="Projeto Equalização 150/1500",
    page_icon="📊",
    layout="wide"
)

st.title("📊 PAINEL DE CONTROLE - PROJETO EQUALIZAÇÃO")
st.markdown("Acompanhe o progresso e a equalização das cotas dos seus FIIs em tempo real.")

# ------------------------------------------------------------------------------
# MENU LATERAL (SIDEBAR) - ENTRADA DE DADOS
# ------------------------------------------------------------------------------
st.sidebar.header("📝 Cotas Atuais")
st.sidebar.markdown("Atualize a quantidade de cotas de cada fundo abaixo:")

alzr11 = st.sidebar.number_input("ALZR11", min_value=0, value=1500, step=1)
xpml11 = st.sidebar.number_input("XPML11", min_value=0, value=106, step=1)
ggrc11 = st.sidebar.number_input("GGRC11", min_value=0, value=1010, step=1)
mall11 = st.sidebar.number_input("MALL11", min_value=0, value=69, step=1)
btlg11 = st.sidebar.number_input("BTLG11", min_value=0, value=64, step=1)
brco11 = st.sidebar.number_input("BRCO11", min_value=0, value=56, step=1)

# Estrutura de dados
fiis = ['ALZR11', 'XPML11', 'GGRC11', 'MALL11', 'BTLG11', 'BRCO11']
cotas_atuais = [alzr11, xpml11, ggrc11, mall11, btlg11, brco11]
metas = [1500, 150, 1500, 150, 150, 150]

# Normalização percentual
progresso = [
    min(100.0, (alzr11 / 1500) * 100),
    min(100.0, (xpml11 / 150) * 100),
    min(100.0, (ggrc11 / 1500) * 100),
    min(100.0, (mall11 / 150) * 100),
    min(100.0, (btlg11 / 150) * 100),
    min(100.0, (brco11 / 150) * 100),
]

menor_progresso = min(progresso)

# Definição Dinâmica de Cores
# 🟢 Verde (#2ec4b6): 100%
# 🔴 Vermelho (#e63946): Menor progresso
# 🟡 Amarelo (#ff9f1c): Em andamento
cores = []
for p in progresso:
    if p >= 100.0:
        cores.append('#2ec4b6')
    elif p == menor_progresso:
        cores.append('#e63946')
    else:
        cores.append('#ff9f1c')

# ------------------------------------------------------------------------------
# CONTEÚDO PRINCIPAL - MÉTRICAS E GRÁFICO
# ------------------------------------------------------------------------------

# Tabela e Cartões de Resumo
col1, col2, col3 = st.columns(3)
col1.metric("Total de FIIs na Carteira", len(fiis))
col2.metric("Metas Batidas (100%)", sum(1 for p in progresso if p >= 100.0))
col3.metric("FII com Menor Progresso", fiis[progresso.index(menor_progresso)], f"{menor_progresso:.1f}%")

st.markdown("---")

# Gráfico Matplotlib
fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.barh(fiis, progresso, color=cores)
ax.set_xlim(0, 115)
ax.set_title('PROJETO EQUALIZAÇÃO 150/1500 - PROGRESSO (%)', fontsize=14, fontweight='bold')
ax.set_xlabel('% Concluído rumo à meta', fontsize=11)

for bar, p in zip(bars, progresso):
    ax.text(
        bar.get_width() + 2,
        bar.get_y() + bar.get_height() / 2,
        f'{p:.1f}%',
        va='center',
        ha='left',
        fontsize=10,
        fontweight='bold',
    )

ax.invert_yaxis()
ax.grid(axis='x', linestyle='--', alpha=0.5)

st.pyplot(fig)

# Tabela Detalhada
st.markdown("### 📋 Tabela de Progresso Detalhada")
df = pd.DataFrame({
    'FII': fiis,
    'Cotas Atuais': cotas_atuais,
    'Meta Final': metas,
    'Cotas Restantes': [max(0, m - c) for m, c in zip(metas, cotas_atuais)],
    'Progresso (%)': [round(p, 1) for p in progresso]
})

st.dataframe(df, use_container_width=True)
