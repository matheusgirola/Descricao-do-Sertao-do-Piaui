"""
Afere o mapa contra as tres distancias que o relato de 1697 da FORA da cadeia
de fazendas — as unicas medidas do texto que nao entraram na construcao do mapa
e que por isso podem julga-lo.

As tres, no texto (OCR em descricao_cap2_ocr.txt, linhas 122-165):

  A. "da qual [a fazenda do Taboleiro Alto] a nova Matriz de Nossa Senhora da
     Vitoria se contam 60 leguas, povoadas com fazendas de gados pelo mesmo
     riacho do Piaui abaixo"
     -> 60 leguas descendo o rio Piaui e depois cortando para a Matriz. A Matriz
        de Nossa Senhora da Vitoria e a atual Oeiras, que nasceu Nossa Senhora
        da Vitoria do Mocha e nao fica sobre o Piaui: o percurso e composto.

  B. "Para a parte do sul, confina esta povoacao com o rio de Sao Francisco,
     para o qual tem dois caminhos com distancia igual de 40 leguas cada um
     [...] Estas 40 leguas se contam [...] da ultima fazenda desta povoacao,
     chamada o Taboleiro Alto"
     -> 40 leguas por terra. O texto nomeia o destino: "vai sair do rio Sao
        Francisco a uma fazenda chamada o Sobrado, 10 leguas acima do Santo Se",
        que nao e o ponto do rio mais proximo em linha reta.

  C. "Distara esta Serra [da Ibiapaba] das ultimas fazendas dos Alongazes, que
     pertencem a esta Freguesia, 20 leguas"
     -> 20 leguas por terra. As fazendas dos Alongazes sao as das tabelas 21 a
        23 (Maratauam, das Cobras e Bitorocara): o relato abre o bloco com "a
        terra dos Alongazes esta por detras destes riachos" e o fecha com
        "muitos mais sitios se tem descoberto nesta terra dos Alongazes".

B e C sao medidas por terra e leem-se contra a legua de sesmaria (~6,2 km em
linha reta); so A tem um trecho por agua. Nenhuma delas move ponto nenhum.
Rodar depois de snap_rios.py.
"""

import json

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.ops import linemerge

KM = 111.32
GPKG = "dados/ibge/bcim_2016_21_11_2018.gpkg"
BBOX = (-46.7, -11.2, -39.7, -2.5)
LEGUA = 6.2  # legua de sesmaria, km em linha reta
OEIRAS = (-42.13108, -7.02444)  # a Matriz de Nossa Senhora da Vitoria do Mocha


def tronco(dr, nome):
    """o curso continuo mais longo com esse nome"""
    u = shapely.union_all(list(dr[dr.nome == nome].geometry.values))
    m = u if u.geom_type == "LineString" else linemerge(u)
    p = [
        g
        for g in (m.geoms if hasattr(m, "geoms") else [m])
        if g.geom_type == "LineString"
    ]
    return max(p, key=lambda g: g.length)


def linha(rot, leguas, km, base, obs=""):
    print(
        f"  {rot:<46s} {leguas:2d} léguas  {km:5.0f} km   {km / leguas:5.1f} km/légua"
        f"   {100 * (km / leguas / base - 1):+4.0f}%"
    )
    if obs:
        print("      " + obs)


def main():
    faz = pd.read_csv("dados/gerados/fazendas_1697_bcim.csv").set_index("numero")
    dr = gpd.read_parquet("dados/gerados/drenagem_bc250.parquet")
    with open("dados/gerados/escala_global.json") as f:
        esc = json.load(f)
    print(
        f"O mapa foi construído com a escala global de {esc['km_por_legua']:.1f} km"
        f" de rio por légua (mediana de {len(esc['amostra'])} grupos)."
    )
    print(
        f"A légua de sesmaria vale ~{LEGUA:.1f} km em linha reta; as três âncoras abaixo"
    )
    print("não entraram nessa conta e servem para conferi-la de fora.\n")
    print(
        f"  {'âncora':<46s} {'o texto':<9s} {'o mapa':>8s} {'implica':>16s}"
        f" {'vs 6,2':>8s}"
    )

    tab = faz.loc[90]  # a fazenda do Taboleiro Alto
    P90 = shapely.points(tab.lon, tab.lat)

    # ---- A. Taboleiro Alto -> Matriz da Vitoria (Oeiras) -------------------
    piaui = tronco(dr, "Rio Piauí")
    d_rio = abs(piaui.project(shapely.points(*OEIRAS)) - piaui.project(P90)) * KM
    d_ter = shapely.distance(shapely.points(*OEIRAS), piaui) * KM
    linha(
        "A. Taboleiro-Alto → Matriz, Piauí abaixo",
        60,
        d_rio + d_ter,
        LEGUA,
        f"{d_rio:.0f} km descendo o rio + {d_ter:.0f} km por terra até a Matriz.",
    )

    # ---- B. Taboleiro Alto -> rio Sao Francisco ---------------------------
    sf = shapely.union_all(list(dr[dr.nome == "Rio São Francisco"].geometry.values))
    d_sf = shapely.distance(P90, sf) * KM
    linha(
        "B. Taboleiro-Alto → rio São Francisco",
        40,
        d_sf,
        LEGUA,
        f"não fecha: o texto pede ~{40 * LEGUA:.0f} km e o mapa dá {d_sf:.0f}. O ponto medido é o\n"
        "      trecho de rio mais próximo em linha reta, e não o Sobrado que o relato\n"
        "      nomeia como fim do caminho — que fica bem mais para jusante.",
    )

    # ---- C. fazendas dos Alongazes -> serra da Ibiapaba -------------------
    ib = gpd.read_file(
        GPKG, layer="rel_elemento_fisiografico_natural_l", engine="pyogrio", bbox=BBOX
    )
    ib = shapely.union_all(
        list(ib[ib.nome.fillna("").str.contains("Ibiapaba")].geometry.values)
    )
    alo = faz[faz.tabela.isin([21, 22, 23])]
    d = np.sort(
        [
            shapely.distance(shapely.points(r.lon, r.lat), ib) * KM
            for _, r in alo.iterrows()
        ]
    )
    linha(
        "C. Alongazes → serra da Ibiapaba (mediana)",
        20,
        float(np.median(d)),
        LEGUA,
        f"as {len(d)} fazendas dos Alongazes ficam de {d[0]:.0f} a {d[-1]:.0f} km"
        " da serra; o texto\n"
        f"      pede ~{20 * LEGUA:.0f} km, que cai dentro dessa faixa.",
    )


if __name__ == "__main__":
    main()
