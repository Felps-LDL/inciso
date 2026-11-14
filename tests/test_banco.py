"""Testes de integração com o Postgres + pgvector (fixture `conn` em conftest.py)."""

import math
from datetime import date

import psycopg
import pytest

from inciso.avaliacao import Avaliacao, Trecho, recall_pergunta
from inciso.banco import (
    Chunk,
    Documento,
    aplicar_esquema,
    buscar,
    inserir_chunks,
    inserir_documento,
    inserir_embeddings,
)

DOC = "cvm-resolucao-175-2022"


def _documento(doc_id: str = DOC) -> Documento:
    return Documento(
        doc_id=doc_id,
        orgao="cvm",
        tipo="resolucao",
        numero=175,
        data_publicacao=date(2022, 12, 23),
        tema="fundos",
        assunto="Fundos de investimento",
        url_origem="https://exemplo.invalid/175",
        sha256="0" * 64,
        texto="x" * 3000,
        versao_extracao="teste",
    )


def _unitario(*v: float) -> list[float]:
    norma = math.sqrt(sum(x * x for x in v))
    return [x / norma for x in v]


def _popular(conn: psycopg.Connection) -> list[int]:
    """Três chunks em 3D. Contra a consulta (1, 0.1, 0), o cosseno ordena a, b, c."""
    inserir_documento(conn, _documento())
    ids = inserir_chunks(
        conn,
        [
            Chunk(DOC, "fixo-800-100", 0, 800, "a"),
            Chunk(DOC, "fixo-800-100", 700, 1500, "b"),
            Chunk(DOC, "fixo-800-100", 1400, 2200, "c"),
        ],
    )
    inserir_embeddings(
        conn,
        "teste-3d",
        [
            (ids[0], _unitario(1, 0, 0)),  # ângulo ~5,7° com a consulta
            (ids[1], _unitario(1, 1, 0)),  # ~39,3°
            (ids[2], _unitario(0, 0, 1)),  # 90°
        ],
    )
    return ids


def test_esquema_e_idempotente(conn: psycopg.Connection) -> None:
    aplicar_esquema(conn)
    aplicar_esquema(conn)
    tabelas = {
        nome
        for (nome,) in conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()"
        )
    }
    assert {"documentos", "chunks", "embeddings"} <= tabelas


def test_busca_ordena_por_cosseno(conn: psycopg.Connection) -> None:
    _popular(conn)
    resultado = buscar(conn, [1, 0.1, 0], modelo="teste-3d", estrategia="fixo-800-100", k=3)
    assert resultado == [Trecho(DOC, 0, 800), Trecho(DOC, 700, 1500), Trecho(DOC, 1400, 2200)]


def test_busca_respeita_k(conn: psycopg.Connection) -> None:
    _popular(conn)
    resultado = buscar(conn, [0, 0, 1], modelo="teste-3d", estrategia="fixo-800-100", k=1)
    assert resultado == [Trecho(DOC, 1400, 2200)]


def test_modelos_de_dimensoes_diferentes_convivem(conn: psycopg.Connection) -> None:
    # O mesmo chunk com um embedding 2D de outro modelo: a busca do modelo 3D não pode tocá-lo.
    ids = _popular(conn)
    inserir_embeddings(conn, "teste-2d", [(ids[2], [1.0, 0.0])])
    assert len(buscar(conn, [1, 0, 0], modelo="teste-3d", estrategia="fixo-800-100", k=5)) == 3
    assert buscar(conn, [1, 0], modelo="teste-2d", estrategia="fixo-800-100", k=5) == [
        Trecho(DOC, 1400, 2200)
    ]


def test_estrategias_convivem(conn: psycopg.Connection) -> None:
    ids = _popular(conn)
    [estrutural] = inserir_chunks(
        conn, [Chunk(DOC, "estrutural-v1", 0, 1200, "art. 1", caminho_estrutural="art.1")]
    )
    inserir_embeddings(conn, "teste-3d", [(estrutural, _unitario(1, 0, 0))])
    fixo = buscar(conn, [1, 0, 0], modelo="teste-3d", estrategia="fixo-800-100", k=5)
    estr = buscar(conn, [1, 0, 0], modelo="teste-3d", estrategia="estrutural-v1", k=5)
    assert len(fixo) == len(ids) == 3
    assert estr == [Trecho(DOC, 0, 1200)]


def test_busca_alimenta_o_recall(conn: psycopg.Connection) -> None:
    _popular(conn)
    gabarito = [Trecho(DOC, 1500, 1900)]  # só o chunk c [1400, 2200) cobre
    longe = buscar(conn, [1, 0.1, 0], modelo="teste-3d", estrategia="fixo-800-100", k=2)
    perto = buscar(conn, [0, 0, 1], modelo="teste-3d", estrategia="fixo-800-100", k=2)
    assert recall_pergunta(Avaliacao(gabarito, longe), k=2) == 0.0
    assert recall_pergunta(Avaliacao(gabarito, perto), k=2) == 1.0


def test_chunk_com_intervalo_invalido_e_rejeitado(conn: psycopg.Connection) -> None:
    inserir_documento(conn, _documento())
    with pytest.raises(psycopg.errors.CheckViolation):
        inserir_chunks(conn, [Chunk(DOC, "fixo-800-100", 500, 500, "")])


def test_k_invalido(conn: psycopg.Connection) -> None:
    with pytest.raises(ValueError, match="k precisa"):
        buscar(conn, [1, 0, 0], modelo="teste-3d", estrategia="fixo-800-100", k=0)
