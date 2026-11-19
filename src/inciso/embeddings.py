"""Embeddings dos chunks e das consultas.

Os chunks de uma estratégia são codificados uma vez e gravados em `embeddings`, com o nome do
modelo na chave; a consulta é codificada na hora da busca, pelo mesmo modelo.

Uso: uv run poe embedar
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import psycopg

from inciso.banco import conectar, inserir_embeddings
from inciso.chunking import nome_estrategia

TAMANHO_LOTE = 64


@dataclass(frozen=True)
class ModeloEmbedding:
    repositorio: str  # id no Hugging Face; é também o valor da coluna embeddings.modelo
    # A família E5 foi treinada com prefixos que separam pergunta de trecho. Sem eles a busca
    # piora sem dar erro nenhum.
    prefixo_consulta: str = ""
    prefixo_trecho: str = ""


E5_BASE = ModeloEmbedding("intfloat/multilingual-e5-base", "query: ", "passage: ")


class Codificador(Protocol):
    """O que o resto do código precisa de um modelo. Nos testes, um falso determinístico."""

    limite_tokens: int

    def codificar(self, textos: Sequence[str]) -> list[list[float]]:
        """Vetores normalizados (norma 1), um por texto."""
        ...

    def contar_tokens(self, textos: Sequence[str]) -> list[int]:
        """Tokens de cada texto, contando os especiais, para comparar com o limite."""
        ...


class CodificadorST:
    """Modelo do sentence-transformers rodando local, em CPU."""

    def __init__(self, modelo: ModeloEmbedding) -> None:
        # Import tardio: carregar o torch leva segundos, e só este caminho precisa dele.
        from sentence_transformers import SentenceTransformer

        self._st = SentenceTransformer(modelo.repositorio, device="cpu")
        self.limite_tokens: int = self._st.max_seq_length

    def codificar(self, textos: Sequence[str]) -> list[list[float]]:
        vetores = self._st.encode(
            list(textos), batch_size=32, normalize_embeddings=True, convert_to_numpy=True
        )
        return vetores.tolist()

    def contar_tokens(self, textos: Sequence[str]) -> list[int]:
        return [len(ids) for ids in self._st.tokenizer(list(textos))["input_ids"]]


@dataclass(frozen=True)
class ResumoEmbeddings:
    criados: int
    truncados: int  # chunks maiores que o limite do modelo: o fim deles não entrou no vetor
    maior_em_tokens: int


def embedar_chunks(
    conn: psycopg.Connection,
    modelo: ModeloEmbedding,
    codificador: Codificador,
    estrategia: str,
    tamanho_lote: int = TAMANHO_LOTE,
) -> ResumoEmbeddings:
    """Gera e grava os embeddings dos chunks da estratégia que ainda não têm vetor do modelo."""
    pendentes = conn.execute(
        """
        SELECT c.id, c.texto FROM chunks c
        WHERE c.estrategia = %s
          AND NOT EXISTS (
              SELECT 1 FROM embeddings e WHERE e.chunk_id = c.id AND e.modelo = %s
          )
        ORDER BY c.id
        """,
        (estrategia, modelo.repositorio),
    ).fetchall()

    truncados = 0
    maior = 0
    for i in range(0, len(pendentes), tamanho_lote):
        lote = pendentes[i : i + tamanho_lote]
        textos = [modelo.prefixo_trecho + texto for _, texto in lote]
        tokens = codificador.contar_tokens(textos)
        truncados += sum(t > codificador.limite_tokens for t in tokens)
        maior = max(maior, *tokens)
        vetores = codificador.codificar(textos)
        inserir_embeddings(
            conn,
            modelo.repositorio,
            [(chunk_id, v) for (chunk_id, _), v in zip(lote, vetores, strict=True)],
        )
    return ResumoEmbeddings(len(pendentes), truncados, maior)


def embedar_consulta(
    modelo: ModeloEmbedding, codificador: Codificador, pergunta: str
) -> list[float]:
    [vetor] = codificador.codificar([modelo.prefixo_consulta + pergunta])
    return vetor


def main() -> None:
    estrategia = nome_estrategia()
    codificador = CodificadorST(E5_BASE)
    with conectar() as conn:
        resumo = embedar_chunks(conn, E5_BASE, codificador, estrategia)
    print(f"{E5_BASE.repositorio} / {estrategia}: {resumo.criados} embeddings novos")
    if resumo.criados:
        print(
            f"  maior chunk: {resumo.maior_em_tokens} tokens (limite {codificador.limite_tokens})"
        )
        print(f"  truncados: {resumo.truncados}")


if __name__ == "__main__":
    main()
