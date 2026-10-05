import pandas as pd
import streamlit as st

from utils.banco import CONSULTAS, criar_banco, executar_sql, resumo_orm
from utils.dados import num

dff = st.session_state["dff"]
rel = st.session_state["relatorio"]

st.title("Tabela dinâmica, dados tratados e consultas SQL")

aba1, aba2, aba3 = st.tabs(["Tabela dinâmica", "Base tratada", "Banco SQLite (SQLAlchemy)"])

DIMENSOES = {"Ano": "ano", "Mês": "mes_nome", "Trimestre": "ano_trimestre", "Região": "regiao", "UF": "uf",
             "Cidade": "cidade", "Cargo": "cargo", "Área": "area", "Senioridade": "senioridade",
             "Tecnologia": "tecnologia", "Modalidade": "modalidade", "Setor da empresa": "empresa_setor",
             "Nível de demanda": "nivel_demanda", "Período": "periodo", "Faixa salarial": "faixa_salarial"}
METRICAS = {"Quantidade de vagas": "quantidade_vagas", "Salário médio nominal": "salario_medio",
            "Salário real (R$ 2024)": "salario_real", "Massa salarial": "massa_salarial"}
AGREGACOES = {"Soma": "sum", "Média": "mean", "Mediana": "median", "Máximo": "max", "Mínimo": "min",
              "Contagem": "count"}

with aba1:
    if dff.empty:
        st.warning("Nenhum registro para os filtros selecionados.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        linhas = c1.selectbox("Linhas", list(DIMENSOES), index=6)
        colunas = c2.selectbox("Colunas", ["(nenhuma)"] + list(DIMENSOES), index=1)
        metrica = c3.selectbox("Métrica", list(METRICAS))
        agg = c4.selectbox("Agregação", list(AGREGACOES), index=0 if metrica == "Quantidade de vagas" else 1)

        kw = dict(index=DIMENSOES[linhas], values=METRICAS[metrica], aggfunc=AGREGACOES[agg], observed=True)
        if colunas != "(nenhuma)" and colunas != linhas:
            kw["columns"] = DIMENSOES[colunas]
            kw["margins"] = True
            kw["margins_name"] = "Total"
        pivo = dff.pivot_table(**kw).round(2)
        casas = 0 if AGREGACOES[agg] in ("sum", "count") else 2
        miolo = pd.IndexSlice[[i for i in pivo.index if i != "Total"], [c for c in pivo.columns if c != "Total"]]
        estilo = (pivo.style.format(lambda v: num(v, casas))
                  .background_gradient(cmap="Blues", axis=None, subset=miolo))
        st.dataframe(estilo, height=min(38 * (len(pivo) + 1) + 3, 600))
        st.download_button("Baixar tabela dinâmica (CSV)", pivo.to_csv().encode("utf-8-sig"),
                           "tabela_dinamica.csv", "text/csv")

with aba2:
    st.markdown(f"**{len(dff):,} registros após filtros**".replace(",", "."))
    st.dataframe(dff, height=420, hide_index=True)
    st.download_button("Baixar dados filtrados (CSV)", dff.to_csv(index=False).encode("utf-8-sig"),
                       "mercado_ti_filtrado.csv", "text/csv")
    with st.expander("Relatório de limpeza e preparação"):
        st.markdown(
            f"""
- Linhas lidas do arquivo: **{rel['linhas_iniciais']}**
- Valores nulos encontrados: **{rel['nulos_por_coluna']}**
- Linhas duplicadas removidas: **{rel['duplicadas']}**
- Linhas inválidas removidas (salário ≤ 0, vagas < 0, mês fora de 1–12): **{rel['invalidas']}**
- Outliers de salário pelo critério IQR (sinalizados na coluna `outlier_salario`): **{rel['outliers_salario']}**
- Linhas finais: **{rel['linhas_finais']}**

**Atributos criados:** `mes_nome`, `trimestre`, `ano_trimestre`, `periodo` (pré/pandemia/pós), `area`,
`faixa_salarial`, `massa_salarial`, `eh_remoto`, `peso_demanda`, `ipca_pct` e `salario_real` (via API do Banco Central).
            """
        )

with aba3:
    st.markdown(
        "A base tratada é persistida em **SQLite** (`database/mercado_ti.db`) com **modelagem relacional** "
        "feita em SQLAlchemy ORM: uma tabela fato (`fato_vagas`) ligada às dimensões `dim_localidade`, "
        "`dim_cargo`, `dim_tecnologia`, `dim_setor` e à tabela `ipca_anual` vinda da API. "
        "As consultas abaixo usam a base completa (sem os filtros da barra lateral)."
    )
    st.code(
        "dim_localidade (id, regiao, uf, cidade)\n"
        "dim_cargo      (id, cargo, area)\n"
        "dim_tecnologia (id, tecnologia)\n"
        "dim_setor      (id, empresa_setor)\n"
        "ipca_anual     (ano, ipca_pct)\n"
        "fato_vagas     (id, data, ano, mes, senioridade, modalidade, nivel_demanda, salario_medio,\n"
        "                quantidade_vagas, localidade_id→dim_localidade, cargo_id→dim_cargo,\n"
        "                tecnologia_id→dim_tecnologia, setor_id→dim_setor)",
        language="text",
    )
    nome = st.selectbox("Consulta SQL", list(CONSULTAS))
    st.code(CONSULTAS[nome].strip(), language="sql")
    try:
        st.dataframe(executar_sql(CONSULTAS[nome]), hide_index=True)
    except Exception as e:  # noqa: BLE001
        st.error(f"Erro ao executar a consulta: {e}")

    st.markdown("**Consulta via ORM (sem SQL manual)** — vagas por área e cargo")
    st.dataframe(resumo_orm(), hide_index=True)

    if st.session_state.get("usando_upload"):
        if st.button("Gravar o CSV enviado no banco SQLite"):
            criar_banco(st.session_state["df"], st.session_state["ipca"])
            st.success("Banco recriado com os dados do arquivo enviado.")