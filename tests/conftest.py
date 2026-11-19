"""Fixture de banco compartilhada pelos testes de integração.

Sem banco acessível, os testes são pulados localmente. No CI, INCISO_EXIGIR_BANCO=1 transforma o
pulo em falha: um serviço mal configurado não pode passar despercebido como "verde".
Cada teste roda num esquema próprio, dentro de uma transação desfeita no final: o banco não
acumula lixo e os testes não enxergam os dados reais da ingestão (que vivem em `public`), mesmo
quando o banco de desenvolvimento é o mesmo.
"""

import os
from collections.abc import Iterator

import psycopg
import pytest

from inciso.banco import aplicar_esquema, conectar


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    try:
        conexao = conectar()
    except psycopg.OperationalError as erro:
        if os.environ.get("INCISO_EXIGIR_BANCO") == "1":
            pytest.fail(f"banco exigido e inacessível: {erro}")
        pytest.skip("banco inacessível; defina DATABASE_URL ou suba o local com: uv run poe db")
    with conexao:
        conexao.execute("CREATE SCHEMA inciso_teste")
        # public continua no caminho porque é onde a extensão vector já pode estar instalada.
        conexao.execute("SET LOCAL search_path TO inciso_teste, public")
        aplicar_esquema(conexao)
        yield conexao
        conexao.rollback()
