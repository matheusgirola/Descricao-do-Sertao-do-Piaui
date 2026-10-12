"""Monta descricao_interativa_bcim.html: base vetorial (SVG) da BCIM 2016 +
vegetacao IBGE 1:5M, com os 125 pontos de 1697 reposicionados sobre a
hidrografia real.  O texto do relato vem de descricao_interativa_1.html."""

import html
import json
import pathlib
import re
import sys

sys.path.insert(0, "scripts")
import numpy as np
import pandas as pd
import shapely
from shapely.ops import linemerge

import base_svg as B

SRC_HTML = "dados/fontes/descricao_interativa_1.html"
OUT = "descricao_interativa_bcim.html"

# rios que o relato de 1697 percorre -> nome na BC250 (mesma tabela de snap_rios.py).
# Sao desenhados a partir da BC250, e nao da BCIM que faz o resto da carta: e nela
# que os 125 pontos foram encaixados, e os dois tracados nao coincidem.
RIOS_RELATO = {
    "Rio Canindé": "rio Canindé",
    "Rio Itaim": "rio Itaim Mirim",
    "Rio Guaribas": "riacho das Guaribas",
    "Riacho do Frade": "riachinho do Frade",
    "Ribeirão Talhado": "riachinho da Serra Talhada",
    "Riacho do Mocambo": "riachinho do Mocambo",
    "Ribeirão da Tranqueira": "riacho da Tranqueira",
    "Rio Poti": "rio Itaim Açu (1697)",
    "Rio do Cais": "riacho do Cais",
    "Riacho Iningá": "riacho Canabrava",
    "Rio São Nicolau": "riacho São Nicolau",
    "Riacho Vitória": "riacho Vitória",
    "Riacho da Serra Negra": "riacho Negro",
    "Rio São Vicente": "riacho São Vicente",
    "Rio Berlengas": "riacho das Berlengas",
    "Rio Maratoã": "riacho Maratauam",
    "Rio Piauí": "rio Piauí",
    "Riacho do Mucaitá": "riacho Moicatá",
    "Rio Itaueira": "riacho da Itaueira",
    "Rio Gurguéia": "rio Gurgueia",
    "Rio Parnaíba": "rio Parnaíba",
}
# os mesmos rios, como a BCIM os nomeia: servem para SUPRIMIR o traçado da BCIM
# onde a BC250 ja desenha o curso grosso, senao o rio aparece em duas linhas
# vizinhas e ligeiramente diferentes.
RIOS_RELATO_BCIM = {
    "Rio Canindé",
    "Rio Itaim",
    "Rio Guaribas",
    "Riacho Guaribas",
    "Riacho do Frade",
    "Ribeirão Talhado",
    "Riacho Talhado",
    "Riacho do Mocambo",
    "Ribeirão da Tranqueira",
    "Riacho Tranqueira",
    "Rio Poti",
    "Rio do Cais",
    "Riacho da Iningá",
    "Rio São Nicolau",
    "Riacho Vitória",
    "Riacho da Serra Negra",
    "Rio São Vicente",
    "Riacho São Vicente",
    "Rio Beriengas",
    "Rio Berlengas",
    "Rio Maratoã",
    "Rio Piauí",
    "Riacho do Mucaitá",
    "Rio Itaueira",
    "Rio Gurguéia",
    "Rio Parnaíba",
}
CIDADES = [
    "Oeiras",
    "Teresina",
    "Parnaíba",
    "Floriano",
    "Picos",
    "Amarante",
    "Jerumenha",
    "Valença do Piauí",
    "Jaicós",
    "Paulistana",
    "Uruçuí",
    "Bom Jesus",
    "Corrente",
    "São Raimundo Nonato",
    "Campo Maior",
    "Piripiri",
    "São Miguel do Tapuio",
    "Barras",
    "Água Branca",
    "Parnaguá",
    "Canto do Buriti",
    "Simplício Mendes",
]


def esc(s):
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- rotulagem
# Georgia italica: os glifos nao tem a mesma largura, e a diferenca entre
# "Rio Poti" e "Ribeirao da Tranqueira" decide se o rotulo cabe no curso.
_FINO = set("iíìjlrtfIJ.,;:'!|()[]- ")
_LARGO = set("ABCDEFGHKLMNOPQRSTUVWXYZmwMW")


def larg_txt(s, fs):
    """largura aproximada de um texto, em px"""
    return fs * sum(0.28 if c in _FINO else 0.62 if c in _LARGO else 0.50 for c in s)


def _sobra(a, b):
    """area de intersecao de duas caixas (x0,y0,x1,y1)"""
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def _reamostra(X, Y, passo=14.0, jan=5):
    """polilinha reamostrada e suavizada.  Sobre uma linha muito quebrada o
    <textPath> empilha as letras no lado de dentro da curva -- e o trilho do
    rotulo nao precisa ser fiel ao rio, so precisa acompanha-lo."""
    s = np.r_[0.0, np.cumsum(np.hypot(np.diff(X), np.diff(Y)))]
    if s[-1] < 2 * passo:
        return X, Y, s
    t = np.r_[np.arange(0, s[-1], passo), s[-1]]
    x, y = np.interp(t, s, X), np.interp(t, s, Y)
    if len(x) >= jan:
        k = np.ones(jan) / jan
        xs, ys = np.convolve(x, k, "same"), np.convolve(y, k, "same")
        m = jan // 2
        xs[:m], xs[-m:], ys[:m], ys[-m:] = x[:m], x[-m:], y[:m], y[-m:]
        x, y = xs, ys
    return x, y, np.r_[0.0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]


def _trecho(x, y, s, a, b):
    i = max(0, int(np.searchsorted(s, a)) - 1)
    j = min(len(x) - 1, int(np.searchsorted(s, b)) + 1)
    return x[i : j + 1], y[i : j + 1]


def _curvatura(x, y):
    """soma dos angulos de virada, em graus -- serve de penalidade"""
    if len(x) < 3:
        return 0.0
    dx, dy = np.diff(x), np.diff(y)
    a = np.degrees(np.arctan2(dy, dx))
    v = np.abs((np.diff(a) + 180) % 360 - 180)
    return float(v.sum())


def cx_texto(x, y, w, fs, anc="middle", dy=0.0):
    x0 = x - w / 2 if anc == "middle" else x
    return (x0, y + dy - fs * 0.82, x0 + w, y + dy + fs * 0.26)


def rotulos_serra(L):
    """(nome, x, y, ang, caixa) para cada serra/chapada nomeada"""
    out, vistos = [], set()
    for _, r in L["serras"].iterrows():
        nm = (r.nome or "").strip()
        if not nm or nm in vistos:
            continue
        vistos.add(nm)
        g = r.geometry
        if g.length * 111 < 45:
            continue
        c = np.asarray((g.geoms[0] if hasattr(g, "geoms") else g).coords)
        i = len(c) // 2
        x, y = B.xy(c[i, 0], c[i, 1])
        p1 = np.array(
            B.xy(c[min(i + 3, len(c) - 1), 0], c[min(i + 3, len(c) - 1), 1])[::-1]
        )
        p0 = np.array(B.xy(c[max(i - 3, 0), 0], c[max(i - 3, 0), 1])[::-1])
        ang = np.degrees(np.arctan2(*(p1 - p0)))
        ang = (ang + 180) % 180 - 90
        w = larg_txt(nm, 17)
        # caixa do texto girado -> retangulo envolvente
        t = np.radians(ang)
        ex = abs(w / 2 * np.cos(t)) + abs(11 * np.sin(t))
        ey = abs(w / 2 * np.sin(t)) + abs(11 * np.cos(t))
        out.append(
            (
                nm,
                float(x),
                float(y),
                float(ang),
                (x - ex, y - 6 - ey, x + ex, y - 6 + ey),
            )
        )
    return out


def rotulos_cidade(L):
    cid = pd.concat([L["cidades"][L["cidades"].nome.isin(CIDADES)], L["capital"]])
    out = []
    for _, r in cid.iterrows():
        x, y = B.xy(r.geometry.x, r.geometry.y)
        w = larg_txt(r.nome, 17)
        out.append((r.nome, float(x), float(y), (x + 5, y - 8, x + 9 + w, y + 8)))
    return out


GROSSOS = ("Rio Parnaíba", "Rio Canindé", "Rio Poti", "Rio Gurguéia", "Rio Piauí")


def rotulos_rio(L, obst):
    """Coloca o nome de cada rio do relato ao longo do curso.

    Antes o rotulo tinha corpo 19 fixo: "Ribeirão Talhado" (140 px) era escrito
    sobre 36 px de rio, e sobrava por cima de tudo o que estivesse ao lado.  Aqui
    o corpo sai do comprimento do proprio curso, quem nao cabe deitado no rio vira
    rotulo reto ao lado dele, e a posicao e escolhida por tentativa: entre uns
    tantos pontos do curso fica o que menos esbarra nos rotulos ja postos (cidades,
    serras e os outros rios) e o menos torto -- curva fechada empilha as letras.
    """
    caixas = [c for *_, c in obst]
    curvos, retos = [], []
    trilhos = {}
    for nome in RIOS_RELATO:
        g = L["dren250"][L["dren250"].nome == nome]
        if not len(g):
            continue
        u = shapely.union_all(g.geometry.values)
        m = u if u.geom_type == "LineString" else linemerge(u)
        partes = [
            p
            for p in (m.geoms if hasattr(m, "geoms") else [m])
            if p.geom_type == "LineString"
        ]
        if not partes:
            continue
        ls = max(partes, key=lambda p: p.length)
        c = np.asarray(ls.simplify(0.02).coords)
        if c[0, 0] > c[-1, 0]:
            c = c[::-1]  # texto da esquerda para a direita
        X, Y = B.xy(c[:, 0], c[:, 1])
        x, y, s = _reamostra(np.asarray(X), np.asarray(Y))
        trilhos[nome] = (x, y, s, float(s[-1]))

    for nome in sorted(trilhos, key=lambda n: -trilhos[n][3]):
        x, y, s, P = trilhos[nome]
        u = larg_txt(nome, 1.0)
        fs = min(20 if nome in GROSSOS else 16, 0.90 * P / u)
        postos = 0
        if fs >= 11:  # cabe deitado sobre o rio
            fs = round(fs)
            w = larg_txt(nome, fs)
            for f0 in [0.5] if P <= 5.5 * w else [0.30, 0.72]:
                melhor, nota = None, 1e18
                for dsl in (0, -0.08, 0.08, -0.16, 0.16, -0.24, 0.24):
                    a0 = (f0 + dsl) * P - w / 2
                    if a0 < 2 or a0 + w > P - 2:
                        continue
                    tx, ty = _trecho(x, y, s, a0, a0 + w)
                    if len(tx) < 2:
                        continue
                    cxa = (
                        tx.min() - 2,
                        ty.min() - fs * 1.05,
                        tx.max() + 2,
                        ty.max() + fs * 0.35,
                    )
                    nt = (
                        sum(_sobra(cxa, o) for o in caixas)
                        + 60 * _curvatura(tx, ty)
                        + 40 * abs(dsl)
                    )
                    if nt < nota:
                        nota, melhor = nt, (a0 + w / 2, cxa)
                if melhor is None:
                    continue
                curvos.append((nome, fs, melhor[0]))
                caixas.append(melhor[1])
                postos += 1
        if postos:
            continue
        fs = 12  # rio curto: rotulo reto ao lado
        w = larg_txt(nome, fs)
        reto, nota = None, 1e18
        for f0 in (0.5, 0.35, 0.65, 0.25, 0.75):
            i = min(max(int(np.searchsorted(s, f0 * P)), 0), len(x) - 1)
            for dx, dy in (
                (0, -fs - 5),
                (0, fs + 9),
                (-w / 2 - 10, 3),
                (w / 2 + 10, 3),
            ):
                cxa = cx_texto(x[i] + dx, y[i] + dy, w, fs)
                nt = sum(_sobra(cxa, o) for o in caixas)
                if nt < nota:
                    nota, reto = nt, (x[i] + dx, y[i] + dy, cxa)
        assert reto is not None, nome
        retos.append((nome, fs, float(reto[0]), float(reto[1])))
        caixas.append(reto[2])
    # dict, e nao set: a ordem dos <path> sai igual a cada execucao
    usados = dict.fromkeys(n for n, *_ in curvos)
    return curvos, retos, {n: trilhos[n] for n in usados}


# ---------------------------------------------------------------- camadas SVG
FR = 38  # largura da moldura da carta, em px de mapa
UF_NOME = {
    "MA": "Maranhão",
    "CE": "Ceará",
    "PE": "Pernambuco",
    "BA": "Bahia",
    "TO": "Tocantins",
    "PA": "Pará",
}


def moldura():
    """borda da carta: escada de 15' alternada, cruzes de grau e os graus escritos.
    E so geometria -- custa ~4 kB no arquivo.  A borda graduada cerca so a carta
    (de X0 para a direita); a coluna do cartucho fica dentro da linha externa,
    como um painel de titulo ao lado da estampa."""
    P = []
    add = P.append
    W, H = B.W, B.H
    X0 = B.PAD
    add('<g id="g-moldura" style="pointer-events:none">')

    # cruzes nos cruzamentos de grau inteiro
    add('<g stroke="#6b5a3e" stroke-width="1.1" opacity=".22">')
    lons = range(int(np.ceil(B.LON0)), int(np.floor(B.LON1)) + 1)
    lats = range(int(np.ceil(B.LAT1)), int(np.floor(B.LAT0)) + 1)
    for lo in lons:
        for la in lats:
            x, y = B.xy(lo, la)
            if not (X0 + FR + 6 < x < W - FR - 6 and FR + 6 < y < H - FR - 6):
                continue
            add(f'<path d="M{x - 8:.0f},{y:.0f}h16M{x:.0f},{y - 8:.0f}v16"/>')
    add("</g>")

    # escada de 15', alternada
    def escada(v0, v1, proj):
        a, b = min(v0, v1), max(v0, v1)
        cortes = (
            [a]
            + [
                v
                for v in np.arange(np.ceil(a / 0.25) * 0.25, b + 1e-9, 0.25)
                if a < v < b
            ]
            + [b]
        )
        out = []
        for i in range(len(cortes) - 1):
            p0, p1 = float(proj(cortes[i])), float(proj(cortes[i + 1]))
            if p0 > p1:
                p0, p1 = p1, p0
            m = (cortes[i] + cortes[i + 1]) / 2
            out.append((p0, p1, int(np.floor(m / 0.25)) % 2 == 0))
        return out

    add(
        f'<rect x="{X0 + FR / 2}" y="{FR / 2}" width="{W - X0 - FR}" height="{H - FR}" fill="none" '
        f'stroke="#faf3e0" stroke-width="{FR}"/>'
    )
    add('<g fill="#4a381f">')
    for p0, p1, escuro in escada(B.LON0, B.LON1, lambda v: B.xy(v, 0)[0]):
        if not escuro:
            continue
        add(
            f'<path d="M{p0:.1f},0h{p1 - p0:.1f}v{FR}h-{p1 - p0:.1f}z'
            f'M{p0:.1f},{H - FR}h{p1 - p0:.1f}v{FR}h-{p1 - p0:.1f}z"/>'
        )
    for p0, p1, escuro in escada(B.LAT1, B.LAT0, lambda v: B.xy(0, v)[1]):
        if not escuro:
            continue
        add(
            f'<path d="M{X0},{p0:.1f}h{FR}v{p1 - p0:.1f}h-{FR}z'
            f'M{W - FR},{p0:.1f}h{FR}v{p1 - p0:.1f}h-{FR}z"/>'
        )
    for cx0, cy0 in ((X0, 0), (W - FR, 0), (X0, H - FR), (W - FR, H - FR)):
        add(f'<rect x="{cx0}" y="{cy0}" width="{FR}" height="{FR}"/>')
    add("</g>")
    add(
        f'<g fill="none" stroke="#3d2d18">'
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" stroke-width="2"/>'
        f'<rect x="{X0 + FR}" y="{FR}" width="{W - X0 - 2 * FR}" height="{H - 2 * FR}" stroke-width="1.6"/>'
        f'<rect x="{X0 + FR + 5}" y="{FR + 5}" width="{W - X0 - 2 * FR - 10}" height="{H - 2 * FR - 10}" '
        f'stroke-width="0.9" opacity=".55"/></g>'
    )

    # os graus escritos, por dentro da moldura
    add(
        '<g font-family="Georgia,serif" font-size="19" fill="#5a4326" opacity=".6" '
        'text-anchor="middle" stroke="#f4ecd8" stroke-width="3" paint-order="stroke">'
    )
    for lo in lons:
        x = float(B.xy(lo, 0)[0])
        if not (X0 + FR + 30 < x < B.W - FR - 30):
            continue
        t = f"{abs(lo)}°O"
        add(f'<text x="{x:.0f}" y="{FR + 24}">{t}</text>')
        add(f'<text x="{x:.0f}" y="{H - FR - 13}">{t}</text>')
    for la in lats:
        y = float(B.xy(0, la)[1])
        if not (FR + 30 < y < B.H - FR - 30):
            continue
        t = f"{abs(la)}°S"
        add(
            f'<text transform="rotate(-90 {X0 + FR + 22} {y:.0f})" x="{X0 + FR + 22}" y="{y:.0f}">{t}</text>'
        )
        add(
            f'<text transform="rotate(-90 {W - FR - 22} {y:.0f})" x="{W - FR - 22}" y="{y:.0f}">{t}</text>'
        )
    add("</g></g>")
    return "".join(P)


def cartucho():
    """A coluna de papel a esquerda da carta: titulo, rosa dos ventos, legenda,
    escalas e a procedencia.  Ela existe por composicao -- a folha e em pe e a
    faixa livre da tela e deitada, entao sobra largura, e o lugar classico do
    titulo numa carta e justamente essa margem que sobra."""
    P = []
    add = P.append
    X0 = B.PAD
    cx = X0 / 2.0
    m0 = 78.0
    m1 = X0 - 78.0
    LARG = m1 - m0
    PXKM = B.K / 111.32  # px por km, no paralelo do meio
    add('<g id="g-cartucho" style="pointer-events:none">')
    add(f'<rect width="{X0}" height="{B.H}" fill="#f4ecd8"/>')

    def filete(y, w=LARG, losango=True):
        a, b = cx - w / 2, cx + w / 2
        g = 26 if losango else 0
        add('<g stroke="#5a4326" fill="none" opacity=".6">')
        for x0, x1 in ((a, cx - g), (cx + g, b)) if losango else ((a, b),):
            add(f'<path d="M{x0:.0f},{y:.0f}H{x1:.0f}" stroke-width="2.2"/>')
            add(f'<path d="M{x0:.0f},{y + 7:.0f}H{x1:.0f}" stroke-width="0.9"/>')
        add("</g>")
        if losango:
            add(
                f'<path d="M{cx:.0f},{y - 6:.0f}l12,10-12,10-12-10z" fill="#8a5a2b" opacity=".85"/>'
            )

    def txt(y, s, fs, x=None, anc="middle", **kw):
        at = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
        add(
            f'<text x="{(cx if x is None else x):.0f}" y="{y:.0f}" font-size="{fs}" '
            f'text-anchor="{anc}"{at}>{esc(s)}</text>'
        )

    add('<g font-family="Georgia,serif" fill="#3a2a18">')
    # ---- titulo ------------------------------------------------------------
    filete(150)
    txt(276, "DESCRIÇÃO DO SERTÃO", 86, letter_spacing=6)
    txt(410, "DO PIAUÍ", 142, letter_spacing=10)
    filete(470)
    txt(548, "que fez o padre Miguel de Carvalho", 52, font_style="italic")
    txt(612, "no ano de 1697", 52, font_style="italic")
    txt(692, "as 125 fazendas de gado do relato,", 46, opacity=".8")
    txt(744, "lançadas sobre a base cartográfica atual", 46, opacity=".8")
    txt(796, "(IBGE — BCIM 1:1.000.000 e BC250 1:250.000)", 42, opacity=".8")
    filete(856)

    # ---- rosa dos ventos ---------------------------------------------------
    ry = 1190.0
    add(f'<g transform="translate({cx:.0f},{ry:.0f})">')
    add(
        '<circle r="292" fill="none" stroke="#5a4326" stroke-width="1.6" opacity=".5"/>'
    )
    add(
        '<circle r="284" fill="none" stroke="#5a4326" stroke-width="0.9" opacity=".5"/>'
    )
    for camada in (1, 0):  # os pontos menores por baixo
        for k in range(camada, 8, 2):
            a = np.radians(k * 45.0)
            R = 258.0 if k % 2 == 0 else 152.0
            r = 60.0 if k % 2 == 0 else 42.0
            tx, ty = R * np.sin(a), -R * np.cos(a)
            l = np.radians(k * 45.0 - 90.0)
            d = np.radians(k * 45.0 + 90.0)
            ax, ay = r * np.sin(l), -r * np.cos(l)
            bx, by = r * np.sin(d), -r * np.cos(d)
            add(f'<path d="M0,0L{ax:.0f},{ay:.0f}L{tx:.0f},{ty:.0f}z" fill="#3a2a18"/>')
            add(
                f'<path d="M0,0L{tx:.0f},{ty:.0f}L{bx:.0f},{by:.0f}z" fill="#d8cba8" '
                f'stroke="#3a2a18" stroke-width="1.2"/>'
            )
    add('<circle r="34" fill="#f4ecd8" stroke="#3a2a18" stroke-width="1.6"/>')
    for k, lt in ((0, "N"), (2, "L"), (4, "S"), (6, "O")):
        a = np.radians(k * 45.0)
        px, py = 330 * np.sin(a), -330 * np.cos(a)
        add(
            f'<text x="{px:.0f}" y="{py + 16:.0f}" font-size="48" text-anchor="middle" '
            f'letter-spacing="2">{lt}</text>'
        )
    add("</g>")
    filete(1546)

    # ---- legenda -----------------------------------------------------------
    txt(1620, "Legenda", 58, letter_spacing=4, font_variant="small-caps")
    y = 1692
    passo = 86
    sx, tx0 = m0 + 8, m0 + 134

    def linha(sim, rot, fs=52, op=None):
        nonlocal y
        add(sim)
        txt(y + 15, rot, fs, x=tx0, anc="start", **({"opacity": op} if op else {}))
        y += passo

    for cor, nome in B.VEG_CORES.values():
        linha(
            f'<rect x="{sx}" y="{y - 18}" width="88" height="36" fill="{cor}" '
            f'stroke="#b6a888" stroke-width="1.2"/>',
            nome,
        )
    linha(
        f'<path d="M{sx},{y}h88" stroke="#2d6f92" stroke-width="7" stroke-linecap="round"/>',
        "rio percorrido em 1697",
    )
    linha(
        f'<path d="M{sx},{y}h88" stroke="#7fa8c4" stroke-width="2.8"/>',
        "demais cursos d’água",
    )
    linha(
        f'<path d="M{sx},{y + 8}q22,-22 44,0t44,0" fill="none" stroke="#8a7048" '
        f'stroke-width="2.4" opacity=".7"/>',
        "curva de nível (400–1200 m)",
    )
    linha(
        f'<path d="M{sx},{y + 4}q22,-16 44,-2t44,-6" fill="none" stroke="#8c5a35" '
        f'stroke-width="5" stroke-linecap="round" opacity=".7"/>',
        "serra ou chapada nomeada",
    )
    linha(
        f'<circle cx="{sx + 44}" cy="{y}" r="9" fill="#3a2a18"/>',
        "cidade de referência",
    )
    linha(
        f'<circle cx="{sx + 44}" cy="{y}" r="13" fill="#c4552a" stroke="#fff" stroke-width="3.5"/>',
        "fazenda no rio que o relato nomeia",
    )
    linha(
        f'<circle cx="{sx + 44}" cy="{y}" r="13" fill="#8a63c4" stroke="#fff" stroke-width="3.5"/>',
        "fazenda na posição da Figura 3",
    )
    filete(2706)

    # ---- escalas: em km e na unidade do proprio relato ----------------------
    txt(2782, "Escala", 54, letter_spacing=4, font_variant="small-caps")

    def barra(y0, total, passo_u, uni_km, rot, marcas):
        w = total * uni_km * PXKM
        x0 = cx - w / 2
        add('<g stroke="#3a2a18" stroke-width="1.4">')
        n = round(total / passo_u)
        for i in range(n):
            a = x0 + i * passo_u * uni_km * PXKM
            add(
                f'<rect x="{a:.1f}" y="{y0}" width="{passo_u * uni_km * PXKM:.1f}" height="34" '
                f'fill="{"#3a2a18" if i % 2 == 0 else "#f4ecd8"}"/>'
            )
        add("</g>")
        for v in marcas:
            a = x0 + v * uni_km * PXKM
            add(
                f'<path d="M{a:.1f},{y0 + 34}v10" stroke="#3a2a18" stroke-width="1.4"/>'
            )
            txt(y0 + 84, f"{v}", 40, x=a)
        txt(y0 + 84, rot, 40, x=x0 + w + 62, anc="start")

    barra(2824, 200, 50, 1.0, "km", (0, 50, 100, 150, 200))
    barra(2962, 30, 5, 6.2, "léguas", (0, 10, 20, 30))
    txt(3126, "a légua de sesmaria vale ~6,2 km em linha reta;", 38, opacity=".85")
    txt(
        3168,
        "medida ao longo dos rios, o relato de 1697 pede ~7,7 km.",
        38,
        opacity=".85",
    )
    filete(3230)

    # ---- procedencia -------------------------------------------------------
    txt(
        3300,
        "Base: BCIM 2016 (1:1.000.000) e BC250 2025 (1:250.000), IBGE;",
        38,
        opacity=".8",
    )
    txt(
        3342,
        "vegetação 1:5.000.000. Fazendas: Baptista, Os Jesuítas no",
        38,
        opacity=".8",
    )
    txt(
        3384,
        "Piauí (1986), fig. 3, com o espaçamento dado pelas léguas",
        38,
        opacity=".8",
    )
    txt(3426, "do próprio relato.", 38, opacity=".8")
    txt(
        3480,
        "Escala verdadeira no paralelo de 7° S.",
        36,
        opacity=".65",
        font_style="italic",
    )
    add("</g></g>")
    return "".join(P)


def svg_base(L):
    serras_txt = rotulos_serra(L)
    cid_txt = rotulos_cidade(L)
    rios_curvos, rios_retos, trilhos = rotulos_rio(L, cid_txt + serras_txt)

    P = []
    add = P.append
    d_pi = B.d(L["pi"], 0.002, close=True)
    add(
        f'<svg id="mapimg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {B.W} {B.H}" '
        f'width="{B.W}" height="{B.H}" shape-rendering="geometricPrecision">'
    )

    add("<defs>")
    add(f'<clipPath id="cpPI"><path d="{d_pi}"/></clipPath>')
    add(
        '<filter id="grao" x="0" y="0" width="100%" height="100%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" result="n"/>'
        '<feColorMatrix in="n" type="saturate" values="0"/>'
        '<feComponentTransfer><feFuncA type="linear" slope="0.055"/></feComponentTransfer>'
        "</filter>"
    )
    # a vegetacao e desenhada duas vezes (dentro e fora do Piaui): definida uma vez
    add('<g id="veg-def">')
    for cls, (cor, _) in B.VEG_CORES.items():
        sub = L["veg"][L["veg"].cls == cls]
        if not len(sub):
            continue
        dd = "".join(B.d(g, 0.008, close=True, prec=0) for g in sub.geometry)
        if dd:
            add(f'<path class="veg-{cls}" d="{dd}" fill="{cor}" stroke="none"/>')
    add("</g>")
    # trilhos dos rotulos de rio
    for nome, (x, y, s, _) in trilhos.items():
        pid = "r" + re.sub(r"\W", "", nome)
        add(
            f'<path id="{pid}" d="M'
            + "L".join(f"{a:.1f},{b:.1f}" for a, b in zip(x, y))
            + '" fill="none"/>'
        )
    add("</defs>")

    # ---- entorno: os estados vizinhos, no que a moldura alcanca -------------
    add(f'<rect width="{B.W}" height="{B.H}" fill="#cfdde2"/>')
    add('<g id="g-viz">')
    add('<g fill="#e9e2ce" stroke="#b6a888" stroke-width="1.6">')
    for g in L["uf"].geometry:
        add(f'<path d="{B.d(g, 0.012, close=True, prec=0)}"/>')
    add("</g>")
    add('<g id="g-veg-fora"><use href="#veg-def"/></g>')
    dd = "".join(B.d(g, 0.02, prec=0) for g in L["dren_fora"].geometry)
    add(
        f'<path d="{dd}" fill="none" stroke="#7fa8c4" stroke-width="1.3" opacity=".8"/>'
    )
    add("</g>")
    # o veu: tudo o que esta fora do Piaui recua um tom (o PI e repintado por cima)
    add(f'<rect width="{B.W}" height="{B.H}" fill="#f6efdc" opacity=".55"/>')
    # nomes dos vizinhos, ja por cima do veu
    add(
        '<g id="g-viz-txt" font-family="Georgia,serif" font-size="40" fill="#9c8a67" '
        'opacity=".75" text-anchor="middle" letter-spacing="7" style="pointer-events:none">'
    )
    for _, r in L["uf"].iterrows():
        g = r.geometry
        partes = list(g.geoms) if hasattr(g, "geoms") else [g]
        p = max(partes, key=lambda q: q.area)
        if p.area < 0.20:
            continue
        c = p.centroid if p.contains(p.centroid) else p.representative_point()
        x, y = B.xy(c.x, c.y)
        nm = UF_NOME.get(r.sigla, r.sigla).upper()
        w = larg_txt(nm, 40) + 7 * len(nm)  # com o letter-spacing
        x = min(max(float(x), B.PAD + FR + 14 + w / 2), B.W - FR - 14 - w / 2)
        y = min(max(float(y), FR + 52), B.H - FR - 22)
        add(f'<text x="{x:.0f}" y="{y:.0f}">{esc(nm)}</text>')
    add("</g>")
    add(f'<path d="{d_pi}" fill="#f4ecd8"/>')

    # ---- vegetacao ---------------------------------------------------------
    add('<g id="g-veg" clip-path="url(#cpPI)" opacity=".95"><use href="#veg-def"/></g>')

    # ---- relevo ------------------------------------------------------------
    add('<g id="g-relevo" clip-path="url(#cpPI)">')
    cv = L["curvas"]
    # so as cotas que desenham as chapadas e serras (o 100/200 m e ruido na depressao)
    for cota, larg, op in [
        (400, 1.0, 0.26),
        (500, 1.0, 0.32),
        (600, 1.2, 0.38),
        (800, 1.4, 0.46),
        (1000, 1.6, 0.52),
        (1200, 1.8, 0.58),
    ]:
        sub = cv[cv.cota == cota]
        if not len(sub):
            continue
        dd = "".join(B.d(g, 0.02, prec=0) for g in sub.geometry)
        if dd:
            add(
                f'<path d="{dd}" fill="none" stroke="#8a7048" stroke-width="{larg}" opacity="{op}"/>'
            )
    dd = "".join(B.d(g, 0.004) for g in L["serras"].geometry)
    add(
        f'<path d="{dd}" fill="none" stroke="#8c5a35" stroke-width="2.6" opacity=".55" stroke-linecap="round"/>'
    )
    add("</g>")

    # rotulos de serras e chapadas
    add(
        '<g id="g-serras-txt" font-family="Georgia,serif" font-style="italic" '
        'font-size="17" fill="#7d4f2c" opacity=".85">'
    )
    for nm, x, y, ang, _ in serras_txt:
        add(
            f'<text x="{x:.0f}" y="{y - 6:.0f}" transform="rotate({ang:.0f} {x:.0f} {y:.0f})" '
            f'text-anchor="middle">{esc(nm)}</text>'
        )
    add("</g>")

    # ---- unidades de conservacao ------------------------------------------
    add('<g id="g-uc" clip-path="url(#cpPI)">')
    for key, cor in [("uc_int", "#3f6b45"), ("uc_sus", "#6d7f4a")]:
        dd = "".join(B.d(g, 0.005, close=True) for g in L[key].geometry)
        if dd:
            add(
                f'<path d="{dd}" fill="{cor}" fill-opacity=".10" stroke="{cor}" '
                f'stroke-width="1.4" stroke-dasharray="7 4" opacity=".8"/>'
            )
    add("</g>")
    add(
        '<g id="g-uc-txt" font-family="Helvetica,Arial,sans-serif" font-size="15" '
        'fill="#3f6b45" opacity=".9" text-anchor="middle">'
    )
    for key in ("uc_int", "uc_sus"):
        for _, r in L[key].iterrows():
            c = r.geometry.representative_point()
            x, y = B.xy(c.x, c.y)
            nm = re.sub(
                r"^(Parque Nacional|Estação Ecológica|Área de Proteção Ambiental|Floresta Nacional|Reserva Extrativista(\s+Marinha)?)\s*(das|dos|da|de|do)?\s+",
                "",
                r.nome or "",
            )
            add(f'<text x="{x:.0f}" y="{y:.0f}">{esc(nm)}</text>')
    add("</g>")

    # ---- agua --------------------------------------------------------------
    add('<g id="g-agua" clip-path="url(#cpPI)">')
    dr = L["dren"]
    prin = dr.nome.isin(RIOS_RELATO_BCIM)
    dd = "".join(B.d(g, 0.006, prec=0) for g in dr[~prin].geometry)
    add(
        f'<path d="{dd}" fill="none" stroke="#7fa8c4" stroke-width="1.1" opacity=".75"/>'
    )
    dd = "".join(B.d(g, 0.004, close=True) for g in L["lagos"].geometry)
    if dd:
        add(f'<path d="{dd}" fill="#8fb8d4" stroke="#5f8fb0" stroke-width="0.8"/>')
    dd = "".join(B.d(g, 0.006, close=True) for g in L["brejo"].geometry)
    if dd:
        add(
            f'<path d="{dd}" fill="#9fbfa6" fill-opacity=".45" stroke="#7fa389" '
            f'stroke-width="0.8" stroke-dasharray="3 3"/>'
        )
    add("</g>")

    # ---- rios do relato de 1697 -------------------------------------------
    add('<g id="g-rios1697" clip-path="url(#cpPI)">')
    for nome in RIOS_RELATO:
        sub = L["dren250"][L["dren250"].nome == nome]
        if not len(sub):
            continue
        dd = "".join(B.d(g, 0.003) for g in sub.geometry)
        larg = 3.4 if nome in GROSSOS else 2.3
        add(
            f'<path d="{dd}" fill="none" stroke="#2d6f92" stroke-width="{larg}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )
    add("</g>")
    # rotulos dos rios
    add(
        '<g id="g-rios-txt" font-family="Georgia,serif" font-style="italic" fill="#1d5a7a" '
        'stroke="#f2ead6" stroke-width="3.2" stroke-opacity=".8" paint-order="stroke">'
    )
    for nome, fs, off in rios_curvos:
        pid = "r" + re.sub(r"\W", "", nome)
        add(
            f'<text dy="-5" font-size="{fs}"><textPath href="#{pid}" startOffset="{off:.0f}" '
            f'text-anchor="middle">{esc(nome)}</textPath></text>'
        )
    for nome, fs, x, y in rios_retos:
        add(
            f'<text x="{x:.0f}" y="{y:.0f}" font-size="{fs}" text-anchor="middle">{esc(nome)}</text>'
        )
    add("</g>")

    # ---- limites -----------------------------------------------------------
    add(
        '<g id="g-mun" opacity=".22" clip-path="url(#cpPI)"><path d="'
        + "".join(B.d(g, 0.012, close=True, prec=0) for g in L["mun"].geometry)
        + '" fill="none" stroke="#6b5a3e" stroke-width="0.7"/></g>'
    )
    add(f'<path d="{d_pi}" fill="none" stroke="#5a4326" stroke-width="2.6"/>')

    # ---- extracao mineral / picos -----------------------------------------
    add('<g id="g-mineral" fill="#8a5a2b" opacity=".8">')
    for _, r in L["mineral"].iterrows():
        x, y = B.xy(r.geometry.x, r.geometry.y)
        add(f'<path d="M{x:.0f},{y - 5:.0f}l5,9h-10z"/>')
    for _, r in L["picos"].iterrows():
        x, y = B.xy(r.geometry.x, r.geometry.y)
        add(f'<path d="M{x:.0f},{y - 8:.0f}l8,14h-16z" fill="#6b4a24"/>')
    add("</g>")

    # ---- cidades -----------------------------------------------------------
    add(
        '<g id="g-cidades" font-family="Helvetica,Arial,sans-serif" font-size="17" fill="#3a2a18">'
    )
    for nm, x, y, _ in cid_txt:
        add(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="4" fill="#3a2a18" stroke="#f4ecd8" stroke-width="1.5"/>'
        )
        add(
            f'<text x="{x + 7:.0f}" y="{y + 5:.0f}" stroke="#f4ecd8" stroke-width="3.5" '
            f'paint-order="stroke">{esc(nm)}</text>'
        )
    add("</g>")

    add(cartucho())
    add(moldura())
    add(
        f'<rect width="{B.W}" height="{B.H}" filter="url(#grao)" opacity=".5" '
        f'style="pointer-events:none"/>'
    )
    add("</svg>")
    return "".join(P)


# ---------------------------------------------------------------- montagem
CAM = {  # secoes sem grupo de fazendas: (lon, lat, zoom)
    0: (-43.2, -6.9, "fit"),
    1: (-43.2, -6.9, "fit"),
    2: (-43.2, -6.9, "fit"),
    3: (-42.128, -7.02, 2.4),  # Mocha / Oeiras
    4: (-41.0, -7.2, 0.9),
    5: (-44.6, -7.6, 0.9),
    6: (-42.2, -4.2, 0.9),
    7: (-43.4, -9.6, 0.9),
    8: (-43.2, -6.9, "fit"),
    33: (-42.128, -7.02, 2.3),  # Brejo da Mocha
    38: (-43.3, -7.9, 1.6),  # lagoas de sal
    40: (-42.8, -5.6, 1.0),  # rio Parnaiba
    41: (-43.2, -6.9, "fit"),
    42: (-43.2, -6.9, "fit"),
}

TROCAS = [
    (
        """o mapa ao lado — a <em>Carta Topographica e Administrativa da Provincia do Piauhy</em> (Villiers de l'Ille Adam, Rio de Janeiro, 1850) — acompanha o itinerário do padre, rio a rio, riacho a riacho. O marcador indica o ponto aproximado a que o texto se refere; trechos de localização incerta trazem a etiqueta <span class="aprox">aproximado</span>.""",
        """o mapa ao lado acompanha o itinerário do padre, rio a rio, riacho a riacho. A base é a <em>Base Cartográfica Contínua do Brasil ao milionésimo</em> (BCIM 2016, IBGE, 1:1.000.000), e os rios que o relato percorre vêm da <em>Base Cartográfica Contínua</em> 1:250.000 (BC250 2025), que os nomeia por muito mais extensão: a mesma hidrografia, o mesmo relevo e os mesmos nomes de rio que se pode conferir hoje em qualquer carta. Sobre ela vão a vegetação natural (IBGE, 1:5.000.000) e as serras e chapadas nomeadas. O marcador indica o ponto aproximado a que o texto se refere; trechos de localização incerta trazem a etiqueta <span class="aprox">aproximado</span>.""",
    ),
    (
        """As localizações seguem a identificação proposta em <em>Os Jesuítas no Piauí</em>, pp. 29–34, projetadas sobre a carta de 1850 — cerca de 150 anos posterior ao relato.""",
        """As localizações partem da Figura 3 de <em>Os Jesuítas no Piauí</em> (Baptista, 1986, p. 36), georreferenciada por ajuste da silhueta do estado contra a malha do IBGE, e são depois encaixadas no curso d'água que o próprio relato nomeia, quando esse curso ainda existe com o mesmo nome na carta de hoje. O <strong>espaçamento ao longo do rio vem do próprio texto</strong>: as 94 distâncias em léguas que o padre anota de uma fazenda à seguinte (&ldquo;dista da que se segue 3 léguas&rdquo;) são acumuladas e projetadas sobre o curso, de modo que a figura fique responsável apenas por onde a corrente de fazendas começa e para que lado corre. A legenda das cores e dos símbolos está na coluna à esquerda da carta, junto do título e das escalas.""",
    ),
]


def main():
    L = B.carrega()
    faz = pd.read_csv("dados/gerados/fazendas_1697_bcim.csv")
    X, Y = B.xy(faz.lon.values, faz.lat.values)
    faz["px"], faz["py"] = np.round(X, 1), np.round(Y, 1)

    src = pathlib.Path(SRC_HTML).read_text(encoding="utf-8")
    css = src[src.find("<style>") + 7 : src.find("</style>")]
    main_html = src[src.find("<main") : src.rfind("</main>") + 7]
    secs = re.findall(r"<section([^>]*)>(.*?)</section>", main_html, re.DOTALL)

    # grupos G9..G39 -> tabela do relato, na ordem em que aparecem
    ordem_tab = [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        8,
        None,
        25,
        26,
        27,
        28,
        None,
        29,
    ]
    grps, novas = {}, []
    it = 0
    for i, (attrs, body) in enumerate(secs):
        g = re.search(r'data-grp="(\w+)"', attrs)
        if g:
            tab = ordem_tab[it]
            it += 1
            while tab is None:
                tab = ordem_tab[it]
                it += 1
            sub = faz[faz.tabela == tab].sort_values("numero")
            grps[g.group(1)] = [
                [
                    int(r.numero),
                    float(r.px),
                    float(r.py),
                    r.fazenda,
                    {"léguas": "l", "rio_nomeado": "r", "afluente": "f"}.get(
                        r.metodo, "a"
                    ),
                    (r.rio_bcim or ""),
                    round(float(r.desloc_km), 1),
                    (None if pd.isna(r.legua_acum) else int(r.legua_acum)),
                ]
                for _, r in sub.iterrows()
            ]
            novas.append(f'<section data-grp="{g.group(1)}">')
        else:
            lon, lat, z = CAM.get(i, (-43.2, -6.9, "fit"))
            x, y = B.xy(lon, lat)
            novas.append(f'<section data-x="{x:.0f}" data-y="{y:.0f}" data-z="{z}">')
    assert len(grps) == 29, len(grps)
    n = sum(len(v) for v in grps.values())
    assert n == 125, n

    corpo = "\n".join(f"{ab}{body}</section>" for ab, (_, body) in zip(novas, secs))
    for velho, novo in TROCAS:
        assert velho in corpo, velho[:60]
        corpo = corpo.replace(velho, novo)
    # as notas que comentam a carta de 1850 nao fazem sentido sobre a base do IBGE
    corpo, n_1850 = re.subn(
        r'\n[ \t]*<p class="nota">(?:(?!</p>).)*1850(?:(?!</p>).)*</p>',
        "",
        corpo,
        flags=re.DOTALL,
    )
    assert n_1850 == 9, n_1850

    js = src[src.rfind("<script>") + 8 :].rsplit("</script>", 1)[0]
    js = js.split("const MAPW", 1)[1].split("\n", 1)[1]
    js_core = js.rsplit("})();", 1)[0].rstrip()
    # a tela agora e retrato: "fit" passa a ser caber inteiro, nao preencher
    js_core = js_core.replace(
        "function fitZoom(){return Math.max(innerWidth/MAPW, innerHeight/MAPH);}",
        "function fitZoom(){const b=folha();return Math.min(b.fw/MAPW, b.fh/MAPH);}",
    )
    js_core = js_core.replace(
        "z=Math.max(z, fitZoom()*0.9);", "z=Math.max(z, fitZoom());"
    )
    # enquadramento dos grupos: folga em px de TELA (o rotulo do ponto nao escala
    # com o zoom) e teto mais baixo -- as primeiras secoes vinham coladas demais
    js_core = js_core.replace(
        "      const pad=90;                       // folga em px de mapa, p/ r\u00f3tulos\n"
        "      z=Math.min(fw/((x1-x0)+pad), fh/((y1-y0)+pad));\n"
        "      z=Math.max(Math.min(z,3.4), 0.75);  // nem colado demais, nem longe demais",
        "      const M=170;                        // folga em px de tela, p/ r\u00f3tulos\n"
        "      z=Math.min((fw-M)/Math.max(x1-x0,1), (fh-M)/Math.max(y1-y0,1));\n"
        "      z=Math.min(z,2.4);                  // o piso vem do fitZoom() logo abaixo",
    )
    # a camera passa a ser presa a FAIXA LIVRE (a que o painel de texto nao cobre):
    # antes o mapa era obrigado a preencher a janela inteira, e grupos do leste do
    # estado (Caninde, Itaim) acabavam empurrados para debaixo do texto
    js_core = js_core.replace(
        "    let tx=cx-x*z, ty=cy-y*z;\n"
        "    const clamp=(t,view,size)=> size>=view ? Math.max(view-size, Math.min(0,t)) : (view-size)/2;\n"
        "    tx=clamp(tx, innerWidth,  MAPW*z);\n"
        "    ty=clamp(ty, innerHeight, MAPH*z);\n"
        "    wrap.style.transform=`translate(${tx}px,${ty}px) scale(${z})`;",
        "    let tx=cx-x*z, ty=cy-y*z;\n"
        "    tx=prendeX(tx, MAPW*z);\n"
        "    ty=prendeY(ty, MAPH*z);\n"
        "    setCam(tx, ty, z);",
    )
    # o marcador guarda como o ponto foi obtido
    js_core = js_core.replace(
        "    list.forEach(([n,x,y,nome])=>{\n"
        "      const d=document.createElement('div');\n"
        "      d.className='pt'; d.style.left=x+'px'; d.style.top=y+'px';\n"
        "      d.innerHTML='<i></i><b>'+n+'</b><em>'+n+' — '+nome+'</em>';",
        "    list.forEach(([n,x,y,nome,met,rio,km,lg])=>{\n"
        "      const d=document.createElement('div');\n"
        "      d.className='pt'+(met==='l'||met==='r'?'':' pt-aprox');\n"
        "      d.style.left=x+'px'; d.style.top=y+'px';\n"
        "      const info = met==='l' ? (rio+' · légua '+lg+' do relato · '+km+' km da Fig. 3')\n"
        "                 : met==='r' ? (rio+' · '+km+' km da Fig. 3')\n"
        "                 : met==='f' ? ('afluente sem nome na carta atual · posição da Figura 3')\n"
        "                             : (rio ? 'sem homônimo na carta atual · '+rio : 'posição da Figura 3');\n"
        "      d.innerHTML='<i></i><b>'+n+'</b><em>'+n+' — '+nome+'<s>'+info+'</s></em>';",
    )
    # o IntersectionObserver nao dispara em alguns contextos; rolagem tambem decide a secao
    js_core = js_core.replace(
        "  const idx=document.getElementById('indice');",
        """  let raf=0;
  addEventListener('scroll',()=>{
    if(raf) return;
    raf=setTimeout(()=>{ raf=0;
      const mid=innerHeight/2; let best=null,bd=1e9;
      for(const s of sections){
        const r=s.getBoundingClientRect();
        if(r.bottom<0||r.top>innerHeight) continue;
        const dd=Math.abs(r.top+r.height/2-mid);
        if(dd<bd){bd=dd;best=s;}
      }
      if(best&&best!==active) goTo(best);
    },60);
  },{passive:true});

  const idx=document.getElementById('indice');""",
    )

    svg = svg_base(L)
    css_extra = """
  #mapimg{display:block;width:%dpx;height:%dpx}
  /* o indice virou cabecalho do proprio texto, e nao mais uma caixa flutuante */
  #topo{position:sticky;top:0;z-index:6;display:flex;gap:8px;align-items:center;
    background:rgba(243,231,207,.97);border-bottom:1px solid rgba(43,32,19,.18);
    padding:10px 26px 9px 44px;margin:0 -26px 0 -44px}
  body.panel-left #topo{padding:10px 44px 9px 26px;margin:0 -44px 0 -26px}
  #topo select,#topo button{background:rgba(243,231,207,.95);border:1px solid rgba(43,32,19,.4);
    color:#3a2a18;border-radius:6px;padding:6px 10px;font-size:.78rem;cursor:pointer;
    font-family:'Helvetica Neue',Arial,sans-serif}
  #topo select{flex:1;min-width:0}
  #topo button:hover,#topo select:hover{background:#fff}
  /* sem o painel de camadas, as camadas que nasciam desligadas ficam desligadas */
  #g-uc,#g-uc-txt,#g-mineral,#g-mun{display:none}
  svg text{pointer-events:none;user-select:none}
  #zoomctl{position:fixed;top:52px;left:auto;right:calc(var(--panelW) + 12px);z-index:10;
    display:flex;flex-direction:column;gap:4px}
  body.panel-left #zoomctl{right:auto;left:calc(var(--panelW) + 12px)}
  @media (max-width:820px){#zoomctl,body.panel-left #zoomctl{left:auto;right:12px}}
  #zoomctl button{width:30px;height:28px;padding:0;cursor:pointer;color:#3a2a18;
    background:rgba(243,231,207,.95);border:1px solid rgba(43,32,19,.4);border-radius:4px;
    font:15px/1 'Helvetica Neue',Arial,sans-serif}
  #zoomctl button:hover{background:#fff}
  #mapwrap.zfx{transition:transform .25s ease-out}
  #viewport{cursor:grab}
  body.arrastando{cursor:grabbing;user-select:none}
  body.arrastando #viewport{cursor:grabbing}
  #mapwrap.nofx{transition:none}
  .pt-aprox i{background:#8a63c4}
  .pt em s{display:block;text-decoration:none;font-style:normal;font-size:9.5px;
    font-family:'Helvetica Neue',Arial,sans-serif;color:#6b5a3e;margin-top:2px}
""" % (B.W, B.H)  # noqa: UP031 -- CSS cheio de chaves

    out = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Descrição do Sertão do Piauí (1697) — sobre a base cartográfica atual</title>
<style>{css}{css_extra}</style>
</head>
<body>
<div id="viewport">
  <div id="mapwrap">
    {svg}
    <div id="pts"></div>
    <div id="marker" class="hidden"></div>
  </div>
</div>

<div id="zoomctl">
  <button id="zin" type="button" title="aproximar">+</button>
  <button id="zout" type="button" title="afastar">−</button>
  <button id="zfit" type="button" title="reenquadrar a seção">⟲</button>
</div>

<div id="legenda">
<b style="display:block;font-variant:small-caps;letter-spacing:.05em">As fazendas de 1697</b>
<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#c4552a;
 border:1px solid #fff;vertical-align:-1px;margin-right:4px"></span>no curso d'água que o relato
nomeia, espaçada pelas léguas do texto<br>
<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#8a63c4;
 border:1px solid #fff;vertical-align:-1px;margin-right:4px"></span>sem homônimo na carta atual —
posição da Figura 3<br>
<span style="opacity:.75">Passe o cursor sobre o ponto ou sobre o parágrafo.</span></div>

<div id="panel">
<header id="topo">
  <select id="indice" title="ir para um trecho"></select>
  <button id="sideBtn" type="button" title="trocar o painel de lado">⇄</button>
</header>
<main>
{corpo}
</main>
</div>

<script id="fazendas-json" type="application/json">{json.dumps(grps, ensure_ascii=False)}</script>
<script>
(function(){{
  const MAPW={B.W}, MAPH={B.H};
{js_core}
  /* ---- camera: a faixa livre e a parte da tela que o painel de texto nao cobre.
     Prender o mapa a ela (e nao a janela inteira) e o que impede os pontos das
     primeiras secoes de irem parar debaixo do texto.  As funcoes sao declaradas
     com `function` de proposito: goTo() ja roda antes daqui e depende do hoisting. */
  var camX=0, camY=0, camZ=1;
  /* a folha inteira -- carta, moldura e cartucho -- cabendo na faixa livre.
     Aperta mais que o freeBox() das secoes de fazenda, que precisa guardar
     folga para os rotulos dos pontos; aqui nao ha rotulo nenhum a proteger. */
  function folha(){{
    const w=innerWidth, h=innerHeight;
    if(w<=820) return {{fw:w*0.96, fh:h*0.62}};
    const pw=Math.min(430,w*0.5);
    return {{fw:(w-pw)*0.97, fh:h*0.97}};
  }}
  function faixa(){{
    const w=innerWidth;
    if(w<=820) return [0,w];
    const pw=Math.min(430,w*0.5);
    return panelSide()==='right' ? [0,w-pw] : [pw,w];
  }}
  function prendeX(t,size){{
    const [L,R]=faixa();
    return size>=R-L ? Math.max(R-size, Math.min(L,t)) : (L+R-size)/2;
  }}
  function prendeY(t,size){{
    return size>=innerHeight ? Math.max(innerHeight-size, Math.min(0,t))
                             : (innerHeight-size)/2;
  }}
  function setCam(tx,ty,z){{
    camX=tx; camY=ty; camZ=z;
    wrap.style.transform='translate('+tx+'px,'+ty+'px) scale('+z+')';
  }}
  /* folga frouxa: para arrastar e para o zoom manual basta manter um pedaco do
     mapa a vista -- e assim que se alcanca o que o painel de texto esconde */
  function solta(t,size,L,R){{
    const g=Math.min(size,150);
    return Math.max(L-size+g, Math.min(R-g, t));
  }}
  function soltaX(t,size){{ const [L,R]=faixa(); return solta(t,size,L,R); }}
  function soltaY(t,size){{ return solta(t,size,0,innerHeight); }}

  /* ---- zoom pelos botoes: o ponto do mapa que esta no centro da faixa livre
     fica parado.  Nao ha zoom pela roda do mouse de proposito -- a roda rola o
     texto, que e o que faz a leitura avancar. */
  var zfxT=0;
  function zoomRel(k){{
    const [L,R]=faixa(), cx=(L+R)/2, cy=innerHeight/2;
    const z=Math.max(fitZoom()*0.6, Math.min(6, camZ*k));
    if(Math.abs(z-camZ)<1e-4) return;
    const mx=(cx-camX)/camZ, my=(cy-camY)/camZ;
    wrap.classList.add('zfx');
    setCam(soltaX(cx-mx*z, MAPW*z), soltaY(cy-my*z, MAPH*z), z);
    curZ=z; scalePts();
    if(!marker.classList.contains('hidden')) marker.style.transform='scale('+(1/z)+')';
    clearTimeout(zfxT); zfxT=setTimeout(()=>wrap.classList.remove('zfx'),320);
  }}
  (function(){{
    const liga=(id,f)=>document.getElementById(id).addEventListener('click',f);
    liga('zin',  ()=>zoomRel(1.4));
    liga('zout', ()=>zoomRel(1/1.4));
    liga('zfit', ()=>{{ wrap.classList.remove('zfx'); if(active) goTo(active); }});
  }})();

  /* ---- arrastar o mapa com o mouse, a qualquer momento.  O #viewport fica sob o
     painel de texto, entao arrastar sobre o texto continua selecionando texto.
     A folga e frouxa (basta manter um pedaco do mapa a vista) para dar acesso ao
     que o painel esconde; o proximo goTo() reenquadra. */
  (function(){{
    const vp=document.getElementById('viewport');
    let ativo=false, px=0, py=0, ox=0, oy=0;
    vp.addEventListener('pointerdown',e=>{{
      if(e.button!==0) return;
      ativo=true; px=e.clientX; py=e.clientY; ox=camX; oy=camY;
      wrap.classList.add('nofx'); document.body.classList.add('arrastando');
      try{{ vp.setPointerCapture(e.pointerId); }}catch(_){{}}
      e.preventDefault();
    }});
    vp.addEventListener('pointermove',e=>{{
      if(!ativo) return;
      setCam(soltaX(ox+e.clientX-px, MAPW*camZ),
             soltaY(oy+e.clientY-py, MAPH*camZ), camZ);
    }});
    const larga=e=>{{
      if(!ativo) return;
      ativo=false; wrap.classList.remove('nofx');
      document.body.classList.remove('arrastando');
      try{{ vp.releasePointerCapture(e.pointerId); }}catch(_){{}}
    }};
    vp.addEventListener('pointerup',larga);
    vp.addEventListener('pointercancel',larga);
    addEventListener('pointerup',larga);          // rede de seguranca: soltar fora do mapa
    vp.addEventListener('dragstart',e=>e.preventDefault());
  }})();

}})();
</script>
</body>
</html>"""
    pathlib.Path(OUT).write_text(out, encoding="utf-8")
    print(OUT, f"{len(out) / 1e6:.2f} MB", "| canvas", B.W, "x", B.H)


if __name__ == "__main__":
    main()
