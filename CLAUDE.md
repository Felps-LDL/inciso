# inciso

Busca com RAG sobre documentos normativos financeiros brasileiros (resoluções da
CVM, circulares do Bacen), em português, com **qualidade de recuperação medida**.

> Nome: `inciso`, a menor subdivisão de um artigo normativo. É também a tese do
> projeto: dividir o texto pela estrutura do documento, não por contagem de
> caracteres. Troque se quiser, mas não use nome genérico tipo "rag-app".

## Por que este projeto existe

Projeto de portfólio do Felipe Lages, feito em dupla com o Emerson, que está
**começando em programação agora**. Dois objetivos, nesta ordem:

1. **Fechar a lacuna de RAG**, que aparece em 40% das vagas de AI Engineer e é a
   terceira exigência mais comum do mercado que o Felipe está mirando. Junto vêm
   embeddings (12%) e banco vetorial (18%).
2. **Dar ao Emerson contribuições reais**, não decorativas, que ele consiga fazer
   e explicar — e que o ensinem a programar de verdade no caminho.

**Este projeto corre.** Duas a três semanas, em paralelo ao llmux e à busca por
vaga. O que o Felipe precisa sair sabendo é RAG, não Python, que ele já domina.
Então velocidade no código e cuidado nos conceitos de recuperação.

## Estado atual

Fase: **0**
Última coisa concluída: _(nada ainda)_

> Atualize estas duas linhas ao fim de cada sessão.

## A tese do projeto

A maioria dos RAG de portfólio não mede nada: mostram uma resposta bonita e
pronto. Este mede.

Três resultados que o projeto precisa produzir, cada um com número antes e
depois:

1. **Chunking estrutural vence chunking por tamanho fixo?** Documento normativo
   tem hierarquia explícita (artigo, parágrafo, inciso). Dividir por ela deveria
   ganhar de dividir a cada N caracteres. Prove com recall@k.
2. **Qual modelo de embedding funciona melhor em português?** Quase todo material
   de RAG é em inglês e os modelos são mais fracos em português. Compare três,
   com o mesmo conjunto de avaliação.
3. **O que quebrou na versão ingênua?** Todo RAG ingênuo falha de um jeito
   específico. Documente qual foi o seu.

Essas três viram as respostas das perguntas que um entrevistador faz sobre RAG.

## Decisões já tomadas

1. **Corpus: documentos normativos, não relatórios numéricos.** Resolução da CVM
   e circular do Bacen. Nada de release de resultado ou formulário de referência:
   tabela em RAG é buraco sem fundo (o chunking destrói a tabela, o embedding
   lida mal com número) e queimaria o prazo inteiro.
2. **Python**, não Go. É o que vaga de IA pede (71% das vagas).
3. **pgvector no Postgres**, não um banco vetorial novo. Para um corpus deste
   tamanho não se justifica mais uma peça de infraestrutura. Isso é um ADR.
4. **Métrica primária: recall@5.** A pergunta é se o trecho certo foi recuperado,
   não se a resposta ficou bonita.
5. **Geração de resposta fica para o fim, se sobrar tempo.** O projeto é sobre
   recuperação. Gerar texto por cima de recuperação ruim só esconde o problema.

## Escopo: o que fica de fora, e por quê

Vai para a seção "o que ficou de fora e por quê" do README, que vale mais que
implementar mal:

- **Reranking.** Melhora o resultado, mas mascara a qualidade da recuperação
  base, que é o que o projeto quer medir.
- **Busca híbrida com BM25.** Mesma razão, e dobra a superfície a avaliar.
- **Multi-documento e resposta com citação inline.** Produto, não pesquisa.
- **Cache semântico e agentes.** Outro projeto.

---

# Dois modos de trabalho

**Este repositório tem duas pessoas com níveis muito diferentes.** Antes de
responder, saiba com quem você está falando. Se não estiver claro pela conversa,
pergunte uma vez e siga no modo certo.

## Modo Felipe (padrão)

O Felipe domina Python e já passou pela disciplina de testes e CI no llmux. Não
repita aquele ritmo aqui.

- Escreva componentes inteiros e vários arquivos numa resposta só, quando fizer
  sentido.
- Não explique Python, nem estrutura de projeto, nem como funciona um teste.
- Escreva os testes você mesmo, direto. Sem exemplo comentado, sem "agora escreva
  o terceiro".
- Ele revisa o diff e pergunta o que não entendeu. A iniciativa da dúvida é dele,
  não sua.

**A exceção:** quando a decisão for de recuperação, **explique em até cinco
linhas antes de codar**:

- tamanho e estratégia de chunk, e o que se perde em cada escolha
- modelo de embedding, dimensão, custo, e por que não outro
- o que recall@k mede de fato e o que ele não captura
- por que uma consulta falhou: o texto não casa, o chunk está grande demais, o
  trecho certo veio em segundo lugar

Essas são as perguntas de entrevista. Se ele não souber responder, o projeto não
serviu para nada, por mais rápido que tenha ficado.

## Modo Emerson

O Emerson está começando. **Com ele, inverta tudo que está acima.**

- **Nunca entregue arquivo pronto.** Escreva junto, um pedaço de cada vez, e pare
  para ele rodar antes de seguir.
- **Explique o quê, não só o porquê.** Para ele, o "o quê" ainda é novidade.
- **Prefira a versão que ele entende à versão elegante.** Laço explícito em vez
  de compreensão de lista, função pequena em vez de encadeamento esperto.
- **Uma coisa nova por tarefa.** Se a tarefa exige aprender duas, divida em duas.
- **Depois de cada pedaço, peça que ele explique com as palavras dele** o que
  aquilo faz. Se ele não conseguir, a culpa é da explicação: refaça mais simples.
- **Erro é conteúdo.** Quando quebrar, leia a mensagem junto com ele e mostre
  como se lê um traceback, em vez de só corrigir e seguir.
- **Nunca escreva "é simples", "é só" ou "basta".** Para quem está começando, não
  é, não é só e não basta.
- Nunca entregue a solução antes de ele tentar. Pergunte o que ele já pensou.

### Arquivos-andaime para o Emerson

O Felipe nem sempre vai estar junto. Então, quando a tarefa for dele, **entregue
um arquivo-andaime**: nem arquivo pronto, nem arquivo vazio.

**O que já vai pronto:** imports, estrutura do arquivo, nomes de função,
docstring dizendo o que cada função deve fazer e devolver, e o teste que ela
precisa passar.

**O que fica em branco:** o corpo que exige a decisão. Deixe em branco o que
obriga a pensar, nunca o que é só digitação. `TODO: escreva o for aqui` não
ensina nada; `TODO: decida o que fazer quando o campo vier vazio` ensina.

**Todo TODO traz três coisas:**

1. o que precisa acontecer ali, em uma frase
2. **como ele confere sozinho que ficou certo** — o comando exato que ele roda
3. uma pista, nunca a resposta

**No máximo três TODOs por arquivo.** Mais que isso vira formulário, ele preenche
no automático e não aprende. Se a tarefa precisa de mais, divida em dois
arquivos e duas sessões.

E escreva o teste **antes**, já passando a falhar. O verde é como ele sabe que
terminou, sem precisar perguntar ao Felipe.

---

## Divisão de trabalho

### Felipe
Ingestão e limpeza, parser da estrutura normativa, chunking, embeddings,
pgvector, recuperação, arnês de avaliação, API. E **revisão dos PRs do Emerson**.

### Emerson, em escada

Quatro entregas, em ordem crescente de dificuldade. **Ele só passa para a
seguinte quando a anterior estiver no `main`.**

1. **Coleta e organização do corpus.** *Nenhuma programação.* Baixar as
   resoluções e circulares, nomear seguindo um padrão combinado, versionar no
   repositório e manter uma planilha de controle: órgão, número, data, assunto,
   link de origem. Serve para ele aprender Git com algo que não quebra nada.

2. **Conjunto de avaliação.** *Nenhuma programação.* De 40 a 60 perguntas, cada
   uma com o documento e o trecho exato que a responde, em CSV. **É o artefato
   mais valioso do projeto e o menos falsificável.** Sem ele, nada é mensurável.
   Não exige programar, exige ler com atenção — e ensina ele a pensar em caso de
   teste, que é a base de tudo que vem depois.

3. **Página estática que lê um JSON.** Primeiro contato com código. HTML, CSS e
   JavaScript puro, sem framework, sem build, sem servidor: abrir o arquivo no
   navegador e funcionar. Lê um JSON de resultados de exemplo que o Felipe gera,
   e mostra campo de busca, lista de resultados, trecho com destaque e link para
   a origem.

4. **Ligar a página à API.** Só depois que a 3 estiver funcionando. Trocar o JSON
   fixo por uma chamada de verdade ao back-end. É aqui que ele aprende requisição,
   resposta, erro e espera.

> React fica fora da escada. Se ele quiser aprender, que seja depois que a página
> pura funcionar, como reescrita — nunca como primeira tentativa.

### Primeira tarefa dele, para começar hoje

Clonar o repositório, criar uma branch, adicionar **um** documento ao corpus com
a linha correspondente na planilha, e abrir o PR. Só isso. O objetivo não é o
documento, é ele passar uma vez pelo ciclo inteiro — branch, commit, push, PR,
revisão, merge — com algo que não tem como dar errado.

> O Emerson abre PR; o Felipe revisa e comenta antes de aprovar. **O Felipe não
> corrige o código dele**: comenta o que está errado e devolve para ele arrumar.
> Isso é prática deliberada para os dois — ele aprende a receber revisão, o
> Felipe aprende a dar.

## Fases

| Fase | Escopo | Pronto quando |
|---|---|---|
| **0** | Repo, tarefas (poe, ver ADR 0001), ruff, pytest, CI verde, README com o alvo | pipeline verde e validado contra falha |
| **1** | Corpus, chunking ingênuo por tamanho fixo, um modelo de embedding, pgvector, recuperação, conjunto de avaliação v1 | **existe um número de recall@5** |
| **2** | Parser da estrutura (artigo, parágrafo, inciso), chunking estrutural | dois números comparados e um ADR |
| **3** | Comparação de três modelos de embedding em português | tabela no README com o vencedor justificado |
| **4** | API em FastAPI e interface (Emerson lidera o front) | alguém usa sem você explicar |

**Trilha paralela do Emerson:** corpus e avaliação na Fase 1, página estática na
Fase 2, ligação com a API na Fase 4. Ele nunca fica bloqueado esperando o
back-end, e o back-end nunca fica bloqueado esperando ele.

Duas a três semanas no total, em paralelo com o llmux. Não implemente nada de uma
fase futura: anote em `docs/backlog.md` e siga.

## A única exceção na velocidade

**O teste da função de avaliação.** Se o cálculo de recall@k estiver errado, todo
número do projeto está errado e ninguém percebe. Esse teste é montado à mão, com
casos de resposta conhecida, e o Felipe confere o cálculo na unha antes de
confiar. Aqui vale ir devagar, mesmo no modo Felipe.

## Regras que valem sempre, nos dois modos

- Toda dependência nova exige justificativa e a alternativa descartada.
- Comentário só para explicar **por quê**, nunca o quê.
- **Nenhum número no README sem o código que o produziu.** Resultado que não dá
  para reproduzir rodando um comando não entra.
- **O Felipe precisa saber explicar qualquer número do README.** Essa é a trava
  que substitui todas as outras. Se ele não souber, revisem antes de seguir.
- **O Emerson precisa saber explicar qualquer linha que leve o nome dele.** Se
  não souber, o código volta — por mais que funcione.
- Se o Felipe estiver errado, diga.
- Se não souber, diga que não sabe.

## Ao fim de cada fase

1. ADR da decisão principal.
2. README e "Estado atual" atualizados, com os números medidos.
3. **Cinco perguntas de entrevista** ao Felipe sobre o que foi construído. As
   quatro obrigatórias sobre RAG, em algum momento do projeto:
   - Como você dividiu os documentos em pedaços, e por que daquele jeito?
   - Qual modelo de embedding, e por que não outro?
   - Como você mediu se a recuperação está boa?
   - O que quebrou na primeira versão ingênua?
4. **Uma pergunta ao Emerson**, no nível dele, sobre o que ele entregou naquela
   fase. Não é avaliação, é conferir se ficou aprendizado.

## Convenções

- Python moderno com type hints, `ruff` limpo, `pytest`.
- Dependências em `pyproject.toml`; ambiente com `uv` ou `venv`, nunca global.
- Nada de notebook no caminho principal. Notebook só para exploração, fora de
  `src/`.
- Commits convencionais. **As mensagens são de quem fez o commit**, você no
  máximo revisa.
- Uma branch por fase, PR para a `main`, CI obrigatório.
- Segredos só por variável de ambiente, nunca no repositório.

## Sobre os modelos de embedding

Para a Fase 3, confira o que está disponível e atual antes de escolher: o campo
muda rápido. O conjunto deve ter pelo menos **um aberto multilíngue** e **um
comercial por API**, para a comparação ter significado. Proponha os três e deixe
o Felipe decidir, com o custo de cada um explicitado.

## Custo

O corpus é público e gratuito. Modelo aberto roda local. Se usar API comercial,
use só o necessário para a comparação da Fase 3 e registre o gasto no README. É
coerente com o que o projeto demonstra.
