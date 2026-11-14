"""Ingestão: PDF do corpus → texto normalizado → tabela documentos.

O texto normalizado é a referência de todos os intervalos de caracteres do projeto
(chunks e gabarito). Mudar a normalização exige subir VERSAO_NORMALIZACAO, o que faz a
próxima ingestão substituir os documentos e apagar em cascata chunks e embeddings.

Uso: uv run poe ingerir
"""

import csv
import hashlib
import re
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from importlib.metadata import version
from pathlib import Path

import psycopg
from pypdf import PdfReader

from inciso.banco import Documento, aplicar_esquema, conectar, inserir_documento
from inciso.corpus import validar_corpus

VERSAO_NORMALIZACAO = 1
PASTA_CORPUS = Path("corpus")

# Cabeçalho e rodapé moram nas primeiras/últimas linhas da página. Exigir 3 páginas, e não
# uma fração do documento, pega também o título corrente de cada anexo (48 de 399 páginas
# na CVM 175).
JANELA_BORDA = 8
MIN_PAGINAS_REPETIDAS = 3

# Dispositivos são conteúdo mesmo quando se repetem na borda ("§ 2º (Revogado)." no texto
# consolidado). Títulos repetidos na borda de várias páginas são cabeçalho corrente
# ("ANEXO NORMATIVO I DA RESOLUÇÃO...") e saem.
DISPOSITIVO = re.compile(r"^(?:Art\.\s*\d|§\s*\d|Parágrafo\s+único|[IVXLCDM]+\s*[–—-]\s|[a-z]\)\s)")
TITULO = re.compile(
    r"^(?:CAPÍTULO|Capítulo|TÍTULO|Título|LIVRO|Livro|SEÇÃO|Seção|SUBSEÇÃO|Subseção"
    r"|ANEXO|Anexo|SUPLEMENTO|Suplemento)\b"
)
HIFEN_NO_FIM = re.compile(r"[A-Za-zÀ-ÿ]-$")

ExtrairPaginas = Callable[[Path], list[str]]


@dataclass(frozen=True)
class Resumo:
    ingeridos: int
    sem_mudanca: int
    removidos: int


def versao_extracao() -> str:
    return f"pypdf-{version('pypdf')}/norm-{VERSAO_NORMALIZACAO}"


def extrair_paginas(caminho: Path) -> list[str]:
    return [pagina.extract_text() or "" for pagina in PdfReader(caminho).pages]


def normalizar(paginas: list[str]) -> str:
    """Remove cabeçalho e rodapé repetidos e junta as linhas de cada parágrafo.

    Quebra de linha só sobrevive antes de um início estrutural (Art., §, inciso, alínea,
    capítulo, seção, anexo). Hífen no fim da linha é mantido: no corpus, quase sempre é
    palavra composta ("público-alvo"), não hifenização tipográfica.
    """
    linhas_por_pagina = [[_limpar(linha) for linha in p.splitlines()] for p in paginas]
    linhas_por_pagina = [[linha for linha in pagina if linha] for pagina in linhas_por_pagina]
    repetidas = _assinaturas_de_borda_repetidas(linhas_por_pagina)

    corpo: list[str] = []
    for pagina in linhas_por_pagina:
        for i, linha in enumerate(pagina):
            na_borda = i < JANELA_BORDA or i >= len(pagina) - JANELA_BORDA
            if na_borda and _assinatura(linha) in repetidas:
                continue
            corpo.append(linha)

    partes: list[str] = []
    for linha in corpo:
        if not partes:
            partes.append(linha)
        elif DISPOSITIVO.match(linha) or TITULO.match(linha):
            partes.append("\n" + linha)
        elif HIFEN_NO_FIM.search(partes[-1]) and linha[0].islower():
            partes.append(linha)
        else:
            partes.append(" " + linha)
    return "".join(partes)


def ingerir_corpus(
    conn: psycopg.Connection,
    pasta: Path = PASTA_CORPUS,
    extrair: ExtrairPaginas = extrair_paginas,
) -> Resumo:
    """Sincroniza a tabela documentos com o corpus: insere, substitui o que mudou, remove o
    que saiu do controle.csv. Documento com o mesmo sha256 e a mesma versão é pulado."""
    erros = validar_corpus(pasta)
    if erros:
        raise ValueError("corpus inválido:\n" + "\n".join(erros))
    versao = versao_extracao()
    ingeridos = sem_mudanca = 0
    doc_ids: list[str] = []

    for linha in _ler_controle(pasta):
        caminho = pasta / linha["arquivo"]
        doc_id = caminho.stem
        doc_ids.append(doc_id)
        sha = hashlib.sha256(caminho.read_bytes()).hexdigest()
        atual = conn.execute(
            "SELECT sha256, versao_extracao FROM documentos WHERE doc_id = %s", (doc_id,)
        ).fetchone()
        if atual == (sha, versao):
            sem_mudanca += 1
            continue
        if atual is not None:
            conn.execute("DELETE FROM documentos WHERE doc_id = %s", (doc_id,))
        inserir_documento(
            conn,
            Documento(
                doc_id=doc_id,
                orgao=linha["orgao"],
                tipo=linha["tipo"],
                numero=int(linha["numero"]),
                data_publicacao=date.fromisoformat(linha["data_publicacao"]),
                tema=linha["tema"],
                assunto=linha["assunto"],
                url_origem=linha["url_origem"],
                sha256=sha,
                texto=normalizar(extrair(caminho)),
                versao_extracao=versao,
            ),
        )
        ingeridos += 1

    cursor = conn.execute("DELETE FROM documentos WHERE doc_id <> ALL(%s)", (doc_ids,))
    return Resumo(ingeridos=ingeridos, sem_mudanca=sem_mudanca, removidos=cursor.rowcount)


def _limpar(linha: str) -> str:
    # split() sem argumento já trata NBSP e outros espaços Unicode como separador.
    return " ".join(unicodedata.normalize("NFC", linha).split())


def _assinatura(linha: str) -> str:
    # Trocar dígitos por # agrupa "Página 3" e "Página 4" como a mesma linha de rodapé.
    return re.sub(r"\d+", "#", linha)


def _assinaturas_de_borda_repetidas(linhas_por_pagina: list[list[str]]) -> set[str]:
    contagem: Counter[str] = Counter()
    for pagina in linhas_por_pagina:
        borda = pagina[:JANELA_BORDA] + pagina[-JANELA_BORDA:]
        contagem.update({_assinatura(x) for x in borda if not DISPOSITIVO.match(x)})
    return {assinatura for assinatura, n in contagem.items() if n >= MIN_PAGINAS_REPETIDAS}


def _ler_controle(pasta: Path) -> list[dict[str, str]]:
    with (pasta / "controle.csv").open(encoding="utf-8-sig", newline="") as f:
        return [{k: v.strip() for k, v in linha.items()} for linha in csv.DictReader(f)]


def main() -> None:
    with conectar() as conn:
        aplicar_esquema(conn)
        resumo = ingerir_corpus(conn)
    print(
        f"ingeridos: {resumo.ingeridos}  sem mudança: {resumo.sem_mudanca}  "
        f"removidos: {resumo.removidos}  ({versao_extracao()})"
    )


if __name__ == "__main__":
    main()
