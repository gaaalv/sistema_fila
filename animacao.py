"""Animação da fila (opção B do enunciado) com sprites, em tkinter.

Reproduz a linha do tempo de eventos gerada por simulacao.simular().
Não calcula nada da simulação: só desenha.

Convenções:
- Coordenadas de layout em pixels do cenário ORIGINAL (237x150) e depois
  multiplicadas por ESCALA.
- Tempo simulado em MINUTOS. Velocidade 1x = tempo real (1 min simulado = 60 s).
- Se um sprite não existir, é desenhado um bonequinho simples no lugar.
"""
import os
import tkinter as tk

from PIL import Image, ImageDraw, ImageOps, ImageTk

import hud

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites")

ESCALA = 3                 # cenário 237x150 -> 711x450
ESCALA_CLIENTE = 0.75 * ESCALA   # sprite 20x24 -> 45x54 (mesma altura visual da Joy)
ESCALA_JOY = 1.0                 # joy.png (45x62) fica do tamanho dos clientes
N_SKINS = 8

# --- Layout (em pixels do cenário original) ---
JOY_POS = (121, 55)        # pés da Joy: atrás do balcão, entre a máquina e o telefone
# Região do balcão desenhada POR CIMA da Joy (esconde a parte de baixo do corpo)
BALCAO_FRENTE = (82, 48, 148, 66)
# 6 pokébolas na abertura da máquina de cura (2 colunas x 3 linhas).
# Tudo em PIXELS INTEIROS da tela (meio pixel faz o Tk arredondar cada bola
# diferente e a grade sai torta). Centro da abertura: (296, 111) com ESCALA=3.
_TIPOS = [["poke", "great"], ["ultra", "poke"], ["great", "ultra"]]
BOLA_PX = 14                        # lado de cada bola na tela (sprite original: 14)
BOLAS_CENTRO = (round(98.67 * ESCALA), round(37 * ESCALA) - 4)
BOLAS_COL = 8                       # distância horizontal do centro (px)
BOLAS_LINHA = 16                    # distância vertical entre linhas (px)
BOLAS_POS = [(BOLAS_CENTRO[0] + (-BOLAS_COL if c == 0 else BOLAS_COL),
              BOLAS_CENTRO[1] + (r - 1) * BOLAS_LINHA, _TIPOS[r][c])
             for r in range(3) for c in range(2)]
ESCALA_BOLA = BOLA_PX / 14.0
CICLO_BRILHO = [0, 1, 2, 3, 2, 1]   # índice dos frames pokebola_<tipo>_N
ATRASO_BOLA = 0.12                  # s entre uma bola e a seguinte (efeito de onda)
VEL_BRILHO = 8.0                    # quadros de brilho por segundo
PONTO_ATENDIMENTO = (115, 77)   # onde o cliente fica sendo atendido
ESPACO_FILA = 10           # distância vertical entre pessoas da fila
MAX_VISIVEIS = 6           # pessoas esperando desenhadas; o resto vira "+N"
PORTA = (115, 142)         # tapete de entrada
ENTRADA = (115, 156)       # onde o cliente aparece (embaixo da porta, atrás do painel)
# Caminho de saída do cliente: sai do balcão pela lateral (não cruza a fila) e
# desce até a porta, tapete e rua.
ROTA_SAIDA = [(134, 78), (134, 138), (115, 146), (115, 156)]
# Integrantes da equipe: NPCs parados no canto superior direito (piso abaixo do
# terminal e do mapa). Cada item: (nome, (x, y dos pés) em unidades do cenário).
# Os quadros ficam em sprites/equipe/<nome>_<quadro>.png (gerar_sprites_equipe.py)
EQUIPE = [("gabriel", (172, 58)), ("lara", (190, 58)), ("maria", (208, 58))]
# Encerramento: depois do fim do tempo simulado a fila é esvaziada rápido e,
# quando o último cliente sai, a equipe vai embora pela porta.
VEL_ENCERRAMENTO = 600     # velocidade mínima (x) enquanto esvazia a fila
TEMPO_MAX_ENCERRAMENTO_S = 40   # se a fila for enorme, corta e segue para a saída
ATRASO_SAIDA_EQUIPE_S = 0.9     # s entre um integrante e o seguinte saindo
MIN_ATENDIMENTO_S = 4.0    # tempo mínimo (s reais, em 1x) que o cliente fica com a Joy
VEL_ANDAR = 16             # unidades do cenário por segundo (tempo real)
FPS_MS = 33
HUD_ALTURA = 108           # altura (px da tela) do painel de dados abaixo da cena


def _p(ponto):
    """Converte ponto do cenário original para pixels do canvas."""
    return ponto[0] * ESCALA, ponto[1] * ESCALA


def _carregar(nome, escala, fallback=None, espelhar=False):
    """Carrega PNG ampliado sem borrar; usa `fallback` (PIL.Image) se faltar."""
    caminho = os.path.join(PASTA, nome)
    if os.path.exists(caminho):
        img = Image.open(caminho).convert("RGBA")
    elif fallback is not None:
        img = fallback.copy()
    else:
        return None
    if espelhar:
        img = ImageOps.mirror(img)
    novo = (max(1, round(img.width * escala)), max(1, round(img.height * escala)))
    return img.resize(novo, Image.NEAREST)


def _boneco(cor, w=20, h=24):
    """Fallback desenhado: cabeça + corpo coloridos."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((5, 2, 15, 12), fill=cor, outline=(40, 40, 40, 255))
    d.rectangle((6, 12, 14, 21), fill=cor, outline=(40, 40, 40, 255))
    return img


_CORES = [(200, 80, 80, 255), (80, 120, 200, 255), (90, 170, 90, 255),
          (200, 160, 60, 255), (160, 90, 180, 255), (70, 170, 170, 255),
          (190, 110, 60, 255), (120, 120, 120, 255)]


class _Cliente:
    def __init__(self, cid):
        self.id = cid
        self.skin = cid % N_SKINS + 1
        self.x, self.y = _p(ENTRADA)
        self.alvo = _p(PORTA)
        self.rota = []              # pontos de saída (pixels) ainda por andar
        self.estado = "esperando"   # esperando | atendido | saindo
        self.dir = "costas"
        self.passo = 0.0
        self.indice = 0             # posição na fila (0 = primeiro esperando)
        self.inicio_sim = False     # o motor já começou o atendimento dele
        self.fim_sim = False        # o motor já terminou o atendimento dele
        self.no_balcao = False      # chegou fisicamente ao balcão
        self.t_balcao = 0.0         # s reais diante da Joy


class _Membro:
    """Integrante da equipe: parado no canto até a hora de sair pela porta."""

    def __init__(self, nome, pos):
        self.nome = nome
        self.dir = "frente"         # olhando para quem entra
        self.x, self.y = _p(pos)
        # desce até o piso livre abaixo do balcão, anda até o corredor x=135 (longe
        # do banco e do espelho do canto) e desce até a porta
        self.rota = [_p((pos[0], 72)), _p((135, 72)), _p((135, 138)),
                     _p((PORTA[0], 146)), _p(ROTA_SAIDA[-1])]
        self.andando = False
        self.passo = 0.0
        self.saiu = False


class CenaFila(tk.Canvas):
    """Canvas que anima a fila a partir de um Resultado do motor."""

    def __init__(self, master, **kw):
        w, h = 237 * ESCALA, 150 * ESCALA
        self._cena_h = h
        super().__init__(master, width=w, height=h + HUD_ALTURA,
                         highlightthickness=0, bg="#206860", **kw)
        self._carregar_imagens(w, h)
        self.on_tick = None     # callback(dict) a cada quadro
        self.on_fim = None      # callback() ao terminar a simulação
        self.velocidade = 60.0  # 60x: 1 min simulado por segundo real
        self._eventos = []
        self._duracao = 0.0
        self.reset()

    # ---------- imagens ----------
    def _carregar_imagens(self, w, h):
        self._fundo = _carregar("cenario_pokecenter.png", ESCALA,
                                Image.new("RGBA", (237, 150), (245, 235, 190, 255)))
        self._fundo_tk = ImageTk.PhotoImage(self._fundo)
        fb_joy = _boneco((240, 150, 170, 255), 22, 30)
        self._joy = ImageTk.PhotoImage(_carregar("joy.png", ESCALA_JOY, fb_joy))
        self._joy_oc = ImageTk.PhotoImage(
            _carregar("joy_ocupada.png", ESCALA_JOY, fb_joy))
        fb_bola = _boneco((230, 60, 60, 255), 14, 14)
        self._bolas = {t: [ImageTk.PhotoImage(_carregar(f"pokebola_{t}_{k}.png",
                                                        ESCALA_BOLA, fb_bola))
                           for k in range(4)]
                       for t in ("poke", "great", "ultra")}
        # parte do balcão que passa na frente da Joy
        x0, y0, x1, y1 = (v * ESCALA for v in BALCAO_FRENTE)
        self._balcao_tk = ImageTk.PhotoImage(self._fundo.crop((x0, y0, x1, y1)))
        self._balcao_xy = (x0, y0)
        self._equipe = list(EQUIPE)
        # painel de dados (estilo menu do Pokémon) e fonte
        self._painel_tk = ImageTk.PhotoImage(hud.painel(w, HUD_ALTURA, ESCALA))
        self._fonte = hud.FontePokemon(16)
        self._cache = {}

    def _sprite_membro(self, nome, direcao, frame):
        """Quadro do integrante da equipe. Se os quadros gerados não existirem,
        usa o sprite parado original (sprites/<nome>.png)."""
        chave = ("equipe", nome, direcao, frame)
        if chave not in self._cache:
            base = "esquerda" if direcao == "direita" else direcao
            sufixo = "" if frame == 0 else ("_a" if frame == 1 else "_b")
            arq = os.path.join("equipe", f"{nome}_{base}{sufixo}.png")
            fb = None
            orig = os.path.join(PASTA, f"{nome}.png")
            if os.path.exists(orig):
                im = Image.open(orig).convert("RGBA")
                im = im.crop(im.getchannel("A").getbbox())
                fb = Image.new("RGBA", (20, 24), (0, 0, 0, 0))
                fb.alpha_composite(im, ((20 - im.width) // 2, 24 - im.height))
            self._cache[chave] = ImageTk.PhotoImage(
                _carregar(arq, ESCALA_CLIENTE, fb or _boneco((120, 120, 120, 255)),
                          espelhar=(direcao == "direita")))
        return self._cache[chave]

    def _sprite_cliente(self, skin, direcao, frame):
        """direcao: frente|costas|esquerda|direita ; frame: 0 parado, 1/2 andando."""
        chave = (skin, direcao, frame)
        if chave not in self._cache:
            base = "esquerda" if direcao == "direita" else direcao
            sufixo = "" if frame == 0 else ("_a" if frame == 1 else "_b")
            nome = os.path.join("clientes", f"cliente_{skin}_{base}{sufixo}.png")
            img = _carregar(nome, ESCALA_CLIENTE,
                            _boneco(_CORES[(skin - 1) % len(_CORES)]),
                            espelhar=(direcao == "direita"))
            self._cache[chave] = ImageTk.PhotoImage(img)
        return self._cache[chave]

    # ---------- controle ----------
    def set_resultado(self, resultado):
        self._eventos = resultado.eventos
        self._duracao = resultado.duracao
        self.reset()

    def reset(self):
        self._rodando = False
        self._t = 0.0
        self._i = 0
        self._clientes = {}
        self._fila = []          # ids esperando, em ordem FIFO
        self._balcao = None         # id de quem está no balcão (controle visual)
        self._atendidos = 0
        self._ultimo_ms = None
        self._relogio_joy = 0.0
        self._joy_ocupada = False
        self._fila_max = 0
        self._fase = "rodando"      # rodando -> encerrando -> equipe -> fim
        self._t_encerramento = 0.0
        self._t_equipe = 0.0
        self._membros = [_Membro(nome, pos) for nome, pos in self._equipe]
        self._desenhar()

    def play(self):
        if self._rodando or not self._eventos:
            return
        if self._fase == "fim":
            self.reset()
        self._rodando = True
        self._ultimo_ms = None
        self._loop()

    def pause(self):
        self._rodando = False

    @property
    def rodando(self):
        return self._rodando

    @property
    def tempo(self):
        return self._t

    # ---------- laço principal ----------
    def _loop(self):
        if not self._rodando:
            return
        import time
        agora = time.perf_counter()
        dt_real = 0.0 if self._ultimo_ms is None else agora - self._ultimo_ms
        self._ultimo_ms = agora
        self._avancar(dt_real)
        self._desenhar()
        if self._fase == "fim":
            self._rodando = False
            if self.on_fim:
                self.on_fim()
            return
        self.after(FPS_MS, self._loop)

    @property
    def _vel(self):
        """Velocidade em uso: no encerramento nunca fica abaixo de VEL_ENCERRAMENTO."""
        if self._fase == "rodando":
            return self.velocidade
        return max(self.velocidade, VEL_ENCERRAMENTO)

    def _avancar(self, dt_real):
        """Avança o relógio simulado e aplica os eventos já ocorridos."""
        if self._fase in ("rodando", "encerrando"):
            self._t += dt_real * self._vel / 60.0
        ev = self._eventos
        while self._i < len(ev) and ev[self._i].tempo <= self._t:
            self._aplicar(ev[self._i])
            self._i += 1
        self._gerir_balcao(dt_real)
        self._fila_max = max(self._fila_max, len(self._fila))
        # reindexa a fila e define os alvos de cada cliente
        for k, cid in enumerate(self._fila):
            c = self._clientes[cid]
            c.indice = k
            if k < MAX_VISIVEIS:
                c.alvo = _p((PONTO_ATENDIMENTO[0],
                             PONTO_ATENDIMENTO[1] + ESPACO_FILA * (k + 1)))
            else:
                c.alvo = _p(PORTA)
        self._mover(dt_real)
        self._relogio_joy += dt_real
        self._gerir_fase(dt_real)

    def _gerir_fase(self, dt_real):
        """rodando -> encerrando (acabou o tempo) -> equipe (sem clientes) -> fim."""
        if self._fase == "rodando" and self._t >= self._duracao:
            self._fase = "encerrando"
        elif self._fase == "encerrando":
            self._t_encerramento += dt_real
            vazio = self._i >= len(self._eventos) and not self._clientes
            if self._t_encerramento > TEMPO_MAX_ENCERRAMENTO_S:
                # fila enorme (ex.: sistema instável): tira todo mundo de uma vez
                self._clientes.clear()
                self._fila.clear()
                self._balcao = None
                self._i = len(self._eventos)
                vazio = True
            if vazio:
                self._fase = "equipe"
                if not self._membros:
                    self._fase = "fim"
        elif self._fase == "equipe":
            self._mover_equipe(dt_real)

    def _mover_equipe(self, dt_real):
        self._t_equipe += dt_real
        passo = VEL_ANDAR * ESCALA * dt_real
        for i, m in enumerate(self._membros):
            m.andando = False
            if m.saiu or self._t_equipe < i * ATRASO_SAIDA_EQUIPE_S:
                continue
            alvo = m.rota[0]
            dx, dy = alvo[0] - m.x, alvo[1] - m.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= 0.5:
                m.rota.pop(0)
                if not m.rota:
                    m.saiu = True
                continue
            mv = min(passo, dist)
            m.x += dx / dist * mv
            m.y += dy / dist * mv
            m.passo += mv
            m.andando = True
            m.dir = (("direita" if dx > 0 else "esquerda") if abs(dx) > abs(dy)
                     else ("frente" if dy > 0 else "costas"))
        if all(m.saiu for m in self._membros):
            self._fase = "fim"

    def _aplicar(self, e):
        """Eventos do motor só marcam o que já aconteceu na simulação; quem
        manda no balcão visual é _gerir_balcao (evita cliente que vai embora
        sem nem ter chegado à Joy quando o atendimento sorteado é curto)."""
        if e.tipo == "chegada":
            self._clientes[e.cliente] = _Cliente(e.cliente)
            self._fila.append(e.cliente)
        elif e.tipo == "inicio":
            self._clientes[e.cliente].inicio_sim = True
        else:  # fim
            self._clientes[e.cliente].fim_sim = True

    def _min_atendimento(self):
        """Tempo mínimo diante da Joy, menor quando a animação está acelerada."""
        return MIN_ATENDIMENTO_S / max(1.0, self._vel / 15.0)

    def _gerir_balcao(self, dt_real):
        # libera o balcão: chegou, ficou o mínimo visual e o motor já terminou
        if self._balcao is not None:
            c = self._clientes[self._balcao]
            if c.no_balcao:
                c.t_balcao += dt_real
                if c.fim_sim and c.t_balcao >= self._min_atendimento():
                    c.estado = "saindo"
                    c.rota = [_p(pt) for pt in ROTA_SAIDA]
                    c.alvo = c.rota.pop(0)
                    self._balcao = None
                    self._atendidos += 1
        # chama o próximo da fila se o motor já começou o atendimento dele
        if self._balcao is None and self._fila:
            c = self._clientes[self._fila[0]]
            if c.inicio_sim:
                self._fila.pop(0)
                c.estado = "atendido"
                c.alvo = _p(PONTO_ATENDIMENTO)
                self._balcao = c.id

    def _mover(self, dt_real):
        # em velocidades altas os clientes andam mais rápido para acompanhar
        passo_max = VEL_ANDAR * ESCALA * dt_real * max(1.0, self._vel / 15.0)
        remover = []
        for cid, c in self._clientes.items():
            dx, dy = c.alvo[0] - c.x, c.alvo[1] - c.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist > 0.5:
                mv = min(passo_max, dist)
                c.x += dx / dist * mv
                c.y += dy / dist * mv
                c.passo += mv
                c.dir = (("direita" if dx > 0 else "esquerda")
                         if abs(dx) > abs(dy) else
                         ("frente" if dy > 0 else "costas"))
            else:
                c.passo = 0.0
                if c.estado == "atendido":
                    c.no_balcao = True     # chegou diante da Joy
                if c.estado != "saindo":
                    c.dir = "costas"   # olhando para o balcão
            if c.estado == "saindo" and dist <= 0.5:
                if c.rota:
                    c.alvo = c.rota.pop(0)     # próximo ponto do caminho até a porta
                else:
                    remover.append(cid)
        for cid in remover:
            del self._clientes[cid]

    # ---------- desenho ----------
    def _desenhar(self):
        self.delete("all")
        self.create_image(0, 0, image=self._fundo_tk, anchor="nw")
        # Joy: alterna entre dois frames enquanto atende
        ocupada = False
        if self._balcao in self._clientes:
            # Joy só começa a "curar" quando o cliente chegou ao balcão
            ocupada = self._clientes[self._balcao].no_balcao
        joy = self._joy_oc if (ocupada and int(self._relogio_joy * 2) % 2) else self._joy
        jx, jy = _p(JOY_POS)
        self.create_image(jx, jy, image=joy, anchor="s")
        # balcão na frente da Joy
        self.create_image(*self._balcao_xy, image=self._balcao_tk, anchor="nw")
        # equipe (depois do balcão: quem passa por ali não pode ficar cortado)
        for m in self._membros:
            if m.saiu:
                continue
            frame = 1 + int(m.passo / (3 * ESCALA)) % 2 if m.andando else 0
            self.create_image(m.x, m.y, anchor="s",
                              image=self._sprite_membro(m.nome, m.dir, frame))
        # pokébolas brilhando na máquina enquanto ela atende (curando)
        if ocupada:
            for k, (bx, by, tipo) in enumerate(BOLAS_POS):
                fase = (self._relogio_joy - k * ATRASO_BOLA) * VEL_BRILHO
                frame = CICLO_BRILHO[int(fase) % len(CICLO_BRILHO)]
                self.create_image(bx, by, image=self._bolas[tipo][frame])
        # clientes ordenados por y (quem está mais embaixo fica na frente)
        visiveis = [c for c in self._clientes.values()
                    if not (c.estado == "esperando" and c.indice >= MAX_VISIVEIS)]
        for c in sorted(visiveis, key=lambda c: c.y):
            frame = 0
            if c.passo > 0:
                frame = 1 + int(c.passo / (3 * ESCALA)) % 2
            self.create_image(c.x, c.y, anchor="s",
                              image=self._sprite_cliente(c.skin, c.dir, frame))
        extra = max(0, len(self._fila) - MAX_VISIVEIS)
        if extra:
            x, y = _p((PONTO_ATENDIMENTO[0] + 16,
                       PONTO_ATENDIMENTO[1] + ESPACO_FILA * MAX_VISIVEIS))
            self._fonte.desenhar(self, x, y - 8, f"+{extra} NA FILA")
        self._joy_ocupada = ocupada
        self._hud()
        if self.on_tick:
            self.on_tick({"t": self._t, "fila": len(self._fila),
                          "ocupado": ocupada, "atendidos": self._atendidos})

    def _hud(self):
        """Painel de dados abaixo da cena (janela de menu + fonte Pokémon GB)."""
        y0 = self._cena_h
        self.create_image(0, y0, image=self._painel_tk, anchor="nw")
        t = self._t
        tempo = f"{int(t // 60):02d}:{int(t % 60):02d}:{int((t * 60) % 60):02d}"
        vel = ("MAX" if self.velocidade >= 20000
               else f"{self.velocidade:g}X")
        esq = (("TEMPO", tempo), ("NA FILA", str(len(self._fila))),
               ("ATENDIDOS", str(self._atendidos)))
        dir_ = (("JOY", "OCUPADA" if self._joy_ocupada else "LIVRE"),
                ("FILA MAX", str(self._fila_max)),
                ("VELOCIDADE", vel))
        f = self._fonte
        # (x do rótulo, x da borda direita onde o valor termina)
        for col, borda, linhas in ((24, 340, esq), (380, 690, dir_)):
            for i, (rotulo, valor) in enumerate(linhas):
                y = y0 + 16 + i * 26
                f.desenhar(self, col, y, rotulo)
                f.desenhar(self, borda - f.largura(valor), y, valor)
