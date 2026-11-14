"""Exploração: quão bem cada biblioteca extrai o texto de um PDF normativo?

Uso: uv run --with pypdf --with pdfplumber python scripts/inspecionar_extracao.py <pdf>

Grava o texto de cada biblioteca em data/extracao/ (gitignored) para leitura a olho
e imprime contagens que indicam se a estrutura sobreviveu. Fora de src/: é um teste de
decisão, não código de produção.
"""

import re
import sys
from collections import Counter
from pathlib import Path

ARTIGO = re.compile(r"\bArt\.\s*\d+")
ORDINAL = re.compile(r"\bArt\.\s*\d+\s*([º°o])")
PARAGRAFO = re.compile(r"§\s*\d+|Parágrafo único", re.IGNORECASE)
INCISO = re.compile(r"^\s*[IVXLC]+\s*[-–—]\s", re.MULTILINE)
HIFEN_QUEBRADO = re.compile(r"[a-zà-ú]-\n[a-zà-ú]")


def com_pypdf(caminho: Path) -> list[str]:
    from pypdf import PdfReader

    return [pagina.extract_text() or "" for pagina in PdfReader(caminho).pages]


def com_pdfplumber(caminho: Path) -> list[str]:
    import pdfplumber

    with pdfplumber.open(caminho) as pdf:
        return [pagina.extract_text() or "" for pagina in pdf.pages]


def linhas_repetidas(paginas: list[str], fracao_minima: float = 0.3) -> list[tuple[str, int]]:
    """Linhas que aparecem em muitas páginas: candidatas a cabeçalho e rodapé."""
    contagem: Counter[str] = Counter()
    for pagina in paginas:
        # Número de página muda a cada folha; trocar dígitos por # agrupa "Página 3" e "Página 4".
        contagem.update({re.sub(r"\d+", "#", linha.strip()) for linha in pagina.splitlines()})
    minimo = max(2, int(len(paginas) * fracao_minima))
    return [(linha, n) for linha, n in contagem.most_common(10) if n >= minimo and linha]


def relatorio(nome: str, paginas: list[str], saida: Path) -> None:
    texto = "\n".join(paginas)
    (saida / f"{nome}.txt").write_text(texto, encoding="utf-8")
    ordinais = Counter(m.group(1) for m in ORDINAL.finditer(texto))
    print(f"\n== {nome} ==")
    print(f"páginas: {len(paginas)}  caracteres: {len(texto):,}")
    print(f"artigos ('Art. N'): {len(ARTIGO.findall(texto))}")
    print(f"ordinal depois do número do artigo: {dict(ordinais)}")
    print(f"parágrafos (§ N / Parágrafo único): {len(PARAGRAFO.findall(texto))}")
    print(f"incisos (linha começando com romano e travessão): {len(INCISO.findall(texto))}")
    print(f"palavras quebradas por hífen no fim da linha: {len(HIFEN_QUEBRADO.findall(texto))}")
    print("linhas repetidas entre páginas (cabeçalho/rodapé?):")
    for linha, n in linhas_repetidas(paginas):
        print(f"  {n:4d}x  {linha[:90]}")


def main() -> None:
    caminho = Path(sys.argv[1])
    saida = Path("data/extracao") / caminho.stem
    saida.mkdir(parents=True, exist_ok=True)
    relatorio("pypdf", com_pypdf(caminho), saida)
    relatorio("pdfplumber", com_pdfplumber(caminho), saida)
    print(f"\ntextos completos em {saida}/")


if __name__ == "__main__":
    main()
