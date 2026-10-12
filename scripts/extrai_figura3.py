"""
Figura 3 de "Os Jesuítas no Piauí" (Baptista, 1986, p. 36) -> 125 pontos em lat/lon.

  1. extrai o raster da figura de dentro do PDF (609x916 px)
  2. segmenta os 125 pontos laranja por cor
  3. aplica a leitura visual dos rótulos numéricos (dicionario NUMERO abaixo)
  4. georreferencia: silhueta do estado x malha do IBGE (BCIM), ICP + ajuste afim
  5. junta os nomes das fazendas (gazetteer_corpos_dagua.csv)

Saida: dados/gerados/pontos_fig3_bruto.csv
"""

import pathlib

import geopandas as gpd
import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader
from pypdf.generic import DictionaryObject, StreamObject
from scipy import ndimage, spatial
from shapely.geometry import LineString, MultiPolygon

PDF = "dados/fontes/OS_JESUÍTAS_NO_PIAUÍ-33-38.pdf"  # recorte com a figura na 1a pagina
SAIDA = "dados/gerados/pontos_fig3_bruto.csv"
FIG = "dados/gerados/figura3.jpg"

# numero impresso ao lado de cada ponto (lido em recortes 8x) -> posicao (x, y) do
# ponto em px. Cada blob recebe o numero do vizinho mais proximo, de modo que a
# leitura nao depende da ordem em que a segmentacao encontra os blobs.
NUMERO = {
    1: (557.6, 627.6),
    2: (544.1, 619.7),
    3: (509.2, 606.0),
    4: (494.6, 597.1),
    5: (480.6, 590.5),
    6: (469.9, 578.4),
    7: (446.7, 556.2),
    8: (440.1, 539.2),
    9: (438.9, 519.8),
    10: (435.8, 510.4),
    11: (424.5, 490.0),
    12: (412.5, 485.0),
    13: (400.5, 481.5),
    14: (390.4, 475.6),
    15: (385.3, 467.7),
    16: (373.5, 457.3),
    17: (361.9, 448.3),
    18: (360.1, 440.7),
    19: (360.0, 424.0),
    20: (346.0, 415.8),
    21: (568.5, 617.2),
    22: (533.1, 601.7),
    23: (486.3, 541.5),
    24: (475.0, 518.8),
    25: (448.5, 504.0),
    26: (441.9, 499.6),
    27: (431.2, 498.8),
    28: (529.4, 457.1),
    29: (514.8, 457.0),
    30: (500.6, 462.1),
    31: (495.2, 485.2),
    32: (486.9, 496.7),
    33: (460.4, 506.7),
    34: (455.0, 474.0),
    35: (423.8, 465.7),
    36: (399.6, 456.4),
    37: (377.9, 461.6),
    38: (435.6, 573.5),
    39: (427.8, 562.3),
    40: (426.0, 545.2),
    41: (394.0, 518.0),
    42: (374.4, 473.4),
    43: (544.5, 275.2),
    44: (510.0, 264.0),
    45: (471.4, 277.6),
    46: (429.8, 319.0),
    47: (413.6, 328.6),
    48: (401.7, 342.5),
    49: (384.9, 330.2),
    50: (367.1, 308.1),
    51: (352.0, 286.1),
    52: (520.2, 309.6),
    53: (457.6, 317.6),
    54: (529.0, 331.5),
    55: (501.7, 322.0),
    56: (484.0, 322.6),
    57: (468.6, 345.4),
    58: (435.1, 326.2),
    59: (545.6, 374.9),
    60: (496.4, 359.1),
    61: (452.0, 357.2),
    62: (423.5, 355.0),
    63: (496.9, 386.6),
    64: (465.2, 395.0),
    65: (515.9, 407.3),
    66: (477.7, 416.9),
    67: (417.2, 384.3),
    68: (414.1, 345.7),
    69: (485.6, 440.9),
    70: (462.7, 429.3),
    71: (449.0, 446.3),
    72: (445.7, 437.5),
    73: (442.1, 426.7),
    74: (427.6, 416.4),
    75: (398.5, 441.6),
    76: (381.6, 397.2),
    77: (389.0, 356.2),
    78: (366.8, 326.3),
    79: (408.6, 288.2),
    80: (414.2, 249.3),
    81: (415.4, 220.0),
    82: (410.1, 192.9),
    83: (471.5, 250.0),
    84: (422.7, 256.0),
    85: (368.9, 288.3),
    86: (384.7, 264.9),
    87: (403.0, 257.8),
    88: (539.8, 638.8),
    89: (298.6, 718.1),
    90: (385.5, 682.8),
    91: (342.2, 735.7),
    92: (456.4, 662.9),
    93: (406.0, 654.0),
    94: (403.1, 638.9),
    95: (393.1, 629.7),
    96: (388.2, 615.4),
    97: (376.0, 608.0),
    98: (368.7, 598.4),
    99: (362.6, 582.7),
    100: (364.7, 567.4),
    101: (372.0, 550.0),
    102: (365.4, 515.6),
    103: (367.7, 496.4),
    104: (356.4, 485.6),
    105: (356.4, 479.4),
    106: (354.6, 472.8),
    107: (354.1, 466.5),
    108: (353.5, 454.2),
    109: (323.4, 573.8),
    110: (342.8, 543.5),
    111: (355.0, 504.0),
    112: (340.1, 538.4),
    113: (340.0, 521.5),
    114: (333.9, 500.3),
    115: (325.7, 495.5),
    116: (296.0, 586.5),
    117: (319.8, 541.9),
    118: (333.8, 460.1),
    119: (214.2, 649.6),
    120: (241.3, 626.1),
    121: (235.1, 600.6),
    122: (245.4, 555.6),
    123: (255.0, 533.5),
    124: (260.6, 505.1),
    125: (273.8, 475.4),
}
# nomes que a tabela do PDF nao traz e o texto de 1697 esclarece
NOMES = {78: "Santo Antônio", 88: "Fazenda de Éguas"}


def figura():
    """figura3.jpg e o fluxo DCT do PDF tal como esta, sem recodificar. O
    pypdf.images regrava o JPEG (e a qualidade muda com a versao do pypdf), e a
    segmentacao muda com ele; o fluxo cru, lido pelo Pillow, da sempre os 125."""
    res = PdfReader(PDF).pages[0]["/Resources"]
    assert isinstance(res, DictionaryObject)
    xo = res["/XObject"]
    assert isinstance(xo, DictionaryObject)
    fl = [o for v in xo.values() if isinstance(o := v.get_object(), StreamObject)]
    st = max(fl, key=lambda o: len(o.get_data()))
    assert st["/Filter"] == ["/DCTDecode"], st["/Filter"]
    pathlib.Path(FIG).write_bytes(st.get_data())
    with Image.open(FIG) as im:
        return np.asarray(im.convert("RGB"))


def pontos(im):
    a = np.asarray(im).astype(int)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    m = (R > 150) & (G > 50) & (G < 170) & (B < 110) & (R - B > 70) & (R - G > 50)
    lab, n = ndimage.label(m)
    tam = ndimage.sum(m, lab, range(1, n + 1))
    fica = [i + 1 for i in range(n) if tam[i] >= 5]
    c = np.array(ndimage.center_of_mass(m, lab, fica))  # (y, x)
    return c[np.lexsort((c[:, 1], c[:, 0]))]


def silhueta(im):
    a = np.asarray(im).astype(int)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    bege = (
        (abs(R - 215) < 26)
        & (abs(G - 213) < 26)
        & (abs(B - 196) < 30)
        & (R >= G)
        & (G > B)
    )
    # 7x7: com 5x5 os rios que saem do estado ficam abertos, o contorno segue o
    # traçado deles e o ICP desanda
    f = ndimage.binary_fill_holes(ndimage.binary_closing(bege, np.ones((7, 7))))
    lab, n = ndimage.label(f)
    st = lab == (np.argmax(ndimage.sum(f, lab, range(1, n + 1))) + 1)
    ys, xs = np.where(st ^ ndimage.binary_erosion(st))
    return np.c_[xs, ys].astype(float)


def contorno_ibge():
    pi = gpd.read_file("dados/gerados/pi_uf.gpkg", layer="pi").geometry.iloc[0]
    ps = list(pi.geoms) if isinstance(pi, MultiPolygon) else [pi]
    ls = LineString(max(ps, key=lambda g: g.area).exterior.coords)
    return np.array(
        [ls.interpolate(d).coords[0] for d in np.arange(0, ls.length, 0.01)]
    )


def umeyama(A, B):
    ca, cb = A.mean(0), B.mean(0)
    Ac, Bc = A - ca, B - cb
    U, S, Vt = np.linalg.svd(Ac.T @ Bc / len(A))
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    Rm = Vt.T @ np.diag([1, d]) @ U.T
    s = (S * np.array([1, d])).sum() / (Ac**2).sum() * len(A)
    return s, Rm, cb - s * Rm @ ca


def ajuste(P, Q):
    """P: contorno da figura em px; Q: contorno do IBGE em lon/lat. -> coef afim"""
    Pm = P.copy()
    Pm[:, 1] = -Pm[:, 1]
    cp, sp = Pm.mean(0), np.sqrt(((Pm - Pm.mean(0)) ** 2).sum(1).mean())
    cq, sq = Q.mean(0), np.sqrt(((Q - Q.mean(0)) ** 2).sum(1).mean())
    X = (Pm - cp) / sp * sq + cq
    tree = spatial.KDTree(Q)
    for _ in range(60):
        d, i = tree.query(X)
        m = d <= np.percentile(d, 90)
        s, Rm, t = umeyama(X[m], Q[i[m]])
        X = s * (Rm @ X.T).T + t
    d, i = tree.query(X)
    m = d <= np.percentile(d, 92)
    A = np.c_[np.ones(m.sum()), P[m, 0], P[m, 1]]
    coef, *_ = np.linalg.lstsq(A, Q[i[m]], rcond=None)
    return coef, float(np.sqrt((d**2).mean()))


def main():
    im = figura()
    cen = pontos(im)
    assert len(cen) == 125, len(cen)
    assert sorted(NUMERO) == list(range(1, 126))
    ref = np.array(list(NUMERO.values()))  # (x, y)
    d, blob = spatial.KDTree(cen[:, ::-1]).query(ref)
    assert len(set(blob)) == 125, "dois numeros no mesmo ponto"
    assert d.max() < 3, d.max()

    coef, rms = ajuste(silhueta(im), contorno_ibge())
    print(f"ajuste afim: RMS do contorno = {rms:.4f}° ({rms * 111:.1f} km)")
    print(
        f"escala {np.hypot(*coef[1]):.5f} °/px (x), {np.hypot(*coef[2]):.5f} °/px (y)"
    )

    linhas = []
    for num, b in zip(NUMERO, blob):
        y, x = cen[b]
        lon, lat = np.array([1, x, y]) @ coef
        linhas.append(
            {
                "numero": num,
                "x_fig3": round(float(x), 2),
                "y_fig3": round(float(y), 2),
                "lon_fig": round(float(lon), 6),
                "lat_fig": round(float(lat), 6),
            }
        )
    df = pd.DataFrame(linhas).sort_values("numero").reset_index(drop=True)

    g = pd.read_csv("dados/fontes/gazetteer_corpos_dagua.csv")
    g = g[g.tabela.astype(str).str.match(r"^\d+$")]
    nm = []
    for _, r in g.iterrows():
        a, b = (
            (r.fazendas_num.split("-") + [r.fazendas_num])[:2]
            if "-" in r.fazendas_num
            else (r.fazendas_num, r.fazendas_num)
        )
        a, b = int(a), int(b)
        fz = [s.strip() for s in str(r.fazendas).split(";")]
        assert len(fz) == b - a + 1, (r.tabela, len(fz))
        for k, n in enumerate(range(a, b + 1)):
            nm.append(
                {
                    "numero": n,
                    "fazenda": NOMES.get(n, fz[k]),
                    "corpo_dagua": r.corpo_dagua,
                    "tabela": int(r.tabela),
                }
            )
    df = df.merge(pd.DataFrame(nm), on="numero", how="left")
    assert df.fazenda.notna().all()
    df.to_csv(SAIDA, index=False)
    print(SAIDA, len(df))


if __name__ == "__main__":
    main()
