"""Leitura das léguas do OCR (scripts/leguas.py)."""

import math

import pytest

import leguas as LG


@pytest.mark.parametrize(
    ("tok", "esperado"),
    [("3", 3.0), ("20", 20.0), ("uma", 1.0), ("duas", 2.0), ("três", 3.0)],
)
def test_valor_le_algarismos_e_extenso(tok, esperado):
    assert LG.valor(tok) == esperado


def test_valor_desconhecido_vira_nan():
    assert math.isnan(LG.valor("muitas"))


def test_sa_tira_acento_e_baixa_caixa():
    assert LG.sa("Léguas Três") == "leguas tres"


@pytest.mark.parametrize(
    ("linha", "numero"),
    [
        ("01 - Fazenda do Saco", 1),
        ("O5- Fazenda Boa Vista", 5),  # O lido no lugar de 0
        ("1º- Fazenda Grande", 1),
        ("11 - Sítio Novo", 11),
        ("O9 - Fazenda Tapera", 9),
    ],
)
def test_entrada_reconhece_inicio_de_fazenda_com_erros_de_ocr(linha, numero):
    m = LG.ENTRADA.match(linha)
    assert m is not None
    assert int(m.group(1).translate(LG.DIG)) == numero


def test_entrada_ignora_texto_corrido():
    assert LG.ENTRADA.match("dista da que se segue 3 léguas") is None
