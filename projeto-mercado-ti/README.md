# Mercado de Trabalho em TI no Brasil (2015–2024)

Projeto de **análise e visualização de dados** com Python para investigar tendências do mercado de trabalho em
Tecnologia da Informação no Brasil: cargos mais demandados, tecnologias em alta, evolução salarial, distribuição
regional das vagas, senioridade e modalidade de trabalho.

> Disciplina: Linguagem de Programação — Análise e Visualização de Dados com Python · Projeto G2 — Tema 25

## Links

| Plataforma | Link |
|---|---|
| Página do projeto (GitHub Pages) | https://kaleolemos-bit.github.io/G1Prog/projeto-mercado-ti/ |
| Dashboard (Streamlit Community Cloud) | https://mercado-ti-kaleo.streamlit.app/ |
| Notebook de análise | [`notebooks/analise_mercado_ti.ipynb`](notebooks/analise_mercado_ti.ipynb) |
| Base de dados | [`dados/simulacao_mercado_ti_brasil.csv`](dados/simulacao_mercado_ti_brasil.csv) |

## Perguntas de negócio

1. Quais cargos possuem maior demanda?
2. Quais tecnologias aparecem com maior frequência?
3. Houve crescimento salarial ao longo do tempo?
4. Existem diferenças regionais relevantes?
5. Quais áreas de TI possuem maior crescimento?
6. Qual nível de experiência é mais exigido?
7. Quais regiões concentram mais oportunidades?

## Principais resultados

| Indicador | Resultado |
|---|---|
| Total de vagas | 177.619 |
| Cargo mais demandado | Cientista de Dados (21,0%) |
| Tecnologia mais requisitada | Java (17,2%) |
| Salário médio nacional | R$ 10.602 (ponderado por vagas) |
| Região com mais vagas | Sudeste (35,3%) |
| Modalidade predominante | Remoto (34,3%) |

- **Salário real caiu ~37%**: o salário nominal ficou estável, mas não acompanhou a inflação (IPCA).
- **Infraestrutura/Nuvem (DevOps)** foi a área que mais cresceu (+21,5% entre 2015 e 2024); **AWS** foi a tecnologia que mais ganhou espaço.
- O **trabalho remoto** teve pico em 2020 (40% das vagas).
- O Sudeste lidera em volume, mas **por cidade monitorada as regiões se equivalem**.
- Correlação entre salário e quantidade de vagas é desprezível (r ≈ 0,02).

> Os dados são **simulados**. As conclusões demonstram o método analítico e não representam fielmente o mercado real.

## Tecnologias

| Obrigatórias | Complementares |
|---|---|
| Python, Pandas, Matplotlib, Seaborn, Plotly, Streamlit, GitHub | NumPy, SQLAlchemy, SQLite, Requests (API do Banco Central), Jupyter |

## Funcionalidades

**Intermediárias**
- Filtros múltiplos (ano, mês, região, estado, cargo, tecnologia, senioridade, modalidade) válidos em todas as páginas
- KPIs dinâmicos
- Gráficos interativos (Plotly)
- Análise temporal (média móvel de 12 meses, variação anual)
- Tratamento de dados (padronização, tipos, nulos, duplicados, regras de consistência, outliers por IQR)
- Upload de arquivos CSV
- Dashboard organizado em seções e abas
- Visualizações comparativas e análise geográfica

**Avançadas**
- **Consumo de API** com Requests — IPCA da API SGS do Banco Central (série 433), com arquivo de contingência
- **Persistência em banco** com SQLAlchemy + SQLite (`database/mercado_ti.db`)
- **Modelagem relacional** — tabela fato `fato_vagas` + dimensões `dim_localidade`, `dim_cargo`, `dim_tecnologia`, `dim_setor` e `ipca_anual`
- **Dashboard multipágina** (`st.navigation`)
- **Mapa interativo** coroplético por estado (Plotly)
- **Séries temporais** (média móvel, variação anual, salário deflacionado)
- **Correlação estatística** (Pearson, Spearman, matriz de correlação, reta de regressão com NumPy)
- **Integração de múltiplas fontes** — CSV + API + banco SQLite

## Estrutura

```
projeto-mercado-ti/
├── app.py                         # entrada do Streamlit: dados, filtros e navegação
├── requirements.txt               # dependências (usado pelo Streamlit Cloud)
├── README.md
├── index.html                     # página do projeto (GitHub Pages)
├── .streamlit/
│   └── config.toml                # tema visual do dashboard
├── paginas/                       # páginas do dashboard
│   ├── visao_geral.py
│   ├── cargos_tecnologias.py
│   ├── regional.py
│   ├── salarios.py
│   ├── explorar.py
│   └── conclusao.py
├── utils/
│   ├── __init__.py
│   ├── dados.py                   # leitura, limpeza, atributos, API IPCA, KPIs
│   ├── banco.py                   # modelo SQLAlchemy, criação do banco e consultas SQL
│   └── graficos.py                # cores e estilo dos gráficos
├── dados/
│   ├── simulacao_mercado_ti_brasil.csv
│   ├── ipca_anual.csv             # contingência caso a API esteja fora do ar
│   └── brasil_estados.geojson     # limites dos estados para o mapa
├── database/
│   ├── criar_banco.py
│   └── mercado_ti.db
├── notebooks/
│   └── analise_mercado_ti.ipynb
└── imagens/                       # gráficos Matplotlib/Seaborn gerados pelo notebook
```

## Autor

Kaleo Accacio Pereira Lemos — projeto acadêmico, 2026.
