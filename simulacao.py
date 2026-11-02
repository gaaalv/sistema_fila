"""Motor da simulação: um atendente, fila FIFO, eventos discretos.

Não depende de interface gráfica. Devolve uma lista de eventos (para a
animação) e as estatísticas finais.
"""
import random
from dataclasses import dataclass, field

from distribuicoes import intervalo_chegada, tempo_atendimento


@dataclass
class Evento:
    tempo: float      # minutos
    tipo: str         # "chegada" | "inicio" | "fim"
    cliente: int      # id do cliente
    fila: int         # nº de pessoas esperando na fila APÓS o evento


@dataclass
class Resultado:
    eventos: list = field(default_factory=list)
    clientes_atendidos: int = 0
    clientes_chegaram: int = 0
    espera_media: float = 0.0       # min
    fila_maxima: int = 0
    fila_media: float = 0.0         # média no tempo
    ocupacao_pct: float = 0.0
    duracao: float = 0.0            # min simulados
    esperas: list = field(default_factory=list)


def verifica_estabilidade(media_min: float, chegadas_por_hora: float) -> float:
    """Retorna rho = lambda * E[S]. rho >= 1 => fila instável."""
    return (chegadas_por_hora / 60.0) * media_min


def simular(media_min: float, chegadas_por_hora: float, horas: float,
            dist: str = "exponencial", seed=None) -> Resultado:
    """Roda uma simulação. Chegadas só ocorrem até o fim do tempo simulado;
    quem está na fila/atendimento nesse momento é atendido até o fim e as
    estatísticas de fila/ocupação são medidas em [0, horas]."""
    rng = random.Random(seed)
    T = horas * 60.0

    # 1) Gera todas as chegadas do período
    chegadas = []
    t = intervalo_chegada(rng, chegadas_por_hora)
    while t < T:
        chegadas.append(t)
        t += intervalo_chegada(rng, chegadas_por_hora)

    # 2) Atendente único, FIFO: cada cliente começa quando chega ou quando
    #    o anterior termina (o que ocorrer por último).
    res = Resultado(duracao=T, clientes_chegaram=len(chegadas))
    inicios, fins = [], []
    livre_em = 0.0
    for i, ch in enumerate(chegadas):
        ini = max(ch, livre_em)
        fim = ini + tempo_atendimento(rng, media_min, dist)
        inicios.append(ini)
        fins.append(fim)
        livre_em = fim
        res.esperas.append(ini - ch)

    # 3) Linha do tempo de eventos
    # desempate no mesmo instante: chegada -> fim -> inicio
    bruto = []
    for i in range(len(chegadas)):
        bruto.append((chegadas[i], 0, "chegada", i))
        bruto.append((inicios[i], 2, "inicio", i))
        bruto.append((fins[i], 1, "fim", i))
    bruto.sort(key=lambda e: (e[0], e[1]))

    na_fila = 0
    ult_t = 0.0
    area_fila = 0.0
    ocupado = 0.0
    em_servico = False
    for tempo, _, tipo, cid in bruto:
        te = min(tempo, T)
        dt = te - ult_t
        if dt > 0:
            area_fila += na_fila * dt
            if em_servico:
                ocupado += dt
            ult_t = te
        if tipo == "chegada":
            na_fila += 1
        elif tipo == "inicio":
            na_fila -= 1
            em_servico = True
        else:
            em_servico = False
        res.fila_maxima = max(res.fila_maxima, na_fila)
        res.eventos.append(Evento(tempo, tipo, cid, na_fila))
    # trecho final até T, se ainda não coberto
    if ult_t < T:
        dt = T - ult_t
        area_fila += na_fila * dt
        if em_servico:
            ocupado += dt

    res.clientes_atendidos = sum(1 for f in fins if f <= T)
    res.espera_media = sum(res.esperas) / len(res.esperas) if res.esperas else 0.0
    res.fila_media = area_fila / T
    res.ocupacao_pct = 100.0 * ocupado / T
    return res
