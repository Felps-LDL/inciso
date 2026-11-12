"""Acesso ao Postgres + pgvector: esquema, inserção e busca exata por similaridade."""

import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from importlib.resources import files

import psycopg

from inciso.avaliacao import Trecho

# Credencial de desenvolvimento do compose.yaml; o CI e quem quiser outro banco usam DATABASE_URL.
URL_PADRAO = "postgresql://inciso:inciso@localhost:5432/inciso"


@dataclass(frozen=True)
class Documento:
    doc_id: str
    orgao: str
    tipo: str
    numero: int
    data_publicacao: date
    tema: str
    assunto: str
    url_origem: str
    sha256: str
    texto: str
    versao_extracao: str


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    estrategia: str
    inicio: int
    fim: int
    texto: str
    caminho_estrutural: str | None = None


def url_do_banco() -> str:
    return os.environ.get("DATABASE_URL", URL_PADRAO)


def conectar(url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(url or url_do_banco())


def aplicar_esquema(conn: psycopg.Connection) -> None:
    conn.execute((files("inciso") / "esquema.sql").read_text(encoding="utf-8"))


def inserir_documento(conn: psycopg.Connection, doc: Documento) -> None:
    conn.execute(
        """
        INSERT INTO documentos (doc_id, orgao, tipo, numero, data_publicacao, tema, assunto,
                                url_origem, sha256, texto, versao_extracao)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            doc.doc_id,
            doc.orgao,
            doc.tipo,
            doc.numero,
            doc.data_publicacao,
            doc.tema,
            doc.assunto,
            doc.url_origem,
            doc.sha256,
            doc.texto,
            doc.versao_extracao,
        ),
    )


def inserir_chunks(conn: psycopg.Connection, chunks: Sequence[Chunk]) -> list[int]:
    """Insere os chunks e devolve os ids, na mesma ordem da entrada."""
    ids: list[int] = []
    with conn.cursor() as cur:
        for c in chunks:
            cur.execute(
                """
                INSERT INTO chunks (doc_id, estrategia, inicio, fim, texto, caminho_estrutural)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (c.doc_id, c.estrategia, c.inicio, c.fim, c.texto, c.caminho_estrutural),
            )
            linha = cur.fetchone()
            assert linha is not None
            ids.append(linha[0])
    return ids


def inserir_embeddings(
    conn: psycopg.Connection, modelo: str, pares: Sequence[tuple[int, Sequence[float]]]
) -> None:
    """Grava (chunk_id, vetor) para um modelo."""
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO embeddings (chunk_id, modelo, embedding) VALUES (%s, %s, %s::vector)",
            [(chunk_id, modelo, _literal_vetor(vetor)) for chunk_id, vetor in pares],
        )


def buscar(
    conn: psycopg.Connection,
    consulta: Sequence[float],
    modelo: str,
    estrategia: str,
    k: int,
) -> list[Trecho]:
    """Os k chunks mais próximos da consulta por distância de cosseno, por busca exata.

    Devolve `Trecho`s para alimentar direto o recall@k de inciso.avaliacao.
    """
    if k < 1:
        raise ValueError("k precisa ser pelo menos 1")
    linhas = conn.execute(
        """
        SELECT c.doc_id, c.inicio, c.fim
        FROM embeddings e
        JOIN chunks c ON c.id = e.chunk_id
        WHERE e.modelo = %s AND c.estrategia = %s
        ORDER BY e.embedding <=> %s::vector, c.id
        LIMIT %s
        """,
        (modelo, estrategia, _literal_vetor(consulta), k),
    ).fetchall()
    return [Trecho(doc_id, inicio, fim) for doc_id, inicio, fim in linhas]


def _literal_vetor(vetor: Sequence[float]) -> str:
    # Formato de texto do pgvector; evita a dependência pgvector-python só para isso.
    return "[" + ",".join(repr(float(x)) for x in vetor) + "]"
