"""Métricas de recuperação: recall@k sobre trechos de documentos (ver ADR 0002).

Gabarito e chunks são intervalos de caracteres no texto normalizado de um documento.
Assim o mesmo gabarito mede qualquer estratégia de chunking.
"""

from collections.abc import Sequence
from dataclasses import dataclass

LIMIAR_PADRAO = 0.5


@dataclass(frozen=True)
class Trecho:
    """Intervalo [inicio, fim) de caracteres no texto normalizado do documento `doc_id`."""

    doc_id: str
    inicio: int
    fim: int

    def __post_init__(self) -> None:
        if not 0 <= self.inicio < self.fim:
            raise ValueError(f"intervalo inválido: [{self.inicio}, {self.fim})")

    def __len__(self) -> int:
        return self.fim - self.inicio


@dataclass(frozen=True)
class Avaliacao:
    """Uma pergunta: os trechos que a respondem e o ranking que a busca devolveu."""

    gabarito: Sequence[Trecho]
    ranking: Sequence[Trecho]


def caracteres_cobertos(alvo: Trecho, recuperados: Sequence[Trecho]) -> int:
    """Caracteres de `alvo` cobertos pela união dos `recuperados`.

    Sobreposição entre chunks (comum no chunking fixo com overlap) não conta duas vezes.
    """
    intervalos = sorted(
        (max(r.inicio, alvo.inicio), min(r.fim, alvo.fim))
        for r in recuperados
        if r.doc_id == alvo.doc_id and r.inicio < alvo.fim and r.fim > alvo.inicio
    )
    cobertos = 0
    fim_anterior = alvo.inicio
    for inicio, fim in intervalos:
        inicio = max(inicio, fim_anterior)
        if fim > inicio:
            cobertos += fim - inicio
            fim_anterior = fim
    return cobertos


def acertou(alvo: Trecho, recuperados: Sequence[Trecho], limiar: float = LIMIAR_PADRAO) -> bool:
    _validar_limiar(limiar)
    # Dividir, e não multiplicar o limiar: 240 / 400 dá exatamente o mesmo float que o
    # literal 0.6, enquanto 0.6 * 400 depende do arredondamento e pode decidir a borda errado.
    return caracteres_cobertos(alvo, recuperados) / len(alvo) >= limiar


def recall_pergunta(avaliacao: Avaliacao, k: int, limiar: float = LIMIAR_PADRAO) -> float:
    """Fração dos trechos do gabarito cobertos pelos k primeiros chunks do ranking."""
    if k < 1:
        raise ValueError("k precisa ser pelo menos 1")
    if not avaliacao.gabarito:
        raise ValueError("pergunta sem gabarito: é erro no conjunto de avaliação, não recall 0")
    top_k = avaliacao.ranking[:k]
    acertos = sum(1 for alvo in avaliacao.gabarito if acertou(alvo, top_k, limiar))
    return acertos / len(avaliacao.gabarito)


def recall_at_k(avaliacoes: Sequence[Avaliacao], k: int, limiar: float = LIMIAR_PADRAO) -> float:
    """Média do recall@k por pergunta (cada pergunta pesa igual, tenha 1 ou 3 trechos)."""
    if not avaliacoes:
        raise ValueError("nenhuma pergunta para avaliar")
    return sum(recall_pergunta(a, k, limiar) for a in avaliacoes) / len(avaliacoes)


def media_caracteres_top_k(avaliacoes: Sequence[Avaliacao], k: int) -> float:
    """Caracteres recuperados por pergunta, em média. Vai ao lado do recall: chunk maior acerta mais
    sem ser melhor, e sem este número a comparação entre estratégias engana."""
    if not avaliacoes:
        raise ValueError("nenhuma pergunta para avaliar")
    if k < 1:
        raise ValueError("k precisa ser pelo menos 1")
    return sum(sum(len(t) for t in a.ranking[:k]) for a in avaliacoes) / len(avaliacoes)


def _validar_limiar(limiar: float) -> None:
    if not 0 < limiar <= 1:
        raise ValueError("limiar precisa estar em (0, 1]")
