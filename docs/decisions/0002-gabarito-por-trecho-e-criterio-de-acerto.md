# 0002. Gabarito por trecho e critério de acerto por cobertura

- Status: Aceito
- Data: 2026-11-12
- Fase: 1

## Contexto

O recall@5 vai comparar estratégias de chunking (Fase 2) e modelos de embedding
(Fase 3) com o **mesmo** conjunto de avaliação. O conjunto é escrito à mão pelo
Emerson, e refazê-lo é caro.

Duas perguntas precisam de resposta antes da primeira pergunta escrita: como o
gabarito aponta para a resposta, e quando um resultado conta como acerto.

## Decisão

1. **O gabarito é um trecho do documento, não um chunk.** No CSV de avaliação ele
   é o `doc_id` mais o texto literal. Na avaliação, vira um intervalo de
   caracteres `[inicio, fim)` no texto normalizado do documento. Os chunks também
   são intervalos no mesmo texto.
2. **Acerto é cobertura.** Uma pergunta acerta quando a **união** dos k primeiros
   chunks recuperados, do mesmo documento, cobre **pelo menos 50%** dos
   caracteres do trecho. A sobreposição entre chunks não conta duas vezes.
3. **O recall@k é a média por pergunta.** Pergunta com vários trechos vale a
   fração de trechos acertados, e cada pergunta pesa igual.
4. **Junto com o recall, sai a média de caracteres recuperados no top-k.**

Implementação e teste montado à mão: `src/inciso/avaliacao.py` e
`tests/test_avaliacao.py`.

## Alternativas descartadas

- **Gabarito por id de chunk.** Morre quando o chunking muda. Fase 1 e Fase 2
  teriam gabaritos diferentes, e não haveria comparação.
- **Exigir o trecho inteiro dentro de um único chunk.** Pune o chunking fixo só por
  cortar no lugar errado, e favorece o estrutural de forma artificial.
- **Qualquer sobreposição, mesmo de 1 caractere.** Conta como acerto um chunk que
  mal toca a borda do trecho, e infla o recall.
- **O melhor chunk sozinho, sem união.** Quem consome o resultado recebe os k
  chunks juntos. Um trecho dividido entre dois chunks recuperados foi, de fato,
  recuperado.
- **Média por trecho, e não por pergunta.** Daria mais peso às perguntas com
  vários trechos.

## Consequências

- O mesmo gabarito mede qualquer chunking. A Fase 2 compara com a Fase 1 sem
  retrabalho do Emerson.
- O limiar de 50% é uma convenção. Ele é declarado no README junto com cada
  número e não muda depois do primeiro número publicado; mudá-lo muda todos os
  resultados.
- O recall@k não captura a posição dentro do top-k (1º e 5º contam igual). Se
  isso importar, o MRR entra como métrica secundária (ver backlog).
- Chunks maiores ganham recall de graça. A média de caracteres recuperados é o
  que expõe isso.
- Converter o texto literal do CSV no intervalo de caracteres depende da
  normalização do texto extraído. Se a extração mudar, os intervalos são
  recalculados a partir do texto literal, e o gabarito continua valendo.
