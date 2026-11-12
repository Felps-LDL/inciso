# Corpus

Esta pasta guarda os documentos que a busca vai consultar: resoluções e
circulares de órgãos que regulam o mercado financeiro, em PDF. Também guarda a
planilha `controle.csv`, que diz o que é cada arquivo e de onde ele veio.

Este guia é para o Emerson, mas serve a qualquer pessoa que for adicionar
documentos.

---

## 1. O que estamos montando, e por quê

O alvo é ter **cerca de 60 documentos, divididos em 4 temas** (uns 15 por tema).

Por que tantos documentos sobre o mesmo assunto? O projeto quer medir se a busca
encontra o trecho certo. Se cada documento falasse de uma coisa diferente, a
busca acertaria sempre, por eliminação, e não aprenderíamos nada. Quando há
várias normas parecidas, todas falando de "cliente", "fundo" e "comunicação", a
busca precisa se esforçar para escolher o trecho certo. É nesse esforço que dá
para comparar uma estratégia com outra.

Por isso, nos temas abaixo, **documentos parecidos entre si são bem-vindos**.
Normas do Bacen e da CVM sobre o mesmo assunto, então, são ótimas.

### Os 4 temas

Na coluna `tema` da planilha, use exatamente o nome entre crases.

| Tema | Valor na coluna `tema` | Documentos-âncora (comece por eles) |
|---|---|---|
| Fundos de investimento | `fundos` | Resolução CVM 175 e os seus anexos |
| Prevenção à lavagem de dinheiro (PLD/FT) | `pld-ft` | Resolução CVM 50; Circular Bacen 3.978 |
| Ofertas públicas e emissores | `ofertas` | Resoluções CVM 160 e 80 |
| Instrumentos financeiros e risco em bancos | `instrumentos-financeiros` | Resolução CMN 4.966 |

Os números dos documentos-âncora foram anotados de memória. Confira no site do
órgão se o número e o assunto batem. Se não baterem, avise no PR.

Para achar documentos relacionados, leia o começo de cada âncora: costuma haver
menções a outras normas ("conforme a Resolução X") e uma lista do que ela revoga
ou altera.

### Onde baixar

- **CVM**: no site da CVM, seção *Legislação*, depois *Resoluções*.
- **Bacen e CMN**: no site do Banco Central, ferramenta *Busca de normas*. As
  resoluções do CMN também ficam ali.

**Baixe a versão vigente.** Muitas normas foram alteradas depois de publicadas.
Quando o site oferecer uma versão "consolidada" ou "compilada" (o texto com todas
as alterações já incluídas), baixe essa. Se não houver, baixe a versão que o site
oferecer e anote no PR que não havia consolidada.

---

## 2. Como nomear o arquivo

```
orgao-tipo-numero-ano.pdf
```

Tudo em **minúsculas**, **sem acento**, **sem espaço** e separado por **hífen**.

| Documento | Nome do arquivo |
|---|---|
| Resolução CVM nº 175, de 2022 | `cvm-resolucao-175-2022.pdf` |
| Circular Bacen nº 3.978, de 2020 | `bacen-circular-3978-2020.pdf` |
| Resolução CMN nº 4.966, de 2021 | `cmn-resolucao-4966-2021.pdf` |

Valores aceitos:

- `orgao`: `cvm`, `bacen` ou `cmn`. O CMN é um órgão separado do Bacen, mesmo com
  as normas no site do Bacen.
- `tipo`: `resolucao`, `circular`, `instrucao` ou `cartacircular`.
- `numero`: só os algarismos, **sem ponto**. Por exemplo, 3.978 vira `3978`.
- `ano`: o ano da publicação, com quatro algarismos.

Por que tanto cuidado com o nome? Ele vira o identificador do documento no
projeto inteiro. Mais tarde, as perguntas de avaliação vão apontar para ele, e
mudar um nome depois quebra essas referências.

---

## 3. A planilha `controle.csv`

Cada documento tem **uma linha** na planilha. As colunas são:

| Coluna | O que vai nela | Exemplo |
|---|---|---|
| `arquivo` | o nome do arquivo, igual ao da pasta | `cvm-resolucao-175-2022.pdf` |
| `orgao` | igual ao início do nome | `cvm` |
| `tipo` | igual ao nome | `resolucao` |
| `numero` | igual ao nome, sem ponto | `175` |
| `data_publicacao` | a data em que a norma foi publicada, no formato AAAA-MM-DD | `2022-12-23` |
| `tema` | um dos 4 temas da seção 1 | `fundos` |
| `assunto` | uma frase sua dizendo do que a norma trata | `Regras gerais dos fundos de investimento` |
| `url_origem` | o link da página de onde você baixou | `https://...` |
| `data_acesso` | o dia em que você baixou, no formato AAAA-MM-DD | `2026-11-12` |

A linha completa do exemplo fica assim:

```
cvm-resolucao-175-2022.pdf,cvm,resolucao,175,2022-12-23,fundos,Regras gerais dos fundos de investimento,https://...,2026-11-12
```

**Edite a planilha no VS Code, não no Excel.** O Excel em português costuma
juntar todas as colunas numa só e estragar os acentos ao salvar. No VS Code,
instale a extensão *Rainbow CSV*, que pinta cada coluna de uma cor. Fica mais
fácil ver quando uma vírgula está fora do lugar.

**Cuidado com vírgula dentro do texto.** A vírgula separa as colunas. Se o
assunto tiver uma vírgula, coloque o texto entre aspas:

```
...,fundos,"Fundos de investimento, regras gerais",https://...
```

---

## 4. Antes do primeiro PR: preparar o computador (uma vez só)

Os comandos abaixo rodam no **PowerShell**. No VS Code, abra o terminal pelo menu
*Terminal → New Terminal*.

**a) Instalar o Git**

```
winget install --id Git.Git -e --source winget
```

O `winget` é o instalador de programas do Windows. Esse comando baixa e instala o
Git, o programa que guarda o histórico de mudanças do projeto.

Depois de instalar, **feche o VS Code inteiro e abra de novo**. O terminal só
passa a enxergar programas recém-instalados quando o VS Code reinicia. Para
conferir se deu certo:

```
git --version
```

Se aparecer algo como `git version 2.xx`, funcionou.

**b) Dizer ao Git quem você é**

```
git config --global user.name "Seu Nome"
git config --global user.email "o-email-da-sua-conta-do-github@exemplo.com"
```

Cada mudança que você registrar vai levar esse nome e esse e-mail. Use o mesmo
e-mail da sua conta do GitHub, assim o GitHub mostra as mudanças como suas.

**c) Aceitar o convite do repositório**

O Felipe te adiciona como colaborador e o GitHub manda um e-mail de convite.
Aceite antes de seguir.

---

## 5. O primeiro PR, passo a passo

Um *PR* (pull request) é um pedido: "revise as minhas mudanças e, se estiverem
boas, junte ao projeto principal". O objetivo deste primeiro PR não é o documento
em si. É você passar uma vez pelo ciclo inteiro com algo que não quebra nada.

**1. Baixar o projeto para o seu computador** (uma vez só)

```
cd ~\Documents
git clone https://github.com/<usuario-do-felipe>/inciso.git
cd inciso
```

- `cd` muda de pasta.
- `git clone` copia o repositório do GitHub para uma pasta nova chamada `inciso`.
- Na primeira vez que o Git falar com o GitHub, ele pode abrir o navegador para
  você entrar na sua conta.

**2. Criar uma branch**

```
git switch -c corpus/primeiro-documento
```

Uma *branch* é uma linha de trabalho separada. Você mexe à vontade nela sem
afetar a versão principal (a `main`). O `-c` significa "crie uma nova".

**3. Colocar o documento na pasta**

Copie o PDF para a pasta `corpus\`, já com o nome no padrão da seção 2.

**4. Adicionar a linha na planilha**

Abra `corpus\controle.csv` no VS Code, acrescente a linha do documento no final e
salve.

**5. Conferir o que mudou**

```
git status
```

Esse comando lista o que mudou desde o último registro. Devem aparecer duas
coisas: o PDF novo e o `controle.csv` modificado. Se aparecer mais alguma coisa,
pare e descubra o que é antes de seguir.

**6. Registrar a mudança (commit)**

```
git add corpus
git commit -m "feat(corpus): <descreva aqui, com as suas palavras>"
```

- `git add corpus` separa as mudanças da pasta `corpus` para entrarem no
  registro.
- `git commit` cria o registro. A mensagem é sua: diga o que entrou. O começo
  `feat(corpus):` é a convenção do projeto. Quer dizer "algo novo, na parte do
  corpus".

**7. Enviar para o GitHub**

```
git push -u origin corpus/primeiro-documento
```

Isso manda a sua branch para o GitHub. O `-u` faz o Git lembrar para onde enviar,
e nas próximas vezes `git push` sozinho já funciona. A resposta do comando traz um
link começando com `https://github.com/.../pull/new/...`.

**8. Abrir o PR**

Abra esse link no navegador. Preencha o título e o checklist do modelo de PR e
clique em *Create pull request*.

**9. Esperar o CI e a revisão**

Em um ou dois minutos, aparece no PR o resultado de uma verificação automática
chamada **check**:

- ✅ **Verde**: a planilha e os arquivos estão consistentes. Agora é esperar a
  revisão do Felipe.
- ❌ **Vermelho**: alguma coisa não bate. Veja a seção 6.

Se o Felipe pedir mudanças, você as faz na mesma branch, repete os passos 5 a 7
(`git push` sem o `-u`) e o PR se atualiza sozinho.

**10. Depois do merge**

Quando o PR for aceito, volte para a `main` e traga a versão nova:

```
git switch main
git pull
```

Para o próximo documento, comece de novo no passo 2, com outro nome de branch.

---

## 6. Quando o check fica vermelho

Vermelho não quer dizer que você quebrou o projeto: a `main` está protegida e só
recebe PR com check verde. Quer dizer que a verificação encontrou algo para
corrigir, e ela diz o quê.

1. No PR, ao lado do check vermelho, clique em **Details**.
2. Abra o passo **Lint, formato e testes**.
3. Procure as linhas que começam com `controle.csv, linha` ou `corpus/`. Elas
   dizem qual linha da planilha tem problema e qual é o problema. Por exemplo:

   ```
   controle.csv, linha 3: a coluna numero diz '3.978', mas o nome do arquivo diz '3978'
   ```

   A linha 1 é o cabeçalho, então a linha 3 é o segundo documento.
4. Corrija, faça um novo commit e dê `git push`. O check roda de novo sozinho.

Se a mensagem não fizer sentido, copie o trecho no PR e pergunte. Uma mensagem
confusa é um defeito da verificação, não seu.

---

## 7. O piloto: 5 documentos antes dos outros 55

O trabalho vai em três etapas:

1. **Primeiro PR: 1 documento.** É o passo a passo da seção 5.
2. **Até completar 5 documentos**, de pelo menos 2 temas e dos dois órgãos (CVM e
   Bacen/CMN). Podem ir num PR só ou em vários. **Depois do quinto, pare e espere
   a revisão do Felipe.** Ele vai conferir se a versão é a vigente, se o tema está
   certo e se o texto do PDF pode ser lido por programa. Se não puder, o formato
   do corpus muda, e é melhor descobrir isso com 5 documentos do que com 60.
3. **Só depois da aprovação, o resto**, em PRs de **até 10 documentos** cada,
   para a revisão caber numa sentada.

### A próxima etapa, para você já saber

Depois do corpus vem o **conjunto de avaliação**: perguntas que alguém faria
sobre essas normas, cada uma com o trecho exato que a responde. Ele segue a mesma
regra: **5 perguntas no piloto**, revisadas pelo Felipe, e só depois as outras. O
guia dessa etapa chega junto com ela.
