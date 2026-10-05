"""
Dashboard — Mercado de Trabalho em Tecnologia da Informação no Brasil (2015–2024)

Arquivo principal do Streamlit. Responsável por:
- carregar e tratar os dados (CSV do projeto ou upload);
- consumir a API do Banco Central (IPCA);
- garantir a existência do banco SQLite;
- desenhar os filtros globais na barra lateral;
- montar a navegação multipágina.

Executar localmente:  streamlit run app.py
"""
import streamlit as st

from utils.banco import banco_existe, criar_banco
from utils.dados import MESES, ORDEM_REGIAO, ORDEM_SENIORIDADE, preparar_base

st.set_page_config(
    page_title="Mercado de TI no Brasil",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        background: #f0fdfa; border: 1px solid #ccfbf1; border-left: 4px solid #0f766e;
        border-radius: 10px; padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] p { font-size: 0.85rem; color: #475569; }
    [data-testid="stMetricValue"] { font-size: 1.45rem; color: #0f172a; }
    .bloco-insight {
        background: #fffbeb; border-left: 4px solid #d97706; border-radius: 8px;
        padding: 12px 16px; margin: 6px 0 18px 0; color: #422006;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Carregamento com cache
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Carregando e tratando os dados...", ttl=3600)
def carregar(conteudo_upload: bytes | None = None):
    import io
    origem = io.BytesIO(conteudo_upload) if conteudo_upload else None
    return preparar_base(origem)


@st.cache_resource(show_spinner="Preparando banco SQLite...")
def garantir_banco():
    if not banco_existe():
        df, _, ipca, _ = carregar()
        criar_banco(df, ipca)
    return True


# ---------------------------------------------------------------------------
# Barra lateral — fonte de dados + filtros globais
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Mercado de TI")
    st.caption("Brasil · 2015–2024")

    with st.expander("Fonte de dados (upload opcional)"):
        arquivo = st.file_uploader(
            "Envie um CSV com a mesma estrutura do dataset", type=["csv"],
            help="Se nenhum arquivo for enviado, o dashboard usa dados/simulacao_mercado_ti_brasil.csv",
        )

try:
    df, relatorio, ipca, fonte_ipca = carregar(arquivo.getvalue() if arquivo else None)
except ValueError as erro:
    st.sidebar.error(str(erro))
    df, relatorio, ipca, fonte_ipca = carregar()

garantir_banco()

with st.sidebar:
    st.markdown("### Filtros")

    anos = sorted(df["ano"].unique())
    faixa_anos = st.slider("Ano", min_value=int(min(anos)), max_value=int(max(anos)),
                           value=(int(min(anos)), int(max(anos))), key="f_ano")

    meses_sel = st.multiselect("Mês", options=list(MESES.keys()), format_func=lambda m: MESES[m],
                               placeholder="Todos os meses", key="f_mes")

    regioes = [r for r in ORDEM_REGIAO if r in df["regiao"].unique()]
    regioes_sel = st.multiselect("Região", regioes, placeholder="Todas as regiões", key="f_regiao")

    base_uf = df[df["regiao"].isin(regioes_sel)] if regioes_sel else df
    ufs_sel = st.multiselect("Estado (UF)", sorted(base_uf["uf"].unique()),
                             placeholder="Todos os estados", key="f_uf")

    cargos_sel = st.multiselect("Cargo", sorted(df["cargo"].unique()), placeholder="Todos os cargos", key="f_cargo")
    tecs_sel = st.multiselect("Tecnologia", sorted(df["tecnologia"].unique()),
                              placeholder="Todas as tecnologias", key="f_tec")
    sen_sel = st.multiselect("Senioridade", ORDEM_SENIORIDADE, placeholder="Todos os níveis", key="f_sen")
    mod_sel = st.multiselect("Modalidade", ["Presencial", "Híbrido", "Remoto"],
                             placeholder="Todas as modalidades", key="f_mod")

    def _limpar():
        for k in ["f_mes", "f_regiao", "f_uf", "f_cargo", "f_tec", "f_sen", "f_mod"]:
            st.session_state[k] = []
        st.session_state["f_ano"] = (int(min(anos)), int(max(anos)))

    st.button("Limpar filtros", on_click=_limpar, width="stretch")

# Aplica os filtros (lista vazia = sem filtro)
filtro = df["ano"].between(*faixa_anos)
for coluna, selecao in [("mes", meses_sel), ("regiao", regioes_sel), ("uf", ufs_sel),
                        ("cargo", cargos_sel), ("tecnologia", tecs_sel),
                        ("senioridade", sen_sel), ("modalidade", mod_sel)]:
    if selecao:
        filtro &= df[coluna].isin(selecao)
dff = df[filtro].copy()

# Disponibiliza para as páginas
st.session_state["df"] = df
st.session_state["dff"] = dff
st.session_state["relatorio"] = relatorio
st.session_state["ipca"] = ipca
st.session_state["fonte_ipca"] = fonte_ipca
st.session_state["usando_upload"] = arquivo is not None

with st.sidebar:
    st.divider()
    st.caption(f"**{len(dff):,}** de {len(df):,} registros selecionados".replace(",", "."))
    st.caption(f"IPCA: {fonte_ipca}")

# ---------------------------------------------------------------------------
# Navegação multipágina
# ---------------------------------------------------------------------------
paginas = st.navigation(
    {
        "Painel": [
            st.Page("paginas/visao_geral.py", title="Visão geral", default=True),
            st.Page("paginas/cargos_tecnologias.py", title="Cargos e tecnologias"),
            st.Page("paginas/regional.py", title="Análise regional"),
            st.Page("paginas/salarios.py", title="Salários e correlação"),
        ],
        "Dados": [
            st.Page("paginas/explorar.py", title="Tabela dinâmica e SQL"),
        ],
        "Resultado": [
            st.Page("paginas/conclusao.py", title="Conclusão executiva"),
        ],
    }
)
paginas.run()