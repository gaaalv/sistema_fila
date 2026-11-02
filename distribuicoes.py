"""Geração dos tempos aleatórios (chegadas e atendimentos).

Todas as funções recebem um objeto random.Random para que a seed
possa ser fixada e os resultados sejam reproduzíveis.
Unidade de tempo usada em todo o programa: MINUTOS.
"""
import random

DISTRIBUICOES = ("exponencial", "normal", "triangular")


def intervalo_chegada(rng: random.Random, chegadas_por_hora: float) -> float:
    """Intervalo entre chegadas (min). Exponencial => chegadas de Poisson."""
    taxa_por_min = chegadas_por_hora / 60.0
    return rng.expovariate(taxa_por_min)


def tempo_atendimento(rng: random.Random, media_min: float,
                      dist: str = "exponencial") -> float:
    """Sorteia o tempo de atendimento (min) com média `media_min`.

    - exponencial: desvio = média (modelo M/M/1, muita variação).
    - normal: desvio = 30% da média; valores <= 0 são descartados e re-sorteados.
    - triangular: de 0,5x a 1,5x a média, com moda na média (média = média).
    """
    if dist == "exponencial":
        return rng.expovariate(1.0 / media_min)
    if dist == "normal":
        while True:
            t = rng.gauss(media_min, 0.3 * media_min)
            if t > 0:
                return t
    if dist == "triangular":
        return rng.triangular(0.5 * media_min, 1.5 * media_min, media_min)
    raise ValueError(f"Distribuição desconhecida: {dist}")


def variancia_atendimento(media_min: float, dist: str) -> float:
    """Variância teórica do tempo de atendimento (usada na fórmula M/G/1).

    Observação: a normal truncada tem variância ligeiramente menor que
    (0,3*média)^2; com 30% de desvio o truncamento é desprezível.
    """
    if dist == "exponencial":
        return media_min ** 2
    if dist == "normal":
        return (0.3 * media_min) ** 2
    if dist == "triangular":
        a, b = 0.5 * media_min, 1.5 * media_min
        c = media_min
        return (a*a + b*b + c*c - a*b - a*c - b*c) / 18.0
    raise ValueError(f"Distribuição desconhecida: {dist}")
