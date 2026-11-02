"""Ponto de entrada: python main.py

Requisitos: Python 3, tkinter (já vem com o Python), pillow, matplotlib.
    pip install pillow matplotlib

Opções (todas opcionais):
    --teste            ambiente de teste da animação: 1x, atendimento de 2 min,
                       24 clientes/h, 1 h simulada, seed 7, inicia sozinho
    --media N          tempo médio de atendimento (min)
    --cheg N           chegadas por hora
    --horas N          tempo simulado (horas)
    --dist D           exponencial | normal | triangular
    --seed N           semente do gerador aleatório
    --vel N            velocidade: 1, 10, 60, 300, 1000 ou 20000 (máximo)
    --auto             inicia a simulação ao abrir
    --barra-nativa     usa a barra de título normal do Windows (sem a barra Pokémon)
"""
import argparse

from gui import App


def main():
    ap = argparse.ArgumentParser(description="Simulador de fila (1 atendente)")
    ap.add_argument("--teste", action="store_true")
    ap.add_argument("--media", type=float)
    ap.add_argument("--cheg", type=float)
    ap.add_argument("--horas", type=float)
    ap.add_argument("--dist", choices=["exponencial", "normal", "triangular"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--vel", type=int, choices=[1, 10, 60, 300, 1000, 20000])
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--barra-nativa", action="store_true")
    a = ap.parse_args()

    params = dict(media=a.media, cheg=a.cheg, horas=a.horas, dist=a.dist,
                  seed=a.seed, vel=a.vel)
    if a.teste:
        base = dict(media=2, cheg=24, horas=1, seed=7, vel=1)
        params = {k: (v if v is not None else base.get(k)) for k, v in params.items()}
        a.auto = True

    app = App(barra_propria=not a.barra_nativa)
    app.aplicar_params(**{k: v for k, v in params.items() if v is not None})
    if a.auto:
        app.after(500, app._iniciar)
    app.mainloop()


if __name__ == "__main__":
    main()
