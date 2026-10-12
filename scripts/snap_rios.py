"""
Reposiciona os 125 pontos da Figura 3 (Baptista, 1986, p. 36 — fazendas visitadas
por Miguel de Carvalho em 1697) sobre a hidrografia real da BC250 2025
(IBGE, Base Cartografica Continua do Brasil, 1:250.000).

Etapas
  1. o ponto bruto vem do georreferenciamento afim da Figura 3 (dados/gerados/pontos_fig3_bruto.csv)
  2. cada corpo d'agua de 1697 e associado ao(s) nome(s) correspondente(s) na carta
  3. os trechos com esse nome sao filtrados pela vizinhanca do grupo (elimina homonimos)
     e encadeados num tronco unico (linemerge + costura gulosa pelos extremos)
  4. o ESPACAMENTO das fazendas ao longo do tronco vem das distancias em leguas
     dadas pelo proprio relato (dados/gerados/leguas_1697.csv); a Figura 3 entra so para
     ancorar e orientar a cadeia no rio (ajuste robusto de s = a + b*legua_acum)
  5. sem leguas utilizaveis -> referenciamento linear + regressao isotonica
  6. sem homonimo na carta -> encaixe no curso d'agua mais proximo (raio curto)
  7. nada disso -> fica a posicao da Figura 3

Por que a BC250 e nao a BCIM (1:1.000.000), que continua sendo a base de DESENHO
do mapa: a BCIM nomeia pouco curso d'agua, e o encaixe depende justamente do
campo `nome`. Na BC250 quinze dos vinte e um rios do relato tem tronco nomeado
mais longo — o rio Itaim passa de 66 para 220 km, o Poti de 327 para 555, a
Tranqueira de 72 para 150 —, e e sobre esse tronco que as leguas do texto sao
projetadas. Quanto mais rio nomeado, menos a cadeia depende da Figura 3.

Cuidado que a troca de carta exigiu: a BC250 desenha o mesmo rio com mais
meandros que a BCIM, de modo que o mesmo percurso mede de 1,10 a 1,21 vez mais
quilometros — e nao na mesma proporcao para todos os rios. Tomada crua, a escala
"km de rio por legua" passaria a medir a resolucao da carta em vez do terreno.
Por isso as leguas sao projetadas sobre o tronco GENERALIZADO (TOL_TRONCO), que
devolve a regua da BCIM, e o ponto e assentado no tracado real so no fim.

Saida: dados/gerados/fazendas_1697_bcim.csv e dados/gerados/escala_global.json
"""

import json
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import LineString
from shapely.ops import linemerge, nearest_points

KM = 111.32  # graus -> km na latitude do Piaui
DRENAGEM = "dados/gerados/drenagem_bc250.parquet"  # BC250 2025 (baixa_bc250.py)
CAP_GENERICO = 6.0  # raio do encaixe generico (km)
# quilometros de rio por legua do relato. A legua de sesmaria vale ~6,2 km em
# linha reta; medida ao longo de um curso sinuoso, o valor sobe. Os limites
# abaixo impedem que um grupo mal posicionado na Figura 3 estique ou comprima
# a cadeia para uma escala impossivel.
#
# A faixa e um pouco mais larga do que era na BCIM (4 a 16): a generalizacao
# abaixo iguala as duas reguas, mas sobra ~7% de sinuosidade que a BC250 ve e a
# BCIM nao.
B_LO, B_HI = 4.0, 18.0  # faixa plausivel ao estimar a escala global
# ...e por isso as leguas nao sao projetadas sobre o tracado cheio da BC250, e
# sim sobre o tronco GENERALIZADO a esta tolerancia. Sem isso "km de rio por
# legua" deixaria de ser uma grandeza do terreno e passaria a medir a resolucao
# da carta: o mesmo percurso rende 1,10 a 1,21 vez mais quilometros na BC250 que
# na BCIM, e nao uniformemente — quem mede o rio com passo mais curto acha o rio
# mais longo. Generalizado a ~445 m a regua volta a coincidir com a da BCIM
# (razao 1,00 a 1,07) e o ganho de cobertura, que e o que interessa, permanece.
# 445 m e muito menos que o passo do relato (uma legua, ~6 km) e que o erro da
# Figura 3 (~1,4 km); o ponto ainda assim e assentado no tracado real no fim.
TOL_TRONCO = 0.004  # graus (~445 m)
BANDA = (0.6, 1.8)  # quanto um grupo pode fugir da escala global
# no encaixe generico evita-se pendurar a fazenda num rio grande de outra bacia:
# se houver um curso menor dentro do raio, ele tem preferencia
GRANDES = {
    "Rio Parnaíba",
    "Rio Canindé",
    "Rio Piauí",
    "Rio Poti",
    "Rio Gurguéia",
    "Rio Itaueira",
    "Rio Longá",
    "Rio Uruçuí-Preto",
    "Rio Paraim",
    "Rio Itaim",
    "Rio Berlengas",
    "Rio Maratoã",
    "Rio Sambito",
    "Rio Fidalgo",
    "Represa da Boa Esperança",
}

# tabela do relato -> (nomes na BC250, raio de busca dos trechos km,
#                      deslocamento maximo aceito km, nota)
#
# Os oito grupos com lista vazia sao os corpos d'agua cujo nome de 1697 nao
# existe mais. Nao e falta de detalhe da carta: procurados no indice de nomes
# inteiro da BC250 — drenagem, povoados, serras, lagoas —, "Cabeca do Tapuio",
# "Sao Vitor", "Bitorocara" e "Guaribas" do sul nao aparecem em lugar nenhum do
# Piaui, e "Santa Catarina", "Santo Antonio", "das Cobras" e "do Buriti" so
# aparecem de 70 a 500 km dali, em outra bacia. Sao toponimos que morreram em
# 330 anos; carta de escala maior nao os traz de volta.
RIOS = {
    1: (["Rio Canindé"], 40, 30, "identificação direta"),
    2: (["Rio Itaim"], 30, 20, "Itaim Mirim = rio Itaim atual"),
    3: (["Rio Guaribas"], 30, 25, "identificação direta"),
    4: (["Riacho do Frade", "Rio do Frade"], 25, 20, "identificação direta"),
    5: (["Ribeirão Talhado"], 25, 20, "Serra Talhada = ribeirão Talhado"),
    6: (
        ["Rio Corrente", "Riacho Corrente", "Riacho da Corrente", "Riacho do Corrente"],
        25,
        20,
        "identificação direta",
    ),
    7: (
        ["Riacho do Mocambo", "Riacho Mocambo", "Rio Mocambo"],
        30,
        25,
        "identificação direta",
    ),
    8: (
        ["Ribeirão da Tranqueira", "Riacho Tranqueira", "Riacho da Tranqueira"],
        50,
        45,
        "as 5 fazendas somam ~9 léguas no relato",
    ),
    9: (["Rio Poti"], 35, 25, "o “Itaim Açu” da Figura 3 é o rio Poti"),
    10: (["Rio do Cais"], 25, 25, "identificação direta"),
    11: ([], 0, 0, "topônimo perdido: não existe na BC250"),
    12: (
        ["Riacho Iningá", "Riacho da Ininga"],
        45,
        40,
        "a fazenda 58 “Iningas” fixa o riacho",
    ),
    13: (["Rio São Nicolau"], 30, 25, "identificação direta"),
    14: (["Riacho Vitória"], 25, 25, "identificação direta"),
    15: (["Riacho da Serra Negra"], 25, 20, "a fazenda 64 “Serra Negra”"),
    16: ([], 0, 0, "topônimo perdido: não existe na BC250"),
    17: ([], 0, 0, "topônimo perdido: não existe na BC250"),
    18: (["Rio São Vicente", "Riacho São Vicente"], 25, 20, "identificação direta"),
    19: (["Rio Berlengas"], 30, 25, "a BC250 grafa “Berlengas”; a BCIM, “Beriengas”"),
    20: ([], 0, 0, "topônimo perdido: não existe na BC250"),
    21: (["Rio Maratoã"], 35, 30, "Maratauam = rio Marataoã/Maratoã"),
    22: ([], 0, 0, "topônimo perdido: não existe na BC250"),
    23: ([], 0, 0, "topônimo perdido: não existe na BC250"),
    24: ([], 0, 0, "topônimo perdido: não existe na BC250"),
    25: (["Rio Piauí"], 85, 80, "as 20 fazendas percorrem o rio inteiro"),
    26: (["Riacho do Mucaitá", "Rio Mucaitá"], 30, 25, "Moicatá = riacho Mucaitá"),
    27: (["Rio Itaueira"], 35, 30, "identificação direta"),
    28: ([], 0, 0, "topônimo perdido: não existe na BC250"),
    29: (["Rio Gurguéia"], 40, 30, "identificação direta"),
}


def troncos(geoms, tol=0.03):
    """Costura os trechos em troncos: linemerge + encadeamento guloso pelos
    extremos. Devolve uma lista de troncos, do mais longo para o mais curto —
    homonimos em bacias diferentes saem como troncos separados."""
    u = shapely.union_all(list(geoms))
    m = u if u.geom_type == "LineString" else linemerge(u)
    partes = [
        g
        for g in (m.geoms if hasattr(m, "geoms") else [m])
        if g.geom_type == "LineString" and len(g.coords) > 1
    ]
    partes.sort(key=lambda g: -g.length)
    pool = [np.array(p.coords) for p in partes]
    saida = []
    while pool:
        cur = pool.pop(0)
        mudou = True
        while mudou and pool:
            mudou = False
            for i, B in enumerate(pool):
                for ia, ib in ((0, -1), (0, 0), (-1, 0), (-1, -1)):
                    if np.hypot(*(cur[ia] - B[ib])) < tol:
                        a = cur[::-1] if ia == 0 else cur
                        b = B if ib == 0 else B[::-1]
                        cur = np.vstack([a, b[1:]])
                        pool.pop(i)
                        mudou = True
                        break
                if mudou:
                    break
        saida.append(LineString(cur))
    saida.sort(key=lambda g: -g.length)
    return saida


def costura(geoms, tol=0.03):
    """compatibilidade: so o tronco mais longo."""
    t = troncos(geoms, tol)
    return t[0], t


def isotonica(y, w=None):
    """regressao isotonica crescente (pool adjacent violators)."""
    y = np.asarray(y, float)
    n = len(y)
    w = np.ones(n) if w is None else np.asarray(w, float)
    val, wt, idx = [], [], []
    for i in range(n):
        val.append(y[i])
        wt.append(w[i])
        idx.append(1)
        while len(val) > 1 and val[-2] > val[-1]:
            v2, w2, n2 = val.pop(), wt.pop(), idx.pop()
            v1, w1, n1 = val.pop(), wt.pop(), idx.pop()
            val.append((v1 * w1 + v2 * w2) / (w1 + w2))
            wt.append(w1 + w2)
            idx.append(n1 + n2)
    out = np.empty(n)
    k = 0
    for v, c in zip(val, idx):
        out[k : k + c] = v
        k += c
    return out


def e_confluencia(tronco, sinal, arv, nomes, alvos, tol_km=2.0):
    """A ponta de jusante do tronco e uma confluencia (encontra outro curso
    d'agua) ou apenas o ponto em que a BCIM deixa de nomear o rio?"""
    c = tronco.coords[-1] if sinal > 0 else tronco.coords[0]
    pt = shapely.points(*c)
    biz = arv.query(pt.buffer(tol_km / KM))
    return any(
        nomes[k] not in alvos and shapely.distance(pt, arv.geometries[k]) * KM <= tol_km
        for k in biz
    )


def assenta(s, tronco, cheio):
    """Posicao ao longo do tronco generalizado -> ponto sobre o tracado real.

    A medida corre no tronco generalizado (regua estavel, ver TOL_TRONCO), mas o
    ponto que vai para o mapa tem de cair em cima da linha que o mapa desenha —
    entre uma coisa e outra ha, no maximo, a propria tolerancia da
    generalizacao: ~445 m, ou 1,5 px na escala da carta."""
    q = tronco.interpolate(s)
    return nearest_points(cheio, q)[0]


def reta(x, y):
    """inclinacao de y = a + b*x por minimos quadrados.

    Preferida a um ajuste robusto (mediana das inclinacoes par a par): num
    grupo em que a Figura 3 acerta as pontas mas erra o espacamento interno —
    o Gurgueia e o caso limite — o ajuste robusto segue as pernas do meio e
    devolve o dobro da escala verdadeira; os minimos quadrados, que dao peso
    as pontas, devolvem a escala que o vao total do grupo implica."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    v = np.var(x)
    b = float(np.cov(x, y, bias=True)[0, 1] / v) if v > 0 else 0.0
    return b, float(np.mean(y) - b * np.mean(x))


def espaca(s, comprimento, minimo):
    """Separa posicoes empatadas ao longo do rio (a regressao isotonica funde
    violadores num mesmo valor), mantendo a ordem e o intervalo do grupo."""
    s = np.asarray(s, float).copy()
    n = len(s)
    if n < 2:
        return np.clip(s, 0, comprimento)
    cresce = s[-1] >= s[0]
    t = s if cresce else -s
    Lmax = comprimento if cresce else 0.0
    Lmin = 0.0 if cresce else -comprimento
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(t[j + 1] - t[i]) < 1e-12:
            j += 1
        k = j - i + 1
        if k > 1:  # bloco empatado de k pontos
            lo = t[i - 1] if i > 0 else Lmin
            hi = t[j + 1] if j + 1 < n else Lmax
            passo = min(minimo, (hi - lo) / (k + 1))
            centro = t[i]
            base = centro - passo * (k - 1) / 2
            base = min(max(base, lo + passo / 2), hi - passo * (k - 0.5))
            for m in range(k):
                t[i + m] = base + m * passo
        i = j + 1
    s = t if cresce else -t
    return np.clip(s, 0, comprimento)


def prepara(tab, grp, lg, nomes, geoms):
    """Monta o contexto de um grupo: tronco do rio nomeado, projecao dos pontos
    da Figura 3 nele e as leguas acumuladas do relato."""
    alvos, maxkm, cap, nota = RIOS[tab]
    grp = grp.sort_values("numero").reset_index(drop=True)
    P = shapely.points(grp.lon_fig.values, grp.lat_fig.values)
    env = shapely.union_all(P)
    L = lg.reindex(grp.numero.values)

    # o tronco e a COMPONENTE CONEXA do rio nomeado mais proxima do grupo.
    # (filtrar trecho a trecho por distancia truncava rios longos — o Gurgueia
    # perdia 250 dos seus 529 km — e com isso reintroduzia o erro da figura.)
    tronco = cheio = None
    if alvos:
        sel = np.isin(nomes, alvos)
        if sel.any():
            comp = troncos(geoms[sel])
            d_comp = np.array([shapely.distance(t, env) for t in comp]) * KM
            cand = [k for k in range(len(comp)) if d_comp[k] <= maxkm]
            if cand:
                # `cheio` e o tracado da BC250 como esta na carta — e nele que o
                # ponto e assentado no fim. `tronco` e o mesmo curso generalizado,
                # e e nele que se mede: ver TOL_TRONCO.
                cheio = comp[max(cand, key=lambda k: comp[k].length)]
                tronco = cheio.simplify(TOL_TRONCO)

    k: dict[str, Any] = {
        "tab": tab,
        "grp": grp,
        "P": P,
        "L": L,
        "alvos": alvos,
        "cap": cap,
        "nota": nota,
        "tronco": tronco,
        "cheio": cheio,
        "c_leg": L.legua_acum.values,
        "e_afl": L.lateral.values.astype(bool),
        "na_barra": L.na_barra.values.astype(bool),
        "na_cabec": L.na_cabeceira.values.astype(bool),
        "ok": np.zeros(len(grp), bool),
        "usa_leg": False,
        "s": None,
        "sinal": 1.0,
    }

    if tronco is not None:
        d_tr = np.array([shapely.distance(p, tronco) for p in P]) * KM
        ok = (d_tr <= cap) & ~k["e_afl"]
        k["ok"] = ok
        if ok.any():
            s = np.array([tronco.project(p) for p in P])
            k["s"] = s
            if ok.sum() >= 2:
                k["sinal"] = (
                    1.0
                    if np.corrcoef(grp.numero.values[ok], s[ok])[0, 1] >= 0
                    else -1.0
                )
            k["usa_leg"] = (
                ok.sum() >= 2
                and np.isfinite(k["c_leg"][ok]).all()
                and np.ptp(k["c_leg"][ok]) > 0
            )
    return k


def escala_global(ctxs):
    """km de rio por legua. A legua de sesmaria vale ~6,2 km em linha reta; ao
    longo de um curso sinuoso o valor sobe. Estima-se um valor unico a partir
    dos grupos grandes e bem comportados, e depois cada grupo so pode
    afastar-se dele dentro de uma banda — assim um grupo que a Figura 3 amontoa
    ou espalha nao consegue inventar uma escala impossivel."""
    amostra = []
    for k in ctxs:
        if not k["usa_leg"]:
            continue
        cc, ss = k["c_leg"][k["ok"]], k["s"][k["ok"]]
        b = abs(reta(cc, ss)[0]) * KM
        if k["ok"].sum() >= 4 and np.ptp(cc) >= 5 and B_LO <= b <= B_HI:
            amostra.append(b)
    return float(np.median(amostra)), amostra


def main():
    df = pd.read_csv("dados/gerados/pontos_fig3_bruto.csv")
    lg = pd.read_csv("dados/gerados/leguas_1697.csv").set_index("numero")
    dr = gpd.read_parquet(DRENAGEM).reset_index(drop=True)
    nomes = dr.nome.fillna("").values
    geoms = dr.geometry.values
    arv = shapely.STRtree(geoms)

    ctxs = [
        prepara(tab, grp, lg, nomes, geoms)
        for tab, grp in df.groupby("tabela", sort=True)
    ]
    B_STAR, amostra = escala_global(ctxs)
    b_lo, b_hi = BANDA[0] * B_STAR, BANDA[1] * B_STAR
    print(
        f"escala: {B_STAR:.1f} km de rio por légua (mediana de {len(amostra)} grupos:"
        f" {', '.join(f'{x:.1f}' for x in sorted(amostra))})"
    )
    print(f"banda aceita por grupo: {b_lo:.1f} a {b_hi:.1f} km/légua\n")
    with open("dados/gerados/escala_global.json", "w") as f:
        json.dump(
            {"km_por_legua": B_STAR, "amostra": sorted(amostra), "banda": [b_lo, b_hi]},
            f,
            indent=1,
        )

    linhas = []
    for k in ctxs:
        tab, grp, P, _L = k["tab"], k["grp"], k["P"], k["L"]
        alvos, cap, nota, tronco = k["alvos"], k["cap"], k["nota"], k["tronco"]
        cheio = k["cheio"]
        c_leg, e_afl, ok = k["c_leg"], k["e_afl"], k["ok"]
        km_leg, ancora = np.nan, ""

        lon = grp.lon_fig.values.copy()
        lat = grp.lat_fig.values.copy()
        metodo = np.array(["figura3"] * len(grp), dtype=object)
        rio = np.array([""] * len(grp), dtype=object)

        if tronco is not None:
            if k["usa_leg"]:
                # ESPACAMENTO POR LEGUAS. A posicao ao longo do tronco e
                # s = a + b*legua_acum: o relato da o espacamento (b vem da
                # escala global, ajustada dentro da banda) e a ancora (a), quando
                # diz que a ultima fazenda esta na barra ou a primeira na
                # cabeceira. A Figura 3 entra so para o rumo e, na falta de
                # ancora textual, para prender a cadeia no rio.
                s, sinal = k["s"], k["sinal"]
                cc, ss = c_leg[ok], s[ok]
                b, _ = reta(cc, ss)
                b = sinal * min(max(abs(b) * KM, b_lo), b_hi) / KM
                if abs(b) * np.ptp(cc) > tronco.length:  # cadeia maior que o tronco
                    b = sinal * tronco.length / np.ptp(cc)
                a = float(np.mean(ss - b * cc))

                i_ok = np.where(ok)[0]
                fim = tronco.length if sinal > 0 else 0.0
                ini = 0.0 if sinal > 0 else tronco.length
                # a ancora textual so vale se nao brigar com a Figura 3 mais do
                # que o deslocamento maximo aceito para o grupo: o relato da o
                # espacamento, a figura continua sendo a unica fonte de posicao.
                a_b = fim - b * cc[-1]
                a_c = ini - b * cc[0]
                if (
                    k["na_barra"][i_ok[-1]]
                    and abs(a_b - a) * KM <= cap
                    and e_confluencia(tronco, sinal, arv, nomes, alvos)
                ):
                    a, ancora = a_b, "barra"
                elif k["na_cabec"][i_ok[0]] and abs(a_c - a) * KM <= cap:
                    a, ancora = a_c, "cabeceira"

                s_leg = a + b * cc
                s_leg -= min(0.0, s_leg.min())  # encaixa dentro do tronco
                s_leg -= max(0.0, s_leg.max() - tronco.length)
                s_leg = np.clip(s_leg, 0, tronco.length)
                km_leg = abs(b) * KM
                pos = [assenta(v, tronco, cheio) for v in s_leg]
                lon[ok] = [q.x for q in pos]
                lat[ok] = [q.y for q in pos]
            elif ok.sum() >= 3:
                # sem leguas utilizaveis: referenciamento linear + isotonica
                s, sinal = k["s"], k["sinal"]
                s_iso = sinal * isotonica(sinal * s[ok])
                vao = abs(s_iso[-1] - s_iso[0]) * KM
                s_iso = espaca(
                    s_iso, tronco.length, minimo=max(1.5, vao / (2.5 * len(s_iso))) / KM
                )
                pos = [assenta(v, tronco, cheio) for v in s_iso]
                lon[ok] = [q.x for q in pos]
                lat[ok] = [q.y for q in pos]
            else:
                for i in np.where(ok)[0]:
                    s_i = k["s"][i]
                    # grupo de uma fazenda so: nao deixa encostar na ponta do
                    # curso (a foz costuma ser um no onde varios rios se tocam)
                    if len(grp) == 1:
                        s_i = min(max(s_i, 0.08 * tronco.length), 0.92 * tronco.length)
                    q = assenta(s_i, tronco, cheio)
                    lon[i], lat[i] = q.x, q.y
            metodo[ok] = "léguas" if k["usa_leg"] else "rio_nomeado"
            rio[ok] = " / ".join(alvos)

        # Fazendas de afluente: sao digressoes do relato — o texto nao as poe no
        # curso principal, mas a tantas leguas de uma fazenda nomeada, num
        # riacho que a BCIM nao nomeia (o Inhinhinga e o riachinho do
        # Buqueirao). Sem o riacho, nao ha em que encaixar: ficam na posicao da
        # Figura 3, marcadas a parte, e o relato entra so na etiqueta.
        # (Projeta-las pelo rumo da figura a tantas leguas da fazenda de
        # referencia jogava a #91 para fora do estado — a figura, que as poe no
        # proprio Piaui, nao da rumo confiavel para isso.)
        for i in np.where(e_afl)[0]:
            metodo[i] = "afluente"

        # fallback: curso d'agua mais proximo (qualquer nome), raio curto
        for i in np.where((metodo == "figura3") | (metodo == "afluente"))[0]:
            dd = np.array([shapely.distance(P[i], g) for g in geoms]) * KM
            cand = np.where(dd <= CAP_GENERICO)[0]
            menor = [c for c in cand if nomes[c] not in GRANDES or nomes[c] in alvos]
            j = int(min(menor, key=lambda c: dd[c])) if menor else int(np.argmin(dd))
            if dd[j] <= CAP_GENERICO:
                q = nearest_points(geoms[j], P[i])[0]
                lon[i], lat[i] = q.x, q.y
                if metodo[i] == "afluente":
                    rio[i] = (nomes[j] or "(sem nome)") + " — afluente"
                else:
                    metodo[i] = "drenagem_próxima"
                    rio[i] = nomes[j] or "(sem nome)"

        for i, r in grp.iterrows():
            d = (
                np.hypot(
                    (lon[i] - r.lon_fig) * np.cos(np.radians(lat[i])),
                    lat[i] - r.lat_fig,
                )
                * KM
            )
            linhas.append(
                {
                    "numero": int(r.numero),
                    "fazenda": r.fazenda,
                    "corpo_dagua": r.corpo_dagua,
                    "tabela": int(tab),
                    "lon": round(float(lon[i]), 6),
                    "lat": round(float(lat[i]), 6),
                    "lon_fig3": r.lon_fig,
                    "lat_fig3": r.lat_fig,
                    "metodo": metodo[i],
                    "desloc_km": round(float(d), 2),
                    "rio_bcim": rio[i],
                    "nota_rio": nota,
                    "legua_acum": (
                        None if not np.isfinite(c_leg[i]) else float(c_leg[i])
                    ),
                    "km_por_legua": (
                        None if not np.isfinite(km_leg) else round(float(km_leg), 2)
                    ),
                    "ancora": ancora,
                }
            )

    res = pd.DataFrame(linhas).sort_values("numero").reset_index(drop=True)
    assert list(res.numero) == list(range(1, 126)), "numeração 1–125"

    # pontos coincidentes: afasta 700 m para nao se sobreporem no mapa
    while True:
        dup = res.duplicated(subset=["lon", "lat"], keep=False)
        if not dup.any():
            break
        idx = res.index[dup]
        print("pontos coincidentes separados:", res.numero[idx].tolist())
        for c, i in enumerate(idx[1:], start=1):
            ang = 2 * np.pi * c / max(1, len(idx) - 1)
            res.loc[i, "lon"] = round(res.loc[i, "lon"] + 0.0063 * np.cos(ang), 6)
            res.loc[i, "lat"] = round(res.loc[i, "lat"] + 0.0063 * np.sin(ang), 6)

    res.to_csv("dados/gerados/fazendas_1697_bcim.csv", index=False)
    print(res.metodo.value_counts().to_string())
    print(
        f"\ndeslocamento em relação à Figura 3, km:  média {res.desloc_km.mean():.1f}  mediana {res.desloc_km.median():.1f}  máx {res.desloc_km.max():.1f}"
    )
    g = res.groupby(["tabela", "corpo_dagua"]).agg(
        n=("numero", "size"),
        no_rio=("metodo", lambda x: int(x.isin(["léguas", "rio_nomeado"]).sum())),
        km_legua=("km_por_legua", "first"),
        ancora=("ancora", "first"),
        desl=("desloc_km", "mean"),
    )
    print(g.round(1).to_string())


if __name__ == "__main__":
    main()
