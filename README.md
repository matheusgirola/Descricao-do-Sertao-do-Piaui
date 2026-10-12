# Fazendas do Piauí em 1697

Mapa interativo das 125 fazendas visitadas por Miguel de Carvalho em 1697 (*Descrição do sertão
do Piauí*), reconstituídas sobre a base cartográfica atual do IBGE a partir das léguas do relato e
da Figura 3 de *Os Jesuítas no Piauí* (Baptista, 1986).

- [`descricao_interativa_bcim.html`](descricao_interativa_bcim.html): o mapa, autocontido (basta
  abrir no navegador).
- [`fazendas_1697_bcim.csv`](fazendas_1697_bcim.csv): as 125 fazendas com coordenadas, método
  de posicionamento e escala usada.

Método, limitações e decisões em [`CLAUDE.md`](CLAUDE.md); a nota metodológica completa está em
[`arquivo/METODOLOGIA_LEGUAS.md`](arquivo/METODOLOGIA_LEGUAS.md).

## Estrutura

```
scripts/          pipeline (extrai_figura3 → leguas → snap_rios → monta_mapa → qc_mapa)
tests/            pytest
dados/fontes/     relato (OCR e HTML do texto), gazetteer, PDFs (fora do git)
dados/ibge/       BCIM 2016 (fora do git) e vegetação 1:5M
dados/gerados/    saídas intermediárias do pipeline
arquivo/          versões antigas (inclui a carta de 1850)
qc/               vistas de conferência (geradas, fora do git)
```

## Rodar

Requer [uv](https://docs.astral.sh/uv/). Da raiz:

```bash
uv sync
uv run python scripts/snap_rios.py
uv run python scripts/monta_mapa.py
uv run pytest
```

A ordem completa dos scripts está no `CLAUDE.md`. Arquivos que não vão para o git e precisam
ser baixados à parte:

| Arquivo | Onde pôr | Fonte |
|---|---|---|
| `bcim_2016_21_11_2018.gpkg` (355 MB) | `dados/ibge/` | [IBGE, BCIM 2016](https://geoftp.ibge.gov.br/cartas_e_mapas/bases_cartograficas_continuas/bcim/versao2016/geopackage/bcim_2016_21_11_2018.gpkg) |
| `OS_JESUÍTAS_NO_PIAUÍ.pdf` | `dados/fontes/` | [EDUFPI](https://ufpi.br/arquivos_download/arquivos/EDUFPI/edufpi_2/OS_JESUÍTAS_NO_PIAUÍ.pdf) |
| `OS_JESUÍTAS_NO_PIAUÍ-33-38.pdf` | `dados/fontes/` | recorte das pp. 33–38 do PDF acima (Figura 3 na 1ª página) |
| `Descrição do sertão do Piauí .pdf` | `dados/fontes/` | ver `dados/fontes/links.txt` |

Sem a BCIM não rodam `monta_mapa.py` nem `afere_ancoras.py`; sem o recorte, não roda
`extrai_figura3.py` (as saídas dele já estão em `dados/gerados/`).
