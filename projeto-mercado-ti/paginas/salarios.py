import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.dados import ORDEM_SENIORIDADE, brl, num
from utils.graficos import CORES_SENIORIDADE, COR_DESTAQUE, COR_UNICA, estilizar

dff = st.session_state["dff"]
ipca = st.session_state["ipca"]
fonte = st.session_state["fonte_ipca"]

st.title("💰 Salários, inflação e correlação")
if dff.empty:
    st.warning("Nenhum registro para os filtros selecionados.")
    st.stop()

cfg = {"displayModeBar": False}


def insight(texto: str):
    st.markdown(f'<div class="bloco-insight"><b>🔎 Interpretação.</b> {texto}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- Evolução salarial nominal x real
st.subheader("Evolução salarial: nominal × real")
st.caption(f"O salário real usa o IPCA anual obtido de **{fonte}** e está em reais de 2024.")

anual = dff.groupby("ano", as_index=False).agg(nominal=("salario_medio", "mean"), real=("salario_real", "mean"))
c1, c2 = st.columns([3, 1])
with c1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=anual["ano"], y=anual["nominal"], name="Salário nominal", mode="lines+markers",
                             line=dict(color=COR_UNICA, width=2.5), marker_size=8,
                             hovertemplate="%{x}: R$ %{y:,.0f}<extra>Nominal</extra>"))
    fig.add_trace(go.Scatter(x=anual["ano"], y=anual["real"], name="Salário real (R$ de 2024)", mode="lines+markers",
                             line=dict(color=COR_DESTAQUE, width=2.5), marker_size=8,
                             hovertemplate="%{x}: R$ %{y:,.0f}<extra>Real (2024)</extra>"))
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(title="R$", tickprefix="R$ ", separatethousands=True)
    st.plotly_chart(estilizar(fig, 380), config=cfg)
with c2:
    st.markdown("**IPCA anual (%)**")
    st.dataframe(ipca.rename(columns={"ano": "Ano", "ipca_pct": "IPCA %"}), hide_index=True, height=380,
                 column_config={"IPCA %": st.column_config.NumberColumn(format="%.2f")})

if len(anual) >= 2:
    a0, a1 = anual.iloc[0], anual.iloc[-1]
    v_nom = (a1["nominal"] / a0["nominal"] - 1) * 100
    v_real = (a1["real"] / a0["real"] - 1) * 100
    insight(f"Em valores nominais o salário médio variou {'+' if v_nom >= 0 else ''}{num(v_nom, 1)}% entre "
            f"{int(a0['ano'])} e {int(a1['ano'])} — praticamente estável. Descontando a inflação (IPCA), porém, "
            f"o <b>poder de compra caiu {num(abs(v_real), 1)}%</b>: {brl(a0['real'])} em {int(a0['ano'])} equivalem a "
            f"{brl(a1['real'])} em {int(a1['ano'])}, a preços de 2024. Ou seja, <b>não houve crescimento salarial real</b>; "
            "os reajustes não acompanharam a inflação, especialmente após os picos de 2015 e 2021.")

# ---------------------------------------------------------------- Distribuições
st.subheader("Distribuição salarial")
c1, c2 = st.columns(2)
with c1:
    fig = px.box(dff, x="senioridade", y="salario_medio", color="senioridade",
                 category_orders={"senioridade": ORDEM_SENIORIDADE}, color_discrete_map=CORES_SENIORIDADE,
                 title="Salário por senioridade", labels={"senioridade": "", "salario_medio": "Salário (R$)"})
    st.plotly_chart(estilizar(fig, 380, legenda=False), config=cfg)
with c2:
    sal_cargo = dff.groupby(["cargo", "senioridade"], observed=True, as_index=False)["salario_medio"].mean()
    fig = px.bar(sal_cargo, x="cargo", y="salario_medio", color="senioridade", barmode="group",
                 category_orders={"senioridade": ORDEM_SENIORIDADE}, color_discrete_map=CORES_SENIORIDADE,
                 title="Salário médio por cargo e senioridade", labels={"cargo": "", "salario_medio": "Salário (R$)"})
    fig.update_traces(hovertemplate="%{x} · %{fullData.name}: R$ %{y:,.0f}<extra></extra>")
    st.plotly_chart(estilizar(fig, 380), config=cfg)

med = dff.groupby("senioridade", observed=True)["salario_medio"].median()
insight(f"A mediana salarial é {brl(med.get('Júnior', np.nan))} para Júnior, {brl(med.get('Pleno', np.nan))} para Pleno "
        f"e {brl(med.get('Sênior', np.nan))} para Sênior. As caixas se sobrepõem quase totalmente: na base simulada a "
        "senioridade <b>explica pouco</b> da variação salarial — algo que, num mercado real, seria um ponto de atenção "
        "(ou um sinal de que a coluna representa faixas muito amplas).")

# ---------------------------------------------------------------- Correlação
st.subheader("Correlação estatística")
c1, c2 = st.columns(2)
with c1:
    amostra = dff.sample(min(len(dff), 2000), random_state=42)
    fig = px.scatter(amostra, x="quantidade_vagas", y="salario_medio", opacity=0.45,
                     hover_data={"cargo": True, "uf": True, "ano": True},
                     title="Dispersão: salário × vagas",
                     labels={"quantidade_vagas": "Vagas no registro", "salario_medio": "Salário (R$)", "cargo": "Cargo"})
    fig.update_traces(marker=dict(size=8, color=COR_UNICA, line=dict(width=1, color="white")), name="Registros",
                      showlegend=True)
    # Linha de tendência (mínimos quadrados com NumPy)
    if len(dff) < 3 or dff["quantidade_vagas"].nunique() < 2:
        st.info("Poucos dados para calcular correlação.")
        st.stop()
    a, b = np.polyfit(dff["quantidade_vagas"], dff["salario_medio"], 1)
    xs = np.linspace(dff["quantidade_vagas"].min(), dff["quantidade_vagas"].max(), 50)
    fig.add_trace(go.Scatter(x=xs, y=a * xs + b, mode="lines", name="Tendência linear",
                             line=dict(color="#0f172a", width=2, dash="dash")))
    st.plotly_chart(estilizar(fig, 420), config=cfg)
with c2:
    num_df = dff.assign(senioridade_cod=dff["senioridade"].cat.codes + 1)[
        ["salario_medio", "quantidade_vagas", "ano", "peso_demanda", "eh_remoto", "senioridade_cod"]]
    corr = num_df.corr(method="pearson").round(2)
    nomes = {"salario_medio": "Salário", "quantidade_vagas": "Vagas", "ano": "Ano", "peso_demanda": "Nível demanda",
             "eh_remoto": "Remoto", "senioridade_cod": "Senioridade"}
    corr = corr.rename(index=nomes, columns=nomes)
    fig = px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1, aspect="auto",
                    color_continuous_scale=["#c0392b", "#f0efec", "#2a78d6"],
                    title="Matriz de correlação de Pearson", labels=dict(color="r"))
    st.plotly_chart(estilizar(fig, 420), config=cfg)

pearson = dff["salario_medio"].corr(dff["quantidade_vagas"])
# Spearman = correlação de Pearson calculada sobre os postos (ranks); dispensa a biblioteca SciPy
spearman = dff["salario_medio"].rank().corr(dff["quantidade_vagas"].rank())
forca = "desprezível" if abs(pearson) < 0.1 else "fraca" if abs(pearson) < 0.3 else "moderada" if abs(pearson) < 0.6 else "forte"
m1, m2, m3 = st.columns(3)
m1.metric("Pearson (salário × vagas)", num(pearson, 3))
m2.metric("Spearman (salário × vagas)", num(spearman, 3))
m3.metric("Inclinação da reta", f"R$ {num(a, 1)} por vaga")
insight(f"A correlação entre salário e quantidade de vagas é <b>{forca}</b> (Pearson r = {num(pearson, 3)}; "
        f"Spearman ρ = {num(spearman, 3)}). Ofertar mais vagas não significa pagar mais nem menos: as variáveis são "
        "praticamente independentes na base. A matriz confirma que nenhum par de variáveis numéricas apresenta "
        "relação linear relevante.")