"""
Cria (ou recria) o banco SQLite database/mercado_ti.db a partir do CSV.

Execute na raiz do projeto:
    python database/criar_banco.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.banco import CAMINHO_BANCO, criar_banco, executar_sql  # noqa: E402
from utils.dados import preparar_base  # noqa: E402

if __name__ == "__main__":
    df, relatorio, ipca, fonte = preparar_base()
    criar_banco(df, ipca)
    print(f"Banco criado em: {CAMINHO_BANCO}")
    print(f"IPCA obtido de: {fonte}")
    print(executar_sql("SELECT name FROM sqlite_master WHERE type='table'"))
    print(executar_sql("SELECT COUNT(*) AS linhas FROM fato_vagas"))
