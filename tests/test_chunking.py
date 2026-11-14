"""Chunking por tamanho fixo: casos montados à mão e propriedades no texto real de exemplo."""

from datetime import date
from itertools import pairwise

import psycopg
import pytest

from inciso.banco import Documento, inserir_documento
from inciso.chunking import chunkear_documentos, chunking_fixo, nome_estrategia

# Posições: aaa=0-2, bbb=4-6, ccc=8-10, ddd=12-14, eee=16-18 (espaços em 3, 7, 11, 15).
PALAVRAS = "aaa bbb ccc ddd eee"


def test_corta_no_espaco_e_sobrepoe_a_palavra_anterior() -> None:
    # Janela [0, 10]: último espaço em [5, 10] é o 7 → "aaa bbb". O próximo começa na
    # primeira palavra em [7-4, 7] = 4 → "bbb ccc", e assim por diante.
    assert chunking_fixo(PALAVRAS, tamanho=10, sobreposicao=4) == [
        (0, 7),
        (4, 11),
        (8, 15),
        (12, 19),
    ]


def test_sem_espaco_corta_no_meio_com_sobreposicao_exata() -> None:
    assert chunking_fixo("x" * 25, tamanho=10, sobreposicao=4) == [
        (0, 10),
        (6, 16),
        (12, 22),
        (18, 25),
    ]


def test_sem_sobreposicao() -> None:
    assert chunking_fixo(PALAVRAS, tamanho=10, sobreposicao=0) == [(0, 7), (8, 15), (16, 19)]


def test_texto_vazio_ou_so_espaco() -> None:
    assert chunking_fixo("", 10, 4) == []
    assert chunking_fixo("   \n ", 10, 4) == []


def test_texto_curto_vira_um_chunk() -> None:
    assert chunking_fixo("Art. 1º", 10, 4) == [(0, 7)]
    assert chunking_fixo("  Art. 1º", 10, 4) == [(2, 9)]


def test_corte_exato_no_tamanho() -> None:
    # Espaço logo depois da janela (posição 10): o chunk tem exatamente 10 caracteres.
    texto = "aaaaaaaaaa bbbbbbbbbb"
    assert chunking_fixo(texto, 10, 4) == [(0, 10), (11, 21)]


def test_palavra_longa_no_fim_da_sobreposicao_nao_trava() -> None:
    # Nenhuma palavra começa em [fim-4, fim]: o próximo chunk começa depois do corte.
    texto = "a " + "b" * 8 + " cc"
    assert chunking_fixo(texto, 12, 4) == [(0, 10), (11, 13)]


@pytest.mark.parametrize(("tamanho", "sobreposicao"), [(0, 0), (10, 5), (10, -1), (800, 400)])
def test_parametros_invalidos(tamanho: int, sobreposicao: int) -> None:
    with pytest.raises(ValueError):
        chunking_fixo("abc", tamanho, sobreposicao)


TEXTO_NORMATIVO = (
    "Art. 5º O fundo de investimento é uma comunhão de recursos, constituído sob a forma de "
    "condomínio de natureza especial, destinado à aplicação em ativos financeiros.\n"
    "§ 1º O regulamento pode prever classes de cotas com direitos e obrigações distintos.\n"
    "I – patrimônio segregado; II – responsabilidade limitada dos cotistas ao valor subscrito.\n"
) * 20


@pytest.mark.parametrize(("tamanho", "sobreposicao"), [(800, 100), (200, 50), (60, 0)])
def test_propriedades_no_texto_normativo(tamanho: int, sobreposicao: int) -> None:
    intervalos = chunking_fixo(TEXTO_NORMATIVO, tamanho, sobreposicao)
    cobertos = set()
    for inicio, fim in intervalos:
        assert 0 < fim - inicio <= tamanho
        # Não parte palavra: começa e termina em fronteira.
        assert not TEXTO_NORMATIVO[inicio].isspace()
        assert inicio == 0 or TEXTO_NORMATIVO[inicio - 1].isspace()
        assert fim == len(TEXTO_NORMATIVO) or TEXTO_NORMATIVO[fim].isspace()
        cobertos.update(range(inicio, fim))
    # Avança sempre, e todo caractere visível cai em algum chunk.
    assert [i for i, _ in intervalos] == sorted({i for i, _ in intervalos})
    visiveis = {i for i, c in enumerate(TEXTO_NORMATIVO) if not c.isspace()}
    assert visiveis <= cobertos


def test_sobreposicao_real_entre_vizinhos() -> None:
    intervalos = chunking_fixo(TEXTO_NORMATIVO, 800, 100)
    for (_, fim_anterior), (inicio, _) in pairwise(intervalos):
        assert 0 < fim_anterior - inicio <= 100


def test_nome_estrategia() -> None:
    assert nome_estrategia() == "fixo-800-100"
    assert nome_estrategia(500, 50) == "fixo-500-50"


def test_chunkear_documentos_grava_fatias_e_e_idempotente(conn: psycopg.Connection) -> None:
    doc = Documento(
        doc_id="cvm-resolucao-999-2099",
        orgao="cvm",
        tipo="resolucao",
        numero=999,
        data_publicacao=date(2099, 1, 1),
        tema="fundos",
        assunto="Documento de teste",
        url_origem="https://exemplo.invalid/999",
        sha256="0" * 64,
        texto=TEXTO_NORMATIVO,
        versao_extracao="teste",
    )
    inserir_documento(conn, doc)

    criados = chunkear_documentos(conn, tamanho=200, sobreposicao=50)
    esperado = chunking_fixo(TEXTO_NORMATIVO, 200, 50)
    assert criados[doc.doc_id] == len(esperado)

    linhas = conn.execute(
        "SELECT inicio, fim, texto, caminho_estrutural FROM chunks "
        "WHERE doc_id = %s AND estrategia = 'fixo-200-50' ORDER BY inicio",
        (doc.doc_id,),
    ).fetchall()
    assert [(i, f) for i, f, _, _ in linhas] == esperado
    assert all(texto == TEXTO_NORMATIVO[i:f] for i, f, texto, _ in linhas)
    assert all(caminho is None for *_, caminho in linhas)

    assert doc.doc_id not in chunkear_documentos(conn, tamanho=200, sobreposicao=50)
    # Outra estratégia é independente.
    assert doc.doc_id in chunkear_documentos(conn, tamanho=300, sobreposicao=50)
