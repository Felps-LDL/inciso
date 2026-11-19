from pathlib import Path

import psycopg
import pytest

from inciso.banco import Chunk, inserir_chunks
from inciso.corpus import COLUNAS
from inciso.ingestao import artigos_repetidos, ingerir_corpus, normalizar, versao_extracao

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


# --- texto consolidado: só a redação vigente ----------------------------------------------

NOTA_BCB = "(Redação dada, a partir de 1º/9/2021, pela Resolução BCB nº 119, de 27/7/2021.)"


def test_ligaduras_viram_letras() -> None:
    assert normalizar(["instrumento ﬁnanceiro e ﬂuxo de caixa"]) == (
        "instrumento financeiro e fluxo de caixa"
    )


def test_caractere_de_uso_privado_sai() -> None:
    assert normalizar(["I - arrendamento mercantil; e \nII - outros"]) == (
        "I - arrendamento mercantil; e\nII - outros"
    )


def test_redacao_antiga_de_inciso_sai_e_a_nota_tambem() -> None:
    # Circular 3.978, art. 28, § 2º: a versão riscada vem logo antes da vigente.
    texto = normalizar(
        [
            "§ 2º No processo de identificação do cliente devem ser coletados:\n"
            "I - o nome completo, o endereço residencial e o CPF; e\n"
            f"I - o nome completo e o CPF; e {NOTA_BCB}\n"
            "II - a denominação social e o CNPJ."
        ]
    )
    assert texto.split("\n") == [
        "§ 2º No processo de identificação do cliente devem ser coletados:",
        "I - o nome completo e o CPF; e",
        "II - a denominação social e o CNPJ.",
    ]


def test_redacao_antiga_de_artigo_quebrada_em_linhas() -> None:
    texto = normalizar(
        [
            "Art. 70. Esta Circular entra em vigor\nem 1º de julho de 2020.\n"
            "Art. 70. Esta Circular entra em vigor em 1º de outubro de 2020. (Redação dada,\n"
            "a partir de 1º/6/2020, pela Circular nº 4.005, de 16/4/2020.)"
        ]
    )
    assert texto == "Art. 70. Esta Circular entra em vigor em 1º de outubro de 2020."


def test_revogado_tira_o_texto_antigo_e_fica_a_marca() -> None:
    texto = normalizar(
        [
            "Art. 68. A Circular nº 3.691 passa a vigorar com alterações.\n"
            "Art. 68. (Revogado pela Resolução BCB nº 282, de 31/12/2022.)\n"
            "Art. 69. Ficam revogados:"
        ]
    )
    assert texto.split("\n") == [
        "Art. 68. (Revogado pela Resolução BCB nº 282, de 31/12/2022.)",
        "Art. 69. Ficam revogados:",
    ]


def test_incluido_mantem_o_anterior_e_tira_a_nota() -> None:
    texto = normalizar(
        [
            "I - primeiro inciso;\n"
            "II - inciso novo; (Incluído, a partir de 1º/10/2023, pela Resolução CMN nº 5.100.)"
        ]
    )
    assert texto == "I - primeiro inciso;\nII - inciso novo;"


def test_link_quebrado_entre_linhas_sai() -> None:
    texto = normalizar(
        [
            "I - texto vigente; (Redação dada pela Resolução CMN\n"
            "nº 5.100, de 24/8/2023.) <https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?\n"
            "tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=5100>\n"
            "II - outro."
        ]
    )
    assert texto == "I - texto vigente;\nII - outro."


def test_nota_cortada_na_mudanca_de_pagina_sai() -> None:
    # O fim "24/8/2023.) <https://...>" caiu na borda da página e saiu como rodapé.
    texto = normalizar(
        [
            "I - prazo de até doze meses; (Incluído, a partir de 1º/10/2023, pela\n"
            "Resolução CMN nº 5.100, de\nII - outro."
        ]
    )
    assert texto == "I - prazo de até doze meses;\nII - outro."


CVM_187 = "Resolução CVM nº 187, de 27 de setembro de 2023."


def test_redacao_antiga_na_cvm() -> None:
    texto = normalizar(
        [
            "VI – substituição do administrador fiduciário ou portabilidade;\n"
            f"VI – transferência de administração ou portabilidade; • Inciso VI com redação "
            f"dada pela {CVM_187}\n"
            "Parágrafo único. Nos casos previstos, o valor deve ter laudo.\n"
            "Parágrafo único. REVOGADO • Parágrafo único revogado pela Resolução CVM nº 181, "
            "de 28 de março de 2023.\n"
            f"§ 3º Texto novo. • § 3º incluído pela {CVM_187}"
        ]
    )
    assert texto.split("\n") == [
        "VI – transferência de administração ou portabilidade;",
        "Parágrafo único. REVOGADO",
        "§ 3º Texto novo.",
    ]


def test_nota_da_cvm_no_meio_da_linha_tira_so_a_nota() -> None:
    texto = normalizar([f"3. Datas. • Item 3 com redação dada pela {CVM_187} 4. Imóvel."])
    assert texto == "3. Datas. 4. Imóvel."


def test_marcador_de_formulario_nao_e_nota() -> None:
    assert normalizar(["● [ ]% do patrimônio líquido ao ano"]) == (
        "● [ ]% do patrimônio líquido ao ano"
    )


def test_versao_nova_sem_nota_tambem_substitui() -> None:
    # CVM 175, art. 140: a redação nova não traz nota nenhuma.
    texto = normalizar(
        [
            "Art. 140. Esta Resolução entra em vigor em 3 de abril de 2023.\n"
            "Art. 140. Esta Resolução entra em vigor em 2 de outubro de 2023.\n"
            "§ 1º O art. 48 entra em vigor depois."
        ]
    )
    assert texto.split("\n") == [
        "Art. 140. Esta Resolução entra em vigor em 2 de outubro de 2023.",
        "§ 1º O art. 48 entra em vigor depois.",
    ]


def test_tres_versoes_seguidas_fica_a_ultima() -> None:
    texto = normalizar(
        ["Art. 134. Adaptar até 2023.\nArt. 134. Adaptar até 2024.\nArt. 134. Adaptar até 2025."]
    )
    assert texto == "Art. 134. Adaptar até 2025."


@pytest.mark.parametrize(
    "linhas",
    [
        "§ 3º Regra.\n§ 3º-A Regra incluída.",
        "Art. 5º Caput.\nArt. 5º-A Artigo incluído.",
        "I – um;\nII – dois;\nIII – três.",
        "a) uma;\nI – outra lista;\na) de novo.",
    ],
)
def test_rotulos_diferentes_nao_se_substituem(linhas: str) -> None:
    assert normalizar([linhas]) == linhas


def test_artigo_antigo_com_filhos_sai_inteiro_e_o_titulo_fica() -> None:
    # CVM 175, Anexo III, arts. 6 e 17.
    texto = normalizar(
        [
            "Art. 16. Anterior.\n"
            "Art. 17. O pedido de representação deve:\n"
            "I – conter os elementos;\n"
            "§ 5º Os custos são do administrador.\n"
            "Seção II – Representação\n"
            "Art. 17 – REVOGADO\n"
            "Art. 18. Seguinte."
        ]
    )
    assert texto.split("\n") == [
        "Art. 16. Anterior.",
        "Seção II – Representação",
        "Art. 17 – REVOGADO",
        "Art. 18. Seguinte.",
    ]


def test_mesmo_numero_em_anexos_diferentes_nao_se_substitui() -> None:
    texto = "Art. 1º Do corpo:\nI – x.\nANEXO I\nArt. 1º Do anexo."
    assert normalizar([texto]) == texto


def test_artigos_repetidos_na_mesma_parte() -> None:
    # Com outro artigo no meio, não é redação antiga adjacente: só o aviso pega.
    texto = "Art. 1º A.\nArt. 2º B.\nArt. 1º De novo.\nANEXO I\nArt. 1º Do anexo."
    assert artigos_repetidos(texto) == ["1"]
    assert artigos_repetidos("Art. 5º A.\nArt. 5º-A B.\nArt. 70–A C.\nArt. 70-B D.") == []


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


def test_artigo_repetido_vira_aviso(conn: psycopg.Connection, tmp_path: Path) -> None:
    def extrair(_: Path) -> list[str]:
        return ["Art. 1º A.\nArt. 2º B.\nArt. 1º De novo."]

    resumo = ingerir_corpus(conn, _corpus(tmp_path, LINHA), extrair=extrair)
    assert resumo.avisos == ("cvm-resolucao-175-2022: artigo repetido na mesma parte: 1",)


def test_corpus_invalido_nao_ingere(conn: psycopg.Connection, tmp_path: Path) -> None:
    _corpus(tmp_path, LINHA | {"tema": "seguros"})
    with pytest.raises(ValueError, match="corpus inválido"):
        ingerir_corpus(conn, tmp_path, extrair=_extrair_falso)
