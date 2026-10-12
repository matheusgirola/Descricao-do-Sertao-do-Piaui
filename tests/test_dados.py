"""Invariantes dos produtos do pipeline: o que tem de continuar valendo depois de
qualquer mudança em leguas.py ou snap_rios.py."""

import json
import pathlib

import pandas as pd
import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def leguas():
    return pd.read_csv(RAIZ / "dados" / "gerados" / "leguas_1697.csv")


@pytest.fixture(scope="module")
def fazendas():
    return pd.read_csv(RAIZ / "dados" / "gerados" / "fazendas_1697_bcim.csv")


def test_leguas_numeracao_1_a_125(leguas):
    assert sorted(leguas.numero) == list(range(1, 126))


def test_leguas_94_passos_legiveis(leguas):
    assert leguas.legua_prox.notna().sum() == 94
    assert leguas.legua_prox.dropna().between(1, 20).all()


def test_digressoes_ancoradas_na_fazenda_de_referencia(leguas):
    lat = leguas[leguas.lateral].set_index("numero")
    assert list(lat.index) == [91, 93]
    assert lat.loc[91, "ref_numero"] == 90 and lat.loc[91, "ref_legua"] == 10
    assert lat.loc[93, "ref_numero"] == 92 and lat.loc[93, "ref_legua"] == 3
    acum = leguas.set_index("numero").legua_acum
    assert acum[91] == acum[90]
    assert acum[93] == acum[92]


def test_legua_acumulada_cresce_dentro_do_grupo(leguas):
    for _, g in leguas[~leguas.lateral].groupby("tabela"):
        v = g.sort_values("ordem").legua_acum.dropna()
        assert v.is_monotonic_increasing


def test_fazendas_numeracao_1_a_125_sem_coordenada_repetida(fazendas):
    assert list(fazendas.numero) == list(range(1, 126))
    assert not fazendas.duplicated(subset=["lon", "lat"]).any()


def test_fazendas_dentro_do_piaui_aproximado(fazendas):
    assert fazendas.lon.between(-46.0, -40.3).all()
    assert fazendas.lat.between(-10.95, -2.7).all()


def test_contagem_por_metodo(fazendas):
    assert fazendas.metodo.value_counts().to_dict() == {
        "léguas": 96,
        "drenagem_próxima": 22,
        "rio_nomeado": 5,
        "afluente": 2,
    }


def test_escala_de_cada_grupo_dentro_da_banda(fazendas):
    # banda 0,6–1,8 x escala global (8,15 km de rio por légua); o CSV arredonda a
    # 2 casas, e os grupos presos na borda da banda ficam a até 0,005 dela
    esc = json.loads((RAIZ / "dados" / "gerados" / "escala_global.json").read_text())
    lo, hi = esc["banda"]
    assert 8.1 < esc["km_por_legua"] < 8.2
    km = fazendas.km_por_legua.dropna()
    assert km.between(lo - 0.01, hi + 0.01).all()


def test_fazendas_da_barra_espacadas_por_leguas(fazendas):
    f = fazendas.set_index("numero")
    for n in (20, 125, 108, 27, 33):
        assert f.loc[n, "metodo"] == "léguas", n
