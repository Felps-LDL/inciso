from pathlib import Path

import psycopg
import pytest

from inciso.banco import Chunk, inserir_chunks
from inciso.corpus import COLUNAS
from inciso.ingestao import ingerir_corpus, normalizar, versao_extracao

TIMBRE = [
    "COMISSÃO DE VALORES MOBILIÁRIOS",
    "Rua Sete de Setembro, 111/2-5º e 23-34º Andares, Centro, Rio de Janeiro/RJ",
    "www.cvm.gov.br",
]


def pagina(*corpo: str, numero: int, titulo: str = "RESOLUÇÃO CVM Nº 175, DE 2022.") -> str:
    """Página no formato que o pypdf devolve para a CVM 175: timbre, título, corpo, número."""
    return "\n".join([*TIMBRE, titulo, *corpo, str(numero)])


# --- normalização -----------------------------------------------------------------------


def test_remove_timbre_titulo_e_numero_de_pagina() -> None:
    texto = normalizar(
        [
            pagina("Art. 1º Esta Resolução dispõe sobre fundos.", numero=1),
            pagina("Art. 2º O fundo é uma comunhão de recursos.", numero=2),
            pagina("Art. 3º O regulamento deve prever classes.", numero=3),
        ]
    )
    assert texto == (
        "Art. 1º Esta Resolução dispõe sobre fundos.\n"
        "Art. 2º O fundo é uma comunhão de recursos.\n"
        "Art. 3º O regulamento deve prever classes."
    )


def test_nao_remove_com_menos_de_tres_paginas() -> None:
    texto = normalizar([pagina("Art. 1º A.", numero=1), pagina("Art. 2º B.", numero=2)])
    assert "www.cvm.gov.br" in texto


def test_titulo_corrente_de_anexo_tambem_sai() -> None:
    anexo = "ANEXO NORMATIVO I DA RESOLUÇÃO CVM Nº 175, DE 2022."
    paginas = [pagina(f"Art. {n}º Texto {n}.", numero=n, titulo=anexo) for n in range(1, 4)]
    paginas.append(pagina("Art. 4º Texto 4.", numero=4))  # outra parte, outro título
    assert "ANEXO NORMATIVO" not in normalizar(paginas)


def test_paragrafo_continua_na_pagina_seguinte() -> None:
    # O caso real do art. 5º: o timbre caía entre o § 3º e o § 4º.
    texto = normalizar(
        [
            pagina("Art. 5º O regulamento pode prever", "classes de cotas.", numero=15),
            pagina("§ 3º O fundo sem classes deve emitir cotas em", numero=16),
            pagina("classe única.", "§ 4º É vedada a afetação.", numero=17),
        ]
    )
    assert texto == (
        "Art. 5º O regulamento pode prever classes de cotas.\n"
        "§ 3º O fundo sem classes deve emitir cotas em classe única.\n"
        "§ 4º É vedada a afetação."
    )


def test_quebra_de_linha_so_antes_de_inicio_estrutural() -> None:
    texto = normalizar(
        [
            "CAPÍTULO III – CARACTERÍSTICAS\n"
            "Seção I – Características Gerais\n"
            "Art. 5º As subclasses podem ser\n"
            "diferenciadas por:\n"
            "I – público-alvo;\n"
            "II – prazos; e\n"
            "a) taxas;\n"
            "Parágrafo único. Denominam-se:"
        ]
    )
    assert texto.split("\n") == [
        "CAPÍTULO III – CARACTERÍSTICAS",
        "Seção I – Características Gerais",
        "Art. 5º As subclasses podem ser diferenciadas por:",
        "I – público-alvo;",
        "II – prazos; e",
        "a) taxas;",
        "Parágrafo único. Denominam-se:",
    ]


@pytest.mark.parametrize(
    ("fim", "comeco", "esperado"),
    [
        ("o público-", "alvo da classe", "o público-alvo da classe"),
        ("os indicadores econômico-", "financeiros", "os indicadores econômico-financeiros"),
        ("conforme o item -", "A do anexo", "conforme o item - A do anexo"),  # maiúscula: não junta
    ],
)
def test_hifen_no_fim_da_linha(fim: str, comeco: str, esperado: str) -> None:
    assert normalizar([f"{fim}\n{comeco}"]) == esperado


def test_marcador_estrutural_repetido_na_borda_nao_e_removido() -> None:
    # No texto consolidado, "§ 2º (Revogado)." pode abrir várias páginas e é conteúdo.
    paginas = [f"§ 2º (Revogado).\nArt. {n}º Texto {n}." for n in range(1, 5)]
    assert normalizar(paginas).count("§ 2º (Revogado).") == 4


def test_espacos_e_nbsp() -> None:
    nbsp = chr(0xA0)
    assert normalizar([f"Art.{nbsp}1º   O  fundo   é  "]) == "Art. 1º O fundo é"


def test_paginas_vazias() -> None:
    assert normalizar(["", "  \n ", "Art. 1º A."]) == "Art. 1º A."
    assert normalizar([]) == ""


# --- ingestão no banco ------------------------------------------------------------------

LINHA = {
    "arquivo": "cvm-resolucao-175-2022.pdf",
    "orgao": "cvm",
    "tipo": "resolucao",
    "numero": "175",
    "data_publicacao": "2022-12-23",
    "tema": "fundos",
    "assunto": "Regras gerais dos fundos de investimento",
    "url_origem": "https://conteudo.cvm.gov.br/legislacao/resolucoes/resol175.html",
    "data_acesso": "2026-11-12",
}
PAGINAS_FALSAS = [pagina(f"Art. {n}º Texto {n}.", numero=n) for n in range(1, 4)]


def _corpus(pasta: Path, *linhas: dict[str, str], conteudo: bytes = b"%PDF-1.7\nv1") -> Path:
    cabecalho = ",".join(COLUNAS)
    corpo = [",".join(linha[c] for c in COLUNAS) for linha in linhas]
    (pasta / "controle.csv").write_text("\n".join([cabecalho, *corpo]) + "\n", encoding="utf-8")
    for linha in linhas:
        (pasta / linha["arquivo"]).write_bytes(conteudo)
    return pasta


def _extrair_falso(_: Path) -> list[str]:
    return PAGINAS_FALSAS


def test_ingere_documento_normalizado(conn: psycopg.Connection, tmp_path: Path) -> None:
    resumo = ingerir_corpus(conn, _corpus(tmp_path, LINHA), extrair=_extrair_falso)
    assert (resumo.ingeridos, resumo.sem_mudanca, resumo.removidos) == (1, 0, 0)
    doc_id, numero, texto, versao = conn.execute(
        "SELECT doc_id, numero, texto, versao_extracao FROM documentos"
    ).fetchone()
    assert (doc_id, numero, versao) == ("cvm-resolucao-175-2022", 175, versao_extracao())
    assert texto == "Art. 1º Texto 1.\nArt. 2º Texto 2.\nArt. 3º Texto 3."


def test_segunda_ingestao_sem_mudanca_e_pulada(conn: psycopg.Connection, tmp_path: Path) -> None:
    pasta = _corpus(tmp_path, LINHA)
    ingerir_corpus(conn, pasta, extrair=_extrair_falso)
    resumo = ingerir_corpus(conn, pasta, extrair=_extrair_falso)
    assert (resumo.ingeridos, resumo.sem_mudanca) == (0, 1)


def test_pdf_alterado_substitui_e_apaga_chunks(conn: psycopg.Connection, tmp_path: Path) -> None:
    ingerir_corpus(conn, _corpus(tmp_path, LINHA), extrair=_extrair_falso)
    inserir_chunks(conn, [Chunk("cvm-resolucao-175-2022", "fixo-800-100", 0, 10, "Art. 1º Te")])
    ingerir_corpus(conn, _corpus(tmp_path, LINHA, conteudo=b"%PDF-1.7\nv2"), extrair=_extrair_falso)
    assert conn.execute("SELECT count(*) FROM chunks").fetchone() == (0,)
    assert conn.execute("SELECT count(*) FROM documentos").fetchone() == (1,)


def test_documento_fora_do_controle_e_removido(conn: psycopg.Connection, tmp_path: Path) -> None:
    ingerir_corpus(conn, _corpus(tmp_path, LINHA), extrair=_extrair_falso)
    vazio = tmp_path / "vazio"
    vazio.mkdir()
    resumo = ingerir_corpus(conn, _corpus(vazio), extrair=_extrair_falso)
    assert resumo.removidos == 1
    assert conn.execute("SELECT count(*) FROM documentos").fetchone() == (0,)


def test_corpus_invalido_nao_ingere(conn: psycopg.Connection, tmp_path: Path) -> None:
    _corpus(tmp_path, LINHA | {"tema": "seguros"})
    with pytest.raises(ValueError, match="corpus inválido"):
        ingerir_corpus(conn, tmp_path, extrair=_extrair_falso)
