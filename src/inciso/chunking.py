"""Chunking ingênuo por tamanho fixo: o baseline da Fase 1.

Corta o texto normalizado a cada `tamanho` caracteres, com `sobreposicao` caracteres
repetidos entre chunks vizinhos, sem olhar a estrutura (artigo, parágrafo, inciso).
A única concessão é não partir palavras: o corte recua até o espaço mais próximo.

Uso: uv run poe chunkear
"""

import psycopg

from inciso.banco import Chunk, conectar, inserir_chunks

TAMANHO_PADRAO = 800
SOBREPOSICAO_PADRAO = 100


def nome_estrategia(tamanho: int = TAMANHO_PADRAO, sobreposicao: int = SOBREPOSICAO_PADRAO) -> str:
    return f"fixo-{tamanho}-{sobreposicao}"


def chunking_fixo(
    texto: str, tamanho: int = TAMANHO_PADRAO, sobreposicao: int = SOBREPOSICAO_PADRAO
) -> list[tuple[int, int]]:
    """Intervalos [inicio, fim) de no máximo `tamanho` caracteres que cobrem todo o texto.

    O fim recua até o último espaço da janela, sem deixar o chunk com menos da metade do
    tamanho. O próximo chunk começa na primeira palavra dentro dos últimos `sobreposicao`
    caracteres do anterior. Palavra maior que a janela é cortada no meio, sem alternativa.
    """
    if tamanho < 1:
        raise ValueError("tamanho precisa ser pelo menos 1")
    if not 0 <= sobreposicao < tamanho // 2:
        raise ValueError("sobreposicao precisa estar em [0, tamanho/2)")

    n = len(texto)
    inicio = _primeiro_nao_espaco(texto, 0)
    intervalos: list[tuple[int, int]] = []
    while inicio < n:
        if inicio + tamanho >= n:
            intervalos.append((inicio, n))
            break
        espaco = _ultimo_espaco(texto, inicio + tamanho // 2, inicio + tamanho)
        if espaco is None:
            fim = inicio + tamanho
            proximo = fim - sobreposicao
        else:
            fim = espaco
            # fim >= inicio + tamanho/2 > inicio + sobreposicao, então proximo > inicio.
            proximo = _inicio_de_palavra(texto, fim - sobreposicao, fim)
            if proximo is None:
                proximo = _primeiro_nao_espaco(texto, fim)
        intervalos.append((inicio, fim))
        inicio = proximo
    return intervalos


def chunkear_documentos(
    conn: psycopg.Connection,
    tamanho: int = TAMANHO_PADRAO,
    sobreposicao: int = SOBREPOSICAO_PADRAO,
) -> dict[str, int]:
    """Gera os chunks da estratégia para os documentos que ainda não os têm.

    Documento reingerido perde os chunks em cascata e volta a ser processado aqui.
    Devolve {doc_id: quantidade de chunks criados}.
    """
    estrategia = nome_estrategia(tamanho, sobreposicao)
    pendentes = conn.execute(
        """
        SELECT d.doc_id, d.texto FROM documentos d
        WHERE NOT EXISTS (
            SELECT 1 FROM chunks c WHERE c.doc_id = d.doc_id AND c.estrategia = %s
        )
        ORDER BY d.doc_id
        """,
        (estrategia,),
    ).fetchall()
    criados: dict[str, int] = {}
    for doc_id, texto in pendentes:
        chunks = [
            Chunk(doc_id, estrategia, inicio, fim, texto[inicio:fim])
            for inicio, fim in chunking_fixo(texto, tamanho, sobreposicao)
        ]
        inserir_chunks(conn, chunks)
        criados[doc_id] = len(chunks)
    return criados


def _ultimo_espaco(texto: str, de: int, ate: int) -> int | None:
    """Posição do último espaço em [de, ate], ou None."""
    for i in range(ate, de - 1, -1):
        if texto[i].isspace():
            return i
    return None


def _inicio_de_palavra(texto: str, de: int, ate: int) -> int | None:
    """Primeira posição em [de, ate] onde começa uma palavra, ou None."""
    for i in range(max(de, 1), min(ate, len(texto) - 1) + 1):
        if not texto[i].isspace() and texto[i - 1].isspace():
            return i
    return None


def _primeiro_nao_espaco(texto: str, de: int) -> int:
    """Primeira posição a partir de `de` que não é espaço, ou len(texto)."""
    i = de
    while i < len(texto) and texto[i].isspace():
        i += 1
    return i


def main() -> None:
    with conectar() as conn:
        criados = chunkear_documentos(conn)
    total = sum(criados.values())
    print(f"{nome_estrategia()}: {total} chunks em {len(criados)} documento(s)")
    for doc_id, n in criados.items():
        print(f"  {doc_id}: {n}")


if __name__ == "__main__":
    main()
