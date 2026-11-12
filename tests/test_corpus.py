import csv
import io
from pathlib import Path

import pytest

from inciso.corpus import COLUNAS, validar_corpus

PDF_FALSO = b"%PDF-1.4\n%fake\n"
CORPUS_REAL = Path(__file__).resolve().parents[1] / "corpus"

LINHA_VALIDA = {
    "arquivo": "cvm-resolucao-175-2022.pdf",
    "orgao": "cvm",
    "tipo": "resolucao",
    "numero": "175",
    "data_publicacao": "2022-12-23",
    "tema": "fundos",
    "assunto": "Fundos de investimento, regras gerais",
    "url_origem": "https://conteudo.cvm.gov.br/legislacao/resolucoes/resol175.html",
    "data_acesso": "2026-11-11",
}


def _csv(*linhas: dict[str, str], cabecalho: tuple[str, ...] = COLUNAS) -> str:
    saida = io.StringIO()
    escritor = csv.DictWriter(saida, fieldnames=cabecalho, lineterminator="\n")
    escritor.writeheader()
    escritor.writerows(linhas)
    return saida.getvalue()


def _montar(
    pasta: Path, conteudo_csv: str, arquivos: tuple[str, ...] = (LINHA_VALIDA["arquivo"],)
) -> Path:
    (pasta / "controle.csv").write_text(conteudo_csv, encoding="utf-8")
    for nome in arquivos:
        (pasta / nome).write_bytes(PDF_FALSO)
    return pasta


def test_corpus_so_com_cabecalho_e_valido(tmp_path: Path) -> None:
    assert validar_corpus(_montar(tmp_path, _csv(), arquivos=())) == []


def test_linha_valida(tmp_path: Path) -> None:
    assert validar_corpus(_montar(tmp_path, _csv(LINHA_VALIDA))) == []


def test_aceita_csv_com_bom(tmp_path: Path) -> None:
    _montar(tmp_path, _csv(LINHA_VALIDA))
    conteudo = (tmp_path / "controle.csv").read_text(encoding="utf-8")
    (tmp_path / "controle.csv").write_text(conteudo, encoding="utf-8-sig")
    assert validar_corpus(tmp_path) == []


def test_sem_controle(tmp_path: Path) -> None:
    assert "não encontrei" in validar_corpus(tmp_path)[0]


def test_cabecalho_errado(tmp_path: Path) -> None:
    erros = validar_corpus(_montar(tmp_path, _csv(cabecalho=COLUNAS[:-1]), arquivos=()))
    assert erros == [
        "controle.csv: a primeira linha (cabeçalho) deve ser exatamente: " + ",".join(COLUNAS)
    ]


def test_virgula_sem_aspas_gera_coluna_a_mais(tmp_path: Path) -> None:
    linha = ",".join(LINHA_VALIDA.values())  # o assunto tem vírgula e aqui vai sem aspas
    _montar(tmp_path, ",".join(COLUNAS) + "\n" + linha + "\n")
    [erro] = validar_corpus(tmp_path)
    assert erro.startswith("controle.csv, linha 2: a linha tem mais colunas")


@pytest.mark.parametrize(
    ("alteracao", "trecho_do_erro"),
    [
        ({"assunto": ""}, "coluna(s) vazia(s) ou faltando: assunto"),
        ({"arquivo": "CVM-Resolucao-175-2022.pdf"}, "não segue o padrão"),
        ({"arquivo": "cvm_resolucao_175_2022.pdf"}, "não segue o padrão"),
        ({"numero": "3.978"}, "a coluna numero diz '3.978', mas o nome do arquivo diz '175'"),
        ({"orgao": "bacen"}, "a coluna orgao diz 'bacen'"),
        ({"tema": "seguros"}, "tema 'seguros' não é um de"),
        ({"data_publicacao": "23/12/2022"}, "data_publicacao '23/12/2022' não é uma data válida"),
        ({"data_acesso": "2026-02-30"}, "data_acesso '2026-02-30' não é uma data válida"),
        ({"data_publicacao": "2023-01-05"}, "o ano no nome do arquivo é 2022"),
        ({"url_origem": "conteudo.cvm.gov.br/x"}, "url_origem precisa começar com https://"),
    ],
)
def test_erros_de_linha(tmp_path: Path, alteracao: dict[str, str], trecho_do_erro: str) -> None:
    _montar(tmp_path, _csv(LINHA_VALIDA | alteracao))
    erros = [e for e in validar_corpus(tmp_path) if "sem linha correspondente" not in e]
    assert any(trecho_do_erro in e for e in erros), erros
    assert all(e.startswith("controle.csv, linha 2: ") for e in erros)


def test_orgao_e_tipo_fora_da_lista(tmp_path: Path) -> None:
    linha = LINHA_VALIDA | {
        "arquivo": "susep-portaria-1-2022.pdf",
        "orgao": "susep",
        "tipo": "portaria",
        "numero": "1",
    }
    erros = validar_corpus(_montar(tmp_path, _csv(linha), arquivos=(linha["arquivo"],)))
    assert any("orgao 'susep' não é um de" in e for e in erros)
    assert any("tipo 'portaria' não é um de" in e for e in erros)


def test_arquivo_listado_que_nao_existe(tmp_path: Path) -> None:
    erros = validar_corpus(_montar(tmp_path, _csv(LINHA_VALIDA), arquivos=()))
    assert erros == [
        "controle.csv, linha 2: o arquivo 'cvm-resolucao-175-2022.pdf' não está na pasta corpus/"
    ]


def test_arquivo_sem_linha(tmp_path: Path) -> None:
    extra = "bacen-circular-3978-2020.pdf"
    erros = validar_corpus(
        _montar(tmp_path, _csv(LINHA_VALIDA), arquivos=(LINHA_VALIDA["arquivo"], extra))
    )
    assert erros == [f"corpus/{extra}: arquivo sem linha correspondente no controle.csv"]


def test_linha_duplicada(tmp_path: Path) -> None:
    erros = validar_corpus(_montar(tmp_path, _csv(LINHA_VALIDA, LINHA_VALIDA)))
    assert erros == [
        "controle.csv, linha 3: 'cvm-resolucao-175-2022.pdf' já aparece numa linha anterior"
    ]


def test_subpasta(tmp_path: Path) -> None:
    _montar(tmp_path, _csv(LINHA_VALIDA))
    (tmp_path / "cvm").mkdir()
    assert validar_corpus(tmp_path) == ["corpus/cvm/: o corpus não usa subpastas, mova os arquivos"]


def test_arquivo_que_nao_e_pdf(tmp_path: Path) -> None:
    _montar(tmp_path, _csv(LINHA_VALIDA))
    (tmp_path / LINHA_VALIDA["arquivo"]).write_bytes(b"<!DOCTYPE html><html>")
    [erro] = validar_corpus(tmp_path)
    assert "não é um PDF de verdade" in erro


def test_arquivo_grande_demais(tmp_path: Path) -> None:
    _montar(tmp_path, _csv(LINHA_VALIDA))
    [erro] = validar_corpus(tmp_path, tamanho_maximo=len(PDF_FALSO) - 1)
    assert "acima do limite" in erro


def test_corpus_real_esta_valido() -> None:
    erros = validar_corpus(CORPUS_REAL)
    assert not erros, "Problemas no corpus:\n" + "\n".join(erros)
