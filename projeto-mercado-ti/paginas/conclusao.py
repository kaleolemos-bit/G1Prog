import streamlit as st

from utils.dados import brl as _brl, calcular_kpis, num


def brl(v):  # escapa o $ para o Markdown não interpretar como fórmula LaTeX
    return _brl(v).replace("$", "\\$")

dff = st.session_state["dff"]
st.title("Conclusão executiva")
if dff.empty:
    st.warning("Nenhum registro para os filtros selecionados.")
    st.stop()

st.caption("Os números abaixo são recalculados conforme os filtros da barra lateral.")

k = calcular_kpis(dff)
total = k["total_vagas"]
anos = sorted(dff["ano"].unique())
a0, a1 = anos[0], anos[-1]

sen = dff.groupby("senioridade", observed=True)["quantidade_vagas"].sum()
area = dff[dff["ano"].isin([a0, a1])].pivot_table(index="area", columns="ano", values="quantidade_vagas", aggfunc="sum")
if a0 != a1:
    area["cresc"] = (area[a1] / area[a0] - 1) * 100
    area_top, area_cresc = area["cresc"].idxmax(), area["cresc"].max()
reg_norm = dff.groupby("regiao").apply(lambda g: g["quantidade_vagas"].sum() / g["cidade"].nunique(),
                                       include_groups=False)
sal = dff.groupby("ano").agg(nom=("salario_medio", "mean"), real=("salario_real", "mean"))
remoto = (dff.groupby("ano")["eh_remoto"].apply(lambda s: s.mean() * 100))

# ---------------------------------------------------------------- Respostas às perguntas
st.subheader("Respostas às perguntas orientadoras")
respostas = [
    ("Quais cargos possuem maior demanda?",
     f"**{k['cargo_top']}** lidera com {num(k['cargo_top_pct'], 1)}% das vagas, mas a distância para os demais "
     "cargos é pequena — a demanda é distribuída entre dados, desenvolvimento e DevOps."),
    ("Quais tecnologias aparecem com maior frequência?",
     f"**{k['tec_top']}** é a mais requisitada ({num(k['tec_top_pct'], 1)}%). As seis tecnologias têm participações "
     "próximas, com alternância de liderança ao longo dos anos."),
    ("Houve crescimento salarial ao longo do tempo?",
     (f"Não em termos reais. O salário nominal ficou estável ({brl(sal['nom'].iloc[0])} → {brl(sal['nom'].iloc[-1])}), "
      f"mas o salário real caiu de {brl(sal['real'].iloc[0])} para {brl(sal['real'].iloc[-1])} (R$ de 2024), "
      f"uma perda de {num((1 - sal['real'].iloc[-1] / sal['real'].iloc[0]) * 100, 1)}% no poder de compra.")
     if len(sal) > 1 else "Selecione mais de um ano para avaliar a evolução."),
    ("Existem diferenças regionais relevantes?",
     f"Em números absolutos sim — **{k['regiao_top']}** concentra {num(k['regiao_top_pct'], 1)}% das vagas. "
     f"Normalizando por cidade monitorada, a variação entre regiões cai para "
     f"{num((reg_norm.max() / reg_norm.min() - 1) * 100, 1)}%, ou seja, a diferença vem do tamanho da amostra regional."),
    ("Quais áreas de TI possuem maior crescimento?",
     f"Entre {a0} e {a1}, **{area_top}** teve o maior crescimento de vagas "
     f"({'+' if area_cresc >= 0 else ''}{num(area_cresc, 1)}%)." if a0 != a1 else
     "Selecione mais de um ano para comparar o crescimento."),
    ("Qual nível de experiência é mais exigido?",
     f"**{sen.idxmax()}** ({num(sen.max() / total * 100, 1)}% das vagas), com distribuição equilibrada entre os três níveis."),
    ("Quais regiões concentram mais oportunidades?",
     f"**{k['regiao_top']}** em volume; **{reg_norm.idxmax()}** em vagas por cidade "
     f"({num(reg_norm.max())} vagas/cidade)."),
]
for pergunta, resposta in respostas:
    with st.container(border=True):
        st.markdown(f"**{pergunta}**")
        st.markdown(resposta)

# ---------------------------------------------------------------- Síntese
st.subheader("Síntese para tomada de decisão")
pico_rem = remoto.idxmax() if not remoto.empty else "—"
st.markdown(
    f"""
1. **Mercado estável e diversificado.** O volume de vagas se manteve próximo de {num(total / len(anos))} por ano,
   sem um cargo ou tecnologia dominante. Para quem está se formando, isso significa várias portas de entrada.
2. **Perda de poder de compra.** Sem reajustes acima da inflação, os salários reais encolheram. Profissionais devem
   negociar reajustes pelo IPCA; empresas que corrigirem salários terão vantagem para reter talentos.
3. **Efeito pandemia no trabalho remoto.** A participação do remoto teve pico em **{pico_rem}**; no recorte,
   a modalidade predominante é **{k['modalidade_top']}** ({num(k['modalidade_top_pct'], 1)}%), com as três modalidades equilibradas.
4. **Oportunidades fora do eixo Sudeste.** Normalizando por cidade, todas as regiões oferecem volume semelhante —
   políticas de contratação remota podem aproveitar talentos do Norte, Nordeste e Centro-Oeste.
5. **Perfis versáteis.** Todas as tecnologias aparecem em todos os cargos: combinar uma linguagem (Python/Java/JavaScript)
   com dados (SQL/Power BI) e nuvem (AWS) amplia a empregabilidade.

> **Limitação:** a base é **simulada**, com distribuição quase uniforme entre categorias. As conclusões ilustram o
> método analítico e não devem ser usadas como retrato fiel do mercado brasileiro.
    """
)