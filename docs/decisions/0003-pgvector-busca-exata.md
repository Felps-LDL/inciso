# 0003. pgvector no Postgres, com busca exata e sem índice ANN

- Status: Aceito
- Data: 2026-11-12
- Fase: 1

## Contexto

O projeto precisa guardar embeddings de alguns milhares de chunks (cerca de 60
documentos) e buscar os k mais próximos de uma pergunta. O número que importa é o
recall@5. Qualquer erro introduzido pela infraestrutura de busca contamina essa
medida.

## Decisão

- **Postgres com a extensão pgvector.** No CI, roda como serviço com a imagem
  `pgvector/pgvector:0.8.7-pg18`. No desenvolvimento local, usa um Postgres
  gerenciado no Neon (plano gratuito, com pgvector), acessado pela variável
  `DATABASE_URL`. O `compose.yaml` com a mesma imagem do CI fica como alternativa,
  para quando houver Docker.
- **Busca exata por distância de cosseno** (`ORDER BY embedding <=> consulta`), sem
  índice HNSW nem IVFFlat.
- **O vetor sem dimensão fixa**, numa tabela `embeddings` separada de `chunks`, com
  chave `(chunk_id, modelo)`.
- **Driver `psycopg` 3**, com o vetor enviado como literal de texto e cast em SQL.

## Alternativas descartadas

- **Banco vetorial dedicado** (Qdrant, Chroma, Weaviate). Seria mais uma peça de
  infraestrutura para um corpus que cabe com folga no Postgres. O Postgres ainda
  guarda documentos, chunks e metadados com integridade referencial na mesma
  consulta.
- **Índice ANN (HNSW).** É aproximado por definição e pode deixar de devolver o
  vizinho mais próximo. Isso introduziria um erro próprio no recall medido. Também
  limita `vector` a 2.000 dimensões no índice.
- **Coluna `vector(N)` com dimensão fixa.** Cada modelo da Fase 3 com dimensão
  diferente exigiria uma migração.
- **SQLAlchemy.** Um ORM inteiro para três tabelas e poucas consultas.
- **asyncpg.** Async não traz nada a um script de avaliação.
- **pgvector-python.** Uma dependência só para serializar o vetor, o que cabe numa
  linha de código.
- **Postgres nativo no Windows.** O pgvector precisaria ser compilado com o Visual
  C++ Build Tools, e o ambiente local divergiria do CI.

## Consequências

- O CI usa uma imagem fixa. O banco local (Neon) pode ter outra versão do Postgres
  e do pgvector. O esquema e as consultas usam só recursos básicos do pgvector
  (`vector` e `<=>`), então a diferença não deve afetar os resultados. Os números
  oficiais do README vêm do mesmo código, rodado contra qualquer um dos dois.
- A busca exata é linear no número de chunks. Com milhares, leva milissegundos; com
  milhões, seria inviável, mas isso está fora do escopo.
- Se a API da Fase 4 precisar de latência menor, entra um índice HNSW parcial por
  modelo, sem mudar o esquema e fora do caminho da avaliação.
- No Windows 11, o Controle Inteligente de Aplicativos bloqueia a DLL compilada do
  `psycopg-binary`, e tende a bloquear outras bibliotecas compiladas (torch,
  tokenizers). Na máquina do Felipe ele foi desativado, e a proteção ficou igual à
  de um Windows comum (Defender, SmartScreen, firewall, UAC).
- O Docker Desktop precisa do WSL2, que não funcionou na máquina do Felipe. Os
  recursos apareciam ativos, mas o WSL dizia "virtualização não habilitada". A
  reinstalação dos recursos ficou presa no download pelo Windows Update. Daí o Neon
  no desenvolvimento local. A causa raiz não foi identificada (ver backlog).
