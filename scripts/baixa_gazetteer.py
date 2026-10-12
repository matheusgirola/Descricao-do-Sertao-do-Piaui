"""
Baixa o indice de nomes da BC250 (IBGE) no retangulo do Piaui — o gazetteer
da carta: todo toponimo que a base carrega, com a classe do objeto a que
pertence (trecho_drenagem, localidade, elemento fisiografico, serra...).

Serve a duas coisas:
  - achar o curso d'agua atual dos oito riachos de 1697 que a BCIM nao nomeia;
  - achar as FAZENDAS de 1697 que sobreviveram como povoado, fazenda ou serra
    homonima, o que da uma ancora de posicao absoluta independente da Figura 3.

Saida: dados/gerados/gazetteer_bc250.parquet (nomeousigla, classe, siglacategoria, siglauf, geometry)
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
CAMADA = "CCAR:BC250_2025_indice_nomes"
BBOX = (-46.7, -11.2, -39.7, -2.5)
PAGINA = 5000
SAIDA = "dados/gerados/gazetteer_bc250.parquet"
CAMPOS = ["nomeousigla", "classe", "siglacategoria", "siglauf"]


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
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(u, timeout=300) as r:
                return r.read()
        except (OSError, http.client.HTTPException) as e:
            print(f"   ...falha ({type(e).__name__}), repetindo", file=sys.stderr)
            time.sleep(5 * (tentativa + 1))
    raise SystemExit("WFS nao respondeu: " + u)


def main():
    cab = busca(url(resultType="hits")).decode("utf-8", "replace")
    total = int(cab.split('numberMatched="')[1].split('"')[0])
    print(f"o WFS declara {total} nomes no retângulo")

    vistos, linhas, geoms, start = set(), [], [], 0
    while True:
        js = json.loads(
            busca(url(outputFormat="application/json", count=PAGINA, startIndex=start))
        )
        f = js["features"]
        print(f"  {start:6d}–{start + len(f):<6d}  {len(f):5d} nomes")
        for x in f:
            if x["id"] in vistos or not x.get("geometry"):
                continue
            vistos.add(x["id"])
            p = x["properties"] or {}
            linhas.append({c: p.get(c) for c in CAMPOS})
            geoms.append(shape(x["geometry"]))
        if len(f) < PAGINA:
            break
        start += PAGINA

    gz = gpd.GeoDataFrame(linhas, geometry=geoms, crs="EPSG:4674")
    if len(gz) < 0.98 * total:
        raise SystemExit(f"baixou {len(gz)} de {total} nomes — paginação incompleta")
    gz.to_parquet(SAIDA)
    print(f"\n{len(gz)} nomes -> {SAIDA}")
    print(gz.classe.value_counts().to_string())


if __name__ == "__main__":
    main()
