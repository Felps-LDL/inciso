# inciso

Busca com RAG sobre documentos normativos financeiros brasileiros (resoluções da
CVM e do CMN, circulares do Bacen), em português, com **qualidade de recuperação
medida**.

O nome vem de *inciso*, a menor subdivisão de um artigo normativo. É também a tese
do projeto: dividir o texto pela estrutura do documento, e não por contagem de
caracteres.

> **Estado:** Fase 0 (fundação). Ainda não há nenhum número medido. A tabela de
> resultados abaixo é o alvo, não uma promessa. Nenhum número entra aqui sem o
> comando que o reproduz.

## A tese

A maioria dos RAG de portfólio não mede nada: mostra uma resposta bonita e para
por aí. Este mede. A métrica primária é **recall@5**, ou seja, se o trecho que
responde à pergunta está entre os cinco primeiros recuperados. A geração de texto
fica para o fim, se sobrar tempo: gerar resposta por cima de uma recuperação ruim
só esconde o problema.

Três perguntas, cada uma com um número antes e outro depois:

1. **O chunking estrutural (artigo, parágrafo, inciso) vence o chunking por
   tamanho fixo?**
2. **Qual modelo de embedding funciona melhor em português?** Três modelos
   comparados no mesmo conjunto de avaliação: pelo menos um aberto multilíngue e
   um comercial por API.
3. **O que quebrou na versão ingênua?**

## Resultados

| Experimento | recall@5 | Tamanho médio do chunk | Comando |
|---|---|---|---|
| Chunking fixo, modelo base (Fase 1) | — | — | — |
| Chunking estrutural, modelo base (Fase 2) | — | — | — |
| Comparação de modelos (Fase 3) | — | — | — |

O tamanho do chunk aparece ao lado do recall porque chunk maior ganha recall de
graça. Comparar estratégias sem ele seria enganoso.

## Corpus

Cerca de **60 documentos normativos em 4 temas**: fundos de investimento, PLD/FT,
ofertas públicas e emissores, instrumentos financeiros e risco em instituições
financeiras.

O que torna a recuperação difícil não é a quantidade de documentos, é a de
**distratores**: trechos de outras normas com vocabulário e assunto parecidos com
o do trecho certo. Sessenta documentos de assuntos todos diferentes seriam fáceis
demais, porque qualquer estratégia acertaria e o recall@5 não discriminaria nada.
Concentrar os documentos em poucos temas, misturando órgãos, cria a competição
que as Fases 2 e 3 precisam para mostrar diferença.

Os PDFs são versionados no repositório, na versão vigente (consolidada) quando o
órgão publica uma. Assim, todo número é reproduzível a partir do commit que o
produziu, mesmo que o link de origem saia do ar. Detalhes em
[`corpus/README.md`](corpus/README.md).

## Fases

| Fase | Escopo | Pronto quando |
|---|---|---|
| **0** | Repo, tarefas (poe), ruff, pytest, CI, README | CI verde e validado contra falha |
| **1** | Corpus, chunking fixo, um modelo de embedding, pgvector, recuperação, avaliação v1 | existe um número de recall@5 |
| **2** | Parser estrutural, chunking estrutural | dois números comparados e um ADR |
| **3** | Três modelos de embedding em português | tabela acima com o vencedor justificado |
| **4** | API (FastAPI) e interface | alguém usa sem precisar de explicação |

As decisões ficam registradas em [`docs/decisions/`](docs/decisions/) e o que
ficou para depois, em [`docs/backlog.md`](docs/backlog.md).

## O que ficou de fora, e por quê

- **Reranking.** Melhora o resultado final, mas mascara a qualidade da
  recuperação base, que é o que este projeto mede.
- **Busca híbrida com BM25.** Mesma razão, e ainda dobraria a superfície a
  avaliar.
- **Multi-documento e resposta com citação inline.** É produto, não pesquisa.
- **Cache semântico e agentes.** São outro projeto.

## Como rodar

Requisitos: [uv](https://docs.astral.sh/uv/), que instala o Python certo
sozinho, e Docker, para o Postgres com pgvector.

```
uv sync
uv run poe db
uv run poe check
```

- `poe db` sobe o Postgres local com pgvector (`compose.yaml`), a mesma imagem
  usada no CI.
- `poe check` roda o lint, a conferência de formatação e os testes, na mesma ordem
  do CI. Sem o banco no ar, os testes de integração são pulados localmente. No CI
  eles são obrigatórios.
- Para ver as outras tarefas, use `uv run poe`.

## Autores

Felipe Lages e Emerson.
