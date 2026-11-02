"""Gera os 9 quadros de cada integrante da equipe (frente, costas, esquerda e a
caminhada de cada lado), no mesmo formato dos clientes (20x24 px, pés na base).

Como funciona:
1. Cada integrante tem um sprite de frente (gabriel.png, lara.png, maria.png) e
   um cliente-modelo (cliente_1 ou cliente_2) do qual foi feito.
2. Compara o modelo com o integrante (só a pose de frente) para descobrir qual
   cor do modelo virou qual cor do integrante: cabelo -> cabelo, camisa ->
   camisa, e assim por diante.
3. Aplica essa troca de cores em TODOS os 9 quadros do modelo. Assim as costas,
   o lado e a caminhada herdam o desenho do modelo com as cores do integrante.
4. Nos 3 quadros de frente, a cabeça original do integrante é colada por cima
   (mantém detalhes como o cabelo espetado e os brincos).

Uso:  python gerar_sprites_equipe.py
Saída: sprites/equipe/<nome>_<quadro>.png
"""
import os
from collections import Counter

from PIL import Image

RAIZ = os.path.dirname(os.path.abspath(__file__))
SPRITES = os.path.join(RAIZ, "sprites")
SAIDA = os.path.join(SPRITES, "equipe")
L, A = 20, 24                       # tela de cada quadro (igual aos clientes)
QUADROS = ["frente", "costas", "esquerda", "frente_a", "frente_b",
           "costas_a", "costas_b", "esquerda_a", "esquerda_b"]

# integrante -> cliente usado como modelo
MODELOS = {"gabriel": 1, "lara": 2, "maria": 2}
# Troca de cores definida à mão (cor do modelo -> cor do integrante). Vale por
# cima da comparação automática. Útil quando o cabelo/roupa do integrante tem
# outro formato e a comparação por posição erra (caso do Gabriel).
MAPA_MANUAL = {
    "gabriel": {                                    # modelo: cliente_1
        (123, 65, 66): (123, 66, 66),               # contorno das mãos
        (82, 16, 0): (0, 1, 1),                     # cabelo (sombra)
        (148, 65, 41): (8, 8, 8),                   # cabelo
        (222, 154, 115): (222, 148, 115),           # pele
        (255, 203, 156): (255, 197, 148),           # pele clara
        (255, 219, 189): (255, 215, 181),           # pele mais clara
        (156, 162, 198): (23, 29, 70),              # camisa
        (206, 211, 231): (34, 42, 96),              # brilho da camisa
        (74, 73, 123): (12, 16, 38),                # sombra da camisa
        (16, 56, 0): (207, 207, 207),               # tênis (sombra)
        (66, 121, 0): (255, 255, 255),              # tênis
    },
}
LINHAS_CABECA = 9                   # linhas (a partir do topo) que formam a cabeça


def _caixa(img):
    return img.getchannel("A").getbbox()


def _na_tela(img):
    """Recorta o desenho e centraliza na tela LxA com os pés na base."""
    img = img.convert("RGBA")
    img = img.crop(_caixa(img))
    tela = Image.new("RGBA", (L, A), (0, 0, 0, 0))
    tela.alpha_composite(img, ((L - img.width) // 2, A - img.height))
    return tela


def _modelo(n, quadro):
    return Image.open(os.path.join(SPRITES, "clientes",
                                   f"cliente_{n}_{quadro}.png")).convert("RGBA")


def _votos(base, membro, linhas, dy, dx):
    """Votos cor-do-modelo -> cor-do-integrante nas `linhas` do modelo, com o
    integrante deslocado (dy, dx)."""
    pb, pm = base.load(), membro.load()
    votos = {}
    for y in linhas:
        for x in range(L):
            cor = pb[x, y]
            if cor[3] == 0:
                continue
            ym, xm = y + dy, x + dx
            if not (0 <= ym < A and 0 <= xm < L):
                continue
            alvo = pm[xm, ym]
            if alvo[3] == 0:
                continue
            votos.setdefault(cor, Counter())[alvo] += 1
    return votos


def _iou(base, membro, dy, dx):
    """Sobreposição das silhuetas com o integrante deslocado (dy, dx)."""
    pb, pm = base.load(), membro.load()
    inter = uniao = 0
    for y in range(A):
        for x in range(L):
            a = pb[x, y][3] > 0
            ym, xm = y + dy, x + dx
            m = 0 <= ym < A and 0 <= xm < L and pm[xm, ym][3] > 0
            inter += a and m
            uniao += a or m
    return inter / uniao


def _mapa_de_cores(base, membro):
    """Para cada cor do modelo, a cor mais frequente do integrante na mesma
    parte do corpo. As duas imagens são alinhadas pela silhueta inteira (pés e
    corpo coincidem mesmo quando o cabelo de um é mais alto)."""
    # maior sobreposição; no empate, o menor deslocamento
    _, _, dy, dx = max((_iou(base, membro, dy, dx), -abs(dy) - abs(dx), dy, dx)
                       for dy in range(-3, 4) for dx in range(-2, 3))
    topo, base_y = _caixa(base)[1], _caixa(base)[3]
    return {c: v.most_common(1)[0][0]
            for c, v in _votos(base, membro, range(topo, base_y), dy, dx).items()}


def _mais_proxima(cor, mapa):
    return min(mapa, key=lambda c: sum((a - b) ** 2 for a, b in zip(c[:3], cor[:3])))


def _recolorir(img, mapa):
    """Troca as cores; cor que não aparecia na pose de frente (ex.: o fundo do
    cabelo nas costas) usa a cor do vizinho mais parecido, com o mesmo brilho."""
    out = img.copy()
    px = out.load()
    for y in range(A):
        for x in range(L):
            cor = px[x, y]
            if cor[3] == 0:
                continue
            if cor not in mapa:
                viz = _mais_proxima(cor, mapa)
                novo = tuple(max(0, min(255, mapa[viz][i] + cor[i] - viz[i]))
                             for i in range(3)) + (255,)
                mapa[cor] = novo
            px[x, y] = mapa[cor]
    return out


def _colar_cabeca(frame, membro_tela, base_idle):
    """Nos quadros de frente: apaga a cabeça do modelo e cola a do integrante."""
    topo_f = _caixa(frame)[1]
    topo_b = _caixa(base_idle)[1]
    topo_m = _caixa(membro_tela)[1]
    desloc = topo_f - topo_b                    # balanço de 1 px na caminhada
    # linhas da cabeça do integrante (mais altas se o cabelo for maior)
    extra = topo_b - topo_m
    n = LINHAS_CABECA + max(0, extra)
    cabeca = membro_tela.crop((0, topo_m, L, topo_m + n))
    out = frame.copy()
    px = out.load()
    for y in range(topo_f, min(A, topo_f + LINHAS_CABECA)):
        for x in range(L):
            px[x, y] = (0, 0, 0, 0)
    out.alpha_composite(cabeca, (0, topo_m + desloc))
    return out


def gerar():
    os.makedirs(SAIDA, exist_ok=True)
    for nome, n in MODELOS.items():
        membro = _na_tela(Image.open(os.path.join(SPRITES, f"{nome}.png")))
        base_idle = _modelo(n, "frente")
        mapa = _mapa_de_cores(base_idle, membro)
        for cor, nova in MAPA_MANUAL.get(nome, {}).items():
            mapa[cor + (255,)] = nova + (255,)
        for q in QUADROS:
            frame = _recolorir(_modelo(n, q), mapa)
            if q.startswith("frente"):
                frame = _colar_cabeca(frame, membro, base_idle)
            frame.save(os.path.join(SAIDA, f"{nome}_{q}.png"))
        print(f"{nome}: modelo cliente_{n}, {len(mapa)} cores mapeadas")


if __name__ == "__main__":
    gerar()
