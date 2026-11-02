"""HUD no estilo dos menus do Pokémon FireRed/LeafGreen.

- painel(): gera a janela azul-esverdeada de listras (mesmas cores da folha
  "Pokemon Menu"), com cantos arredondados, no tamanho que precisarmos.
- FontePokemon: desenha texto no canvas com a fonte "Pokemon GB.ttf".

A fonte não tem alguns caracteres (%, ã, õ, Ã, Ç, Ê, Õ, º). Para esses, o
código usa uma fonte reserva (%) ou a letra sem acento.
"""
import os
import unicodedata

from PIL import Image, ImageDraw, ImageFont, ImageTk

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites")
FONTE_TTF = os.path.join(PASTA, "PokemonGB.ttf")
SEM_GLIFO = set("%ÃÇÊÕãõº")

PAD = 3                     # folga no topo de cada glifo (px)
ESPESSURA = ((0, 0),)       # traço original da fonte (sem engrossar: bordas retas)

# cores medidas na folha "Pokemon Menu" (primeira janela)
LISTRAS = ((72, 168, 160), (56, 136, 136))
BORDA = (32, 104, 96)


def painel(largura, altura, px=3, raio=4.5):
    """Janela de listras com borda escura e cantos arredondados.
    `px` = tamanho de cada pixel original na tela (mesma escala do cenário)."""
    w, h = largura // px, altura // px
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pix = img.load()

    def dentro(x, y):
        cx = raio if x < raio else (w - 1 - raio if x > w - 1 - raio else x)
        cy = raio if y < raio else (h - 1 - raio if y > h - 1 - raio else y)
        return (x - cx) ** 2 + (y - cy) ** 2 <= raio ** 2

    for y in range(h):
        for x in range(w):
            if not dentro(x, y):
                continue
            borda = any(not (0 <= x + dx < w and 0 <= y + dy < h
                             and dentro(x + dx, y + dy))
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            pix[x, y] = (BORDA if borda else LISTRAS[y % 2]) + (255,)
    return img.resize((w * px, h * px), Image.NEAREST)


class FontePokemon:
    """Texto pixelado com sombra, desenhado glifo a glifo (com cache)."""

    def __init__(self, tamanho=16, cor=(255, 255, 255), sombra=BORDA):
        self.tamanho, self.cor, self.sombra = tamanho, cor, sombra
        try:
            self._fonte = ImageFont.truetype(FONTE_TTF, tamanho)
        except OSError:
            self._fonte = ImageFont.load_default()
        try:
            self._reserva = ImageFont.truetype("arialbd.ttf", tamanho - 2)
        except OSError:
            self._reserva = self._fonte
        self._cache = {}

    def _glifo(self, ch):
        if ch not in self._cache:
            fonte, c = self._fonte, ch
            if ch in SEM_GLIFO:
                if ch == "%":
                    fonte = self._reserva
                else:   # tira o acento: ã -> a, Ç -> C ...
                    c = unicodedata.normalize("NFD", ch)[0]
            adv = max(1, round(fonte.getlength(c))) + 1     # +1 px entre letras
            # PAD no topo: o glifo tem pixels acima da linha de origem e
            # sem folga a linha de cima da letra saía cortada
            img = Image.new("RGBA", (adv + 5, self.tamanho + PAD + 8), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.fontmode = "1"        # sem suavização: pixel nítido
            dy = PAD + (1 if fonte is self._reserva and ch == "%" else 0)
            espessura = ESPESSURA
            for cor, off in ((self.sombra, 2), (self.cor, 0)):
                for ox, oy in espessura:
                    d.text((off + ox, dy + off + oy), c, font=fonte,
                           fill=cor + (255,))
            tinta = Image.new("L", img.size, 0)
            ImageDraw.Draw(tinta).text((0, dy), c, font=fonte, fill=255)
            self._cache[ch] = (ImageTk.PhotoImage(img), adv, tinta.getbbox())
        return self._cache[ch]

    def largura(self, texto):
        return sum(self._glifo(ch)[1] for ch in texto)

    def caixa(self, texto):
        """Retângulo (esq, topo, dir, base) ocupado pela TINTA do texto,
        relativo ao ponto onde desenhar() começa. Serve para centralizar de
        verdade (a caixa da fonte tem folgas que não são letra)."""
        x, esq, topo, dir_, base = 0, None, None, None, None
        for ch in texto:
            _, adv, bb = self._glifo(ch)
            if bb is not None and ch != " ":
                esq = x + bb[0] if esq is None else min(esq, x + bb[0])
                dir_ = x + bb[2] if dir_ is None else max(dir_, x + bb[2])
                topo = bb[1] if topo is None else min(topo, bb[1])
                base = bb[3] if base is None else max(base, bb[3])
            x += adv
        if esq is None:
            return (0, 0, 0, 0)
        return (esq, topo, dir_, base)

    def desenhar_centrado(self, canvas, cx, cy, texto, horizontal=True):
        """Centraliza a tinta do texto em (cx, cy). Com horizontal=False,
        `cx` é o x onde o texto começa e só o vertical é centralizado."""
        esq, topo, dir_, base = self.caixa(texto)
        x = cx - (esq + dir_) / 2 if horizontal else cx
        y = cy - (topo + base) / 2
        return self.desenhar(canvas, round(x), round(y), texto)

    def desenhar(self, canvas, x, y, texto):
        """Escreve `texto` com o canto superior esquerdo em (x, y)."""
        for ch in texto:
            img, adv, _ = self._glifo(ch)
            if ch != " ":
                canvas.create_image(x, y, image=img, anchor="nw")
            x += adv
        return x
