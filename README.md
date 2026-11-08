# Simulador de Fila com um Atendente — Pokémon Center

Atividade avaliativa de **Pesquisa Operacional** (Ciências da Computação, prof. Rafael Fiore).
Simula uma fila com **um único atendente** (a Enfermeira Joy), mostra a fila evoluindo em uma
animação com sprites, calcula estatísticas, repete a simulação várias vezes e compara com a teoria.

## Como rodar

### 1. Pré-requisitos
- **Python 3.9+** (desenvolvido em 3.14) com **tkinter** (já vem com o instalador oficial do Python no
  Windows/macOS; no Linux: `sudo apt install python3-tk`).
- Bibliotecas externas: **pillow** e **matplotlib** (listadas em `requirements.txt`).

### 2. Instalar as bibliotecas
Windows (duplo clique ou no terminal):

```bat
instalar.bat
```

Linux / macOS:

```sh
sh instalar.sh
```

Ou manualmente, em qualquer sistema:

```sh
pip install -r requirements.txt
```

(Opcional: crie um ambiente virtual antes — `python -m venv .venv` e ative-o.)

### 3. Executar

```sh
python main.py
```

Na janela: preencha **tempo médio de atendimento**, **chegadas por hora**, **horas simuladas**,
distribuição, replicações e seed e inicie. As abas mostram a animação, o gráfico da fila
no tempo, as replicações vs. teoria e a análise de carga (ρ → 100%).

Opções de linha de comando (todas opcionais):

| Opção | O que faz |
|---|---|
| `--teste` | Ambiente de teste da animação: 1x, atendimento 2 min, 24 clientes/h, 1 h, seed 7, inicia sozinho |
| `--media N` | Tempo médio de atendimento (min) |
| `--cheg N` | Chegadas por hora |
| `--horas N` | Tempo simulado (horas) |
| `--dist D` | `exponencial`, `normal` ou `triangular` |
| `--seed N` | Semente do gerador aleatório |
| `--vel N` | Velocidade: 1, 10, 60, 300, 1000 ou 20000 (máximo) |
| `--auto` | Inicia a simulação ao abrir |
| `--barra-nativa` | Usa a barra de título normal do Windows em vez da barra estilo Pokémon |

Exemplo do cenário de teste do enunciado (10 min, 5 clientes/h, 8 h):

```sh
python main.py --media 10 --cheg 5 --horas 8 --dist exponencial --seed 42 --vel 1000 --auto
```

## Estrutura do projeto

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | Ponto de entrada e argumentos de linha de comando |
| `distribuicoes.py` | Sorteio dos tempos (chegadas e atendimentos) e variância teórica |
| `simulacao.py` | Motor da simulação (sem interface) |
| `estatisticas.py` | Replicações, teoria (M/M/1 e M/G/1) e varredura de carga |
| `gui.py` | Interface tkinter + gráficos matplotlib em abas |
| `animacao.py` | Animação da fila com sprites (canvas do tkinter) |
| `hud.py`, `janela.py` | Visual estilo menu Pokémon: painel, fonte e barra de título própria |
| `gerar_sprites_equipe.py` | Script auxiliar que gera os sprites da equipe |
| `sprites/` | Imagens, fonte e créditos (`LEIAME.txt`) |

## Decisões de projeto e por quê

### Separar motor, estatística e interface
`simulacao.py` e `distribuicoes.py` não importam nada de interface. O enunciado pede "funções separadas
para a geração dos tempos, a simulação e a exibição", e isso também permite rodar a simulação
rapidamente (dezenas de replicações) sem abrir janela. A animação **não calcula nada**: apenas reproduz
a lista de eventos que o motor gerou, garantindo que o que se vê é exatamente o que é contabilizado.

### Unidade de tempo única: minutos
Chegadas são informadas por hora e atendimento em minutos. Tudo é convertido para **minutos** logo na
entrada (ex.: `taxa_por_min = chegadas_por_hora / 60`), evitando o erro de unidades que o enunciado
alerta.

### Chegadas: distribuição exponencial
O intervalo entre chegadas é sorteado com `expovariate`, o que equivale a chegadas de **Poisson**
(clientes independentes, sem memória). É a sugestão do enunciado e a hipótese padrão de filas M/M/1,
permitindo comparar com a teoria.

### Atendimento: três distribuições à escolha do usuário
O tempo de atendimento tem a média informada pelo usuário, mas varia por cliente:

- **Exponencial (padrão)** — desvio = média; é o modelo M/M/1, com solução teórica exata, usada para
  validar o simulador (no cenário 10 min / 5 por hora a teoria dá Wq ≈ 50 min e Lq ≈ 4,2).
- **Normal truncada** — desvio de 30% da média; valores ≤ 0 são descartados e re-sorteados (como sugere
  o enunciado). Representa um atendimento mais regular. Com 30% o truncamento é desprezível.
- **Triangular** — de 0,5× a 1,5× a média, com moda na média: atendimento limitado (sem tempos
  absurdos) e a média continua sendo a informada.

Oferecer as três permite **mostrar como a variabilidade do atendimento afeta a fila** (com a mesma média,
quanto maior a variância, maior a espera) e justifica a escolha padrão.

### Seed via `random.Random(seed)`
Cada simulação cria seu próprio gerador em vez de usar o global. Assim a seed é reproduzível e uma
execução não interfere na outra. Nas replicações usa-se `seed, seed+1, ...` — cada rodada é diferente,
mas o conjunto inteiro é reproduzível.

### Simulação por eventos discretos, FIFO
Com um só atendente FIFO, cada cliente começa em `max(chegada, instante em que o anterior termina)`.
É simples, correto e rápido. A linha do tempo de eventos (`chegada`, `inicio`, `fim`) é então ordenada,
com desempate **chegada → fim → início** no mesmo instante, e percorrida acumulando:

- **fila média** = área sob a curva "nº na fila × tempo" ÷ tempo total (média *no tempo*, não por evento);
- **ocupação** = tempo com atendente em serviço ÷ tempo total;
- **fila máxima** e **espera média** (média de `início − chegada`).

### Fim do tempo simulado
Chegadas só ocorrem até o fim do período; quem já está na fila é atendido até o fim, mas as métricas de
fila/ocupação são medidas em `[0, T]`. Assim não há clientes "cortados" no meio e as estatísticas cobrem
exatamente o tempo pedido. "Clientes atendidos" conta só quem terminou até `T`.

### Detecção de estabilidade (ρ ≥ 1)
`ρ = (chegadas/min) × tempo médio`. Se ρ ≥ 1, a interface mostra um aviso e pergunta se o usuário quer
simular mesmo assim — o enunciado exige detectar e avisar, mas simular a instabilidade também é
didático (fila crescendo sem parar), por isso não bloqueamos.

### Teoria: Pollaczek-Khinchine (M/G/1)
Para comparar com os resultados, `teoria()` usa a fórmula M/G/1: `Lq = λ²·E[S²] / (2(1−ρ))` e
`Wq = Lq/λ`, com `E[S²] = Var + média²`. Para exponencial isso reduz exatamente ao M/M/1. Usar M/G/1
permite comparar **as três distribuições** com a teoria, e não só a exponencial. Para isso
`variancia_atendimento()` dá a variância teórica de cada uma.

### Replicações com média ± desvio padrão
Uma única execução curta varia muito (o enunciado avisa). Por isso `replicar()` roda *n* vezes
(configurável na interface) e reporta média e desvio padrão de cada métrica; o gráfico compara essa
média com a teoria.

### Análise de carga (ρ → 100%)
`varredura_carga()` varia ρ de 0,1 a 0,95 ajustando a taxa de chegada e mede fila/espera contra a
teoria. Mostra o crescimento explosivo da fila perto de 100% (ponto extra do enunciado). Usa pelo menos
200 h simuladas por ponto para que o regime estável apareça.

### Interface em tkinter + matplotlib embutido
Ambos são permitidos pelo enunciado e o tkinter já acompanha o Python (menos dependências para instalar
no dia da apresentação). Os resultados ficam em **abas** (animação, fila no tempo, replicações/teoria,
carga) para o professor alterar parâmetros e ver tudo sem trocar de programa. Como a animação roda
em tempo real, há seletor de **velocidade** (1x até máximo), útil para o teste de 1 hora ao vivo.

### Animação com sprites (opção B do enunciado)
A fila é representada por "pessoinhas" que entram, esperam, são atendidas e saem, em um cenário de
Pokémon Center. Decisões:

- Cenário desenhado em resolução original e **ampliado por inteiro (3×, `NEAREST`)** para manter o
  visual pixelado nítido.
- No máximo **6 pessoas** desenhadas na fila; o resto aparece como "+N", para não poluir a tela.
- **Se um sprite faltar**, desenha-se um bonequinho simples (fallback) em vez de quebrar.
- **Encerramento**: ao acabar o tempo, a fila restante é esvaziada rapidamente (limite de 40 s reais)
  e a equipe sai pela porta, dando um fecho claro à simulação.
- Integrantes da equipe aparecem como NPCs no cenário (`gerar_sprites_equipe.py` gera as 9 poses de
  cada um reaproveitando o desenho dos clientes-modelo com as cores de cada integrante).

### HUD e barra de título no estilo Pokémon
`hud.py` gera o painel de listras **por código** (em vez de imagem fixa), então serve para qualquer
tamanho; a fonte *Pokemon GB* é desenhada via Pillow, com fonte reserva para caracteres que ela não
tem (%, acentos). `janela.py` troca a barra do Windows por uma barra temática (`overrideredirect`) e
trata as limitações disso (barra de tarefas, minimizar) via `ctypes`, dentro de `try/except` para não
quebrar em outros sistemas. Há `--barra-nativa` para desligar tudo caso dê problema no computador da
apresentação.

## Créditos dos assets
Veja `sprites/LEIAME.txt`: sprites de NPCs (Pokémon Emerald, Furs The Fox / Spriters Resource),
pokébolas (rip por redblueyellow), menu (RedZagoon), fonte *Pokemon GB* e sprites da Enfermeira Joy.
Uso estritamente acadêmico; Pokémon é marca da Nintendo/Game Freak/Creatures.
