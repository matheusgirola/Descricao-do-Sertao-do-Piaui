"""Gera a base cartografica vetorial (SVG) do Piaui a partir da BCIM 2016 +
vegetacao IBGE 1:5.000.000.  Usado por monta_mapa.py."""

import unicodedata

import geopandas as gpd
import numpy as np
import shapely

GPKG = "dados/ibge/bcim_2016_21_11_2018.gpkg"
VEG = "dados/ibge/veg5000/Vegetacao_5000.shp"

# --- enquadramento (equirretangular; 1 px = 1/K grau) -----------------------
# A folga lateral (~0,95 grau) e a faixa em que aparecem os estados vizinhos, em
# tom ofuscado.  Ao norte e ao sul ela e menor (~0,5 grau) de proposito: a folha
# e em pe e a faixa livre da tela e deitada, entao e a ALTURA que limita o zoom
# de abertura -- cada grau de folga vertical encolhe o Piaui na tela.
LON0, LON1 = -46.95, -39.40
LAT0, LAT1 = -2.25, -11.45
K = 390.0
COS = np.cos(np.radians((LAT0 + LAT1) / 2))
# ... e a largura que sobra: PAD e uma coluna de papel a esquerda da carta, onde
# vao o titulo, a rosa dos ventos, a legenda e as escalas (ver cartucho()).
PAD = 1480
W = round((LON1 - LON0) * COS * K) + PAD
H = round((LAT0 - LAT1) * K)


def xy(lon, lat):
    return ((np.asarray(lon) - LON0) * COS * K + PAD, (LAT0 - np.asarray(lat)) * K)


def d(geom, tol=0.0, close=False, prec=1):
    """geometria -> atributo d de <path>"""
    if geom is None or geom.is_empty:
        return ""
    if tol:
        geom = geom.simplify(tol)
    out = []
    for g in geom.geoms if hasattr(geom, "geoms") else [geom]:
        rings = []
        if g.geom_type == "Polygon":
            rings = [g.exterior] + list(g.interiors)
        elif g.geom_type == "LineString":
            rings = [g]
        else:
            continue
        for r in rings:
            c = np.asarray(r.coords)
            if len(c) < 2:
                continue
            X, Y = xy(c[:, 0], c[:, 1])
            X = np.round(X, prec)
            Y = np.round(Y, prec)
            keep = np.r_[True, (np.diff(X) != 0) | (np.diff(Y) != 0)]
            X, Y = X[keep], Y[keep]
            if len(X) < 2:
                continue
            out.append(
                "M"
                + "L".join(f"{a:g},{b:g}" for a, b in zip(X, Y))
                + ("Z" if close else "")
            )
    return "".join(out)


def _fix(s):
    """dbf gravado em utf-8 e lido como latin-1"""
    try:
        return str(s).encode("latin1").decode("utf-8")
    except UnicodeError:
        return str(s)


def sem_acento(s):
    return (
        unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    )


# --- classes de vegetacao ---------------------------------------------------
def classe_veg(cls, prim):
    t = sem_acento(
        cls
        if cls
        and "agraria" not in sem_acento(cls)
        and "secundaria" not in sem_acento(cls)
        else (prim or cls)
    )
    if "massa dagua" in t:
        return None
    if "pioneira" in t or "marinha" in t:
        return "pioneira"
    if "/" in t or "contato" in t or "tensao" in t:
        return "contato"
    if "savana-estepica" in t or "savana estepica" in t:
        return "caatinga"
    if "floresta" in t:
        return "floresta"
    if "savana" in t:
        return "cerrado"
    return "contato"


VEG_CORES = {
    "caatinga": ("#e2d3ae", "caatinga (savana-estépica)"),
    "cerrado": ("#d6dcb4", "cerrado (savana)"),
    "floresta": ("#bfd0ad", "floresta estacional / mata seca"),
    "contato": ("#dcd8b2", "contato / tensão ecológica"),
    "pioneira": ("#ece0c4", "formações pioneiras (litoral)"),
}


def carrega():
    """devolve um dicionario de camadas ja recortadas para o Piaui + entorno"""
    pi = gpd.read_file("dados/gerados/pi_uf.gpkg", layer="pi").geometry.iloc[0]
    bb = (LON0, LAT1, LON1, LAT0)
    quadro = shapely.box(LON0, LAT1, LON1, LAT0)
    L = {}
    L["pi"] = pi
    L["quadro"] = quadro
    uf = gpd.read_file(GPKG, layer="lim_unidade_federacao_a", engine="pyogrio", bbox=bb)
    uf = uf[uf.sigla != "PI"].copy()
    uf["geometry"] = uf.geometry.intersection(quadro).difference(pi)
    L["uf"] = uf[~uf.geometry.is_empty]
    mun = gpd.read_file(GPKG, layer="lim_municipio_a", engine="pyogrio", bbox=bb)
    L["mun"] = mun[mun.intersects(pi)]  # o desenho e recortado no PI de qualquer forma

    dr = gpd.read_parquet("dados/gerados/drenagem_bbox.parquet")
    dr = dr[dr.intersects(quadro)]
    L["dren"] = dr[dr.intersects(pi.buffer(0.18))]

    # A drenagem de fundo continua vindo da BCIM — 18 mil trechos generalizados,
    # que e o que cabe num HTML autocontido. Mas os pontos de 1697 sao encaixados
    # na BC250 (ver scripts/snap_rios.py), cujo tracado nao coincide com o da BCIM:
    # desenhados sobre a BCIM, os marcadores flutuariam ao lado do rio. Por isso
    # os rios que o relato percorre — e so eles — vem da BC250, que e tambem a
    # linha que os rotulos acompanham.
    d2 = gpd.read_parquet("dados/gerados/drenagem_bc250.parquet")
    L["dren250"] = d2[d2.nome.notna() & d2.intersects(quadro)]

    # entorno: so os cursos de porte, senao a faixa dos vizinhos pesa mais que o
    # proprio Piaui no arquivo (11,6 mil trechos, 330 kB) e ainda compete com ele
    fora = dr[~dr.intersects(pi.buffer(0.02))].copy()
    fora["geometry"] = fora.geometry.intersection(quadro)
    fora = fora[~fora.geometry.is_empty]
    tot = (fora.geometry.length * 111).groupby(fora.nome.fillna("")).sum()
    manter = {n for n in tot[tot >= 60].index if n}
    L["dren_fora"] = fora[fora.nome.isin(manter)]

    for lyr, key in [
        ("hid_massa_dagua_a", "lagos"),
        ("hid_terreno_sujeito_inundacao_a", "brejo"),
        ("rel_elemento_fisiografico_natural_l", "serras"),
        ("rel_curva_nivel_l", "curvas"),
        ("lim_unidade_protecao_integral_a", "uc_int"),
        ("lim_unidade_uso_sustentavel_a", "uc_sus"),
        ("eco_ext_mineral_p", "mineral"),
        ("rel_pico_p", "picos"),
        ("loc_cidade_p", "cidades"),
        ("loc_capital_p", "capital"),
    ]:
        g = gpd.read_file(GPKG, layer=lyr, engine="pyogrio", bbox=bb)
        L[key] = g[g.intersects(pi.buffer(0.12))] if len(g) else g

    v = gpd.read_file(VEG, engine="pyogrio")
    v = v[v.intersects(quadro)].copy()
    v["cls"] = [
        classe_veg(_fix(a), _fix(b) if b else None)
        for a, b in zip(v.DSC_CLASS_, v.DSC_VEG_PR)
    ]
    v = v[v.cls.notna()]
    v["geometry"] = v.geometry.intersection(quadro)
    L["veg"] = v[~v.geometry.is_empty]
    return L
