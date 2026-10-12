"""
Extrai do OCR do relato de 1697 as distâncias em léguas entre fazendas
consecutivas ("dista da que se segue N léguas") e monta, para cada um dos
29 corpos d'água, a posição acumulada de cada fazenda ao longo do curso.

Saída: dados/gerados/leguas_1697.csv
    numero, fazenda_relato, tabela, ordem, legua_prox, legua_acum,
    na_cabeceira, na_barra, dist_barra
"""

import pathlib
import re
import unicodedata

import pandas as pd

RAIZ = pathlib.Path(__file__).resolve().parent.parent
OCR = RAIZ / "dados" / "fontes" / "descricao_cap2_ocr.txt"

# ---- cabeçalhos de seção do relato -> tabela do gazetteer -------------------
# (linha de início no OCR é achada por regex; a ordem abaixo é a do texto)
SECOES = [
    (r"^VI\s*-\s*O principal riacho", 1, 20),
    (r"^O primeiro riacho que entra no Canind", 2, 7),
    (r"^VIII\s*-\s*O riacho das Guaribas", 3, 6),
    (r"^IXa\s*-\s*Riachinho do Frade", 4, 1),
    (r"^IXb\s*-\s*Riachinho da serra Talhada", 5, 1),
    (r"^IXc\s*-\s*Riachinho Corrente", 6, 1),
    (r"^IXd\s*-\s*Riachino do Mocambo", 7, 1),
    (r"^X\s*-\s*O rio Itaim A", 9, 9),
    (r"^XI\s*-\s*Riacho do Cais", 10, 2),
    (r"^XII\s*-\s*Riacho Cabe", 11, 3),
    (r"^XIII\s*-\s*Riacho Canabrava", 12, 2),
    (r"^XIV\s*-\s*Riacho S[ãa]o Nicolau", 13, 4),
    (r"^XIVa\s*-\s*Riacho Vit", 14, 1),
    (r"^XIVb\s*-\s*Riacho negro", 15, 1),
    (r"^XV\s*-\s*Rio S[ãa]o Vitor", 16, 4),
    (r"^XVI\s*-\s*Riacho Santa Catarina", 17, 2),
    (r"^XVII\s*-\s*Segue-se o riacho de S", 18, 4),
    (r"^XVIII\s*-\s*Riacho Berlengas", 19, 3),
    (r"^XVilla\s*-\s*Riachinho Santo Ant", 20, 1),
    (r"^XIX\s*-\s*Riacho Maratamhaim", 21, 4),
    (r"^XX\s*-\s*Riacho das Cobras", 22, 2),
    (r"^Riacho a Bitorocara", 23, 3),
    (r"^XXla\s*-\s*Riachinho do Buriti", 24, 1),
    (r"^XXII\s*-\s*Riacho da Tranqueira", 8, 5),
    (r"^XXIII\s*-\s*Riacho Piau", 25, 20),
    (r"^XXV\s*-\s*Riacho Moicat", 26, 3),
    (r"^XXVI\s*-\s*Riacho da Itaueira", 27, 4),
    (r"^XXVII\s*-\s*Riacho das Guaribas", 28, 3),
    (r"^XXVIII\s*-\s*Perto das cabeceiras", None, 2),
    (r"^XXIX\s*-\s*Rio Gurgueia", 29, 7),
]

PRIMEIRO = {
    1: 1,
    2: 21,
    3: 28,
    4: 34,
    5: 35,
    6: 36,
    7: 37,
    8: 38,
    9: 43,
    10: 52,
    11: 54,
    12: 57,
    13: 59,
    14: 63,
    15: 64,
    16: 65,
    17: 69,
    18: 71,
    19: 75,
    20: 78,
    21: 79,
    22: 83,
    23: 85,
    24: 88,
    25: 89,
    26: 109,
    27: 112,
    28: 116,
    29: 119,
}

EXTENSO = {
    "uma": 1,
    "um": 1,
    "duas": 2,
    "dois": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
}

# início de uma entrada de fazenda: "01 -", "O5-", "1º-", "11-", "O9 -"
ENTRADA = re.compile(r"^\s*([0-9OSIl]{1,3})\s*[ºo°]?\s*[-–—]\s*(?=[A-ZÉ])")
DIG = str.maketrans({"O": "0", "S": "5", "I": "1", "l": "1"})
# rodapé/cabeçalho de página que atravessa as entradas
LIXO = re.compile(r"^(Descri[çc][ãa]o do sert|\d+\s*[+*«»·]\s*Pe\.|Pe\. Miguel|\s*$)")


def sa(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def valor(tok):
    tok = tok.strip()
    if tok.isdigit():
        return float(tok)
    return float(EXTENSO.get(sa(tok), "nan"))


def main():
    linhas = OCR.read_text(encoding="utf-8").splitlines()

    # localiza o início de cada seção
    ini = []
    for pad, tab, n in SECOES:
        rx = re.compile(pad)
        achou = [i for i, l in enumerate(linhas) if rx.match(l.strip())]
        assert achou, f"seção não encontrada: {pad}"
        ini.append((achou[0], tab, n))
    ini.sort()
    assert [t for _, t, _ in ini] == [t for _, t, _ in SECOES], "ordem das seções"

    reg = []
    for k, (i0, tab, n_esp) in enumerate(ini):
        i1 = ini[k + 1][0] if k + 1 < len(ini) else len(linhas)
        bloco = linhas[i0:i1]

        # agrupa as linhas de cada entrada numerada
        entradas, atual, ordens = [], None, []
        for l in bloco:
            if LIXO.match(l.strip()):
                continue
            m = ENTRADA.match(l)
            if m:
                if atual is not None:
                    entradas.append(atual)
                atual = [l]
                ordens.append(int(m.group(1).translate(DIG)))
            elif atual is not None:
                atual.append(l)
        if atual is not None:
            entradas.append(atual)

        assert len(entradas) == n_esp, (
            f"tabela {tab}: {len(entradas)} entradas, esperado {n_esp}"
        )
        assert ordens == list(range(1, n_esp + 1)), (
            f"tabela {tab}: numeração das entradas {ordens}"
        )

        if tab is None:  # lagoas de sal: não entram nas 125
            continue
        base = PRIMEIRO[tab]
        for j, ent in enumerate(entradas):
            t = " ".join(x.strip() for x in ent)
            t = re.sub(r"\s+", " ", t)
            ts = sa(t)

            # passo até a fazenda seguinte
            m = re.search(
                r"(?:dist[ao] d[ae] (?:que se (?:lhe )?segue|que segue|seguinte)"
                r"|d[ae] fazenda que se segue"  # OCR comeu o \u201cdista\u201d (#122)
                r"|desta a debaixo se acham)"  # forma arcaica (#1)
                r"\s+([0-9]+|[a-z]+)\s+leguas?",
                ts,
            )
            passo = valor(m.group(1)) if m else float("nan")

            # distância até a barra (última fazenda de alguns riachos)
            mb = re.search(r"dist[ao] da barra\s+([0-9]+|[a-z]+)\s+leguas?", ts)
            d_barra = valor(mb.group(1)) if mb else float("nan")

            # digressão: fazenda de um afluente, medida a partir de outra
            # fazenda nomeada e não da anterior da cadeia
            ml = re.search(
                r"dist[ao] d[oa] ([a-z\-]+(?:[ \-][a-z\-]+)?)\s+"
                r"([0-9]+|[a-z]+)\s+leguas?",
                ts,
            )
            lateral = m is None and mb is None and ml is not None
            ref_legua = valor(ml.group(2)) if lateral else float("nan")

            reg.append(
                {
                    "numero": base + j,
                    "tabela": tab,
                    "ordem": j + 1,
                    "legua_prox": passo,
                    "dist_barra": d_barra,
                    "lateral": lateral,
                    "ref_legua": ref_legua,
                    "ref_nome": ml.group(1) if lateral else None,
                    "na_cabeceira": bool(re.search(r"cabece", ts)) and j == 0,
                    "na_barra": bool(
                        re.search(
                            r"(na barra|junto da barra|"
                            r"e a ultima de sua barra)",
                            ts,
                        )
                    ),
                    "trecho": t[:90],
                }
            )

    df = pd.DataFrame(reg)

    # nomes das fazendas, para resolver as referências das digressões
    faz = pd.read_csv(RAIZ / "fazendas_1697_bcim.csv")[["numero", "fazenda"]]
    df = df.merge(faz, on="numero", how="left")
    chave = {
        n: sa(f).replace("-", " ").replace(" ", "")
        for n, f in zip(faz.numero, faz.fazenda)
    }

    df["ref_numero"] = pd.NA
    for i, r in df[df.lateral].iterrows():
        alvo = sa(str(r.ref_nome)).replace("-", " ").replace(" ", "")
        cand = [
            n
            for n in df[df.tabela == r.tabela].numero
            if n < r.numero and chave.get(n, "") == alvo
        ]
        assert cand, f"#{r.numero}: referência '{r.ref_nome}' não resolvida"
        df.loc[i, "ref_numero"] = cand[-1]  # pyrefly: ignore[unsupported-operation]

    # posição acumulada em léguas ao longo do curso principal.
    # as digressões (fazendas de afluente) não consomem passo: o passo da
    # entrada anterior aponta para a próxima fazenda do curso principal.
    df["legua_acum"] = float("nan")
    for tab, g in df.groupby("tabela"):
        g = g.sort_values("ordem")
        soma = 0.0
        for i, r in g.iterrows():
            if r.lateral:
                continue
            df.loc[i, "legua_acum"] = soma  # pyrefly: ignore[unsupported-operation]
            soma += r.legua_prox  # passo ilegível (NaN) propaga NaN, de propósito
    for i, r in df[df.lateral].iterrows():  # ancoradas na fazenda de referência
        ref = df.loc[df.numero == r.ref_numero, "legua_acum"].iloc[0]
        df.loc[i, "legua_acum"] = ref  # pyrefly: ignore[unsupported-operation]

    assert sorted(df.numero) == list(range(1, 126)), "numeração 1–125"
    df = df.sort_values("numero")
    df.to_csv(RAIZ / "dados" / "gerados" / "leguas_1697.csv", index=False)

    n_ok = df.legua_prox.notna().sum()
    print(f"{len(df)} fazendas, {n_ok} passos em léguas lidos")
    falta = df[df.legua_prox.isna()]
    print(f"\nsem passo ({len(falta)}) — última de cada riacho ou omissão:")
    for _, r in falta.iterrows():
        ult = "última" if r.ordem == df[df.tabela == r.tabela].ordem.max() else "MEIO!"
        print(
            f"  #{r.numero:3d} tab {r.tabela:2d} ordem {r.ordem:2d} {ult:7s} {r.trecho[:60]}"
        )
    print("\ndigressões (fazenda de afluente, fora da cadeia principal):")
    for _, r in df[df.lateral].iterrows():
        print(
            f"  #{r.numero} {r.fazenda} — {r.ref_legua:.0f} léguas de "
            f"#{r.ref_numero} ({r.ref_nome})"
        )
    print("\nléguas por grupo:")
    for tab, g in df.groupby("tabela"):
        gp = g[~g.lateral]
        n_nan = int(gp.legua_acum.isna().sum())
        print(
            f"  tab {tab:2d}: {len(g):2d} fz, cadeia {len(gp):2d}, "
            f"total {gp.legua_acum.max():5.1f} léguas"
            + (f"  ({n_nan} sem posição)" if n_nan else "")
        )


if __name__ == "__main__":
    main()
