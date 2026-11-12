"""Validação do corpus: o controle.csv e os PDFs de corpus/ precisam concordar.

As mensagens de erro são o feedback que o Emerson lê no CI, por isso dizem a linha,
o problema e, quando dá, como corrigir.
"""

import csv
import re
from datetime import date
from pathlib import Path

COLUNAS = (
    "arquivo",
    "orgao",
    "tipo",
    "numero",
    "data_publicacao",
    "tema",
    "assunto",
    "url_origem",
    "data_acesso",
)
ORGAOS = frozenset({"cvm", "bacen", "cmn"})
TIPOS = frozenset({"resolucao", "circular", "instrucao", "cartacircular"})
TEMAS = frozenset({"fundos", "pld-ft", "ofertas", "instrumentos-financeiros"})
ARQUIVOS_DE_APOIO = frozenset({"README.md", "controle.csv"})

# Um anexo escaneado passa disso fácil; uma vez no histórico do Git, não sai mais.
TAMANHO_MAXIMO = 20 * 1024 * 1024

# O nome sem extensão é o doc_id do projeto inteiro (avaliação, banco, resultados).
# Mudar este padrão depois obriga a reescrever o conjunto de avaliação.
PADRAO_NOME = re.compile(
    r"^(?P<orgao>[a-z]+)-(?P<tipo>[a-z]+)-(?P<numero>[1-9]\d*)-(?P<ano>\d{4})\.pdf$"
)
PADRAO_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validar_corpus(pasta: Path, tamanho_maximo: int = TAMANHO_MAXIMO) -> list[str]:
    """Devolve a lista de problemas do corpus em `pasta`; lista vazia quando está tudo certo."""
    controle = pasta / "controle.csv"
    if not controle.is_file():
        return [f"não encontrei o arquivo {controle}"]

    # utf-8-sig aceita o arquivo com ou sem BOM, que alguns editores no Windows acrescentam.
    with controle.open(encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        if tuple(leitor.fieldnames or ()) != COLUNAS:
            return [
                "controle.csv: a primeira linha (cabeçalho) deve ser exatamente: "
                + ",".join(COLUNAS)
            ]
        linhas = list(enumerate(leitor, start=2))

    erros: list[str] = []
    listados: set[str] = set()
    for numero_linha, linha in linhas:
        for problema in _validar_linha(linha, pasta, tamanho_maximo):
            erros.append(f"controle.csv, linha {numero_linha}: {problema}")
        arquivo = (linha.get("arquivo") or "").strip()
        if arquivo in listados:
            erros.append(
                f"controle.csv, linha {numero_linha}: '{arquivo}' já aparece numa linha anterior"
            )
        listados.add(arquivo)

    for caminho in sorted(pasta.iterdir()):
        if caminho.name in ARQUIVOS_DE_APOIO:
            continue
        if caminho.is_dir():
            erros.append(f"corpus/{caminho.name}/: o corpus não usa subpastas, mova os arquivos")
        elif caminho.name not in listados:
            erros.append(f"corpus/{caminho.name}: arquivo sem linha correspondente no controle.csv")
    return erros


def _validar_linha(
    linha: dict[str | None, str | None], pasta: Path, tamanho_maximo: int
) -> list[str]:
    if None in linha:
        return [
            "a linha tem mais colunas que o cabeçalho. "
            'Se algum texto tem vírgula, coloque-o entre aspas: "assim, com vírgula"'
        ]
    valores = {coluna: (linha.get(coluna) or "").strip() for coluna in COLUNAS}
    vazias = [coluna for coluna, valor in valores.items() if not valor]
    if vazias:
        return [f"coluna(s) vazia(s) ou faltando: {', '.join(vazias)}"]

    erros: list[str] = []
    arquivo = valores["arquivo"]
    nome = PADRAO_NOME.match(arquivo)
    if nome is None:
        erros.append(
            f"o nome '{arquivo}' não segue o padrão orgao-tipo-numero-ano.pdf, "
            "tudo minúsculo e sem acento (exemplo: cvm-resolucao-175-2022.pdf)"
        )
    else:
        for coluna in ("orgao", "tipo", "numero"):
            if nome[coluna] != valores[coluna]:
                erros.append(
                    f"a coluna {coluna} diz '{valores[coluna]}', "
                    f"mas o nome do arquivo diz '{nome[coluna]}'"
                )

    if valores["orgao"] not in ORGAOS:
        erros.append(f"orgao '{valores['orgao']}' não é um de: {', '.join(sorted(ORGAOS))}")
    if valores["tipo"] not in TIPOS:
        erros.append(f"tipo '{valores['tipo']}' não é um de: {', '.join(sorted(TIPOS))}")
    if valores["tema"] not in TEMAS:
        erros.append(f"tema '{valores['tema']}' não é um de: {', '.join(sorted(TEMAS))}")

    datas: dict[str, date] = {}
    for coluna in ("data_publicacao", "data_acesso"):
        try:
            if not PADRAO_DATA.match(valores[coluna]):
                raise ValueError
            datas[coluna] = date.fromisoformat(valores[coluna])
        except ValueError:
            erros.append(
                f"{coluna} '{valores[coluna]}' não é uma data válida no formato AAAA-MM-DD "
                "(exemplo: 2022-12-23)"
            )
    if nome is not None and "data_publicacao" in datas:
        ano_publicacao = datas["data_publicacao"].year
        if ano_publicacao != int(nome["ano"]):
            erros.append(
                f"o ano no nome do arquivo é {nome['ano']}, "
                f"mas data_publicacao é de {ano_publicacao}"
            )

    if not valores["url_origem"].startswith(("https://", "http://")):
        erros.append("url_origem precisa começar com https:// (copie o link da barra do navegador)")

    caminho = pasta / arquivo
    if not caminho.is_file():
        erros.append(f"o arquivo '{arquivo}' não está na pasta corpus/")
        return erros
    tamanho = caminho.stat().st_size
    if tamanho > tamanho_maximo:
        erros.append(
            f"'{arquivo}' tem {tamanho / 1024 / 1024:.1f} MB, acima do limite de "
            f"{tamanho_maximo / 1024 / 1024:.0f} MB. Fale com o Felipe antes de versionar"
        )
    with caminho.open("rb") as f:
        if f.read(5) != b"%PDF-":
            erros.append(
                f"'{arquivo}' não é um PDF de verdade. "
                "Talvez tenha sido salva a página do site em vez do documento"
            )
    return erros
