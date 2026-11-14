"""Teste montado à mão da métrica de recuperação (CLAUDE.md: "a única exceção na velocidade").

Cada caso traz a conta no comentário para ser conferida na unha. O gabarito-base é um
parágrafo de 400 caracteres: [1000, 1400) na Resolução CVM 175.
"""

import pytest

from inciso.avaliacao import (
    Avaliacao,
    Trecho,
    acertou,
    caracteres_cobertos,
    media_caracteres_top_k,
    recall_at_k,
    recall_pergunta,
)

CVM = "cvm-resolucao-175-2022"
BACEN = "bacen-circular-3978-2020"
ALVO = Trecho(CVM, 1000, 1400)  # 400 caracteres


def chunk(inicio: int, fim: int, doc_id: str = CVM) -> Trecho:
    return Trecho(doc_id, inicio, fim)


def irrelevantes(n: int) -> list[Trecho]:
    return [chunk(5000 + 1000 * i, 5800 + 1000 * i) for i in range(n)]


# --- cobertura de um trecho -------------------------------------------------------------


def test_chunk_que_contem_o_trecho_inteiro() -> None:
    # [800, 1600) contém [1000, 1400): 400 de 400
    assert caracteres_cobertos(ALVO, [chunk(800, 1600)]) == 400


def test_trecho_cortado_ao_meio_pelo_chunking_fixo() -> None:
    a = chunk(600, 1240)  # cobre [1000, 1240) = 240 → 60%
    b = chunk(1240, 2040)  # cobre [1240, 1400) = 160 → 40%
    assert caracteres_cobertos(ALVO, [a]) == 240
    assert caracteres_cobertos(ALVO, [b]) == 160
    assert caracteres_cobertos(ALVO, [a, b]) == 400
    assert acertou(ALVO, [a])  # 60% ≥ 50%
    assert not acertou(ALVO, [b])  # 40% < 50%
    assert acertou(ALVO, [b, a])  # a união vale, a ordem não


def test_mesmo_intervalo_em_outro_documento_nao_conta() -> None:
    assert caracteres_cobertos(ALVO, [chunk(1000, 1400, BACEN)]) == 0


def test_chunk_que_so_encosta_na_borda_nao_conta() -> None:
    # [1400, 1800) começa onde o alvo termina (intervalo aberto à direita): 0 caracteres
    assert caracteres_cobertos(ALVO, [chunk(1400, 1800), chunk(200, 1000)]) == 0


def test_sobreposicao_entre_chunks_nao_conta_duas_vezes() -> None:
    a = chunk(1000, 1120)  # 120
    b = chunk(1050, 1180)  # 130, dos quais [1050, 1120) = 70 já estão em a
    # união [1000, 1180) = 180 → 45%: erra. Somando ingenuamente, 250 → 62,5%: acertaria.
    assert caracteres_cobertos(ALVO, [a, b]) == 180
    assert not acertou(ALVO, [a, b])


def test_chunk_dentro_de_outro_chunk() -> None:
    # [1100, 1200) está dentro de [900, 1500); a união é [1000, 1400) = 400
    assert caracteres_cobertos(ALVO, [chunk(900, 1500), chunk(1100, 1200)]) == 400


def test_borda_exata_do_limiar() -> None:
    assert acertou(ALVO, [chunk(1000, 1200)])  # 200/400 = 50% → acerta (≥)
    assert not acertou(ALVO, [chunk(1000, 1199)])  # 199/400 = 49,75% → erra


def test_limiar_configuravel() -> None:
    a = chunk(600, 1240)  # 60%
    assert acertou(ALVO, [a], limiar=0.6)
    assert not acertou(ALVO, [a], limiar=0.61)
    assert acertou(ALVO, [chunk(1399, 1400)], limiar=0.0025)  # 1/400 = 0,25%


# --- recall de uma pergunta -------------------------------------------------------------


def test_trecho_certo_em_sexto_lugar() -> None:
    ranking = [*irrelevantes(5), chunk(800, 1600)]
    avaliacao = Avaliacao(gabarito=[ALVO], ranking=ranking)
    assert recall_pergunta(avaliacao, k=5) == 0.0
    assert recall_pergunta(avaliacao, k=6) == 1.0


def test_metades_em_posicoes_diferentes_do_ranking() -> None:
    a = chunk(600, 1240)  # 60%
    b = chunk(1240, 2040)  # 40%
    # b em 1º e a em 6º: com k=5 só b conta → 40% → erra; com k=6, a entra → acerta
    avaliacao = Avaliacao(gabarito=[ALVO], ranking=[b, *irrelevantes(4), a])
    assert recall_pergunta(avaliacao, k=5) == 0.0
    assert recall_pergunta(avaliacao, k=6) == 1.0


def test_gabarito_com_dois_trechos_e_so_um_recuperado() -> None:
    outro = Trecho(BACEN, 300, 500)
    avaliacao = Avaliacao(gabarito=[ALVO, outro], ranking=[chunk(800, 1600)])
    assert recall_pergunta(avaliacao, k=5) == 0.5  # 1 de 2


def test_ranking_vazio() -> None:
    assert recall_pergunta(Avaliacao(gabarito=[ALVO], ranking=[]), k=5) == 0.0


def test_ranking_menor_que_k() -> None:
    assert recall_pergunta(Avaliacao(gabarito=[ALVO], ranking=[chunk(800, 1600)]), k=5) == 1.0


# --- recall do conjunto -----------------------------------------------------------------


def test_media_sobre_perguntas() -> None:
    acerta = Avaliacao(gabarito=[ALVO], ranking=[chunk(800, 1600)])  # 1
    erra = Avaliacao(gabarito=[ALVO], ranking=irrelevantes(5))  # 0
    metade = Avaliacao(gabarito=[ALVO, Trecho(BACEN, 300, 500)], ranking=[chunk(800, 1600)])  # 0,5
    # (1 + 0 + 1 + 0,5) / 4 = 2,5 / 4 = 0,625
    assert recall_at_k([acerta, erra, acerta, metade], k=5) == 0.625


def test_cada_pergunta_pesa_igual() -> None:
    # Pergunta com 2 trechos (1 acerto) e pergunta com 1 trecho (acerto):
    # média por pergunta = (0,5 + 1) / 2 = 0,75; contando trechos seria 2/3. Usamos por pergunta.
    duas = Avaliacao(gabarito=[ALVO, Trecho(BACEN, 300, 500)], ranking=[chunk(800, 1600)])
    uma = Avaliacao(gabarito=[ALVO], ranking=[chunk(800, 1600)])
    assert recall_at_k([duas, uma], k=5) == 0.75


# --- caracteres recuperados -------------------------------------------------------------


def test_media_de_caracteres_no_top_k() -> None:
    p1 = Avaliacao(gabarito=[ALVO], ranking=[chunk(0, 800), chunk(800, 1600), chunk(1600, 2400)])
    p2 = Avaliacao(gabarito=[ALVO], ranking=[chunk(1000, 1400)])
    # k=2: p1 → 800 + 800 = 1600; p2 tem só 1 chunk → 400; média (1600 + 400) / 2 = 1000
    assert media_caracteres_top_k([p1, p2], k=2) == 1000.0


# --- entradas inválidas -----------------------------------------------------------------


@pytest.mark.parametrize(("inicio", "fim"), [(10, 10), (10, 5), (-1, 5)])
def test_trecho_invalido(inicio: int, fim: int) -> None:
    with pytest.raises(ValueError, match="intervalo inválido"):
        Trecho(CVM, inicio, fim)


def test_k_invalido() -> None:
    with pytest.raises(ValueError, match="k precisa"):
        recall_pergunta(Avaliacao(gabarito=[ALVO], ranking=[]), k=0)
    with pytest.raises(ValueError, match="k precisa"):
        media_caracteres_top_k([Avaliacao(gabarito=[ALVO], ranking=[])], k=0)


def test_pergunta_sem_gabarito() -> None:
    with pytest.raises(ValueError, match="sem gabarito"):
        recall_pergunta(Avaliacao(gabarito=[], ranking=[chunk(0, 10)]), k=5)


@pytest.mark.parametrize("limiar", [0.0, -0.1, 1.01])
def test_limiar_invalido(limiar: float) -> None:
    with pytest.raises(ValueError, match="limiar"):
        acertou(ALVO, [chunk(800, 1600)], limiar=limiar)


def test_conjunto_vazio() -> None:
    with pytest.raises(ValueError, match="nenhuma pergunta"):
        recall_at_k([], k=5)
    with pytest.raises(ValueError, match="nenhuma pergunta"):
        media_caracteres_top_k([], k=5)
