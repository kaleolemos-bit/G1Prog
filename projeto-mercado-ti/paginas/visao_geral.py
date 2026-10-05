import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.dados import brl, calcular_kpis, num
from utils.graficos import COR_DESTAQUE, COR_UNICA, estilizar

df = st.session_state["df"]
dff = st.session_state["dff"]

st.title("Mercado de Trabalho em Tecnologia da Informação no Brasil")
st.markdown(
    "##### Dashboard analítico de vagas, salários, tecnologias e regiões · 2015 a 2024"
)

with st.expander("📌 Descrição do problema", expanded=True):
    st.markdown(
        """
A transformação digital aumentou a procura por profissionais de **desenvolvimento de software,
dados, nuvem e infraestrutura**. Empresas, estudantes e instituições de ensino precisam saber
**quais cargos e tecnologias são mais demandados, como os salários evoluíram e onde estão as oportunidades**.

Este dashboard investiga uma base simulada com **4.440 registros mensais** de vagas de TI
(5 regiões, 20 estados, 37 cidades) e responde às perguntas orientadoras do projeto:
cargos com maior demanda, tecnologias mais frequentes, evolução salarial, diferenças regionais,
áreas que mais crescem, senioridade mais exigida e regiões com mais oportunidades.

Use os **filtros da barra lateral** — eles valem para todas as páginas.
        """
    )

if dff.empty:
    st.warning("Nenhum registro corresponde aos filtros selecionados. Ajuste os filtros na barra lateral.")
    st.stop()

# ---------------------------------------------------------------- KPIs
k = calcular_kpis(dff)
st.subheader("Indicadores-chave")
c1, c2, c3 = st.columns(3)
c1.metric("Total de vagas", num(k["total_vagas"]), help="Soma de quantidade_vagas no recorte filtrado")
c2.metric("Cargo mais demandado", k["cargo_top"], f"{num(k['cargo_top_pct'], 1)}% das vagas", delta_color="off")
c3.metric("Tecnologia mais requisitada", k["tec_top"], f"{num(k['tec_top_pct'], 1)}% das vagas", delta_color="off")
c4, c5, c6 = st.columns(3)
c4.metric("Salário médio nacional", brl(k["salario_medio"]),
          help="Média do salário ponderada pela quantidade de vagas")
c5.metric("Região com mais vagas", k["regiao_top"], f"{num(k['regiao_top_pct'], 1)}% das vagas", delta_color="off")
c6.metric("Modalidade predominante", k["modalidade_top"], f"{num(k['modalidade_top_pct'], 1)}% das vagas",
          delta_color="off")

# ---------------------------------------------------------------- Série temporal
st.subheader("Evolução temporal das vagas")
mensal = dff.groupby("data", as_index=False)["quantidade_vagas"].sum().sort_values("data")
mensal["media_movel_12m"] = mensal["quantidade_vagas"].rolling(12, min_periods=3).mean()

fig = go.Figure()
fig.add_trace(go.Scatter(x=mensal["data"], y=mensal["quantidade_vagas"], name="Vagas no mês",
                         mode="lines", line=dict(color="#9ec5f4", width=1.5),
                         hovertemplate="%{x|%b/%Y}: %{y:,.0f} vagas<extra></extra>"))
fig.add_trace(go.Scatter(x=mensal["data"], y=mensal["media_movel_12m"], name="Média móvel 12 meses",
                         mode="lines", line=dict(color=COR_UNICA, width=2.5),
                         hovertemplate="%{x|%b/%Y}: %{y:,.0f} (média 12m)<extra></extra>"))
fig.add_vrect(x0="2020-03-01", x1="2021-12-31", fillcolor="#f1f5f9", line_width=0, layer="below",
              annotation_text="Pandemia", annotation_position="top left")
fig.update_yaxes(title="Vagas", separatethousands=True)
st.plotly_chart(estilizar(fig, 400), config={"displayModeBar": False})

# ---------------------------------------------------------------- Crescimento anual
anual = dff.groupby("ano", as_index=False).agg(vagas=("quantidade_vagas", "sum"))
anual["variacao_pct"] = anual["vagas"].pct_change() * 100
col_a, col_b = st.columns([3, 2])
with col_a:
    fig2 = px.bar(anual, x="ano", y="variacao_pct", title="Variação anual do total de vagas (%)",
                  labels={"ano": "Ano", "variacao_pct": "Variação (%)"})
    fig2.update_traces(marker_color=[COR_UNICA if (v or 0) >= 0 else COR_DESTAQUE for v in anual["variacao_pct"]],
                       hovertemplate="%{x}: %{y:.1f}%<extra></extra>")
    fig2.update_xaxes(dtick=1)
    st.plotly_chart(estilizar(fig2, 330, legenda=False), config={"displayModeBar": False})
with col_b:
    st.markdown("**Vagas por ano**")
    tabela = anual.assign(
        vagas=anual["vagas"].map(num),
        variacao_pct=anual["variacao_pct"].map(lambda v: "—" if v != v else f"{v:+.1f}%".replace(".", ",")),
    ).rename(columns={"ano": "Ano", "vagas": "Vagas", "variacao_pct": "Var. anual"})
    st.dataframe(tabela, hide_index=True, height=35 * (len(tabela) + 1) + 3)

# ---------------------------------------------------------------- Interpretação
if len(anual) >= 2:
    ini, fim = anual.iloc[0], anual.iloc[-1]
    cresc = (fim["vagas"] / ini["vagas"] - 1) * 100
    pico = mensal.loc[mensal["quantidade_vagas"].idxmax()]
    vale = mensal.loc[mensal["quantidade_vagas"].idxmin()]
    cv = mensal["quantidade_vagas"].std() / mensal["quantidade_vagas"].mean() * 100
    tendencia = ("crescimento" if cresc > 3 else "queda" if cresc < -3 else "estabilidade")
    st.markdown(
        f"""<div class="bloco-insight"><b>🔎 Interpretação.</b>
        Entre {int(ini['ano'])} e {int(fim['ano'])} o volume anual de vagas passou de
        {num(ini['vagas'])} para {num(fim['vagas'])} ({'+' if cresc>=0 else ''}{num(cresc, 1)}%), indicando <b>{tendencia}</b> do mercado no recorte.
        O mês de maior oferta foi {pico['data']:%m/%Y} ({num(pico['quantidade_vagas'])} vagas) e o de menor,
        {vale['data']:%m/%Y} ({num(vale['quantidade_vagas'])}). A variação mês a mês é baixa
        (coeficiente de variação de {num(cv, 1)}%), por isso a <b>média móvel de 12 meses</b> é a melhor forma de ler a tendência:
        ela mostra um mercado estável em volume, sem saltos estruturais — o que muda ao longo do tempo é a
        <b>composição</b> (tecnologias, modalidade e salário real), explorada nas próximas páginas.</div>""",
        unsafe_allow_html=True,
    )
