# 0001. Tarefas com uv e poethepoet, não Makefile

- Status: Aceito
- Data: 2026-11-11
- Fase: 0

## Contexto

O plano original previa um Makefile. O desenvolvimento acontece em Windows
nativo, sem WSL, e o CI roda em Linux. O Emerson também usa Windows e está
começando a programar, então cada ferramenta a mais que ele precisa instalar é
um ponto de falha antes do primeiro PR.

É preciso um comando único que rode lint, formatação e testes de forma idêntica
nos três lugares: na máquina do Felipe, na do Emerson e no CI.

## Decisão

- **uv** gerencia a versão do Python, o venv e as dependências, com `uv.lock`
  versionado e `uv sync --locked` no CI.
- **poethepoet** define as tarefas no `pyproject.toml`, como dependência dev. O
  comando canônico é `uv run poe check`.

## Alternativas descartadas

- **Makefile.** O Windows não tem `make`. Mesmo instalado (via winget), o make
  executa as receitas no shell que encontrar no PATH, sh ou cmd, e o
  comportamento muda conforme a máquina. A frase "funciona no meu computador" é
  exatamente o que o CI existe para eliminar.
- **just.** Funciona bem e é multiplataforma, mas é mais um binário a instalar em
  cada máquina e no CI. No Windows, ainda exige configurar `windows-shell`. Não
  traz nada que o poe não traga para tarefas deste tamanho.
- **Scripts `.ps1`.** Não rodam no runner Linux sem instalar o `pwsh`, e
  duplicariam a lógica numa segunda linguagem.
- **Só `uv run ruff ...` e `uv run pytest` no README.** Sem um alvo único, CI e
  local divergem com o tempo.

## Consequências

- Nenhuma instalação além do uv. O poe vem com `uv sync`.
- A sequência `check` para na primeira falha e propaga o código de saída. Isso
  foi validado quebrando um teste de propósito (Fase 0).
- Tarefas complexas, com muita lógica de shell, ficariam desconfortáveis no poe.
  Se aparecerem, a lógica vai para um script Python chamado pela tarefa, e não
  para dentro do `pyproject.toml`.
