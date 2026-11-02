"""Replicações, teoria (M/M/1 e M/G/1) e análise de carga."""
import statistics

from distribuicoes import variancia_atendimento
from simulacao import simular

METRICAS = ("clientes_atendidos", "espera_media", "fila_maxima",
            "fila_media", "ocupacao_pct")


def teoria(media_min: float, chegadas_por_hora: float, dist: str):
    """Valores teóricos em regime estável (fórmula de Pollaczek-Khinchine).

    Para exponencial coincide com M/M/1 (Wq = rho*E[S]/(1-rho)).
    Retorna dict com Wq (min) e Lq, ou None se rho >= 1.
    """
    lam = chegadas_por_hora / 60.0
    rho = lam * media_min
    if rho >= 1:
        return None
    var = variancia_atendimento(media_min, dist)
    es2 = var + media_min ** 2
    lq = (lam ** 2) * es2 / (2 * (1 - rho))
    wq = lq / lam
    return {"rho": rho, "Wq": wq, "Lq": lq, "ocupacao_pct": 100 * rho}


def replicar(media_min, chegadas_por_hora, horas, dist="exponencial",
             n=30, seed=None):
    """Executa n simulações (seeds seed, seed+1, ...).
    Retorna dict metrica -> (media, desvio_padrao) e a lista de resultados."""
    resultados = []
    for i in range(n):
        s = None if seed is None else seed + i
        resultados.append(simular(media_min, chegadas_por_hora, horas, dist, s))
    resumo = {}
    for m in METRICAS:
        vals = [getattr(r, m) for r in resultados]
        sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
        resumo[m] = (statistics.mean(vals), sd)
    return resumo, resultados


def varredura_carga(media_min, horas, dist, rhos, n=20, seed=None):
    """Para cada rho, ajusta a taxa de chegada e mede fila média / espera."""
    linhas = []
    for rho in rhos:
        chegadas_h = rho / media_min * 60.0
        resumo, _ = replicar(media_min, chegadas_h, horas, dist, n, seed)
        t = teoria(media_min, chegadas_h, dist)
        linhas.append({
            "rho": rho,
            "fila_media": resumo["fila_media"][0],
            "espera_media": resumo["espera_media"][0],
            "Lq_teoria": t["Lq"] if t else float("nan"),
            "Wq_teoria": t["Wq"] if t else float("nan"),
        })
    return linhas
