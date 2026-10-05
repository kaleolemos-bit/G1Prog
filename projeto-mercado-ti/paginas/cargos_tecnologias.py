import plotly.express as px
import streamlit as st

from utils.dados import ESCALA_SEQUENCIAL, ORDEM_MODALIDADE, ORDEM_SENIORIDADE, num
from utils.graficos import (CORES_CARGO, CORES_MODALIDADE, CORES_SENIORIDADE,
                            CORES_TEC, COR_DESTAQUE, COR_UNICA, estilizar)

dff = st.session_state["dff"]
st.title("Cargos, tecnologias, senioridade e modalidade")
if dff.empty:
    st.warning("Nenhum registro para os filtros selecionados.")
    st.stop()

cfg = {"displayModeBar": False}


def insight(texto: str):
    st.markdown(f'<div class="bloco-insight"><b>Interpretação.</b> {texto}</div>', unsafe_allow_html=True)


total = dff["quantidade_vagas"].sum()
aba1, aba2, aba3, aba4 = st.tabs(["Cargos", "Tecnologias", "Senioridade", "Modalidade de trabalho"])

# ============================================================== CARGOS
with aba1:
    por_cargo = (dff.groupby("cargo", as_index=False)
                 .agg(vagas=("quantidade_vagas", "sum"), salario=("salario_medio", "mean"))
                 .sort_values("vagas"))
    por_cargo["participacao"] = por_cargo["vagas"] / total * 100
    c1, c2 = st.columns([3, 2])
    with c1:
        fig = px.bar(por_cargo, x="vagas", y="cargo", orientation="h", title="Vagas por cargo",
                     labels={"vagas": "Vagas", "cargo": ""}, text=por_cargo["vagas"].map(num),
                     color="cargo", color_discrete_map=CORES_CARGO)
        fig.update_traces(textposition="outside", hovertemplate="%{y}: %{x:,.0f} vagas<extra></extra>",
                          cliponaxis=False)
        fig.update_xaxes(range=[0, por_cargo["vagas"].max() * 1.18])
        st.plotly_chart(estilizar(fig, 360, legenda=False), config=cfg)
    with c2:
        st.markdown("**Ranking de cargos**")
        st.dataframe(
            por_cargo.sort_values("vagas", ascending=False).assign(
                vagas=lambda d: d["vagas"].map(num),
                salario=lambda d: d["salario"].map(lambda v: f"R$ {num(v)}"),
                participacao=lambda d: d["participacao"].map(lambda v: f"{num(v, 1)}%"),
            ).rename(columns={"cargo": "Cargo", "vagas": "Vagas", "salario": "Salário médio",
                              "participacao": "Participação"}),
            hide_index=True,
        )

    # Crescimento por área (primeiro vs. último ano do recorte)
    anos = sorted(dff["ano"].unique())
    if len(anos) >= 2:
        a0, a1 = anos[0], anos[-1]
        cresc = (dff[dff["ano"].isin([a0, a1])]
                 .pivot_table(index="area", columns="ano", values="quantidade_vagas", aggfunc="sum")
                 .reset_index())
        cresc["crescimento"] = (cresc[a1] / cresc[a0] - 1) * 100
        cresc = cresc.sort_values("crescimento")
        fig = px.bar(cresc, x="crescimento", y="area", orientation="h",
                     title=f"Crescimento de vagas por área de TI ({a0} → {a1})",
                     labels={"crescimento": "Crescimento (%)", "area": ""})
        fig.update_traces(marker_color=[COR_UNICA if v >= 0 else COR_DESTAQUE for v in cresc["crescimento"]],
                          hovertemplate="%{y}: %{x:.1f}%<extra></extra>")
        st.plotly_chart(estilizar(fig, 260, legenda=False), config=cfg)
        melhor = cresc.iloc[-1]
    top, ult = por_cargo.iloc[-1], por_cargo.iloc[0]
    diff = (top["vagas"] / ult["vagas"] - 1) * 100
    txt = (f"<b>{top['cargo']}</b> lidera com {num(top['vagas'])} vagas ({num(top['participacao'], 1)}% do total), "
           f"enquanto <b>{ult['cargo']}</b> tem a menor oferta ({num(ult['vagas'])}). A diferença entre o primeiro e o "
           f"último colocado é de {num(diff, 1)}%, ou seja, a demanda está <b>bem distribuída</b> entre os perfis — "
           f"não há um cargo dominante. ")
    if len(anos) >= 2:
        txt += (f"Entre {a0} e {a1}, a área que mais cresceu foi <b>{melhor['area']}</b> "
                f"({'+' if melhor['crescimento'] >= 0 else ''}{num(melhor['crescimento'], 1)}%).")
    insight(txt)

# ============================================================== TECNOLOGIAS
with aba2:
    por_tec = dff.groupby("tecnologia", as_index=False)["quantidade_vagas"].sum().sort_values("quantidade_vagas")
    por_tec["pct"] = por_tec["quantidade_vagas"] / total * 100
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(por_tec, x="quantidade_vagas", y="tecnologia", orientation="h",
                     title="Ranking de tecnologias (vagas)", color="tecnologia", color_discrete_map=CORES_TEC,
                     labels={"quantidade_vagas": "Vagas", "tecnologia": ""},
                     text=por_tec["pct"].map(lambda v: f"{num(v, 1)}%"))
        fig.update_traces(textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}: %{x:,.0f} vagas<extra></extra>")
        fig.update_xaxes(range=[0, por_tec["quantidade_vagas"].max() * 1.18])
        st.plotly_chart(estilizar(fig, 360, legenda=False), config=cfg)
    with c2:
        heat = dff.pivot_table(index="cargo", columns="tecnologia", values="quantidade_vagas", aggfunc="sum")
        fig = px.imshow(heat, text_auto=",.0f", aspect="auto", color_continuous_scale=ESCALA_SEQUENCIAL,
                        title="Cargo × tecnologia (vagas)", labels=dict(color="Vagas", x="", y=""))
        fig.update_traces(hovertemplate="%{y} · %{x}: %{z:,.0f} vagas<extra></extra>")
        st.plotly_chart(estilizar(fig, 360), config=cfg)

    evol = dff.groupby(["ano", "tecnologia"], as_index=False)["quantidade_vagas"].sum()
    evol["participacao"] = evol["quantidade_vagas"] / evol.groupby("ano")["quantidade_vagas"].transform("sum") * 100
    fig = px.line(evol, x="ano", y="participacao", color="tecnologia", markers=True,
                  color_discrete_map=CORES_TEC, title="Participação de cada tecnologia nas vagas por ano (%)",
                  labels={"ano": "Ano", "participacao": "Participação (%)", "tecnologia": "Tecnologia"})
    fig.update_traces(line_width=2, marker_size=7, hovertemplate="%{x}: %{y:.1f}%<extra>%{fullData.name}</extra>")
    fig.update_xaxes(dtick=1)
    st.plotly_chart(estilizar(fig, 380), config=cfg)

    t_top, t_low = por_tec.iloc[-1], por_tec.iloc[0]
    txt = (f"<b>{t_top['tecnologia']}</b> é a tecnologia mais requisitada ({num(t_top['pct'], 1)}% das vagas) e "
           f"<b>{t_low['tecnologia']}</b> a menos citada ({num(t_low['pct'], 1)}%). ")
    if evol["ano"].nunique() >= 2:
        a0, a1 = evol["ano"].min(), evol["ano"].max()
        var = (evol[evol["ano"] == a1].set_index("tecnologia")["participacao"]
               - evol[evol["ano"] == a0].set_index("tecnologia")["participacao"]).dropna().sort_values()
        if not var.empty:
            txt += (f"Comparando {a0} e {a1}, quem mais ganhou espaço foi <b>{var.index[-1]}</b> "
                    f"({'+' if var.iloc[-1] >= 0 else ''}{num(var.iloc[-1], 1)} p.p.) e quem mais perdeu foi "
                    f"<b>{var.index[0]}</b> ({num(var.iloc[0], 1)} p.p.). O mapa de calor mostra que todas as "
                    "tecnologias aparecem em todos os cargos — o mercado simulado valoriza perfis versáteis.")
    insight(txt)

# ============================================================== SENIORIDADE
with aba3:
    sen = (dff.groupby(["cargo", "senioridade"], observed=True, as_index=False)["quantidade_vagas"].sum())
    c1, c2 = st.columns([3, 2])
    with c1:
        fig = px.bar(sen, x="cargo", y="quantidade_vagas", color="senioridade", barmode="group",
                     category_orders={"senioridade": ORDEM_SENIORIDADE}, color_discrete_map=CORES_SENIORIDADE,
                     title="Vagas por cargo e senioridade", labels={"cargo": "", "quantidade_vagas": "Vagas"})
        fig.update_traces(hovertemplate="%{x} · %{fullData.name}: %{y:,.0f}<extra></extra>")
        st.plotly_chart(estilizar(fig, 380), config=cfg)
    with c2:
        tot_sen = dff.groupby("senioridade", observed=True)["quantidade_vagas"].sum()
        fig = px.bar(x=tot_sen.index.astype(str), y=tot_sen.values, color=tot_sen.index.astype(str),
                     color_discrete_map=CORES_SENIORIDADE, title="Total por nível",
                     labels={"x": "", "y": "Vagas"}, text=[f"{num(v / total * 100, 1)}%" for v in tot_sen.values])
        fig.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(estilizar(fig, 380, legenda=False), config=cfg)
    nivel = tot_sen.idxmax()
    insight(f"O nível mais exigido é <b>{nivel}</b>, com {num(tot_sen.max() / total * 100, 1)}% das vagas. "
            "A distribuição entre Júnior, Pleno e Sênior é próxima de um terço para cada nível, sinal de que há "
            "<b>porta de entrada</b> para iniciantes e, ao mesmo tempo, espaço para profissionais experientes.")

# ============================================================== MODALIDADE
with aba4:
    mod = dff.groupby(["ano", "modalidade"], observed=True, as_index=False)["quantidade_vagas"].sum()
    mod["pct"] = mod["quantidade_vagas"] / mod.groupby("ano")["quantidade_vagas"].transform("sum") * 100
    fig = px.line(mod, x="ano", y="pct", color="modalidade", markers=True,
                  category_orders={"modalidade": ORDEM_MODALIDADE}, color_discrete_map=CORES_MODALIDADE,
                  title="Participação de cada modalidade por ano (%)",
                  labels={"ano": "Ano", "pct": "Participação (%)", "modalidade": "Modalidade"})
    fig.update_traces(line_width=2, marker_size=8, hovertemplate="%{x}: %{y:.1f}%<extra>%{fullData.name}</extra>")
    fig.update_xaxes(dtick=1)
    if 2020 in mod["ano"].values:
        fig.add_vrect(x0=2019.5, x1=2021.5, fillcolor="#f1f5f9", line_width=0, layer="below",
                      annotation_text="Pandemia", annotation_position="top left")
    st.plotly_chart(estilizar(fig, 380), config=cfg)

    remoto = mod[mod["modalidade"] == "Remoto"].set_index("ano")["pct"]
    tot_mod = dff.groupby("modalidade", observed=True)["quantidade_vagas"].sum()
    txt = (f"No recorte, a modalidade predominante é <b>{tot_mod.idxmax()}</b> "
           f"({num(tot_mod.max() / total * 100, 1)}% das vagas). ")
    if not remoto.empty:
        txt += (f"A participação do trabalho remoto atingiu o pico em <b>{remoto.idxmax()}</b> "
                f"({num(remoto.max(), 1)}%)")
        txt += (", coerente com a adoção emergencial do home office na pandemia; nos anos seguintes o "
                "presencial e o híbrido recuperam espaço, e as três modalidades voltam a se equilibrar."
                if remoto.idxmax() in (2020, 2021) else ".")
    insight(txt)