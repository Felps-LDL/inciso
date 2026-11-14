"""Fixture de banco compartilhada pelos testes de integração.

Sem banco acessível, os testes são pulados localmente. No CI, INCISO_EXIGIR_BANCO=1 transforma o
pulo em falha: um serviço mal configurado não pode passar despercebido como "verde".
Cada teste roda dentro de uma transação desfeita no final, então o banco não acumula lixo.
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
        aplicar_esquema(conexao)
        yield conexao
        conexao.rollback()
