"""Funções puras do encaixe na hidrografia (scripts/snap_rios.py)."""

import numpy as np
import pytest
import shapely
from shapely.geometry import LineString

import snap_rios as S


# ---- isotonica: regressão isotônica crescente (pool adjacent violators) ----
def test_isotonica_mantem_sequencia_ja_crescente():
    y = [1.0, 2.0, 3.0, 5.0]
    assert np.allclose(S.isotonica(y), y)


def test_isotonica_funde_violadores_na_media():
    # 3 > 2 viola a ordem: os dois viram a média, 2,5
    assert np.allclose(S.isotonica([1.0, 3.0, 2.0, 4.0]), [1.0, 2.5, 2.5, 4.0])


def test_isotonica_respeita_pesos():
    # peso 3 no segundo ponto puxa a média para ele: (5*1 + 1*3) / 4 = 2
    out = S.isotonica([5.0, 1.0], w=[1.0, 3.0])
    assert np.allclose(out, [2.0, 2.0])


def test_isotonica_resultado_e_monotono():
    rng = np.random.default_rng(0)
    out = S.isotonica(rng.normal(size=50))
    assert np.all(np.diff(out) >= -1e-12)


# ---- reta: inclinação por mínimos quadrados ----
def test_reta_recupera_reta_exata():
    x = np.array([0.0, 2.0, 5.0, 9.0])
    b, a = S.reta(x, 3.0 + 7.7 * x)
    assert b == pytest.approx(7.7)
    assert a == pytest.approx(3.0)


def test_reta_com_x_constante_nao_divide_por_zero():
    b, a = S.reta([4.0, 4.0, 4.0], [1.0, 2.0, 3.0])
    assert b == 0.0
    assert a == pytest.approx(2.0)


def test_reta_da_peso_as_pontas():
    # a figura acerta as pontas e erra o meio: mínimos quadrados seguem o vão total
    x = np.array([0.0, 1.0, 2.0, 3.0, 10.0])
    y = np.array([0.0, 5.0, 10.0, 15.0, 20.0])
    b, _ = S.reta(x, y)
    assert 1.5 < b < 3.0  # a mediana das inclinações par a par daria 5


# ---- espaca: separa posições empatadas ----
def test_espaca_separa_empates_e_mantem_ordem():
    s = S.espaca([1.0, 3.0, 3.0, 3.0, 6.0], comprimento=10.0, minimo=0.5)
    assert len(set(np.round(s, 9))) == 5
    assert np.all(np.diff(s) > 0)
    assert s.min() >= 0.0 and s.max() <= 10.0


def test_espaca_sem_empates_nao_mexe():
    s = [1.0, 2.0, 4.0]
    assert np.allclose(S.espaca(s, comprimento=10.0, minimo=0.5), s)


def test_espaca_sequencia_decrescente():
    s = S.espaca([8.0, 5.0, 5.0, 2.0], comprimento=10.0, minimo=0.5)
    assert np.all(np.diff(s) < 0)


# ---- troncos: costura dos trechos ----
def test_troncos_costura_trechos_que_se_tocam():
    a = LineString([(0, 0), (1, 0)])
    b = LineString([(1, 0), (2, 0)])
    (t,) = S.troncos([a, b])
    assert t.length == pytest.approx(2.0)


def test_troncos_costura_trecho_invertido_com_folga():
    a = LineString([(0, 0), (1, 0)])
    b = LineString([(3, 0), (1.01, 0)])  # invertido e a 0,01 grau do extremo
    tr = S.troncos([a, b], tol=0.03)
    assert len(tr) == 1


def test_troncos_separa_homonimos_distantes_do_maior_para_o_menor():
    a = LineString([(0, 0), (1, 0)])
    b = LineString([(5, 5), (8, 5)])
    tr = S.troncos([a, b])
    assert [round(t.length, 6) for t in tr] == [3.0, 1.0]


# ---- assenta: régua generalizada -> traçado real ----
def test_assenta_cai_sobre_o_tracado_real():
    cheio = LineString([(0, 0), (1, 0.001), (2, 0), (3, 0.001), (4, 0)])
    tronco = cheio.simplify(S.TOL_TRONCO)
    q = S.assenta(tronco.length / 2, tronco, cheio)
    assert shapely.distance(q, cheio) == pytest.approx(0.0, abs=1e-12)
