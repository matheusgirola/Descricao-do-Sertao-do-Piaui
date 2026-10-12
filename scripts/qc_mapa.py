"""Gera imagens de conferencia: a base + os 125 pontos, ligados por um traco
a posicao original lida na Figura 3."""

import os
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, "scripts")
import numpy as np
import pandas as pd

import base_svg as B

SAIDA = "qc"


def main():
    h = pathlib.Path("descricao_interativa_bcim.html").read_text(encoding="utf-8")
    i = h.find('<svg id="mapimg"')
    j = h.find("</svg>", i)
    core = h[i:j].split(">", 1)[1]
    f = pd.read_csv("dados/gerados/fazendas_1697_bcim.csv")
    X, Y = B.xy(f.lon.values, f.lat.values)
    Xo, Yo = B.xy(f.lon_fig3.values, f.lat_fig3.values)
    g = []
    for x0, y0, x1, y1 in zip(Xo, Yo, X, Y):
        g.append(
            f'<line x1="{x0:.0f}" y1="{y0:.0f}" x2="{x1:.0f}" y2="{y1:.0f}" stroke="#999" stroke-width="1.5"/>'
        )
    for x, y in zip(Xo, Yo):
        g.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="none" stroke="#888" stroke-width="1.5"/>'
        )
    for x, y, n, m in zip(X, Y, f.numero, f.metodo):
        c = {"léguas": "#c4361a", "rio_nomeado": "#d98f2a", "afluente": "#2a7fb8"}.get(
            m, "#8a4bd0"
        )
        g.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="{c}" stroke="#fff" stroke-width="1.6"/>'
            f'<text x="{x + 8:.0f}" y="{y + 5:.0f}" font-size="17" font-family="Helvetica" fill="#000" '
            f'stroke="#fff" stroke-width="3" paint-order="stroke">{n}</text>'
        )
    core += "".join(g)
    os.makedirs(SAIDA, exist_ok=True)

    # As vistas saem dos proprios pontos, e nao de um viewBox escrito a mao:
    # a coluna do cartucho (B.PAD) ja deslocou a estampa uma vez, e as vistas
    # fixas ficaram enquadrando o Maranhao. Aqui basta dizer QUE grupos olhar.
    def vista(tabs=None, folga=90):
        m = np.ones(len(f), bool) if tabs is None else np.asarray(f.tabela.isin(tabs))
        xs = np.r_[X[m], Xo[m]]
        ys = np.r_[Y[m], Yo[m]]
        # quadrada: a miniatura do qlmanage e quadrada e corta o que sobra
        lado = max(np.ptp(xs), np.ptp(ys)) + 2 * folga
        lado = max(lado, 260.0)
        cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        return cx - lado / 2, cy - lado / 2, lado, lado

    vistas = {
        "qc_geral": vista(),
        "qc_itaim": vista([2, 3]),  # o grupo que mais mudou com a BC250
        "qc_tranqueira": vista([8, 16, 17]),  # maior deslocamento em relacao a figura
        "qc_poti": vista([9, 18, 19, 20]),
        "qc_maratoa": vista([21]),  # mudou com a troca do codec da Figura 3
        "qc_caninde": vista([1, 24, 7]),
        "qc_piaui": vista([25, 26, 12]),
        "qc_sul": vista([27, 28, 29]),
    }
    tmp = []
    for nm, (x, y, w, hh) in vistas.items():
        p = f"{SAIDA}/{nm}.svg"
        tmp.append(p)
        pathlib.Path(p).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:.0f} {y:.0f} {w:.0f} {hh:.0f}" '
            f'width="{w:.0f}" height="{hh:.0f}">' + core + "</svg>"
        )
    if shutil.which("qlmanage"):
        subprocess.run(
            ["qlmanage", "-t", "-s", "1600", "-o", SAIDA] + tmp,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    print("gerado em", SAIDA)


if __name__ == "__main__":
    main()
