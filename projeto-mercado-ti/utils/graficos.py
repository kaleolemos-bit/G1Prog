"""Padrões visuais compartilhados pelos gráficos Plotly do dashboard."""
import plotly.graph_objects as go

from utils.dados import (ORDEM_MODALIDADE, ORDEM_REGIAO, ORDEM_SENIORIDADE,
                         mapa_cores)

CARGOS = ["Analista de Dados", "Cientista de Dados", "Dev Backend", "Dev Frontend", "DevOps"]
TECNOLOGIAS = ["Python", "SQL", "Java", "JavaScript", "AWS", "Power BI"]

# Cada entidade tem sempre a mesma cor, em qualquer gráfico e com qualquer filtro
CORES_CARGO = mapa_cores(CARGOS)
CORES_TEC = mapa_cores(TECNOLOGIAS)
CORES_REGIAO = mapa_cores(ORDEM_REGIAO)
CORES_MODALIDADE = mapa_cores(ORDEM_MODALIDADE)
CORES_SENIORIDADE = mapa_cores(ORDEM_SENIORIDADE)
COR_UNICA = "#2a78d6"
COR_DESTAQUE = "#eb6834"

FONTE = "Inter, 'Segoe UI', sans-serif"


def estilizar(fig: go.Figure, altura: int = 380, legenda: bool = True) -> go.Figure:
    fig.update_layout(
        height=altura,
        margin=dict(l=10, r=10, t=95 if legenda else 45, b=10),
        title=dict(y=0.99, yref="container", yanchor="top", x=0, xanchor="left", xref="paper"),
        font=dict(family=FONTE, size=13, color="#334155"),
        title_font=dict(size=15, color="#0f172a"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font_family=FONTE),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text=""),
        showlegend=legenda,
        bargap=0.25,
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, linecolor="#cbd5e1", ticks="outside", tickcolor="#cbd5e1")
    fig.update_yaxes(gridcolor="#e2e8f0", zeroline=False)
    return fig
