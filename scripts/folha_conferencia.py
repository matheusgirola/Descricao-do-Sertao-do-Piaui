"""
Folha de conferência das leituras feitas sobre as fontes -> qc/conferencia.html

  A. números dos 125 pontos da Figura 3 (dicionário NUMERO, lido à vista)
  B. georreferenciamento da Figura 3: rios da BC250 sobre a figura, rio a rio,
     contra uma linha de base aleatória, e o teste de deslocamento
  C. léguas do OCR (leguas.py) contra o texto conferido do relato
  D. Tabelas 1-29: nome na tabela de Baptista x nome no relato

Arquivo autocontido (a figura vai embutida em base64). Fica em qc/, fora do git.
"""

import base64
import html
import json
import pathlib
import re
import sys
import unicodedata

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from PIL import Image
from scipy import ndimage, spatial

sys.path.insert(0, "scripts")
import extrai_figura3 as E

SAIDA = pathlib.Path("qc/conferencia.html")
TEXTO = "dados/fontes/descricao_interativa_1.html"
S = 6  # ampliação dos recortes
RC = 22  # meio lado do recorte, px da figura
# grandes rios do relato (e vizinhos que a figura desenha), nomes da BC250
RIOS_TESTE = [
    "Rio Canindé",
    "Rio Piauí",
    "Rio Poti",
    "Rio Gurguéia",
    "Rio Itaim",
    "Rio Guaribas",
    "Rio Itaueira",
    "Rio Longá",
    "Rio Uruçuí-Preto",
    "Rio Sambito",
    "Rio Maratoã",
    "Rio São Nicolau",
    "Rio Berlengas",
]
KM = 111.32


def sa(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def amostra(geoms, passo=0.01):
    out = []
    for g in geoms:
        for ls in g.geoms if g.geom_type.startswith("Multi") else [g]:
            k = max(2, int(ls.length / passo) + 1)
            t = np.linspace(0, 1, k)
            out.append(
                np.array([ls.interpolate(v, normalized=True).coords[0] for v in t])
            )
    return np.vstack(out)


def georref(im):
    """ajuste da figura, rios da figura (px azuis no interior) e o teste"""
    coef, rms = E.ajuste(E.silhueta(im), E.contorno_ibge())
    a = im.astype(int)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    azul = (B > 150) & (R < 120) & (B - R > 80)
    # longe do contorno: o Parnaíba é o próprio contorno e já entrou no ajuste
    bege = (
        (abs(R - 215) < 26)
        & (abs(G - 213) < 26)
        & (abs(B - 196) < 30)
        & (R >= G)
        & (G > B)
    )
    f = ndimage.binary_fill_holes(ndimage.binary_closing(bege, np.ones((7, 7))))
    lab, n = ndimage.label(f)
    st = lab == (np.argmax(ndimage.sum(f, lab, range(1, n + 1))) + 1)
    borda = np.asarray(ndimage.distance_transform_edt(st))
    ys, xs = np.where(azul & (borda > 10))
    T = spatial.KDTree(np.c_[np.ones(len(xs)), xs, ys] @ coef)

    pi = gpd.read_file("dados/gerados/pi_uf.gpkg", layer="pi").geometry.iloc[0]
    dentro = pi.buffer(-0.1)
    bc = gpd.read_parquet("dados/gerados/drenagem_bc250.parquet")
    por_rio, todos = [], []
    for r in RIOS_TESTE:
        P = amostra(bc[bc.nome == r].geometry)
        P = P[shapely.contains_xy(dentro, P[:, 0], P[:, 1])]
        q = T.query(P)[0] * KM
        todos.append(P)
        por_rio.append((r, len(P) * 0.01 * KM, np.median(q), np.percentile(q, 90)))
    P = np.vstack(todos)
    rng = np.random.default_rng(0)
    x0, y0, x1, y1 = pi.bounds
    rp = np.c_[rng.uniform(x0, x1, 30000), rng.uniform(y0, y1, 30000)]
    rp = rp[shapely.contains_xy(dentro, rp[:, 0], rp[:, 1])]
    grade = np.round(np.arange(-0.15, 0.1501, 0.025), 3)
    M = np.array(
        # (dx, dy) = deslocamento da figura: os rios vão no sentido oposto
        [[np.median(T.query(P - [dx, dy])[0]) * KM for dx in grade] for dy in grade]
    )
    # rios da BC250 e contorno do IBGE levados para px da figura (afim inversa)
    A = np.array([coef[1], coef[2]]).T  # [lon, lat] = coef[0] + A @ [x, y]
    Ai = np.linalg.inv(A)

    def px(xy):
        return (Ai @ (np.asarray(xy) - coef[0]).T).T

    linhas = []
    for g in bc[bc.nome.isin(RIOS_TESTE + ["Rio Parnaíba"])].geometry:
        g = g.simplify(0.003)
        for ls in g.geoms if g.geom_type.startswith("Multi") else [g]:
            linhas.append(px(np.array(ls.coords)))
    cont = px(E.contorno_ibge())
    return {
        "coef": coef,
        "rms_km": rms * KM,
        "por_rio": por_rio,
        "med": float(np.median(T.query(P)[0]) * KM),
        "aleat": float(np.median(T.query(rp)[0]) * KM),
        "grade": grade,
        "M": M,
        "linhas": linhas,
        "contorno": cont,
    }


def texto_relato():
    h = pathlib.Path(TEXTO).read_text(encoding="utf-8")
    out = {}
    for n, corpo in re.findall(
        r'<p class="faz" data-n="(\d+)">(.*?)</p>', h, re.DOTALL
    ):
        bs = re.findall(r"<b>(.*?)</b>", corpo)
        out[int(n)] = (
            re.sub(r"<[^>]+>", "", bs[1]) if len(bs) > 1 else "",
            html.unescape(re.sub(r"<[^>]+>", "", corpo)),
        )
    assert sorted(out) == list(range(1, 126))
    return out


EXT = r"\d+|uma|um|duas|dois|três|quatro|cinco|seis|sete|oito|nove|dez"
RX_LEG = re.compile(rf"\b({EXT})\s+léguas?\b", re.IGNORECASE)
VAL = {
    "uma": 1,
    "um": 1,
    "duas": 2,
    "dois": 2,
    "três": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
}
VAL |= {"oito": 8, "nove": 9, "dez": 10}


def leguas_no_texto(t):
    return sorted(
        float(m) if m.isdigit() else float(VAL[m.lower()]) for m in RX_LEG.findall(t)
    )


def fmt(v):
    return "" if pd.isna(v) else f"{v:g}"


def main():
    im = np.asarray(Image.open(E.FIG).convert("RGB"))
    H, W = im.shape[:2]
    b64 = base64.b64encode(pathlib.Path(E.FIG).read_bytes()).decode()
    pts = pd.read_csv("dados/gerados/pontos_fig3_bruto.csv").set_index("numero")
    leg = pd.read_csv("dados/gerados/leguas_1697.csv").set_index("numero")
    rel = texto_relato()
    geo = georref(im)

    # ---- C: léguas do OCR x léguas do texto conferido --------------------
    diverg = []
    for n in range(1, 126):
        r = leg.loc[n]
        ocr = sorted(
            float(v) for v in (r.legua_prox, r.dist_barra, r.ref_legua) if pd.notna(v)
        )
        if ocr != leguas_no_texto(rel[n][1]):
            diverg.append(n)

    # ---- A: recortes ------------------------------------------------------
    tiles = []
    for tab, g in pts.groupby("tabela", sort=False):
        cards = []
        for n, r in g.iterrows():
            x, y = r.x_fig3, r.y_fig3
            bx, by = -(x - RC) * S, -(y - RC) * S
            par = " par" if n in (16, 37) else ""
            cards.append(
                f'<figure class="tile{par}" data-k="Ponto {n}">'
                f'<div class="crop" style="background-position:{bx:.0f}px {by:.0f}px">'
                f'<span class="ring"></span></div>'
                f"<figcaption><b>{n}</b> {html.escape(r.fazenda)}"
                f'<span class="xy">x {x:.0f} · y {y:.0f}</span></figcaption></figure>'
            )
        tiles.append(
            f"<h3>Tabela {tab} — {html.escape(g.corpo_dagua.iloc[0])}</h3>"
            f'<div class="tiles">{"".join(cards)}</div>'
        )

    # rótulos da visão geral
    rot = "".join(
        f'<circle cx="{r.x_fig3:.1f}" cy="{r.y_fig3:.1f}" r="3.2"/>'
        f'<text x="{r.x_fig3 + 4:.1f}" y="{r.y_fig3 - 3:.1f}">{n}</text>'
        for n, r in pts.iterrows()
    )

    # ---- B: georreferenciamento ------------------------------------------
    def poly(a):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in a)

    rios_svg = "".join(f'<polyline points="{poly(a)}"/>' for a in geo["linhas"])
    cont_svg = f'<polyline points="{poly(geo["contorno"][::3])}"/>'
    M, grade = geo["M"], geo["grade"]
    lo, hi = M.min(), M.max()
    cab = "".join(f"<th>{v * KM * 0.993 + 0:+.0f}</th>" for v in grade)
    corpo_grade = ""
    for i, dy in enumerate(grade[::-1]):
        row = M[::-1][i]
        tds = ""
        for j, v in enumerate(row):
            cl = ("zero " if dy == 0 and grade[j] == 0 else "") + (
                "best" if v == lo else ""
            )
            tds += (
                f'<td style="--t:{(v - lo) / (hi - lo):.3f}" class="{cl}">{v:.1f}</td>'
            )
        corpo_grade += f"<tr><th>{dy * KM + 0:+.0f}</th>{tds}</tr>"
    i_b, j_b = np.unravel_index(M.argmin(), M.shape)
    dx_b, dy_b = grade[j_b] * KM * 0.993 + 0, grade[i_b] * KM + 0
    rios_tab = "".join(
        f"<tr><td>{html.escape(r)}</td><td>{L:.0f}</td><td>{m:.1f}</td><td>{p:.1f}</td></tr>"
        for r, L, m, p in geo["por_rio"]
    )

    # ---- C: tabela das léguas ---------------------------------------------
    linhas_leg = []
    for n in range(1, 126):
        r = leg.loc[n]
        obs = []
        if r.lateral:
            obs.append(f"digressão: {r.ref_legua:g} léguas de #{int(r.ref_numero)}")
        if pd.notna(r.dist_barra):
            obs.append(f"dista da barra {r.dist_barra:g}")
        if r.na_cabeceira:
            obs.append("na cabeceira")
        if r.na_barra:
            obs.append("na barra")
        if pd.isna(r.legua_prox) and not r.lateral:
            obs.append("sem passo (última do riacho)")
        t = html.escape(rel[n][1])
        t = RX_LEG.sub(lambda m: f"<mark>{m.group(0)}</mark>", t)
        cls = ' class="div"' if n in diverg else ""
        linhas_leg.append(
            f'<tr data-k="Léguas #{n}"{cls}><td>{n}</td><td>{int(r.tabela)}</td>'
            f"<td>{html.escape(rel[n][0])}</td><td class='num'>{fmt(r.legua_prox)}</td>"
            f"<td class='num'>{fmt(r.legua_acum)}</td><td>{'; '.join(obs)}</td>"
            f'<td class="trecho">{t}</td></tr>'
        )

    # ---- D: nomes das tabelas ----------------------------------------------
    notas_nome = {
        55: "pode estar trocado com 56",
        56: "pode estar trocado com 55",
        78: "nome ausente na tabela; tirado do relato",
        88: "nome ausente na tabela; tirado do relato",
    }
    for n in range(71, 79):
        notas_nome.setdefault(
            n, "legenda das Tabelas 18–20 deslocada no PDF; corrigida"
        )
    linhas_nome = []
    for n in range(1, 126):
        r = pts.loc[n]
        nr = rel[n][0]
        dif = sa(r.fazenda) != sa(nr)
        nota = notas_nome.get(n, "")
        cls = " dif" if dif else ""
        linhas_nome.append(
            f'<tr data-k="Tabela #{n}" class="{cls.strip()}"><td>{n}</td>'
            f"<td>{int(r.tabela)}</td><td>{html.escape(str(r.corpo_dagua))}</td>"
            f"<td>{html.escape(str(r.fazenda))}</td><td>{html.escape(nr)}</td>"
            f"<td>{nota}</td></tr>"
        )
    n_dif = sum(sa(pts.loc[n, "fazenda"]) != sa(rel[n][0]) for n in range(1, 126))

    c = geo["coef"]
    esc_x, esc_y = np.hypot(*c[1]), np.hypot(*c[2])
    subs = {
        "B64": b64,
        "W": str(W),
        "H": str(H),
        "WS": str(W * S),
        "HS": str(H * S),
        "TS": str(2 * RC * S),
        "TILES": "".join(tiles),
        "ROT": rot,
        "RIOS": rios_svg,
        "CONT": cont_svg,
        "RMS": f"{geo['rms_km']:.1f}",
        "ESC": f"{esc_x:.5f} °/px em x e {esc_y:.5f} em y",
        "MED": f"{geo['med']:.1f}",
        "ALEAT": f"{geo['aleat']:.1f}",
        "BEST": f"{lo:.1f}",
        "DXB": f"{dx_b:+.1f}",
        "DYB": f"{dy_b:+.1f}",
        "CAB": cab,
        "GRADE": corpo_grade,
        "RIOSTAB": rios_tab,
        "NDIV": str(len(diverg)),
        "DIVLISTA": ", ".join(f"#{n}" for n in diverg) or "nenhuma",
        "NPASSOS": str(int(leg.legua_prox.notna().sum())),
        "LEG": "".join(linhas_leg),
        "NOMES": "".join(linhas_nome),
        "NDIF": str(n_dif),
    }
    out = MODELO
    for k, v in subs.items():
        out = out.replace("{{" + k + "}}", v)
    assert "{{" not in out, re.findall(r"\{\{\w+\}\}", out)
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(out, encoding="utf-8")
    print(f"{SAIDA}  ({SAIDA.stat().st_size / 1e6:.1f} MB)")
    print(json.dumps({"diverg_leguas": diverg, "nomes_diferentes": n_dif}))
    print(
        f"rios do relato: mediana {geo['med']:.1f} km (aleatório {geo['aleat']:.1f});"
        f" melhor deslocamento {dx_b:+.1f} km E, {dy_b:+.1f} km N -> {lo:.1f} km"
    )


MODELO = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Folha de conferência</title>
<style>
:root{--bg:#f7f5ef;--fg:#1f1d1a;--mute:#6b665d;--line:#d9d4c7;--card:#fffdf8;
--acc:#b4441c;--ok:#2f7d4f;--warn:#b07a12;--bad:#c0392b;--mark:#ffe58a;--rio:#0a6fd6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1b1a17;--fg:#ece8df;
--mute:#a29c90;--line:#3a3731;--card:#24221e;--acc:#e8835a;--mark:#6b5a12;--rio:#5fb0ff}}
:root[data-theme="dark"]{--bg:#1b1a17;--fg:#ece8df;--mute:#a29c90;--line:#3a3731;
--card:#24221e;--acc:#e8835a;--mark:#6b5a12;--rio:#5fb0ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 Georgia,serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 80px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:22px;margin:48px 0 8px;border-top:2px solid var(--fg);padding-top:12px}
h3{font:600 14px/1.3 system-ui,sans-serif;margin:24px 0 8px;color:var(--mute);text-transform:uppercase;letter-spacing:.04em}
p,li{max-width:76ch}.mute{color:var(--mute)}
nav{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);
padding:8px 0;font:14px system-ui,sans-serif;display:flex;gap:16px;flex-wrap:wrap;align-items:center}
nav a{color:var(--fg)}#cont{margin-left:auto;color:var(--acc);font-weight:600}
.box{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:12px 16px;margin:12px 0}
.verdict{font:600 15px system-ui,sans-serif}.verdict.ok{color:var(--ok)}.verdict.warn{color:var(--warn)}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax({{TS}}px,1fr));gap:10px}
.tile{margin:0;background:var(--card);border:2px solid var(--line);border-radius:6px;overflow:hidden;cursor:pointer}
.tile.par{border-color:var(--warn)}
.tile.flag{border-color:var(--bad);box-shadow:0 0 0 3px color-mix(in srgb,var(--bad) 30%,transparent)}
.crop{position:relative;width:{{TS}}px;height:{{TS}}px;margin:0 auto;
background-image:url(data:image/jpeg;base64,{{B64}});background-size:{{WS}}px {{HS}}px;background-repeat:no-repeat}
body.pix .crop{image-rendering:pixelated}
.ring{position:absolute;left:50%;top:50%;width:34px;height:34px;margin:-17px 0 0 -17px;
border:2px dashed #e0119d;border-radius:50%}
body.noring .ring{display:none}
figcaption{font:13px/1.3 system-ui,sans-serif;padding:6px 8px;display:flex;gap:6px;align-items:baseline;flex-wrap:wrap}
figcaption b{font-size:18px;color:var(--acc)}.xy{margin-left:auto;color:var(--mute);font-size:11px}
.tile.flag figcaption::after{content:"divergente";color:var(--bad);font-weight:700;width:100%}
.ctl{font:14px system-ui,sans-serif;display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin:8px 0}
.figwrap{overflow:auto;max-height:80vh;border:1px solid var(--line);border-radius:6px;background:#fff}
.figwrap svg{display:block}
#ov text{font:600 7px system-ui,sans-serif;fill:#e0119d;paint-order:stroke;stroke:#fff;stroke-width:2px}
#ov circle{fill:none;stroke:#e0119d;stroke-width:.8}
#geo .rios polyline{fill:none;stroke:#e0119d;stroke-width:1.4;stroke-linejoin:round}
#geo .cont polyline{fill:none;stroke:#111;stroke-width:1;stroke-dasharray:3 2}
table{border-collapse:collapse;font:13px/1.35 system-ui,sans-serif;width:100%}
th,td{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}
th{background:var(--bg)}
h2{scroll-margin-top:48px}
td.num{text-align:right;font-variant-numeric:tabular-nums}
td.trecho{font-family:Georgia,serif;font-size:13px;min-width:320px}
mark{background:var(--mark);color:inherit;padding:0 2px}
tr[data-k]{cursor:pointer}tr.flag td{background:color-mix(in srgb,var(--bad) 18%,transparent)}
tr.div td,tr.dif td:nth-child(4),tr.dif td:nth-child(5){background:color-mix(in srgb,var(--warn) 16%,transparent)}
.grade td{text-align:center;font-variant-numeric:tabular-nums;width:6.5%;
background:color-mix(in srgb,var(--ok) calc((1 - var(--t))*55%),transparent)}
.grade td.zero{outline:2px solid var(--fg)}.grade td.best{outline:2px dashed var(--acc);font-weight:700}
.grade th{position:static;text-align:center;font-weight:400;color:var(--mute)}
.scroll{overflow-x:auto}
textarea{width:100%;min-height:90px;font:13px ui-monospace,monospace;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:8px}
button{font:13px system-ui,sans-serif;padding:4px 10px;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:4px;cursor:pointer}
@media (max-width:640px){.crop{transform:scale(.8);transform-origin:top center;height:calc({{TS}}px*.8)}}
</style></head><body>
<main>
<h1>Folha de conferência</h1>
<p class="mute">Fontes de dados do mapa das fazendas de 1697: o que foi lido por máquina ou à vista e precisa de olho humano.
Clique num recorte ou numa linha para marcá-lo como <b>divergente</b>; a lista de marcados aparece no fim da página (e fica guardada neste navegador).</p>
<nav><a href="#a">A. Números da Figura 3</a><a href="#b">B. Georreferenciamento</a>
<a href="#c">C. Léguas</a><a href="#d">D. Nomes das tabelas</a><a href="#fim">Marcados</a><span id="cont"></span></nav>

<h2 id="a">A. Números dos pontos da Figura 3 <span class="mute">— prioridade 1</span></h2>
<div class="box"><p>A posição dos 125 pontos laranja é automática (segmentação de cor). O <b>número</b> de cada ponto
foi lido à vista, em recortes ampliados, e nada no código confere essa leitura. Em cada recorte, o ponto
em questão está no centro, dentro do círculo tracejado; confira se o rótulo impresso ao lado dele é o número da legenda.
Os pontos 16 e 37 (borda amarela) ficam a 6 px um do outro: a atribuição foi decidida pela cadeia do Canindé.</p></div>
<div class="ctl"><label><input type="checkbox" id="pix"> pixels crus (sem suavizar)</label>
<label><input type="checkbox" id="noring"> esconder círculo</label></div>
{{TILES}}
<h3>Visão geral, com os números atribuídos (magenta)</h3>
<div class="ctl"><label><input type="checkbox" id="ovon" checked> mostrar números atribuídos</label>
<label>zoom <input type="range" id="ovz" min="1" max="4" step=".25" value="1.75"></label></div>
<div class="figwrap"><svg id="ov" viewBox="0 0 {{W}} {{H}}" width="{{W}}" height="{{H}}">
<image href="data:image/jpeg;base64,{{B64}}" width="{{W}}" height="{{H}}"/><g id="ovg">{{ROT}}</g></svg></div>

<h2 id="b">B. Georreferenciamento da Figura 3 <span class="mute">— prioridade 3</span></h2>
<div class="box"><p>Ajuste automático: o contorno do Piauí na figura foi casado com o da malha do IBGE (ICP + afim);
escala {{ESC}}; RMS do contorno <b>{{RMS}} km</b>. Abaixo, os grandes rios da BC250 (magenta) e o contorno do IBGE
(tracejado preto) foram levados para dentro da figura pela transformação inversa. Se o ajuste estiver certo, o magenta
corre sobre o azul da figura — lembrando que a figura é esquemática.</p>
<p class="verdict ok">Aferição: os rios da BC250 ficam a {{MED}} km (mediana) das linhas azuis da figura;
pontos sorteados ao acaso no estado ficam a {{ALEAT}} km.</p>
<p class="verdict warn">Correção ao CLAUDE.md: a aferição antiga (“rios da figura a 1,4 km da drenagem da BCIM”) não discrimina
nada — pontos aleatórios dão os mesmos 1,4 km, porque a drenagem 1:1M é densa. O teste acima, contra os rios nomeados, é o que vale.</p></div>
<div class="ctl"><label>opacidade da figura <input type="range" id="op" min="0" max="1" step=".05" value=".85"></label>
<label><input type="checkbox" id="rioson" checked> rios BC250</label>
<label><input type="checkbox" id="conton" checked> contorno IBGE</label>
<label>zoom <input type="range" id="gz" min="1" max="4" step=".25" value="1.25"></label></div>
<div class="figwrap"><svg id="geo" viewBox="0 0 {{W}} {{H}}" width="{{W}}" height="{{H}}">
<image id="geoimg" href="data:image/jpeg;base64,{{B64}}" width="{{W}}" height="{{H}}" opacity=".85"/>
<g class="rios">{{RIOS}}</g><g class="cont">{{CONT}}</g></svg></div>
<h3>Rio a rio: distância da BC250 às linhas da figura (km)</h3>
<div class="scroll"><table style="max-width:560px"><tr><th>Rio</th><th>km no estado</th><th>mediana</th><th>p90</th></tr>{{RIOSTAB}}</table></div>
<h3>Teste de deslocamento: mediana (km) se a figura fosse deslizada</h3>
<p>Linhas: deslocamento N–S (km); colunas: deslocamento L–O (km). Contorno cheio = ajuste atual; tracejado = melhor.
O mínimo, {{BEST}} km, cai com a figura deslizada {{DXB}} km para leste e {{DYB}} km para norte: a figura georreferenciada
está uns 5 km a oeste dos rios — menos que o RMS do contorno ({{RMS}} km) e que o deslocamento mediano das fazendas (10,9 km).</p>
<div class="scroll"><table class="grade"><tr><th></th>{{CAB}}</tr>{{GRADE}}</table></div>

<h2 id="c">C. Léguas <span class="mute">— prioridade 2</span></h2>
<div class="box"><p>O <code>leguas.py</code> lê o OCR (<code>descricao_cap2_ocr.txt</code>), não o texto que você conferiu
(<code>descricao_interativa_1.html</code>). Comparação automática, entrada por entrada, de todos os números de léguas:</p>
<p class="verdict ok">{{NDIV}} divergências em 125 entradas ({{DIVLISTA}}). {{NPASSOS}} passos lidos.</p>
<p>Resta conferir a <b>interpretação</b>: que número é passo até a seguinte, distância à barra ou digressão
(#91 e #93 não consomem passo; #111 é distância à barra).</p></div>
<div class="scroll"><table><tr><th>nº</th><th>tab.</th><th>fazenda (relato)</th><th>passo</th><th>acum.</th><th>leitura</th><th>texto conferido</th></tr>{{LEG}}</table></div>

<h2 id="d">D. Nomes e números das Tabelas 1–29 <span class="mute">— conferir contra pp. 30–34</span></h2>
<div class="box"><p>Nome e número de cada fazenda vêm das tabelas de Baptista, transcritas em <code>gazetteer_corpos_dagua.csv</code>.
Ao lado, o nome que o relato dá. {{NDIF}} nomes diferem na grafia (amarelo) — quase todos variação ortográfica; o que importa é a
<b>correspondência de número</b>, sobretudo em 71–78 (legenda deslocada no PDF) e 55/56.</p></div>
<div class="scroll"><table><tr><th>nº</th><th>tab.</th><th>corpo d'água</th><th>nome na tabela</th><th>nome no relato</th><th>nota</th></tr>{{NOMES}}</table></div>

<h2 id="fim">Marcados como divergentes</h2>
<p class="mute">Copie e me envie esta lista (acrescente o número certo ao lado de cada ponto, se souber).</p>
<textarea id="lista" readonly></textarea>
<p><button id="limpa">limpar marcações</button></p>
</main>
<script>
(function(){
var KEY='conferencia-fig3-v1',sel={};
try{sel=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
var els=document.querySelectorAll('[data-k]');
function upd(){var ks=Object.keys(sel).filter(function(k){return sel[k]});
document.getElementById('lista').value=ks.join('\\n');
document.getElementById('cont').textContent=ks.length?ks.length+' marcado(s)':'';
els.forEach(function(e){e.classList.toggle('flag',!!sel[e.dataset.k])});
try{localStorage.setItem(KEY,JSON.stringify(sel))}catch(e){}}
els.forEach(function(e){e.addEventListener('click',function(){sel[e.dataset.k]=!sel[e.dataset.k];upd()})});
document.getElementById('limpa').onclick=function(){sel={};upd()};
function chk(id,f){var c=document.getElementById(id);c.onchange=function(){f(c.checked)};f(c.checked)}
chk('pix',function(v){document.body.classList.toggle('pix',v)});
chk('noring',function(v){document.body.classList.toggle('noring',v)});
chk('ovon',function(v){document.getElementById('ovg').style.display=v?'':'none'});
chk('rioson',function(v){document.querySelector('#geo .rios').style.display=v?'':'none'});
chk('conton',function(v){document.querySelector('#geo .cont').style.display=v?'':'none'});
function zoom(id,svg){var r=document.getElementById(id),s=document.getElementById(svg);
function z(){s.setAttribute('width',{{W}}*r.value);s.setAttribute('height',{{H}}*r.value)}r.oninput=z;z()}
zoom('ovz','ov');zoom('gz','geo');
var op=document.getElementById('op');op.oninput=function(){document.getElementById('geoimg').setAttribute('opacity',op.value)};
upd();
})();
</script></body></html>
"""

if __name__ == "__main__":
    main()
