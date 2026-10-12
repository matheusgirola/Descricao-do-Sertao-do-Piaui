"""
Baixa a drenagem da Base Cartografica Continua 1:250.000 (BC250, IBGE) para o
retangulo do Piaui, via WFS do geoservicos.ibge.gov.br.

Motivo: a BCIM (1:1.000.000) nomeia pouca drenagem — oito dos 29 corpos d'agua
de 1697 nao tem homonimo nela, e as fazendas desses grupos ficam sem nada em
que projetar as leguas do relato. A BC250 nomeia muito mais.

Saida: dados/gerados/drenagem_bc250.parquet  (colunas: id, nome, geometry)
"""

import http.client
import json
import sys
import time
import urllib.parse
import urllib.request

import geopandas as gpd
from shapely.geometry import shape

WFS = "https://geoservicos.ibge.gov.br/geoserver/ows"
CAMADA = "CCAR:BC250_2025_hid_trecho_drenagem_l"
BBOX = (-46.7, -11.2, -39.7, -2.5)  # Piaui + folga (a mesma do mapa)
PAGINA = 5000
SAIDA = "dados/gerados/drenagem_bc250.parquet"


def url(**extra):
    q = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": CAMADA,
        "srsName": "EPSG:4674",
        "bbox": "{},{},{},{},EPSG:4674".format(*BBOX),
    }
    q.update(extra)
    return WFS + "?" + urllib.parse.urlencode(q)


def busca(u):
    """o WFS do IBGE cai de vez em quando; repete algumas vezes antes de desistir."""
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(u, timeout=300) as r:
                return r.read()
        except (OSError, http.client.HTTPException) as e:
            print(f"   ...falha ({type(e).__name__}), repetindo", file=sys.stderr)
            time.sleep(5 * (tentativa + 1))
    raise SystemExit("WFS nao respondeu: " + u)


def main():
    # quantas feicoes o servidor diz que existem — serve de conferencia no fim
    cab = busca(url(resultType="hits")).decode("utf-8", "replace")
    total = int(cab.split('numberMatched="')[1].split('"')[0])
    print(f"o WFS declara {total} trechos no retângulo")

    # o GeoServer nao aceita sortBy nesta camada; a paginacao vai por
    # startIndex e os ids sao guardados para remover eventuais repetidos
    vistos, feicoes, start = set(), [], 0
    while True:
        js = json.loads(
            busca(url(outputFormat="application/json", count=PAGINA, startIndex=start))
        )
        f = js["features"]
        print(f"  {start:6d}–{start + len(f):<6d}  {len(f):5d} feições")
        for x in f:
            if x["id"] in vistos or not x.get("geometry"):
                continue
            vistos.add(x["id"])
            feicoes.append(
                (x["id"], (x["properties"] or {}).get("nome"), shape(x["geometry"]))
            )
        if len(f) < PAGINA:
            break
        start += PAGINA

    dr = gpd.GeoDataFrame(
        {"id": [a for a, _, _ in feicoes], "nome": [b for _, b, _ in feicoes]},
        geometry=[g for _, _, g in feicoes],
        crs="EPSG:4674",
    )
    dr = dr[dr.geometry.notna() & ~dr.geometry.is_empty].reset_index(drop=True)
    if len(dr) < 0.98 * total:
        raise SystemExit(f"baixou {len(dr)} de {total} trechos — paginação incompleta")
    dr.to_parquet(SAIDA)
    print(f"\n{len(dr)} trechos (de {total}) -> {SAIDA}")
    print(f"{dr.nome.notna().sum()} com nome, {dr.nome.nunique()} nomes distintos")


if __name__ == "__main__":
    main()
