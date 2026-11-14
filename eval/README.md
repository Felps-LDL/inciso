# Conjunto de avaliação

Esta pasta guarda as perguntas que usamos para medir a busca. Cada pergunta vem
com o trecho exato do documento que a responde. Tudo fica num arquivo só,
`perguntas.csv`.

Este guia é para o Emerson, mas serve a qualquer pessoa que for escrever
perguntas.

---

## 1. O que é isto, e por que é a parte mais importante do projeto

A busca recebe uma pergunta e devolve os 5 pedaços de texto que ela acha mais
parecidos com a pergunta. Mas como saber se ela acertou? Alguém precisa dizer,
antes, qual é a resposta certa. É isso que você vai escrever: para cada pergunta,
o pedaço do documento que a responde. Chamamos esse pedaço de **trecho**.

Com as perguntas e os trechos prontos, um programa faz o resto. Ele roda cada
pergunta na busca e confere se o trecho certo apareceu entre os 5 primeiros
resultados. A porcentagem de acertos é o **recall@5**, o número principal do
projeto.

Por que é a parte mais importante:

- **Sem ela, nenhum número existe.** Todo o resto do projeto (o jeito de cortar
  os documentos, a escolha do modelo) é comparado por esse número.
- **Ninguém consegue fingir.** Cada linha diz "esta pergunta, este trecho". Dá
  para qualquer pessoa abrir o documento e conferir.
- **É um teste.** Cada pergunta é um caso de teste da busca: uma entrada (a
  pergunta) e a saída esperada (o trecho). Pensar em bons casos de teste é a base
  de tudo que você vai fazer em programação depois.

---

## 2. As colunas de `perguntas.csv`

| Coluna | O que vai nela | Exemplo |
|---|---|---|
| `id` | um código da pergunta: `p` e três algarismos, em sequência | `p001` |
| `pergunta` | a pergunta, do jeito que uma pessoa faria (seção 4) | `Se acontecer algo grave com o fundo, quem tem que avisar os investidores?` |
| `doc_id` | o nome do arquivo em `corpus/`, **sem o `.pdf`** | `cvm-resolucao-175-2022` |
| `referencia` | onde o trecho está, para uma pessoa achar | `art. 64, caput` |
| `trecho` | o texto que responde, copiado do documento **letra por letra** (seção 3) | ver abaixo |

A linha completa do exemplo fica assim (é uma linha só, mesmo que a tela quebre):

```
p001,"Se acontecer algo grave com o fundo, quem tem que avisar os investidores?",cvm-resolucao-175-2022,"art. 64, caput","O administrador é obrigado a divulgar qualquer fato relevante ocorrido ou relacionado ao funcionamento do fundo, da classe ou aos ativos integrantes da carteira, assim que dele tiver conhecimento"
```

**Sempre coloque `pergunta`, `referencia` e `trecho` entre aspas.** Quase
sempre esses textos têm vírgula, e a vírgula separa as colunas. Com aspas, o CSV
entende que a vírgula faz parte do texto. Se o próprio texto tiver aspas, escreva
duas aspas seguidas (`""`) no lugar de cada uma.

Como na planilha do corpus, **edite no VS Code com o Rainbow CSV, não no Excel.**

### A coluna `referencia`

Escreva do jeito que se cita uma norma: `art. 5º, § 2º, III` (artigo 5º,
parágrafo 2º, inciso III). Use `caput` para o texto principal do artigo, antes
dos parágrafos.

**Atenção na CVM 175 e em outras normas com anexos:** a numeração dos artigos
recomeça em cada anexo. Então existe um "art. 10" no texto principal e outro
"art. 10" em cada anexo. Quando o trecho estiver num anexo, diga qual:
`Anexo Normativo I, art. 10, § 1º`.

### Pergunta respondida por dois trechos

Às vezes a resposta está em dois lugares, como um artigo que diz a regra e outro
que diz a exceção. Nesse caso, repita a pergunta numa segunda linha **com o mesmo
`id`** e o segundo trecho:

```
p007,"<a pergunta>",<doc_id>,"art. 12, caput","<primeiro trecho>"
p007,"<a pergunta>",<doc_id>,"art. 15, § 3º","<segundo trecho>"
```

Use isso pouco. A maioria das perguntas deve ter um trecho só.

---

## 3. Como escolher e copiar o trecho

### Qual pedaço escolher

O trecho é **o menor pedaço que responde à pergunta sozinho**. Na maioria das
vezes é uma frase, um parágrafo (§) ou um inciso. Em geral, entre uma linha e um
parágrafo de texto.

- **Pequeno demais**, como só "assim que dele tiver conhecimento": fora do
  contexto, ninguém sabe do que se trata.
- **Grande demais**, como o artigo inteiro com todos os parágrafos, quando só uma
  frase responde: a busca precisa trazer muito texto para "acertar", e o número
  fica pior do que a busca de verdade é.

Por que o tamanho importa: a busca conta como acerto quando os 5 resultados
juntos cobrem **pelo menos metade** do trecho. Um trecho com sobra de texto que
não responde nada deixa essa metade mais difícil de alcançar sem motivo.

### Como copiar

1. Abra o PDF que está em `corpus/` no navegador (Edge ou Chrome).
2. Selecione o trecho com o mouse e copie (Ctrl+C).
3. Cole no VS Code, dentro das aspas da coluna `trecho`.
4. **Junte tudo numa linha só.** O texto copiado de PDF vem com quebras de linha
   no meio das frases. Troque cada quebra por um espaço. O programa que confere
   os trechos ignora diferenças de espaço e de quebra de linha, então não precisa
   se preocupar se ficarem dois espaços seguidos.
5. **Não corrija nada.** Nem acento, nem erro de digitação da norma, nem o
   travessão (`–`), nem o `º`. O trecho precisa ser idêntico ao documento, letra
   por letra, para o programa achá-lo.

**Cuidado com trecho que atravessa a mudança de página.** No PDF, entre uma página
e outra, existe o cabeçalho da CVM (endereço, telefone) e o número da página. Se
você copiar por cima da mudança de página, esse texto vem junto e precisa ser
apagado. Sempre que der, escolha trechos que caibam numa página só.

**Nunca use o sumário** (a lista de capítulos com pontilhado e número de página,
no começo do documento) como trecho. Ele repete os títulos, mas não responde
nada.

---

## 4. Como escrever a pergunta

Esta é a regra mais importante do guia, e a mais fácil de errar sem perceber.

**Escreva a pergunta como uma pessoa que nunca leu a norma faria.** Imagine um
investidor, ou o gerente de um banco, com uma dúvida. Essa pessoa não sabe as
palavras que a norma usa. Ela pergunta com as palavras dela.

### Por que isso importa

A busca é melhor em achar textos que usam **as mesmas palavras** da pergunta. Se
você ler o trecho e escrever a pergunta copiando palavras dele, a busca acha o
trecho pela coincidência das palavras, quase sempre. O número fica perto de 100%
para qualquer jeito de buscar, e o projeto perde a capacidade de dizer qual
jeito é melhor. A pergunta parece boa, mas o teste fica fácil demais e não mede
nada.

### Exemplo

O trecho é o do art. 64 da CVM 175:

> O administrador é obrigado a divulgar qualquer fato relevante ocorrido ou
> relacionado ao funcionamento do fundo, [...] assim que dele tiver conhecimento

| | Pergunta | Por quê |
|---|---|---|
| ❌ Ruim | "O administrador é obrigado a divulgar fato relevante relacionado ao funcionamento do fundo?" | Copia "administrador", "obrigado", "divulgar", "fato relevante" e "funcionamento do fundo". |
| ✅ Boa | "Se acontecer algo grave com o fundo, quem tem que avisar os investidores, e em quanto tempo?" | Não repete nenhuma palavra importante do trecho. É como alguém perguntaria de verdade. |

### Um jeito de fazer

1. Leia o trecho e entenda o que ele diz.
2. **Feche o PDF.**
3. Pense em quem teria essa dúvida e escreva a pergunta como essa pessoa falaria.
4. Volte ao trecho e marque as palavras da sua pergunta que também aparecem nele.
   Se forem mais de duas palavras importantes, reescreva.

### O que pode repetir

- **Termos técnicos sem outro nome**, como "cotista", "CVM", "PLD/FT" e
  "debênture". Ninguém pergunta sobre cotista sem dizer "cotista".
- **Palavras pequenas**, como "o", "de", "que", "quem" e "quando". Elas não contam.

### O que não pode

- **Citar o artigo ou o número da norma** ("O que diz o art. 64?", "Na Resolução
  175, ..."). Isso entrega a resposta.
- **Pergunta de sim ou não**, quando der para evitar. "Quem avisa?" e "Em quanto
  tempo?" testam mais que "O administrador avisa?".
- **Pergunta que precisa de uma tabela ou de uma conta** para ser respondida. A
  busca deste projeto encontra texto, não faz cálculos.

### Variedade

Misture os tipos de pergunta: **quem** faz, **o que** é proibido, **em quanto
tempo**, **o que acontece se**, **o que é** (definição). E espalhe por partes
diferentes do documento: não tire 5 perguntas do mesmo capítulo.

Se a mesma pergunta puder ser respondida por mais de um lugar do documento,
coloque todos os lugares (seção 2, "dois trechos") ou escolha outra pergunta.
Senão, a busca pode trazer uma resposta certa que não está no gabarito e ser
contada como erro.

---

## 5. O piloto: 5 perguntas antes das outras

Como no corpus, o trabalho vai em etapas:

1. **Piloto: 5 perguntas sobre a CVM 175**, que já está no corpus. De pelo menos
   3 capítulos diferentes e de tipos diferentes (seção 4, "Variedade"). Abra um
   PR com elas e **pare até a revisão do Felipe.** Na revisão, vocês dois
   calibram juntos a regra da seção 4: o que conta como "copiar palavra" na
   prática.
2. **Depois da aprovação, o resto**, até **40 a 60 perguntas** no total, em PRs
   de até 10 perguntas cada.
   - Espalhe pelos documentos e pelos 4 temas do corpus. Umas 20 a 30 normas
     diferentes devem ter pelo menos uma pergunta.
   - **No máximo 5 perguntas por documento.** Os documentos sem pergunta não são
     desperdício: eles atrapalham a busca de propósito, com textos parecidos, e
     é assim que o teste fica difícil o bastante.
   - Os `id`s seguem em sequência: `p006`, `p007`, e assim por diante.

### Como abrir o PR

São os mesmos passos da seção 5 do [guia do corpus](../corpus/README.md), com
três diferenças:

- o nome da branch: `git switch -c avaliacao/piloto`
- o arquivo que você edita: `eval/perguntas.csv`
- o commit: `git add eval` e uma mensagem começando com `feat(avaliacao):`

### Como saber se ficou certo

O check do PR confere duas coisas em cada linha:

- se o `doc_id` existe no corpus;
- se o trecho existe **de verdade** dentro do documento, letra por letra, ignorando
  só os espaços e as quebras de linha.

Se o check ficar vermelho, a mensagem diz qual pergunta e qual é o problema. O
caso mais comum é um trecho com uma letra diferente do documento, ou com um
pedaço do cabeçalho de página que veio junto na cópia (seção 3).

O check **não** confere se a pergunta é boa. Isso é a revisão do Felipe, e é
para isso que serve o piloto.
