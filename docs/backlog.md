# Backlog

O que pertence a uma fase futura fica anotado aqui, e não é implementado antes da
hora. Cada item diz o porquê, para não ser preciso redescobrir o motivo depois.

## Fase 1

### Antes de o Emerson baixar em escala (durante o piloto de 5 documentos)

- **Teste de extração de texto dos PDFs.** Extrair o texto de 2 ou 3 PDFs do
  piloto (CVM e Bacen) e conferir se os marcadores "Art.", "§" e os incisos em
  romano sobrevivem, sem cabeçalho de página nem hifenização no meio de artigo.
  Se não sobreviverem, o corpus troca para a versão HTML oficial. É o item mais
  caro de errar: o parser da Fase 2 depende disso.
  - **CVM 175 consolidada (2026-11-13): passou.** Com o
    `scripts/inspecionar_extracao.py`, pypdf e pdfplumber deram o mesmo resultado:
    399 páginas, "Art. 4º", "§ 1º" e "I –" intactos, só 7 palavras quebradas por
    hífen. O problema encontrado foi o timbre da CVM (5 linhas de endereço) e o
    número da página, repetidos em todas as páginas e caindo **no meio do artigo**
    (entre o § 3º e o § 4º do art. 5º). A normalização da ingestão precisa remover
    as linhas repetidas entre páginas. Falta testar um documento do Bacen.
  - **Ingestão feita** (`src/inciso/ingestao.py`, `uv run poe ingerir`). Na CVM 175,
    a normalização tirou o timbre, os números de página e os títulos correntes, e
    o texto foi de 925 mil para 703 mil caracteres: 24% era ruído de página. O que
    sobrou de "www.cvm.gov.br" é conteúdo real (formulários dos anexos).
  - **Sumário no início do documento.** A CVM 175 abre com um índice ("Art. 5º
    ............ 16"). Ele vira chunks que repetem os títulos sem conteúdo e podem
    competir com o trecho certo. Medir na Fase 1 se ele aparece nos top-5 errados,
    antes de decidir se a normalização deve removê-lo.
- **Medir o tamanho real do corpus** com os 5 primeiros PDFs. A estimativa é de
  20 a 60 MB para 60 documentos.

### Infraestrutura

- **Feito:** `compose.yaml`, `src/inciso/esquema.sql`, `src/inciso/banco.py`, com
  busca exata por cosseno e serviço no CI. ADR 0003.
- **Postgres + pgvector local via Docker Desktop**, com backend WSL2
  (`wsl --install` exige reiniciar o Windows; depois,
  `winget install --id Docker.DockerDesktop -e`). A mesma imagem
  `pgvector/pgvector` roda como `services:` no CI. Vira ADR na Fase 1, junto com o
  "por que pgvector, e não um banco vetorial dedicado".
- Pasta `data/`, já no `.gitignore`, para os derivados da ingestão.
- Pasta `notebooks/` para exploração, fora de `src/` e fora do caminho principal.

### Formato do gabarito de avaliação (primeiro ADR da Fase 1)

**Decidido no ADR 0002 e implementado em `src/inciso/avaliacao.py`.** Falta o guia
`eval/README.md` para o Emerson. MRR como métrica secundária, para capturar a
posição dentro do top-k, só entra se a comparação das Fases 2 e 3 precisar dele.

- O gabarito é **independente do chunking**: `doc_id` + **trecho literal** + a
  referência estrutural legível (por exemplo, "art. 5º, § 2º, III"). Nunca um id
  de chunk, que deixa de existir quando o chunking muda na Fase 2.
- O critério de acerto é por **sobreposição** com o trecho (por exemplo, ≥ 50%
  dos caracteres), e não "contém o trecho inteiro", que pune artificialmente o
  chunking fixo.
- Reportar o **tamanho médio do chunk** (ou os tokens recuperados) ao lado do
  recall@5. Chunk maior ganha recall de graça.
- O critério entra no teste feito à mão da função de recall@k. Mudar o critério
  depois muda todos os números já publicados.
- Guia `eval/README.md` para o Emerson, com **piloto de 5 perguntas** revisadas
  antes das outras.

### Risco: sobreposição léxica no conjunto de avaliação

Se a pergunta repetir as palavras do trecho-resposta, a busca acerta por
coincidência de vocabulário. O recall@5 fica perto de 1,0 para qualquer
estratégia e qualquer modelo, e a comparação das Fases 2 e 3 perde o sentido.

**Regra operacional para o `eval/README.md`:** escreva a pergunta como um usuário
a faria, sem conhecer o texto da norma. Não copie substantivos nem verbos do
trecho, a não ser termos técnicos sem sinônimo (por exemplo, "PLD/FT" e
"cotista").

| Ruim | Bom |
|---|---|
| "Quais são as hipóteses em que o administrador fiduciário deve comunicar fato relevante aos cotistas?" Copia "administrador fiduciário", "comunicar", "fato relevante" e "cotistas" do trecho. | "Se acontecer algo grave com o fundo, quem tem que avisar os investidores, e em quanto tempo?" |

**Verificação mecânica:** um script calcula a fração de palavras da pergunta (sem
stopwords) que aparecem no trecho, e sinaliza as perguntas acima de um limiar. O
piloto de 5 perguntas é onde se calibram a regra e o limiar com o Emerson.

**Alarme:** se o chunking ingênuo der recall@5 ≥ 0,9, ou o conjunto de avaliação
está fácil demais, ou o corpus tem poucos distratores. Nesse caso, entram mais
documentos nos temas existentes, não temas novos.

### Esquema do banco: a Fase 2 e a Fase 3 precisam ser inserções, não migrations

- `documents`: `doc_id` (o nome do arquivo sem extensão), os metadados do
  `controle.csv`, o `sha256` do PDF, o texto normalizado extraído (guardado uma
  vez) e a `extraction_version`.
- `chunks`: id, `doc_id`, **`strategy`** (`fixed-800-100`, `structural-v1`...),
  `char_start` e `char_end` no texto do documento, o texto, e
  **`structure_path` anulável**. Ele fica nulo na Fase 1 e é preenchido na Fase 2.
- `embeddings`, separada de `chunks`: PK `(chunk_id, model)`, coluna `vector`
  **sem dimensão fixa**. Os três modelos da Fase 3 têm dimensões diferentes.
- **Sem índice ANN na avaliação.** Com poucos milhares de vetores, a busca exata é
  instantânea, e o HNSW/IVFFlat introduz um erro de recall próprio, que
  contaminaria a medição. Isso evita também o limite de 2.000 dimensões do HNSW
  em `vector`.
- Execuções de avaliação registradas em `results/*.json`, versionado: estratégia,
  modelo, k, critério de acerto, versão do conjunto de avaliação e commit. É isso
  que liga cada número do README ao código que o produziu.

## Fase 2

- **Início dos anexos.** A normalização remove o título corrente "ANEXO NORMATIVO I
  DA RESOLUÇÃO..." como cabeçalho. Se o título de abertura do anexo for idêntico,
  ele sai junto. O parser estrutural precisa de outro sinal para saber onde cada
  anexo começa: a numeração dos artigos recomeça em cada anexo.

## Fase 3

- Modelos com mais de 2.000 dimensões (por exemplo, os comerciais de 3.072)
  funcionam com busca exata. Se algum dia precisarem de índice, use `halfvec` ou
  dimensão reduzida.
- Registrar no README o gasto com a API comercial.

## Fase 4

- Se o Emerson precisar rodar a API na máquina dele (Windows), o Controle
  Inteligente de Aplicativos pode bloquear as bibliotecas compiladas, como
  aconteceu com o `psycopg` na máquina do Felipe. Saídas: a API roda num
  container Docker, ou na máquina do Felipe.

- Se a API precisar de latência menor que a da busca exata, criar um índice HNSW
  **parcial por modelo** (`WHERE model = ...`, com cast para a dimensão). O
  esquema não muda.

## Sem fase definida

- **WSL2 e Docker na máquina do Felipe.** Os recursos apareciam ativos, mas o WSL
  dizia "virtualização não habilitada". Na reinstalação, o
  `dism /enable-feature:VirtualMachinePlatform` ficou preso no download pelo
  Windows Update (o progresso alternava entre 0% e 50%). Hoje os recursos estão
  desativados. Tentar de novo depois de uma próxima atualização do Windows. Se a
  mensagem original voltar, abrir uma issue em microsoft/WSL com a saída do
  `wsl --status`. Até lá, o desenvolvimento local usa o Neon (ADR 0003).

- Hooks de pre-commit (ruff). Hoje o CI cobre isso. Reavaliar se o vai-e-volta
  de PR por formatação começar a custar tempo.
- Matriz Windows no CI. Só se aparecer um bug que dependa de plataforma.
