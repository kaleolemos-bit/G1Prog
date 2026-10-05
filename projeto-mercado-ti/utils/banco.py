"""
Persistência em banco de dados com SQLAlchemy + SQLite.

Modelagem relacional (esquema estrela):

    dim_localidade (id, regiao, uf, cidade)
    dim_cargo      (id, cargo, area)
    dim_tecnologia (id, tecnologia)
    dim_setor      (id, empresa_setor)
    ipca_anual     (ano PK, ipca_pct)
    fato_vagas     (id, data, ano, mes, senioridade, modalidade, nivel_demanda,
                    salario_medio, quantidade_vagas,
                    localidade_id FK, cargo_id FK, tecnologia_id FK, setor_id FK)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import (Date, Float, ForeignKey, Integer, String, create_engine,
                        func, select, text)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_BANCO = RAIZ / "database" / "mercado_ti.db"


class Base(DeclarativeBase):
    pass


class Localidade(Base):
    __tablename__ = "dim_localidade"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    regiao: Mapped[str] = mapped_column(String(20))
    uf: Mapped[str] = mapped_column(String(2))
    cidade: Mapped[str] = mapped_column(String(60))
    vagas: Mapped[list["FatoVaga"]] = relationship(back_populates="localidade")


class Cargo(Base):
    __tablename__ = "dim_cargo"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cargo: Mapped[str] = mapped_column(String(60), unique=True)
    area: Mapped[str] = mapped_column(String(40))
    vagas: Mapped[list["FatoVaga"]] = relationship(back_populates="cargo")


class Tecnologia(Base):
    __tablename__ = "dim_tecnologia"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tecnologia: Mapped[str] = mapped_column(String(40), unique=True)
    vagas: Mapped[list["FatoVaga"]] = relationship(back_populates="tecnologia")


class Setor(Base):
    __tablename__ = "dim_setor"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_setor: Mapped[str] = mapped_column(String(40), unique=True)


class IpcaAnual(Base):
    __tablename__ = "ipca_anual"
    ano: Mapped[int] = mapped_column(Integer, primary_key=True)
    ipca_pct: Mapped[float] = mapped_column(Float)


class FatoVaga(Base):
    __tablename__ = "fato_vagas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[object] = mapped_column(Date)
    ano: Mapped[int] = mapped_column(Integer, index=True)
    mes: Mapped[int] = mapped_column(Integer)
    senioridade: Mapped[str] = mapped_column(String(10))
    modalidade: Mapped[str] = mapped_column(String(12))
    nivel_demanda: Mapped[str] = mapped_column(String(10))
    salario_medio: Mapped[float] = mapped_column(Float)
    quantidade_vagas: Mapped[int] = mapped_column(Integer)
    localidade_id: Mapped[int] = mapped_column(ForeignKey("dim_localidade.id"))
    cargo_id: Mapped[int] = mapped_column(ForeignKey("dim_cargo.id"))
    tecnologia_id: Mapped[int] = mapped_column(ForeignKey("dim_tecnologia.id"))
    setor_id: Mapped[int] = mapped_column(ForeignKey("dim_setor.id"))

    localidade: Mapped[Localidade] = relationship(back_populates="vagas")
    cargo: Mapped[Cargo] = relationship(back_populates="vagas")
    tecnologia: Mapped[Tecnologia] = relationship(back_populates="vagas")


def obter_engine(caminho: Path = CAMINHO_BANCO):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{caminho}", future=True)


def criar_banco(df: pd.DataFrame, ipca: pd.DataFrame | None = None, caminho: Path = CAMINHO_BANCO) -> Path:
    """Recria o banco SQLite a partir do DataFrame já tratado."""
    engine = obter_engine(caminho)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    loc = df[["regiao", "uf", "cidade"]].drop_duplicates().sort_values(["regiao", "uf", "cidade"]).reset_index(drop=True)
    loc["id"] = loc.index + 1
    car = df[["cargo", "area"]].drop_duplicates().sort_values("cargo").reset_index(drop=True)
    car["id"] = car.index + 1
    tec = df[["tecnologia"]].drop_duplicates().sort_values("tecnologia").reset_index(drop=True)
    tec["id"] = tec.index + 1
    st_ = df[["empresa_setor"]].drop_duplicates().sort_values("empresa_setor").reset_index(drop=True)
    st_["id"] = st_.index + 1

    fato = (df.merge(loc.rename(columns={"id": "localidade_id"}), on=["regiao", "uf", "cidade"])
              .merge(car[["cargo", "id"]].rename(columns={"id": "cargo_id"}), on="cargo")
              .merge(tec.rename(columns={"id": "tecnologia_id"}), on="tecnologia")
              .merge(st_.rename(columns={"id": "setor_id"}), on="empresa_setor"))
    fato = fato[["data", "ano", "mes", "senioridade", "modalidade", "nivel_demanda",
                 "salario_medio", "quantidade_vagas", "localidade_id", "cargo_id",
                 "tecnologia_id", "setor_id"]].copy()
    for c in ["senioridade", "modalidade", "nivel_demanda"]:
        fato[c] = fato[c].astype(str)
    fato["data"] = pd.to_datetime(fato["data"]).dt.date

    with Session(engine) as s:
        s.bulk_insert_mappings(Localidade, loc.to_dict("records"))
        s.bulk_insert_mappings(Cargo, car.to_dict("records"))
        s.bulk_insert_mappings(Tecnologia, tec.to_dict("records"))
        s.bulk_insert_mappings(Setor, st_.to_dict("records"))
        if ipca is not None:
            s.bulk_insert_mappings(IpcaAnual, ipca[["ano", "ipca_pct"]].to_dict("records"))
        s.bulk_insert_mappings(FatoVaga, fato.to_dict("records"))
        s.commit()
    return caminho


def banco_existe(caminho: Path = CAMINHO_BANCO) -> bool:
    if not caminho.exists():
        return False
    try:
        with obter_engine(caminho).connect() as c:
            return c.execute(text("SELECT COUNT(*) FROM fato_vagas")).scalar() > 0
    except Exception:
        return False


# Consultas SQL prontas exibidas no dashboard -------------------------------
CONSULTAS = {
    "Vagas e salário por região (JOIN fato × localidade)": """
SELECT l.regiao,
       SUM(f.quantidade_vagas)                                   AS total_vagas,
       ROUND(SUM(f.salario_medio * f.quantidade_vagas) / SUM(f.quantidade_vagas), 2) AS salario_ponderado,
       COUNT(DISTINCT l.cidade)                                   AS cidades
FROM fato_vagas f
JOIN dim_localidade l ON l.id = f.localidade_id
GROUP BY l.regiao
ORDER BY total_vagas DESC;""",
    "Ranking de tecnologias por ano (JOIN fato × tecnologia)": """
SELECT f.ano, t.tecnologia, SUM(f.quantidade_vagas) AS vagas
FROM fato_vagas f
JOIN dim_tecnologia t ON t.id = f.tecnologia_id
GROUP BY f.ano, t.tecnologia
ORDER BY f.ano, vagas DESC;""",
    "Cargo × senioridade: salário médio (JOIN fato × cargo)": """
SELECT c.cargo, f.senioridade,
       ROUND(AVG(f.salario_medio), 2) AS salario_medio,
       SUM(f.quantidade_vagas)        AS vagas
FROM fato_vagas f
JOIN dim_cargo c ON c.id = f.cargo_id
GROUP BY c.cargo, f.senioridade
ORDER BY c.cargo, f.senioridade;""",
    "Salário real (R$ de 2024) por ano — JOIN com IPCA da API": """
WITH idx AS (
  SELECT ano, ipca_pct,
         EXP(SUM(LN(1 + ipca_pct / 100.0)) OVER (ORDER BY ano)) AS indice
  FROM ipca_anual
)
SELECT f.ano,
       ROUND(AVG(f.salario_medio), 2) AS salario_nominal,
       i.ipca_pct,
       ROUND(AVG(f.salario_medio) * (SELECT indice FROM idx WHERE ano = 2024) / i.indice, 2) AS salario_real_2024
FROM fato_vagas f
JOIN idx i ON i.ano = f.ano
GROUP BY f.ano
ORDER BY f.ano;""",
    "Top 10 cidades em vagas": """
SELECT l.cidade, l.uf, SUM(f.quantidade_vagas) AS vagas
FROM fato_vagas f
JOIN dim_localidade l ON l.id = f.localidade_id
GROUP BY l.cidade, l.uf
ORDER BY vagas DESC
LIMIT 10;""",
}


def executar_sql(sql: str, caminho: Path = CAMINHO_BANCO) -> pd.DataFrame:
    with obter_engine(caminho).connect() as c:
        return pd.read_sql(text(sql), c)


def resumo_orm(caminho: Path = CAMINHO_BANCO) -> pd.DataFrame:
    """Exemplo de consulta usando a API ORM (sem SQL escrito à mão)."""
    engine = obter_engine(caminho)
    with Session(engine) as s:
        stmt = (select(Cargo.area, Cargo.cargo, func.sum(FatoVaga.quantidade_vagas).label("vagas"))
                .join(FatoVaga, FatoVaga.cargo_id == Cargo.id)
                .group_by(Cargo.area, Cargo.cargo)
                .order_by(func.sum(FatoVaga.quantidade_vagas).desc()))
        return pd.DataFrame(s.execute(stmt).all(), columns=["area", "cargo", "vagas"])
