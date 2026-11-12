-- Idempotente: roda a cada ingestão e em cada teste. Ver docs/backlog.md (esquema) e ADR 0002.
-- Objetivo: Fase 2 (outra estratégia de chunking) e Fase 3 (outros modelos) só inserem linhas.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documentos (
    doc_id          text PRIMARY KEY,  -- nome do arquivo em corpus/ sem a extensão
    orgao           text NOT NULL,
    tipo            text NOT NULL,
    numero          integer NOT NULL,
    data_publicacao date NOT NULL,
    tema            text NOT NULL,
    assunto         text NOT NULL,
    url_origem      text NOT NULL,
    sha256          text NOT NULL,     -- do PDF: liga cada número à versão exata do documento
    texto           text NOT NULL,     -- texto normalizado; os intervalos dos chunks apontam para ele
    versao_extracao text NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doc_id             text NOT NULL REFERENCES documentos ON DELETE CASCADE,
    estrategia         text NOT NULL,  -- ex.: fixo-800-100, estrutural-v1
    inicio             integer NOT NULL,
    fim                integer NOT NULL,
    texto              text NOT NULL,
    caminho_estrutural text,           -- ex.: art.5/§2/III; nulo no chunking fixo
    CHECK (0 <= inicio AND inicio < fim),
    UNIQUE (doc_id, estrategia, inicio, fim)
);

CREATE INDEX IF NOT EXISTS chunks_por_estrategia ON chunks (estrategia);

-- Vetor sem dimensão fixa: os modelos da Fase 3 têm dimensões diferentes.
-- Sem índice ANN de propósito: a busca exata não introduz erro no recall medido.
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id  bigint NOT NULL REFERENCES chunks ON DELETE CASCADE,
    modelo    text NOT NULL,
    embedding vector NOT NULL,
    PRIMARY KEY (chunk_id, modelo)
);
