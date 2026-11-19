"""Embeddings com um codificador falso: o modelo real não roda nos testes (download de ~1 GB)."""

import math
from collections.abc import Sequence
from datetime import date

import psycopg

from inciso.avaliacao import Trecho
from inciso.banco import Chunk, Documento, buscar, inserir_chunks, inserir_documento
from inciso.embeddings import ModeloEmbedding, embedar_chunks, embedar_consulta

MODELO = ModeloEmbedding("teste/falso", "query: ", "passage: ")
DOC = "cvm-resolucao-999-2099"


class Falso:
    """Vetor 3D = contagem de 'a', 'b' e 'c', normalizado. Um token por caractere."""

    def __init__(self, limite_tokens: int = 1000) -> None:
        self.limite_tokens = limite_tokens
        self.recebidos: list[str] = []

    def codificar(self, textos: Sequence[str]) -> list[list[float]]:
        self.recebidos.extend(textos)
        vetores = []
        for t in textos:
            v = [t.count("a") + 1e-9, t.count("b"), t.count("c")]
            norma = math.sqrt(sum(x * x for x in v))
            vetores.append([x / norma for x in v])
        return vetores

    def contar_tokens(self, textos: Sequence[str]) -> list[int]:
        return [len(t) for t in textos]


def _popular(conn: psycopg.Connection, textos: list[str]) -> list[int]:
    texto = " ".join(textos)
    inserir_documento(
        conn,
        Documento(
            DOC,
            "cvm",
            "resolucao",
            999,
            date(2099, 1, 1),
            "fundos",
            "teste",
            "https://exemplo.invalid",
            "0" * 64,
            texto,
            "teste",
        ),
    )
    chunks, inicio = [], 0
    for t in textos:
        chunks.append(Chunk(DOC, "fixo-teste", inicio, inicio + len(t), t))
        inicio += len(t) + 1
    return inserir_chunks(conn, chunks)


def test_prefixo_de_trecho_e_de_consulta() -> None:
    falso = Falso()
    embedar_consulta(MODELO, falso, "quem avisa os cotistas?")
    assert falso.recebidos == ["query: quem avisa os cotistas?"]


def test_grava_so_o_que_falta_e_com_prefixo(conn: psycopg.Connection) -> None:
    _popular(conn, ["aaaa", "bbbb", "cccc"])
    falso = Falso()
    resumo = embedar_chunks(conn, MODELO, falso, "fixo-teste", tamanho_lote=2)
    assert resumo.criados == 3
    assert falso.recebidos == ["passage: aaaa", "passage: bbbb", "passage: cccc"]
    assert embedar_chunks(conn, MODELO, Falso(), "fixo-teste").criados == 0
    # Outro modelo sobre os mesmos chunks é independente.
    outro = ModeloEmbedding("teste/outro")
    assert embedar_chunks(conn, outro, Falso(), "fixo-teste").criados == 3


def test_conta_chunks_truncados(conn: psycopg.Connection) -> None:
    # Com prefixo, os textos têm 13, 14 e 18 tokens; o limite 14 corta só o último.
    _popular(conn, ["aaaa", "bbbbb", "ccccccccc"])
    resumo = embedar_chunks(conn, MODELO, Falso(limite_tokens=14), "fixo-teste")
    assert (resumo.truncados, resumo.maior_em_tokens) == (1, 18)


def test_consulta_encontra_o_chunk_certo(conn: psycopg.Connection) -> None:
    _popular(conn, ["aaaa", "bbbb", "cccc"])
    falso = Falso()
    embedar_chunks(conn, MODELO, falso, "fixo-teste")
    consulta = embedar_consulta(MODELO, falso, "bb")  # "query: bb": 0 'a', 2 'b', 0 'c'
    [primeiro] = buscar(conn, consulta, MODELO.repositorio, "fixo-teste", k=1)
    assert primeiro == Trecho(DOC, 5, 9)
