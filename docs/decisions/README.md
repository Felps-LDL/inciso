# Registros de decisão (ADR)

Uma decisão por arquivo, numerada em sequência: `NNNN-titulo-curto.md`. ADR
aceito não se edita. Se a decisão mudar, escreva um ADR novo que substitui o
anterior e marque o antigo como `Substituído por NNNN`.

Ao fim de cada fase, a decisão principal da fase vira ADR.

## Modelo

```markdown
# NNNN. Título

- Status: Proposto | Aceito | Substituído por NNNN
- Data: AAAA-MM-DD
- Fase: N

## Contexto

O problema e as restrições que forçam uma decisão.

## Decisão

O que foi decidido, em uma ou duas frases.

## Alternativas descartadas

Cada uma com o motivo.

## Consequências

O que fica mais fácil, o que fica mais difícil, e o que precisaria acontecer para
revermos a decisão.
```

## Índice

- [0001. Tarefas com uv e poethepoet, não Makefile](0001-tarefas-com-uv-e-poe.md)
- [0002. Gabarito por trecho e critério de acerto por cobertura](0002-gabarito-por-trecho-e-criterio-de-acerto.md)
- [0003. pgvector no Postgres, com busca exata e sem índice ANN](0003-pgvector-busca-exata.md)
