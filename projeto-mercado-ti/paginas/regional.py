import json

import plotly.express as px
import streamlit as st

from utils.dados import ESCALA_SEQUENCIAL, GEOJSON, ORDEM_REGIAO, brl, num
from utils.graficos import CORES_REGIAO, estilizar

dff = st.session_state["dff"]
st.title("🗺️ Análise regional")
if dff.empty:
    st.warning("Nenhum registro para os filtros selecionados.")
    st.stop()

cfg = {"displayModeBar": False}


@st.cache_data
def carregar_geojson():
    with open(GEOJSON, encoding="utf-8") as f:
        return json.load(f)


geo = carregar_geojson()
total = dff["quantidade_vagas"].sum()

por_uf = (dff.groupby(["regiao", "uf"], as_index=False)
          .agg(vagas=("quantidade_vagas", "sum"), cidades=("cidade", "nunique"),
               salario=("salario_medio", "mean"), remoto=("eh_remoto", "mean")))
por_uf["vagas_por_cidade"] = por_uf["vagas"] / por_uf["cidades"]
por_uf["participacao"] = por_uf["vagas"] / total * 100
por_uf["remoto"] *= 100

metricas = {
    "Total de vagas": ("vagas", ",.0f"),
    "Vagas por cidade monitorada": ("vagas_por_cidade", ",.0f"),
    "Salário médio (R$)": ("salario", ",.0f"),
    "% de vagas remotas": ("remoto", ".1f"),
}
escolha = st.radio("Indicador do mapa", list(metricas), horizontal=True)
col, fmt = metricas[escolha]

c1, c2 = st.columns([3, 2])
with c1:
    fig = px.choropleth(por_uf, geojson=geo, locations="uf", featureidkey="properties.sigla", color=col,
                        color_continuous_scale=ESCALA_SEQUENCIAL, hover_name="uf",
                        hover_data={"uf": False, "regiao": True, "vagas": ":,.0f", "cidades": True,
                                    "salario": ":,.0f", col: f":{fmt}"},
                        labels={col: escolha, "regiao": "Região", "vagas": "Vagas", "cidades": "Cidades",
                                "salario": "Salário médio"})
    fig.update_geos(fitbounds="geojson", visible=False, bgcolor="rgba(0,0,0,0)", projection_type="mercator")
    fig.update_traces(marker_line_color="#ffffff", marker_line_width=0.8)
    fig = estilizar(fig, 520)
    fig.update_layout(title=f"{escolha} por estado", coloraxis_colorbar=dict(title="", thickness=14),
                      margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, config=cfg)
    st.caption("Estados em branco não possuem registros no dataset (ou foram removidos pelos filtros).")
with c2:
    st.markdown("**Ranking de estados**")
    st.dataframe(
        por_uf.sort_values(col, ascending=False)[["uf", "regiao", "vagas", "cidades", "vagas_por_cidade", "salario"]]
        .rename(columns={"uf": "UF", "regiao": "Região", "vagas": "Vagas", "cidades": "Cidades",
                         "vagas_por_cidade": "Vagas/cidade", "salario": "Salário médio"}),
        hide_index=True, height=480,
        column_config={
            "Vagas": st.column_config.NumberColumn(format="%d"),
            "Vagas/cidade": st.column_config.NumberColumn(format="%.0f"),
            "Salário médio": st.column_config.NumberColumn(format="R$ %.0f"),
        },
    )

# ---------------------------------------------------------------- Comparação entre regiões
st.subheader("Comparação entre regiões")
por_reg = (dff.groupby("regiao", as_index=False)
           .agg(vagas=("quantidade_vagas", "sum"), cidades=("cidade", "nunique"), salario=("salario_medio", "mean")))
por_reg["vagas_por_cidade"] = por_reg["vagas"] / por_reg["cidades"]
por_reg["participacao"] = por_reg["vagas"] / total * 100
ordem = [r for r in ORDEM_REGIAO if r in por_reg["regiao"].values]

c1, c2 = st.columns(2)
with c1:
    d = por_reg.sort_values("vagas", ascending=False)
    fig = px.bar(d, x="regiao", y="vagas", color="regiao", color_discrete_map=CORES_REGIAO,
                 title="Total de vagas por região", labels={"regiao": "", "vagas": "Vagas"},
                 text=d["participacao"].map(lambda v: f"{num(v, 1)}%"))
    fig.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:,.0f} vagas<extra></extra>")
    st.plotly_chart(estilizar(fig, 360, legenda=False), config=cfg)
with c2:
    d = por_reg.sort_values("vagas_por_cidade", ascending=False)
    fig = px.bar(d, x="regiao", y="vagas_por_cidade", color="regiao", color_discrete_map=CORES_REGIAO,
                 title="Vagas por cidade monitorada (normalizado)", labels={"regiao": "", "vagas_por_cidade": "Vagas/cidade"},
                 text=d["vagas_por_cidade"].map(num))
    fig.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:,.0f} vagas/cidade<extra></extra>")
    st.plotly_chart(estilizar(fig, 360, legenda=False), config=cfg)

# Heatmap regional ao longo do tempo
heat = dff.pivot_table(index="regiao", columns="ano", values="quantidade_vagas", aggfunc="sum").reindex(ordem)
fig = px.imshow(heat, text_auto=",.0f", aspect="auto", color_continuous_scale=ESCALA_SEQUENCIAL,
                title="Heatmap regional — vagas por região e ano", labels=dict(color="Vagas", x="Ano", y=""))
fig.update_xaxes(dtick=1)
fig.update_traces(hovertemplate="%{y} · %{x}: %{z:,.0f} vagas<extra></extra>")
st.plotly_chart(estilizar(fig, 330), config=cfg)

heat2 = dff.pivot_table(index="regiao", columns="cargo", values="quantidade_vagas", aggfunc="sum").reindex(ordem)
heat2 = heat2.div(heat2.sum(axis=1), axis=0) * 100
fig = px.imshow(heat2, text_auto=".1f", aspect="auto", color_continuous_scale=ESCALA_SEQUENCIAL,
                title="Perfil de cargos em cada região (% das vagas da região)", labels=dict(color="%", x="", y=""))
fig.update_traces(hovertemplate="%{y} · %{x}: %{z:.1f}%<extra></extra>")
st.plotly_chart(estilizar(fig, 330), config=cfg)

top = por_reg.sort_values("vagas", ascending=False).iloc[0]
top_norm = por_reg.sort_values("vagas_por_cidade", ascending=False).iloc[0]
sal_max = por_reg.sort_values("salario", ascending=False).iloc[0]
sal_min = por_reg.sort_values("salario").iloc[0]
amostra = "; ".join(f"{r.regiao}: {r.cidades} cidades" for r in por_reg.sort_values("cidades", ascending=False).itertuples())
st.markdown(
    f"""<div class="bloco-insight"><b>🔎 Interpretação.</b>
    <b>{top['regiao']}</b> concentra o maior número absoluto de vagas ({num(top['participacao'], 1)}% do total).
    Porém, ao dividir pelo número de cidades monitoradas, a liderança passa a ser de <b>{top_norm['regiao']}</b>
    ({num(top_norm['vagas_por_cidade'])} vagas/cidade) e as diferenças entre regiões quase desaparecem —
    a concentração absoluta reflete principalmente <b>quantas cidades de cada região estão na amostra</b>
    ({amostra}). Em salário, a maior média está em
    <b>{sal_max['regiao']}</b> ({brl(sal_max['salario'])}) e a menor em <b>{sal_min['regiao']}</b>
    ({brl(sal_min['salario'])}), uma diferença de {num((sal_max['salario'] / sal_min['salario'] - 1) * 100, 1)}%.
    O perfil de cargos é parecido entre regiões, o que sugere oportunidades distribuídas pelo país.</div>""",
    unsafe_allow_html=True,
)
