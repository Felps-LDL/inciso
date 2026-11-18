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

VERSAO_NORMALIZACAO = 2
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

# O texto consolidado da CVM, do Bacen e do CMN mantém a redação antiga, riscada, logo antes
# da nova (às vezes duas antigas). A extração perde o risco; o que sobra é o mesmo rótulo em
# linhas seguidas, e a última é a vigente. Nem toda versão nova traz nota de alteração (o
# art. 140 da CVM 175 não traz), então a nota não serve de critério. Dois dispositivos
# vizinhos legítimos nunca têm o mesmo rótulo: haveria um Art. ou § entre eles.
ROTULO = re.compile(
    r"^(?:Art\.\s*\d+(?:\s*[º°o])?(?:[-–][A-Z])?|§\s*\d+\s*[º°]?(?:[-–][A-Z])?"
    r"|Parágrafo\s+único|[IVXLCDM]+(?=\s*[–—-]\s)|[a-z]\)(?=\s))"
)
# Quando o artigo inteiro foi substituído, a versão antiga vem com os seus parágrafos e
# incisos antes do novo artigo de mesmo número (CVM 175, Anexo III, art. 17).
NUMERO_DO_ARTIGO = re.compile(r"^Art\.\s*(\d+)(?:\s*[º°o])?([-–][A-Z])?")
# Notas de alteração citam outra norma e não são conteúdo. Bacen/CMN: "(Redação dada ... pela
# Resolução CMN nº 5.100...)"; CVM: "• Inciso VI com redação dada pela Resolução CVM nº 187,
# de 27 de setembro de 2023." "(Revogado ...)" e "REVOGADO" ficam: são o único texto que
# resta do dispositivo. Nota sem o ")" final é a que teve o fim cortado como rodapé.
NOTA_DE_ALTERACAO = re.compile(
    r"\s*\((?:Redação dada|Incluíd[oa])[^()]*(?:\)|$)"
    r"|\s*•[^•]*?\b(?:com redação dada|incluíd[oa]s?|revogad[oa]s?|renumerad[oa]s?)\s+pela\s+"
    r"Resolução\s+CVM\s+nº\s*[\d.]+,\s*de\s+\d+º?\s+de\s+\w+\s+de\s+\d{4}\.?",
    re.IGNORECASE,
)
LINK = re.compile(r"\s*<https?://[^>]*>")
# Ligaduras tipográficas (ﬁ, ﬂ...) fazem "ﬁnanceiro" virar outra palavra para o tokenizador
# e para quem compara com texto copiado do navegador.
LIGADURAS = {cp: unicodedata.normalize("NFKC", chr(cp)) for cp in range(0xFB00, 0xFB07)}

ExtrairPaginas = Callable[[Path], list[str]]


@dataclass(frozen=True)
class Resumo:
    ingeridos: int
    sem_mudanca: int
    removidos: int
    avisos: tuple[str, ...] = ()


def versao_extracao() -> str:
    return f"pypdf-{version('pypdf')}/norm-{VERSAO_NORMALIZACAO}"


def extrair_paginas(caminho: Path) -> list[str]:
    return [pagina.extract_text() or "" for pagina in PdfReader(caminho).pages]


def normalizar(paginas: list[str]) -> str:
    """Remove cabeçalho e rodapé repetidos e junta as linhas de cada parágrafo.

    Quebra de linha só sobrevive antes de um início estrutural (Art., §, inciso, alínea,
    capítulo, seção, anexo). Hífen no fim da linha é mantido: no corpus, quase sempre é
    palavra composta ("público-alvo"), não hifenização tipográfica. Depois, só fica a
    redação vigente de cada dispositivo, sem notas de alteração nem links.
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
    return _so_redacao_vigente(LINK.sub("", "".join(partes)))


def artigos_repetidos(texto: str) -> list[str]:
    """Números de artigo que aparecem duas vezes na mesma parte (corpo ou um anexo).

    É a redação antiga que a limpeza não alcança: um artigo antigo com os seus incisos,
    seguido do artigo novo. A numeração recomeça em cada anexo, então a contagem também.
    """
    repetidos: list[str] = []
    vistos: set[str] = set()
    for linha in texto.split("\n"):
        if linha.startswith(("ANEXO", "Anexo")):
            vistos = set()
        elif numero := _numero_do_artigo(linha):
            if numero in vistos:
                repetidos.append(numero)
            vistos.add(numero)
    return repetidos


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
    avisos: list[str] = []

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
        texto = normalizar(extrair(caminho))
        if repetidos := artigos_repetidos(texto):
            avisos.append(f"{doc_id}: artigo repetido na mesma parte: {', '.join(repetidos)}")
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
                texto=texto,
                versao_extracao=versao,
            ),
        )
        ingeridos += 1

    cursor = conn.execute("DELETE FROM documentos WHERE doc_id <> ALL(%s)", (doc_ids,))
    return Resumo(ingeridos, sem_mudanca, cursor.rowcount, tuple(avisos))


def _limpar(linha: str) -> str:
    linha = unicodedata.normalize("NFC", linha).translate(LIGADURAS)
    # Caracteres de uso privado são glifos de fonte sem significado (U+E5CE na CMN 4.966).
    linha = "".join(c for c in linha if unicodedata.category(c) != "Co")
    # split() sem argumento já trata NBSP e outros espaços Unicode como separador.
    return " ".join(linha.split())


def _rotulo(linha: str) -> str | None:
    m = ROTULO.match(linha)
    return re.sub(r"\s+", "", m.group()) if m else None


def _numero_do_artigo(linha: str) -> str | None:
    m = NUMERO_DO_ARTIGO.match(linha)
    return m.group(1) + (m.group(2) or "").replace("–", "-") if m else None


def _so_redacao_vigente(texto: str) -> str:
    vigentes: list[str] = []
    artigo_anterior: tuple[str, int] | None = None  # (número, onde começa o bloco dele)
    for linha in texto.split("\n"):
        rotulo = _rotulo(linha)
        while rotulo is not None and vigentes and _rotulo(vigentes[-1]) == rotulo:
            vigentes.pop()
        if numero := _numero_do_artigo(linha):
            if artigo_anterior is not None and artigo_anterior[0] == numero:
                inicio = artigo_anterior[1]
                vigentes[inicio:] = [x for x in vigentes[inicio:] if TITULO.match(x)]
            artigo_anterior = (numero, len(vigentes))
        elif linha.startswith(("ANEXO", "Anexo")):
            artigo_anterior = None
        vigentes.append(NOTA_DE_ALTERACAO.sub("", linha))
    return "\n".join(vigentes)


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
    for aviso in resumo.avisos:
        print(f"AVISO {aviso}")


if __name__ == "__main__":
    main()
