"""Interface gráfica (tkinter + matplotlib embutido em abas)."""
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import janela
from animacao import CenaFila
from distribuicoes import DISTRIBUICOES
from estatisticas import replicar, teoria, varredura_carga
from simulacao import simular, verifica_estabilidade

VELOCIDADES = {"1x (tempo real)": 1, "10x": 10, "60x": 60, "300x": 300,
               "1000x": 1000, "Máximo": 20000}
NOMES_DIST = {"exponencial": "Exponencial (M/M/1)",
              "normal": "Normal truncada (desvio 30%)",
              "triangular": "Triangular (0,5x a 1,5x)"}


class App(tk.Tk):
    TITULO = "Simulador de Fila - Pokémon Center"

    def __init__(self, barra_propria=True):
        janela.definir_id_do_app()      # ícone próprio na barra de tarefas
        super().__init__()
        self.title(self.TITULO)
        self.resultado = None
        self._historico_n = 0
        self._minimizado = False
        self._icone_janela()
        # tudo fica dentro de `corpo`; a barra de título própria entra acima dele
        self.corpo = tk.Frame(self, bg=janela.COR_BORDA)
        self.corpo.pack(side="bottom", fill="both", expand=True,
                        padx=4 if barra_propria else 0,
                        pady=(0, 4) if barra_propria else 0)
        self._montar_painel()
        self._montar_abas()
        if barra_propria:
            janela.instalar_barra(self, self.corpo, self.TITULO)
        else:
            self.after(200, lambda: janela.aplicar_icone(self))
        self.cena.on_tick = self._ao_tick
        self.cena.on_fim = self._ao_fim
        self.protocol("WM_DELETE_WINDOW", self._fechar)

    def _icone_janela(self):
        """Ícone de pokébola na janela/barra de tarefas (se o sprite existir)."""
        try:
            import os
            from PIL import Image, ImageTk
            ic = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "sprites", "pokebola_poke_0.png"))
            ic = ic.convert("RGBA").resize((32, 32), Image.NEAREST)
            self._ic_tk = ImageTk.PhotoImage(ic)
            self.iconphoto(True, self._ic_tk)
            ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "sprites", "pokebola.ico")
            if os.path.exists(ico):
                self.iconbitmap(default=ico)   # barra de tarefas / Alt+Tab
        except Exception:
            pass

    def aplicar_params(self, media=None, cheg=None, horas=None, dist=None,
                       seed=None, vel=None, reps=None):
        """Preenche os campos (usado pelo main.py / modo teste)."""
        if media is not None: self.v_media.set(f"{media:g}")
        if cheg is not None: self.v_chegadas.set(f"{cheg:g}")
        if horas is not None: self.v_horas.set(f"{horas:g}")
        if dist is not None: self.v_dist.set(NOMES_DIST[dist])
        if seed is not None: self.v_seed.set(str(seed))
        if reps is not None: self.v_reps.set(str(reps))
        if vel is not None:
            self.v_vel.set(next(k for k, v in VELOCIDADES.items() if v == vel))
            self._mudou_velocidade()

    # ------------------------------------------------------------------
    # Painel de parâmetros (esquerda)
    # ------------------------------------------------------------------
    def _montar_painel(self):
        p = ttk.Frame(self.corpo, padding=10)
        p.pack(side="left", fill="y")

        ttk.Label(p, text="Parâmetros", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.v_media = tk.StringVar(value="10")
        self.v_chegadas = tk.StringVar(value="5")
        self.v_horas = tk.StringVar(value="8")
        self.v_dist = tk.StringVar(value=NOMES_DIST["exponencial"])
        self.v_seed = tk.StringVar(value="")
        self.v_reps = tk.StringVar(value="30")
        self.v_vel = tk.StringVar(value="60x")

        def linha(rotulo, var, widget="entry", valores=None):
            ttk.Label(p, text=rotulo).pack(anchor="w", pady=(6, 0))
            if widget == "combo":
                w = ttk.Combobox(p, textvariable=var, values=valores,
                                 state="readonly", width=28)
            else:
                w = ttk.Entry(p, textvariable=var, width=30)
            w.pack(anchor="w")
            return w

        linha("Tempo médio de atendimento (min)", self.v_media)
        linha("Chegadas esperadas (clientes/hora)", self.v_chegadas)
        linha("Tempo simulado (horas)", self.v_horas)
        linha("Distribuição do atendimento", self.v_dist, "combo",
              list(NOMES_DIST.values()))
        linha("Seed (vazio = aleatória)", self.v_seed)
        linha("Nº de replicações", self.v_reps)
        c = linha("Velocidade da animação", self.v_vel, "combo", list(VELOCIDADES))
        c.bind("<<ComboboxSelected>>", self._mudou_velocidade)

        self.lbl_aviso = ttk.Label(p, text="", foreground="#b00020", wraplength=250)
        self.lbl_aviso.pack(anchor="w", pady=(8, 0))

        bt = ttk.Frame(p)
        bt.pack(anchor="w", pady=8)
        self.btn_play = ttk.Button(bt, text="Iniciar", width=12, command=self._iniciar)
        self.btn_play.grid(row=0, column=0, padx=(0, 4), pady=2)
        ttk.Button(bt, text="Resultado direto", width=16,
                   command=self._resultado_direto).grid(row=0, column=1, pady=2)
        ttk.Button(bt, text="Replicações", width=12,
                   command=self._rodar_replicacoes).grid(row=1, column=0, padx=(0, 4), pady=2)
        ttk.Button(bt, text="Análise de carga", width=16,
                   command=self._rodar_carga).grid(row=1, column=1, pady=2)

        ttk.Separator(p).pack(fill="x", pady=6)
        ttk.Label(p, text="Ao vivo", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.v_live = {k: tk.StringVar(value="-") for k in
                       ("Tempo simulado", "Na fila agora", "Clientes atendidos", "Joy")}
        self._tabela(p, self.v_live)

        ttk.Separator(p).pack(fill="x", pady=6)
        ttk.Label(p, text="Resumo final (1 execução)",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.v_fim = {k: tk.StringVar(value="-") for k in
                      ("Clientes atendidos", "Espera média na fila",
                       "Tamanho máximo da fila", "Tamanho médio da fila",
                       "Atendente ocupado")}
        self._tabela(p, self.v_fim)
        self.v_teoria = tk.StringVar(value="")
        ttk.Label(p, textvariable=self.v_teoria, wraplength=250,
                  foreground="#444").pack(anchor="w", pady=(6, 0))

    def _tabela(self, pai, vars_):
        f = ttk.Frame(pai)
        f.pack(anchor="w", fill="x")
        for i, (k, v) in enumerate(vars_.items()):
            ttk.Label(f, text=k + ":").grid(row=i, column=0, sticky="w")
            ttk.Label(f, textvariable=v, font=("Consolas", 10, "bold")).grid(
                row=i, column=1, sticky="e", padx=(10, 0))
        f.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    # Abas (direita)
    # ------------------------------------------------------------------
    def _montar_abas(self):
        self.abas = ttk.Notebook(self.corpo)
        self.abas.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # 1) Animação
        f1 = ttk.Frame(self.abas)
        self.abas.add(f1, text="Animação")
        self.cena = CenaFila(f1)
        self.cena.pack(padx=6, pady=6)

        # 2) Fila no tempo
        f2 = ttk.Frame(self.abas)
        self.abas.add(f2, text="Fila no tempo")
        self.fig_fila = Figure(figsize=(7, 4.2), dpi=100)
        self.cv_fila = FigureCanvasTkAgg(self.fig_fila, f2)
        self.cv_fila.get_tk_widget().pack(fill="both", expand=True)

        # 3) Replicações e teoria
        f3 = ttk.Frame(self.abas)
        self.abas.add(f3, text="Replicações e teoria")
        self.fig_rep = Figure(figsize=(7, 3), dpi=100)
        self.cv_rep = FigureCanvasTkAgg(self.fig_rep, f3)
        self.cv_rep.get_tk_widget().pack(fill="x")
        cols = ("cenario", "wq", "lq", "ocup", "fmax", "atend")
        self.tv = ttk.Treeview(f3, columns=cols, show="headings", height=6)
        for c, t, w in (("cenario", "Cenário (atend., chegadas/h, horas, dist.)", 270),
                        ("wq", "Espera média (min)", 120), ("lq", "Fila média", 80),
                        ("ocup", "Ocupação %", 90), ("fmax", "Fila máx.", 80),
                        ("atend", "Atendidos", 80)):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=w, anchor="center")
        self.tv.pack(fill="both", expand=True, padx=6, pady=6)

        # 4) Carga
        f4 = ttk.Frame(self.abas)
        self.abas.add(f4, text="Carga (ρ → 100%)")
        self.fig_carga = Figure(figsize=(7, 4.2), dpi=100)
        self.cv_carga = FigureCanvasTkAgg(self.fig_carga, f4)
        self.cv_carga.get_tk_widget().pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Leitura e validação dos parâmetros
    # ------------------------------------------------------------------
    def _ler(self):
        """Lê os campos. Devolve dict ou None (com mensagem de erro)."""
        try:
            media = float(self.v_media.get().replace(",", "."))
            cheg = float(self.v_chegadas.get().replace(",", "."))
            horas = float(self.v_horas.get().replace(",", "."))
            reps = int(self.v_reps.get())
            seed = int(self.v_seed.get()) if self.v_seed.get().strip() else None
        except ValueError:
            messagebox.showerror("Parâmetros inválidos",
                                 "Verifique se os campos contêm números válidos "
                                 "(a seed e as replicações devem ser inteiras).")
            return None
        if media <= 0 or cheg <= 0 or horas <= 0 or reps < 1:
            messagebox.showerror("Parâmetros inválidos",
                                 "Todos os valores devem ser positivos.")
            return None
        dist = next(k for k, v in NOMES_DIST.items() if v == self.v_dist.get())
        return dict(media=media, cheg=cheg, horas=horas, reps=reps,
                    seed=seed, dist=dist)

    def _checa_estabilidade(self, p):
        """Avisa se rho >= 1. Retorna False se o usuário cancelar."""
        rho = verifica_estabilidade(p["media"], p["cheg"])
        if rho >= 1:
            self.lbl_aviso.config(
                text=f"⚠ Sistema INSTÁVEL: ρ = {rho:.2f} ≥ 1. O atendente não dá "
                     "conta da demanda e a fila cresce indefinidamente.")
            return messagebox.askyesno(
                "Fila instável",
                f"ρ = chegadas × tempo de atendimento = {rho:.2f} ≥ 1.\n\n"
                "A fila vai crescer sem parar. Deseja simular mesmo assim?")
        self.lbl_aviso.config(text=f"Carga do atendente: ρ = {rho:.2f} (estável)")
        return True

    def _mudou_velocidade(self, _evt=None):
        self.cena.velocidade = VELOCIDADES[self.v_vel.get()]

    # ------------------------------------------------------------------
    # Ações dos botões
    # ------------------------------------------------------------------
    def _simular(self, p):
        self.resultado = simular(p["media"], p["cheg"], p["horas"],
                                 p["dist"], p["seed"])
        self._params = p
        self._plot_fila(self.resultado, p["horas"])

    def _iniciar(self):
        # Botão alterna entre Iniciar / Pausar / Continuar
        if self.cena.rodando:
            self.cena.pause()
            self.btn_play.config(text="Continuar")
            return
        if self.btn_play.cget("text") == "Continuar":
            self.cena.play()
            self.btn_play.config(text="Pausar")
            return
        p = self._ler()
        if not p or not self._checa_estabilidade(p):
            return
        self._limpar_resumo()
        self._simular(p)
        self._mudou_velocidade()
        self.cena.set_resultado(self.resultado)
        self.abas.select(0)
        self.cena.play()
        self.btn_play.config(text="Pausar")

    def _resultado_direto(self):
        p = self._ler()
        if not p or not self._checa_estabilidade(p):
            return
        self.cena.pause()
        self.btn_play.config(text="Iniciar")
        self._simular(p)
        self._preencher_resumo()
        self.abas.select(1)

    def _rodar_replicacoes(self):
        p = self._ler()
        if not p or not self._checa_estabilidade(p):
            return
        self.config(cursor="watch"); self.update_idletasks()
        try:
            resumo, _ = replicar(p["media"], p["cheg"], p["horas"], p["dist"],
                                 p["reps"], p["seed"])
        finally:
            self.config(cursor="")
        t = teoria(p["media"], p["cheg"], p["dist"])
        self._plot_replicacoes(resumo, t, p)
        rotulo = (f"{p['media']:g} min, {p['cheg']:g}/h, {p['horas']:g} h, "
                  f"{p['dist'][:4]}., n={p['reps']}")
        self.tv.insert("", "end", values=(
            rotulo,
            f"{resumo['espera_media'][0]:.1f} ± {resumo['espera_media'][1]:.1f}",
            f"{resumo['fila_media'][0]:.2f} ± {resumo['fila_media'][1]:.2f}",
            f"{resumo['ocupacao_pct'][0]:.1f} ± {resumo['ocupacao_pct'][1]:.1f}",
            f"{resumo['fila_maxima'][0]:.1f} ± {resumo['fila_maxima'][1]:.1f}",
            f"{resumo['clientes_atendidos'][0]:.0f} ± {resumo['clientes_atendidos'][1]:.0f}"))
        self.abas.select(2)

    def _rodar_carga(self):
        p = self._ler()
        if not p:
            return
        self.config(cursor="watch"); self.update_idletasks()
        try:
            rhos = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95]
            linhas = varredura_carga(p["media"], max(p["horas"], 200), p["dist"],
                                     rhos, n=15, seed=p["seed"])
        finally:
            self.config(cursor="")
        self._plot_carga(linhas, p)
        self.abas.select(3)

    # ------------------------------------------------------------------
    # Callbacks da animação
    # ------------------------------------------------------------------
    def _ao_tick(self, info):
        t = info["t"]
        self.v_live["Tempo simulado"].set(
            f"{int(t // 60):02d}:{int(t % 60):02d}:{int((t * 60) % 60):02d}")
        self.v_live["Na fila agora"].set(str(info["fila"]))
        self.v_live["Clientes atendidos"].set(str(info["atendidos"]))
        self.v_live["Joy"].set("ocupada" if info["ocupado"] else "livre")

    def _ao_fim(self):
        self.btn_play.config(text="Iniciar")
        self._preencher_resumo()

    def _limpar_resumo(self):
        for v in self.v_fim.values():
            v.set("-")
        self.v_teoria.set("")

    def _preencher_resumo(self):
        r, p = self.resultado, self._params
        self.v_fim["Clientes atendidos"].set(str(r.clientes_atendidos))
        self.v_fim["Espera média na fila"].set(f"{r.espera_media:.1f} min")
        self.v_fim["Tamanho máximo da fila"].set(str(r.fila_maxima))
        self.v_fim["Tamanho médio da fila"].set(f"{r.fila_media:.2f}")
        self.v_fim["Atendente ocupado"].set(f"{r.ocupacao_pct:.1f} %")
        t = teoria(p["media"], p["cheg"], p["dist"])
        if t is None:
            self.v_teoria.set("Teoria: sistema instável (ρ ≥ 1), sem regime estável.")
        else:
            nome = "M/M/1" if p["dist"] == "exponencial" else "M/G/1"
            self.v_teoria.set(
                f"Teoria ({nome}): espera {t['Wq']:.1f} min, fila média "
                f"{t['Lq']:.2f}, ocupação {t['ocupacao_pct']:.1f}%. Uma única "
                "execução curta pode diferir bastante; veja as replicações.")

    # ------------------------------------------------------------------
    # Gráficos
    # ------------------------------------------------------------------
    def _plot_fila(self, res, horas):
        fig = self.fig_fila
        fig.clear()
        ax = fig.add_subplot(111)
        xs = [0] + [e.tempo / 60 for e in res.eventos]
        ys = [0] + [e.fila for e in res.eventos]
        ax.step(xs, ys, where="post", color="#1f77b4", linewidth=1.2)
        ax.fill_between(xs, ys, step="post", alpha=0.15, color="#1f77b4")
        ax.axhline(res.fila_media, color="#d62728", linestyle="--",
                   label=f"média = {res.fila_media:.2f}")
        ax.set_xlim(0, horas)
        ax.set_xlabel("Tempo (horas)")
        ax.set_ylabel("Pessoas na fila")
        ax.set_title("Evolução da fila ao longo do tempo")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        self.cv_fila.draw()

    def _plot_replicacoes(self, resumo, t, p):
        fig = self.fig_rep
        fig.clear()
        itens = (("espera_media", "Espera média (min)", t and t["Wq"]),
                 ("fila_media", "Fila média (pessoas)", t and t["Lq"]),
                 ("ocupacao_pct", "Ocupação (%)", t and t["ocupacao_pct"]))
        for i, (chave, titulo, ref) in enumerate(itens, 1):
            ax = fig.add_subplot(1, 3, i)
            m, sd = resumo[chave]
            ax.bar(["simulado"], [m], yerr=[sd], capsize=6, color="#1f77b4")
            if ref is not None:
                ax.axhline(ref, color="#d62728", linestyle="--", label=f"teoria {ref:.1f}")
                ax.legend(fontsize=8)
            ax.set_title(titulo, fontsize=10)
        fig.suptitle(f"{p['reps']} replicações de {p['horas']:g} h "
                     f"(barras = média ± desvio)", fontsize=10)
        fig.tight_layout()
        self.cv_rep.draw()

    def _plot_carga(self, linhas, p):
        fig = self.fig_carga
        fig.clear()
        rhos = [l["rho"] for l in linhas]
        ax1 = fig.add_subplot(1, 2, 1)
        ax1.plot(rhos, [l["fila_media"] for l in linhas], "o-", label="simulado")
        ax1.plot(rhos, [l["Lq_teoria"] for l in linhas], "s--", label="teoria")
        ax1.set_xlabel("Carga ρ"); ax1.set_ylabel("Fila média (pessoas)")
        ax1.set_title("Fila média x carga"); ax1.legend(); ax1.grid(alpha=0.3)
        ax2 = fig.add_subplot(1, 2, 2)
        ax2.plot(rhos, [l["espera_media"] for l in linhas], "o-", label="simulado")
        ax2.plot(rhos, [l["Wq_teoria"] for l in linhas], "s--", label="teoria")
        ax2.set_xlabel("Carga ρ"); ax2.set_ylabel("Espera média (min)")
        ax2.set_title("Espera média x carga"); ax2.legend(); ax2.grid(alpha=0.3)
        fig.suptitle(f"Efeito da carga (atend. {p['media']:g} min, "
                     f"{NOMES_DIST[p['dist']]})", fontsize=10)
        fig.tight_layout()
        self.cv_carga.draw()

    def _fechar(self):
        self.cena.pause()
        self.destroy()
