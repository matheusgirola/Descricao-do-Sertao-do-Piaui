# CLAUDE.md

Mapa interativo das 125 fazendas visitadas por **Miguel de Carvalho em 1697** (*Descrição do
sertão do Piauí*) sobre a base atual do IBGE: `descricao_interativa_bcim.html`, o relato num painel
que rola sobre um mapa vetorial que acompanha a leitura rio a rio. Nomes: Tabelas 1–29 de *Os
Jesuítas no Piauí* (pp. 30–34); posições: **Figura 3** (Baptista, 1986, p. 36). Versões completas
desta nota, da nota metodológica ABNT (com equações) e das de 1828/1850 (`CLAUDE_1.md`) em `arquivo/`.

## Ambiente e pipeline

uv + Python 3.13 (`~/.claude/python-project-rules.md`); tudo com `uv run`, da raiz: `uv sync`,
`uv run python scripts/<script>.py`, `pytest` (`pythonpath = ["scripts"]`), `ruff check .`, `pyrefly
check` (3 `ignore` em `leguas.py`: falsos positivos do pandas), `uvx prek install`. Encaixe mudou de
propósito? Atualize `tests/test_dados.py`. Saídas em `dados/gerados/` (`g/`); entradas em `dados/`.

| Ordem | Script | Saída |
|---|---|---|
| 1 | `extrai_figura3.py` — PDF → Figura 3 → 125 pontos em lat/lon | `g/pontos_fig3_bruto.csv`, `g/figura3.jpg` |
| 2 | `leguas.py` — OCR do relato → léguas entre fazendas | `g/leguas_1697.csv` |
| — | `baixa_bc250.py`, `baixa_gazetteer.py` — WFS do IBGE (só com BC250 nova) | `g/*_bc250.parquet` |
| 3 | `snap_rios.py` — encaixa os pontos na hidrografia | `g/fazendas_1697_bcim.csv` (copiar à mão para a raiz), `g/escala_global.json` |
| 4 | `monta_mapa.py` (usa `base_svg.py`) — monta o HTML, determinístico byte a byte | `descricao_interativa_bcim.html` |
| 5 | `qc_mapa.py` — vistas; `folha_conferencia.py` — folha para conferir Fig. 3, léguas e tabelas | `qc/` |
| 6 | `afere_ancoras.py` — confere a escala contra 3 distâncias externas | stdout |

## Método

**1. Leitura da Figura 3.** O JPEG embutido no PDF vai **sem recodificar** para `figura3.jpg` e o
Pillow decodifica (pixels idênticos do 9.5 ao 12.3). Não usar `pypdf.images`: ele regrava o JPEG e
a segmentação muda (123 pontos com pypdf 6.20, 80 com 5.1). Raster 609×916 px; 125 pontos laranja por
segmentação de cor (componentes ≥5 px; o menor tem 7). Rótulos de ~6 px lidos à vista em recortes
8×; `NUMERO` guarda a posição (x, y) de cada número e cada blob recebe o do vizinho mais próximo
(`assert` de unicidade e < 3 px). Os pontos **16** e **37** ficam a 6 px um do outro: 16 = o de
noroeste, pela cadeia do Canindé; efeito nulo, pois cada um vai para o seu riacho.

**2. Georreferenciamento.** Plot equirretangular puro: silhueta do Piauí (fechamento 7×7 — com
5×5 os rios deixam o contorno aberto e o ICP desanda) ajustada por ICP + afim contra a BCIM.
Escala 0,00920 °/px em x e 0,00918 em y, rotação −0,21°, RMS do contorno 5,0 km; grau 2 não
melhora. Aferição (`folha_conferencia.py`): os rios do relato na BC250 ficam a **5,7 km** (mediana)
das linhas da figura, contra 13,9 km ao acaso; o ótimo pede a figura ~5 km a leste. Os antigos
"1,4 km da drenagem da BCIM" não valem: pontos ao acaso dão o mesmo (a drenagem 1:1M é densa).

**3. Léguas (`leguas.py`).** "Dista da que se segue N léguas": **94 passos** legíveis (1 a 20
léguas). O parser acha as 29 seções pelo algarismo romano e valida 1..n em cada seção e 1–125 no
total (falha alto). Variantes tratadas: `O5`/`OS`/`0O8`, "desta à debaixo se acham" (#1), "dista
da que segue" (#119), "e da fazenda que se segue" (#122); "dista da barra uma légua" (#111) é
`dist_barra`, não passo; a seção XXVIII (lagoas de sal) não entra. Légua acumulada
L = soma dos passos anteriores. **Digressões:** #91 (riacho Inhinhinga, 10 léguas de #90) e #93
(riachinho do Buqueirão, 3 léguas de #92) não consomem passo; sem isso o Piauí perdia 44 léguas.

**4. Tronco e régua (`snap_rios.py`).** Cada corpo d'água é ligado ao nome na **BC250** (`RIOS`).
O tronco é a **componente conexa** mais longa do rio nomeado dentro do raio do grupo (trechos
avulsos truncavam rios: o Gurguéia perdia 250 km). A BC250 nomeia muito mais rio que a BCIM
(Itaim 66 → 220 km, Poti 327 → 555, Tranqueira 72 → 150), e mais rio nomeado é menos dependência
da figura. Mas ela mede o mesmo percurso 1,10–1,21× mais longo (Mandelbrot), e não igual para
todos: por isso as léguas são medidas no tronco **generalizado** por Douglas–Peucker,
`TOL_TRONCO = 0.004` (~445 m), que devolve a razão 1,00–1,07 com a BCIM; o ponto é assentado no
traçado real só no fim (`assenta()`). A BCIM continua sendo a base de desenho.

**5. Escala `b` (km de rio por légua).** Modelo `s = a + b·L` ao longo do tronco; `b` por
**mínimos quadrados**, não robusto (a mediana par a par segue as pernas do meio: Gurguéia 15,6
contra 6,6). Escala **global** b\* = mediana dos grupos com ≥4 fazendas, ≥5 léguas e 4–18
km/légua (`B_LO`, `B_HI`): **8,15** (10 grupos), gravada em `dados/gerados/escala_global.json`. Cada grupo
fica na banda 0,6–1,8× (4,89–14,67, `BANDA`) e a cadeia não pode exceder o tronco.
b\*/6,2 = 1,31: sinuosidade de rio sinuoso, não meandrante (limiar 1,5).

| Tab. | Rio (BC250) | Faz. | Léguas | b livre | Amostra | b adotado | Âncora |
|---:|---|---:|---:|---:|:-:|---:|---|
| 1 | Canindé | 20 | 59 | 7,7 | sim | 7,14 ¹ | cabeceira |
| 2 | Itaim | 6 | 10 | 15,8 | sim | 14,67 ² | barra |
| 3 | Guaribas | 6 | 11 | 8,6 | sim | 8,61 | barra |
| 8 | Tranqueira | 5 | 9 | 14,8 | sim | 14,67 ² | barra |
| 9 | Poti | 9 | 21 | 14,2 | sim | 14,22 | figura |
| 10 | do Cais | 2 | 3 | 31,2 | não | 14,67 ² | figura |
| 12 | Iningá | 2 | 3 | 10,5 | não | 10,45 | barra |
| 13 | São Nicolau | 3 | 12 | 6,7 | não | 6,66 | barra |
| 18 | São Vicente | 4 | 10 | 4,1 | sim | 4,89 ³ | figura |
| 19 | Berlengas | 3 | 7 | 11,5 | não | 11,53 | figura |
| 21 | Maratoã | 4 | 9 | 12,1 | sim | 12,11 | cabeceira |
| 25 | Piauí | 18 | 62 | 7,7 | sim | 7,66 | barra |
| 26 | Mucaitá | 3 | 8 | 10,2 | não | 10,20 | figura |
| 27 | Itaueira | 4 | 9 | 4,889 | sim | 4,89 ³ | figura |
| 29 | Gurguéia | 7 | 32 | 6,8 | sim | 6,82 | barra |

¹ limitado pelo comprimento do tronco; ² teto da banda; ³ piso da banda (o Itaueira, por 0,002).
**A mediana é sensível à amostra:** com 10 grupos é a média dos dois centrais (7,69 e 8,61). Com o
JPEG original o Maratoã passou de 3 fazendas/5 léguas a 4/9, entrou na amostra e levou b\* de 7,73
(9 grupos) a 8,15; as fazendas mudaram 0,26 km na mediana, e só #79–#81 mais de 10 km.

**6. Âncora `a`.** Por padrão, a média dos resíduos contra a Figura 3, a única fonte de posição
absoluta. Âncora textual ("na barra" da última, "na cabeceira" da primeira) só se não brigar com a
figura mais que o deslocamento máximo do grupo; a da barra exige ainda outro curso a ≤ 2 km da
ponta (confluência de verdade, e não o ponto onde o nome acaba). Aceita em 9 grupos: 7 pela barra e
2 pela cabeceira (Canindé, Maratoã).

**7. Resultado.** 96 fazendas espaçadas por léguas, 5 por `rio_nomeado` (projeção + regressão
isotônica), 22 por `drenagem_próxima` (riacho mais próximo, raio 6 km, `CAP_GENERICO`) e 2
`afluente` (#91, #93, na posição da figura). Deslocamento em relação à figura: mediana 10,9 km,
média 14,7, máximo 74,9 — é o relato, e não a figura, que decide o espaçamento.

**Fazendas "na barra".** Santa Rosa (#20) e Sítio Real (#125) caem sobre o Parnaíba, Tapera (#108) e
Saco (#27) sobre o Canindé, Tucano (#33) sobre o Itaim, todas a 0,00 km. Isso confirma pouco: #125,
#108, #27 e #33 são de grupos presos na barra, e a #20 fecha a cadeia do Canindé, que, mais longa
que o tronco, foi esticada de ponta a ponta. Nas cinco os 0,00 km vêm da construção; o que se
confere é só que a confluência achada é a do rio que o texto nomeia. A única independente é São
Cosme (#51), de grupo ancorado pela figura: fica sobre o Poti, a 6 km da foz pelo rio.

**Onde relato e figura brigam.** *Gurguéia (29):* 20 léguas entre #124 e #125 contra 41 km na
figura; adotou-se o relato, preso na barra, e #119–#124 sobem ~50 km. *Maratoã (21):* #79 Ginipapo
"na cabeceira"; a cadeia começa na ponta de montante do rio nomeado (junto de Campo Maior) e desce
até Barras, ~30 km a noroeste da figura. *Tranqueira (8)* e *Piauí (25):* a figura amontoa o
primeiro e distorce o meio do segundo.

**Aferição externa (`afere_ancoras.py`)** — distâncias do relato que não entraram na construção:

| Âncora | Texto | Mapa | km/légua |
|---|---|---|---|
| Tabuleiro-Alto (#90) → Matriz da Vitória (Oeiras), "pelo riacho do Piauí abaixo" | 60 léguas | 333 km de rio + 48 por terra | **6,4 (+2%)** |
| Alongazes → serra da Ibiapaba | 20 léguas | 86–187 km (mediana 158) | 7,9; os 124 km cabem na faixa |
| Tabuleiro-Alto → rio São Francisco | 40 léguas | 93 km | 2,3 — **não fecha** |

A terceira mede até o ponto do rio mais próximo, não até o Sobrado ("10 léguas acima do Santo
Sé") que o texto nomeia; localizar o Sobrado resolveria, e diria se a #90 está certa.

**Limitações.** Comprimentos em graus × 111,32 sem cos φ (até ~2% a mais em trechos leste–oeste).
Légua: 6,2 km é a de 18 ao grau; a de sesmaria (3.000 braças) vale ~6,6 — falta decidir e citar a
fonte metrológica (sinuosidade 1,31 ou 1,23). Escala linear dentro de cada rio. A figura ainda
decide a âncora em 6 grupos, o sentido em todos e a escolha do tronco. Grupos de 2–3 fazendas têm a
escala da banda. ε não é neutro: muda b\* e todas as posições. Um passo mal lido no OCR desloca
o resto do grupo, e as travas de numeração não o detectam.

## Identificações apuradas (não reabrir sem motivo novo)

"Itaim Açu" = **rio Poti** (fazendas 48 *Poti* e 51 *São Cosme*, na foz, hoje Teresina); "Itaim
Mirim" = **rio Itaim**; "Maratauam" = **Maratoã**; "Moicatá" = **riacho do Mucaitá**; "Berlengas" =
**Rio Berlengas** (a BCIM grafa "Beriengas"); "Canabrava" = **riacho Iningá** (fazenda *Iningas*);
"riacho Negro" = **riacho da Serra Negra**; "riachinho da Serra Talhada" = **ribeirão Talhado**.
Legendas das Tabelas 18–20 do PDF estão deslocadas: São Vicente = 71–74, Berlengas = 75–77, Santo
Antônio = 78. A #88 é a "fazenda de Éguas" de Domingos Afonso Sertão, na cabeceira do Canindé. Nº
55/56: "Olho d'Água" e "Sítio da Cruz" podem estar trocados.

**Oito topônimos perdidos** — Cabeça do Tapuio, São Vítor, Santa Catarina, Santo Antônio, das
Cobras, Bitorocara, riachinho do Buriti, Guaribas do sul: procurados nos 47 mil nomes da BC250
(`dados/gerados/gazetteer_bc250.parquet`), quatro não existem e quatro só aparecem a 70–500 km, em outra
bacia. Nomes de fazendas casam com povoados só em *Sussuapara* (#30, 3,9 km) e *São Nicolau* (#60,
7,8 km). Sair daí exige fonte documental (sesmarias, inventários, cartas setecentistas).

## O HTML

1,4 MB **autocontido** (sem CDN nem tiles). SVG inline 4403×3588 px, equirretangular, 390 px/grau,
x corrigido por cos φ: carta de 2923 px + coluna do cartucho (`B.PAD = 1480`, já somado em
`B.xy()`). Câmera = `transform` do `#mapwrap`, presa à **faixa livre** (`faixa()`/`prendeX`),
folga `M = 170` px, zoom ≤ 2,4, abertura por `fitZoom()`/`folha()`; arrasto no `#viewport`,
botões `#zoomctl`, **sem zoom pela roda** (ela rola o texto). Índice em `#topo` (sticky) com `⇄`.
Sem painel de camadas (`g-uc`, `g-mineral`, `g-mun` escondidos por CSS). Folga ~0,95° E–O e ~0,5°
N–S; entorno (`#g-viz`) sob véu de papel, Piauí repintado por cima, fora dele só rios com ≥ 60 km
no quadro; vegetação definida uma vez e usada com `<use>`. `moldura()` e `cartucho()` (título,
rosa, legenda só do que se desenha, escala km/léguas). `rotulos_rio()`: corpo pelo comprimento do
curso, rótulo reto se não cabe, posição contra colisões e curvatura, trilho suavizado, auréola.
Marcador laranja = no rio que o relato nomeia; roxo = sem homônimo (posição da figura).

## Fontes e arquivos

**Estrutura.** Raiz: os produtos (HTML e CSV), `scripts/`, `tests/`, `dados/`, `arquivo/` (versões
antigas; carta de 1850 em `arquivo/carta_1850/`). Fora do git (links no `README.md`): PDFs de
`dados/fontes/`, BCIM e zips de `dados/ibge/`, `qc/`. **Base cartográfica.** **BCIM 2016**
(`dados/ibge/`, 1:1M, EPSG:4674): base de desenho — drenagem, massas d'água, curvas, serras, UCs,
mineração, cidades. **BC250 2025** (1:250k): base do encaixe, por WFS
(`CCAR:BC250_2025_hid_trecho_drenagem_l`, `..._indice_nomes`; sem `sortBy`, paginação por
`startIndex`, ids conferidos). **Vegetação IBGE 1:5M** (`dados/ibge/veg5000/`): a BCIM não traz a do
interior. **Geologia** não entrou (`geol_area.zip`, 417 MB, exigiria generalização pesada).
Colunas: `fazendas_1697_bcim.csv` (raiz) — `numero, fazenda, corpo_dagua, tabela, lon, lat,
lon_fig3, lat_fig3, metodo, desloc_km, rio_bcim, nota_rio, legua_acum, km_por_legua, ancora`;
`g/leguas_1697.csv` — `numero, tabela, ordem, legua_prox, legua_acum, dist_barra, lateral,
ref_numero, ref_legua, na_cabeceira, na_barra`. Pré-visualizar: `.claude/launch.json`.

## Ao editar

- 1–125 sem lacuna nem repetição continua valendo (`assert` em `snap_rios.py` e `monta_mapa.py`).
- `RIOS[tabela] = (nomes na BC250, raio km, deslocamento máximo km, nota)` — nomes da **BC250**
  ("Rio Berlengas"). O deslocamento máximo decide o encaixe e a âncora; 45 km (tab. 8) e 80 km
  (tab. 25) são deliberados. `TOL_TRONCO`, `B_LO`/`B_HI` e `BANDA` mexem em todo o mapa.
- `monta_mapa.py`: `RIOS_RELATO` (BC250, traço grosso e rótulo) e `RIOS_RELATO_BCIM` (suprime o
  traço fino) andam juntas. Texto de `dados/fontes/descricao_interativa_1.html` ou `TROCAS`; seções sem
  fazendas em `CAM`. **Não edite o HTML publicado à mão.**
- Depois de rodar, olhar `qc/` (vistas quadradas, por tabela): vazado = figura, cheio = final;
  vermelho = léguas, laranja = rio nomeado, azul = afluente, roxo = drenagem próxima.

## Pendências e referências

**Próximos passos.** Localizar o Sobrado (âncora do São Francisco); fonte documental para os 22
pontos sem rio nomeado; rever `CAP_GENERICO` (6 km, calibrado na BCIM) à luz da BC250; geologia;
completar as referências (Baptista 1986, edição do relato, fonte metrológica da légua).

**Referências.** BARLOW et al., *Statistical inference under order restrictions*, Wiley, 1972.
DOUGLAS; PEUCKER, *The Canadian Cartographer* 10(2):112-122, 1973. IBGE, *BCIM* 2016 e *BC250*
2025. LEOPOLD; WOLMAN; MILLER, *Fluvial processes in geomorphology*, 1964. MANDELBROT, *Science*
156:636-638, 1967. SEN, *JASA* 63:1379-1389, 1968. Formato ABNT completo em
`arquivo/METODOLOGIA_LEGUAS.md`.
