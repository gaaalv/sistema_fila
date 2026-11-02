"""Barra de título própria (estilo menu do Pokémon) para a janela principal.

Remove a barra do sistema (overrideredirect) e desenha uma nova com o painel
do HUD, ícone de pokébola, título na fonte Pokemon GB e botões minimizar/fechar.

Cuidados de Windows (overrideredirect tira a janela da barra de tarefas e
impede minimizar), tratados aqui:
- mostrar_na_barra_de_tarefas(): põe o estilo WS_EX_APPWINDOW via ctypes.
- minimizar(): devolve a barra nativa só durante o iconify e a remove ao voltar.
Se algo falhar em outro sistema, o programa continua rodando (try/except).
Para desligar tudo: python main.py --barra-nativa
"""

import os
import tkinter as tk

from PIL import Image, ImageTk

import hud

COR_BORDA = "#206860"  # mesma cor escura do contorno do painel
ALTURA = 36  # altura da barra (px)
ESCALA = 3  # tamanho do pixel do painel (igual ao cenário)
BOTAO_L, BOTAO_A = 34, 24


def _icone_pokebola(tamanho):
    caminho = os.path.join(hud.PASTA, "pokebola_poke_0.png")
    if not os.path.exists(caminho):
        return None
    img = Image.open(caminho).convert("RGBA")
    return img.resize((tamanho, tamanho), Image.NEAREST)


def definir_id_do_app():
    """Dá ao programa um identificador próprio no Windows. Sem isso a barra de
    tarefas agrupa a janela sob o ícone do Python e ignora o nosso."""
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "simulador.fila.pokemoncenter"
        )
    except Exception:
        pass


ICO = os.path.join(hud.PASTA, "pokebola.ico")


def aplicar_icone(app):
    """Põe o ícone da pokébola direto na janela do Windows (WM_SETICON).
    Precisa rodar DEPOIS de qualquer overrideredirect/withdraw, porque o Tk
    recria a janela do sistema e perde o ícone definido antes."""
    try:
        import ctypes
        from ctypes import wintypes

        if not os.path.exists(ICO):
            return False
        u = ctypes.windll.user32
        u.LoadImageW.restype = ctypes.c_void_p
        u.LoadImageW.argtypes = [
            wintypes.HINSTANCE,
            wintypes.LPCWSTR,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        u.SendMessageW.argtypes = [
            ctypes.c_void_p,
            wintypes.UINT,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        u.GetParent.restype = ctypes.c_void_p
        hwnd = u.GetParent(app.winfo_id()) or app.winfo_id()
        IMAGE_ICON, LR_LOADFROMFILE = 1, 0x10
        grande = u.LoadImageW(None, ICO, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        pequeno = u.LoadImageW(None, ICO, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        app._icones_win = (grande, pequeno)  # mantém vivos
        u.SendMessageW(hwnd, 0x0080, 1, grande)  # WM_SETICON, ICON_BIG
        u.SendMessageW(hwnd, 0x0080, 0, pequeno)  # WM_SETICON, ICON_SMALL
        return bool(grande and pequeno)
    except Exception:
        return False


def mostrar_na_barra_de_tarefas(app):
    """Faz a janela sem moldura aparecer na barra de tarefas (Windows)."""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(app.winfo_id())
        GWL_EXSTYLE, APPWINDOW, TOOLWINDOW = -20, 0x00040000, 0x00000080
        estilo = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (estilo & ~TOOLWINDOW) | APPWINDOW)
        app.withdraw()
        app.after(10, app.deiconify)
        app.after(120, lambda: aplicar_icone(app))
    except Exception:
        pass


def minimizar(app):
    """Minimiza (precisa da moldura nativa temporariamente)."""
    app._minimizado = True
    # O Tk só aceita iconify depois que a janela é remapeada sem o flag de
    # override-redirect: withdraw -> tira o flag -> iconify.
    app.withdraw()
    app.overrideredirect(False)
    app.update_idletasks()
    app.iconify()


def _ao_restaurar(app, evento):
    if evento.widget is app and getattr(app, "_minimizado", False):
        app._minimizado = False

        def refazer():
            app.overrideredirect(True)
            mostrar_na_barra_de_tarefas(app)

        app.after(20, refazer)


class BarraTitulo(tk.Canvas):
    def __init__(self, app, titulo, largura):
        super().__init__(
            app, width=largura, height=ALTURA, bg=COR_BORDA, highlightthickness=0
        )
        self.app = app
        self._largura = largura
        self._fundo = ImageTk.PhotoImage(hud.painel(largura, ALTURA, ESCALA))
        self.create_image(0, 0, image=self._fundo, anchor="nw")

        ic = _icone_pokebola(22)
        if ic is not None:
            self._ic = ImageTk.PhotoImage(ic)
            self.create_image(14, ALTURA // 2, image=self._ic, anchor="w")
        self._fonte = hud.FontePokemon(16)
        self._fonte.desenhar_centrado(self, 46, ALTURA / 2, titulo, horizontal=False)

        # botões (da direita para a esquerda): fechar, minimizar
        y0 = (ALTURA - BOTAO_A) // 2
        x_fechar = largura - 12 - BOTAO_L
        x_min = x_fechar - 8 - BOTAO_L
        self._botao(x_min, y0, "min")
        self._botao(x_fechar, y0, "fechar")

        self._off = (0, 0)
        self.bind("<ButtonPress-1>", self._comecar_arraste)
        self.bind("<B1-Motion>", self._arrastar)

    def _botao(self, x, y, nome):
        normal = "#388888"
        hover = "#C84646" if nome == "fechar" else "#48A8A0"
        r = self.create_rectangle(
            x, y, x + BOTAO_L, y + BOTAO_A, fill=normal, outline="#206860", width=2
        )
        if nome == "fechar":
            f = self._fonte
            f.desenhar_centrado(self, x + BOTAO_L / 2, y + BOTAO_A / 2, "X")
        else:  # traço de "minimizar" com sombra
            self.create_rectangle(
                x + 10, y + 14, x + 26, y + 18, fill="#206860", outline=""
            )
            self.create_rectangle(
                x + 9, y + 13, x + 25, y + 17, fill="white", outline=""
            )
        # área clicável por cima de tudo
        area = self.create_rectangle(
            x, y, x + BOTAO_L, y + BOTAO_A, fill="", outline=""
        )
        acao = (
            (lambda e: minimizar(self.app))
            if nome == "min"
            else (lambda e: self.app._fechar())
        )
        self.tag_bind(area, "<Enter>", lambda e: self.itemconfig(r, fill=hover))
        self.tag_bind(area, "<Leave>", lambda e: self.itemconfig(r, fill=normal))
        self.tag_bind(area, "<ButtonRelease-1>", acao)

    def _comecar_arraste(self, e):
        self._off = (e.x_root - self.app.winfo_x(), e.y_root - self.app.winfo_y())

    def _arrastar(self, e):
        if e.x < self._largura - 2 * (BOTAO_L + 12):
            self.app.geometry(f"+{e.x_root - self._off[0]}+{e.y_root - self._off[1]}")


def instalar_barra(app, corpo, titulo):
    """Troca a barra do sistema pela barra própria. Chamar com a UI montada."""
    app.update_idletasks()
    largura = max(app.winfo_reqwidth(), 480)
    altura = app.winfo_reqheight() + ALTURA
    barra = BarraTitulo(app, titulo, largura)
    barra.pack(side="top", fill="x", before=corpo)
    # centraliza na tela
    x = max(0, (app.winfo_screenwidth() - largura) // 2)
    y = max(0, (app.winfo_screenheight() - altura) // 2 - 10)
    app.geometry(f"{largura}x{altura}+{x}+{y}")
    app.configure(bg=COR_BORDA)
    app.overrideredirect(True)
    app.bind("<Map>", lambda e: _ao_restaurar(app, e))
    app.after(150, lambda: mostrar_na_barra_de_tarefas(app))
    return barra
