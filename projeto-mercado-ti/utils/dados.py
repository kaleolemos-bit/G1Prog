"""
Módulo de dados do projeto Mercado de Trabalho em TI no Brasil (2015–2024).

Responsável por:
- leitura do CSV (arquivo do projeto ou upload do usuário);
- limpeza e preparação da base;
- engenharia de atributos;
- consumo da API do Banco Central (IPCA) para calcular o salário real;
- funções auxiliares de KPIs.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "dados"
CSV_PADRAO = PASTA_DADOS / "simulacao_mercado_ti_brasil.csv"
IPCA_FALLBACK = PASTA_DADOS / "ipca_anual.csv"
GEOJSON = PASTA_DADOS / "brasil_estados.geojson"

COLUNAS_OBRIGATORIAS = [
    "ano", "mes", "data", "regiao", "uf", "cidade", "cargo", "senioridade",
    "tecnologia", "modalidade", "salario_medio", "quantidade_vagas",
    "empresa_setor", "nivel_demanda",
]

ORDEM_SENIORIDADE = ["Júnior", "Pleno", "Sênior"]
ORDEM_DEMANDA = ["Baixo", "Médio", "Alto", "Crítico"]
ORDEM_MODALIDADE = ["Presencial", "Híbrido", "Remoto"]
ORDEM_REGIAO = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
MESES = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
         7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}

# Paleta categórica validada (ordem fixa: a cor acompanha a entidade, não o ranking)
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ESCALA_SEQUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def mapa_cores(valores: list[str]) -> dict[str, str]:
    """Atribui cores fixas, na ordem da paleta, para uma lista de categorias."""
    return {v: PALETA[i % len(PALETA)] for i, v in enumerate(valores)}


# ---------------------------------------------------------------------------
# 1. Leitura
# ---------------------------------------------------------------------------
def ler_csv(origem=None) -> pd.DataFrame:
    """Lê o CSV padrão do projeto ou um arquivo enviado por upload.

    `encoding='utf-8-sig'` remove o BOM presente no início do arquivo original.
    """
    origem = origem if origem is not None else CSV_PADRAO
    df = pd.read_csv(origem, encoding="utf-8-sig")
    df.columns = df.columns.str.strip().str.lower()
    faltantes = set(COLUNAS_OBRIGATORIAS) - set(df.columns)
    if faltantes:
        raise ValueError(f"O arquivo não possui as colunas obrigatórias: {sorted(faltantes)}")
    return df


# ---------------------------------------------------------------------------
# 2. Limpeza e preparação
# ---------------------------------------------------------------------------
def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Limpa a base e devolve (df_limpo, relatorio_de_limpeza)."""
    rel = {"linhas_iniciais": len(df)}
    df = df.copy()

    # Padroniza textos: remove espaços extras e normaliza capitalização de UF
    texto = ["regiao", "uf", "cidade", "cargo", "senioridade", "tecnologia",
             "modalidade", "empresa_setor", "nivel_demanda"]
    for c in texto:
        df[c] = df[c].astype("string").str.strip()
    df["uf"] = df["uf"].str.upper()

    # Tipos numéricos (valores inválidos viram NaN)
    for c in ["ano", "mes", "salario_medio", "quantidade_vagas"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    # Reconstrói a data a partir de ano/mês quando estiver ausente
    sem_data = df["data"].isna() & df["ano"].notna() & df["mes"].notna()
    df.loc[sem_data, "data"] = pd.to_datetime(
        dict(year=df.loc[sem_data, "ano"], month=df.loc[sem_data, "mes"], day=1)
    )

    rel["nulos_por_coluna"] = int(df.isna().sum().sum())
    rel["duplicadas"] = int(df.duplicated().sum())
    df = df.drop_duplicates()

    # Remove linhas sem as informações essenciais
    df = df.dropna(subset=["ano", "mes", "uf", "cargo", "salario_medio", "quantidade_vagas"])

    # Regras de consistência
    invalidas = (df["salario_medio"] <= 0) | (df["quantidade_vagas"] < 0) | (~df["mes"].between(1, 12))
    rel["invalidas"] = int(invalidas.sum())
    df = df[~invalidas]

    # Outliers de salário pelo critério IQR (sinalizados, não removidos)
    q1, q3 = df["salario_medio"].quantile([0.25, 0.75])
    iqr = q3 - q1
    df["outlier_salario"] = ~df["salario_medio"].between(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    rel["outliers_salario"] = int(df["outlier_salario"].sum())

    df["ano"] = df["ano"].astype(int)
    df["mes"] = df["mes"].astype(int)
    df["quantidade_vagas"] = df["quantidade_vagas"].astype(int)

    # Categorias ordenadas facilitam ordenação correta nos gráficos
    df["senioridade"] = pd.Categorical(df["senioridade"], ORDEM_SENIORIDADE, ordered=True)
    df["nivel_demanda"] = pd.Categorical(df["nivel_demanda"], ORDEM_DEMANDA, ordered=True)
    df["modalidade"] = pd.Categorical(df["modalidade"], ORDEM_MODALIDADE, ordered=True)

    rel["linhas_finais"] = len(df)
    return df.reset_index(drop=True), rel


# ---------------------------------------------------------------------------
# 3. Engenharia de atributos
# ---------------------------------------------------------------------------
def criar_atributos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["mes_nome"] = df["mes"].map(MESES)
    df["trimestre"] = ((df["mes"] - 1) // 3 + 1).astype(int)
    df["ano_trimestre"] = df["ano"].astype(str) + "-T" + df["trimestre"].astype(str)
    df["periodo"] = pd.cut(
        df["ano"], bins=[2014, 2019, 2021, 2024],
        labels=["Pré-pandemia (2015–2019)", "Pandemia (2020–2021)", "Pós-pandemia (2022–2024)"],
    )
    df["area"] = df["cargo"].map({
        "Analista de Dados": "Dados", "Cientista de Dados": "Dados",
        "Dev Backend": "Desenvolvimento", "Dev Frontend": "Desenvolvimento",
        "DevOps": "Infraestrutura/Nuvem",
    }).fillna("Outros")
    df["faixa_salarial"] = pd.cut(
        df["salario_medio"], bins=[0, 6000, 10000, 14000, np.inf],
        labels=["Até R$ 6 mil", "R$ 6–10 mil", "R$ 10–14 mil", "Acima de R$ 14 mil"],
    )
    df["massa_salarial"] = df["salario_medio"] * df["quantidade_vagas"]
    df["eh_remoto"] = (df["modalidade"] == "Remoto").astype(int)
    df["peso_demanda"] = df["nivel_demanda"].cat.codes + 1  # 1=Baixo … 4=Crítico
    return df


# ---------------------------------------------------------------------------
# 4. API do Banco Central — IPCA (integração de múltiplas fontes)
# ---------------------------------------------------------------------------
URL_IPCA = ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
            "?formato=json&dataInicial=01/01/2015&dataFinal=31/12/2024")


def obter_ipca(timeout: int = 10) -> tuple[pd.DataFrame, str]:
    """Busca o IPCA mensal na API SGS do Banco Central e acumula por ano.

    Retorna (df_ipca_anual, fonte). Se a API estiver indisponível,
    usa o arquivo local dados/ipca_anual.csv como contingência.
    """
    try:
        resp = requests.get(URL_IPCA, timeout=timeout)
        resp.raise_for_status()
        mensal = pd.DataFrame(resp.json())
        mensal["data"] = pd.to_datetime(mensal["data"], format="%d/%m/%Y")
        mensal["valor"] = mensal["valor"].astype(float)
        anual = (mensal.assign(ano=mensal["data"].dt.year)
                 .groupby("ano")["valor"]
                 .apply(lambda s: (np.prod(1 + s / 100) - 1) * 100)
                 .round(2).reset_index(name="ipca_pct"))
        if len(anual) < 10:
            raise ValueError("Série incompleta")
        return anual, "API Banco Central (SGS 433)"
    except Exception:
        return pd.read_csv(IPCA_FALLBACK), "Arquivo local (contingência)"


def adicionar_salario_real(df: pd.DataFrame, ipca: pd.DataFrame, ano_base: int = 2024) -> pd.DataFrame:
    """Converte o salário nominal para valores reais (R$ de `ano_base`)."""
    ipca = ipca.sort_values("ano").copy()
    ipca["indice"] = (1 + ipca["ipca_pct"] / 100).cumprod()
    base = ipca.loc[ipca["ano"] == ano_base, "indice"].iloc[0]
    ipca["fator"] = base / ipca["indice"]
    df = df.merge(ipca[["ano", "ipca_pct", "fator"]], on="ano", how="left")
    df["salario_real"] = df["salario_medio"] * df["fator"].fillna(1)
    return df.drop(columns="fator")


# ---------------------------------------------------------------------------
# 5. Pipeline completo
# ---------------------------------------------------------------------------
def preparar_base(origem=None, usar_api: bool = True):
    bruto = ler_csv(origem)
    limpo, relatorio = limpar(bruto)
    df = criar_atributos(limpo)
    ipca, fonte = obter_ipca() if usar_api else (pd.read_csv(IPCA_FALLBACK), "Arquivo local")
    df = adicionar_salario_real(df, ipca)
    return df, relatorio, ipca, fonte


# ---------------------------------------------------------------------------
# 6. KPIs
# ---------------------------------------------------------------------------
def media_ponderada(df: pd.DataFrame, valor: str = "salario_medio", peso: str = "quantidade_vagas") -> float:
    if df.empty or df[peso].sum() == 0:
        return float("nan")
    return float(np.average(df[valor], weights=df[peso]))


def lider(df: pd.DataFrame, coluna: str) -> tuple[str, int]:
    """Categoria com mais vagas e o respectivo total."""
    if df.empty:
        return "—", 0
    s = df.groupby(coluna, observed=True)["quantidade_vagas"].sum().sort_values(ascending=False)
    return str(s.index[0]), int(s.iloc[0])


def calcular_kpis(df: pd.DataFrame) -> dict:
    total = int(df["quantidade_vagas"].sum())
    cargo, v_cargo = lider(df, "cargo")
    tec, v_tec = lider(df, "tecnologia")
    reg, v_reg = lider(df, "regiao")
    mod, v_mod = lider(df, "modalidade")
    return {
        "total_vagas": total,
        "cargo_top": cargo, "cargo_top_pct": v_cargo / total * 100 if total else 0,
        "tec_top": tec, "tec_top_pct": v_tec / total * 100 if total else 0,
        "salario_medio": media_ponderada(df),
        "regiao_top": reg, "regiao_top_pct": v_reg / total * 100 if total else 0,
        "modalidade_top": mod, "modalidade_top_pct": v_mod / total * 100 if total else 0,
        "registros": len(df),
    }


def brl(valor: float, casas: int = 0) -> str:
    """Formata número no padrão monetário brasileiro."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    txt = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {txt}"


def num(valor: float, casas: int = 0) -> str:
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
