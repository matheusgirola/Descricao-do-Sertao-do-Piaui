# CLAUDE.md

Mapa interativo das 125 fazendas de gado visitadas por **Miguel de Carvalho em 1697**
(*Descrição do sertão do Piauí*), plotadas sobre a base cartográfica **atual** do IBGE.

> Substitui o CLAUDE.md anterior (guardado como `CLAUDE_1.md`), que descrevia as versões
> sobre as cartas de 1828 e 1850. Aquelas versões continuam válidas; o que mudou é a
> **camada raiz de coordenadas** e a base sobre a qual o mapa é desenhado.

## O que é o projeto

O relato de 1697 percorre 29 corpos d'água, um a um, listando as fazendas de cada um na
ordem em que ficam ao longo do curso. As Tabelas 1–29 de *Os Jesuítas no Piauí* (pp. 30–34)
dão os nomes das 125 fazendas; a **Figura 3** (Baptista, 1986, p. 36, adaptada) as posiciona
num mapa mudo do Piauí.

O produto é `descricao_interativa_bcim.html`: o texto do relato num painel que rola e, ao
fundo, um mapa vetorial do Piauí que acompanha a leitura rio a rio.

## Pipeline (`work/`, na ordem em que roda)

| Script | O que faz |
|---|---|
| `work/extrai_figura3.py` | PDF → Figura 3 → 125 pontos em lat/lon (`work/pontos_fig3_bruto.csv`) |
| `work/leguas.py` | OCR do relato → distâncias em léguas entre fazendas (`work/leguas_1697.csv`) |
| `work/baixa_bc250.py` | WFS do IBGE → drenagem BC250 do Piauí (`work/drenagem_bc250.parquet`) |
| `work/baixa_gazetteer.py` | WFS do IBGE → índice de nomes da BC250 (`work/gazetteer_bc250.parquet`) |
| `work/snap_rios.py` | encaixa os 125 pontos na hidrografia real (`work/fazendas_1697_bcim.csv`) |
| `work/base_svg.py` | carrega e projeta as camadas da BCIM + BC250 + vegetação (biblioteca) |
| `work/monta_mapa.py` | monta `descricao_interativa_bcim.html` |
| `work/qc_mapa.py` | imagens de conferência em `work/qc/` |
| `work/afere_ancoras.py` | confere a escala contra 3 distâncias do relato que não entraram no mapa |

Os dois `baixa_*.py` só precisam rodar uma vez: gravam parquets que o resto do
pipeline lê. Rodá-los de novo só faz sentido quando sair versão nova da BC250.

A metodologia da conversão léguas → km está escrita em `METODOLOGIA_LEGUAS.md`.

## Ambiente

Projeto gerido por **uv** (`pyproject.toml` + `uv.lock`, Python 3.13), seguindo as regras
globais em `~/.claude/python-project-rules.md`. Tudo roda com `uv run`, da raiz do projeto
(os scripts usam caminhos relativos a ela):

- `uv sync` — instala o ambiente travado
- `uv run python work/<script>.py` — roda um passo do pipeline
- `uv run pytest` — testes em `tests/` (`pythonpath = ["work"]`: os scripts são módulos soltos)
- `uv run ruff check .` / `uv run ruff format .` — lint e formatação (padrões do ruff + `I`)
- `uv run pyrefly check` — tipos; os 3 `# pyrefly: ignore[unsupported-operation]` de
  `leguas.py` são falsos positivos das anotações do pandas para `df.loc[...] = valor`
- `.pre-commit-config.yaml` tem hooks locais (ruff, pyrefly, pytest); instalar com
  `uvx prek install` depois de um `git init`

Os testes cobrem as funções puras de `snap_rios.py` e `leguas.py` e os **invariantes dos
CSVs** (1–125, 94 passos, digressões #91/#93, contagem por método, escala dentro da banda).
Mudou o encaixe de propósito? Atualize `tests/test_dados.py` junto.

**`extrai_figura3.py` lê a Figura 3 do JPEG embutido no PDF, sem recodificar.** O fluxo
DCT cru sai do PDF direto para `work/figura3.jpg` (os bytes são os do PDF) e é decodificado
pelo Pillow, que dá os mesmos pixels do 9.5 ao 12.3. Não usar o `pypdf.images`: ele regrava o
JPEG, a qualidade muda com a versão do pypdf, e a segmentação muda junto (123 pontos com a
6.20, 80 com a 5.1). Com o fluxo cru a contagem tem folga — o menor ponto tem 7 px, e o
mínimo de 5 px pode ir de 2 a 5 sem mudar os 125. A numeração não depende da ordem dos
blobs: `NUMERO` guarda a posição (x, y) de cada número, e cada blob recebe o do vizinho mais
próximo (`assert` de unicidade e de distância < 3 px).

Até 2026-10-12 a referência era outra: o fluxo cru regravado em qualidade 75 pela IJG
libjpeg 9e do Pillow do Anaconda, reproduzido depois com o `jpeglib`. A troca para o JPEG
original moveu a figura georreferenciada 0,8 km (mediana) e levou o rio Maratoã para a
amostra da escala global, que foi de 7,7 para 8,2 km/légua (ver §4).

### 1. Leitura da Figura 3

Raster embutido no PDF, 609×916 px. Os 125 pontos laranja saem por segmentação de cor
(exatamente 125 componentes com ≥5 px; o menor tem 7). Os rótulos numéricos têm ~6 px de altura — OCR não
funciona; foram lidos visualmente em recortes ampliados 8×, faixa por faixa. Validação:
o conjunto é 1–125, cada número uma vez.

**Ressalva:** os pontos dos números **16** (Retiro, rio Canindé) e **37** (Mocambo) ficam a
6 px um do outro e seus rótulos são ilegíveis na resolução original. A atribuição adotada
(16 = o ponto de noroeste) segue a continuidade da cadeia do Canindé (#15 → #16 → #17). O
efeito prático é nulo: cada um é encaixado no seu próprio riacho na etapa 3.

### 2. Georreferenciamento

A Figura 3 é um **plot equirretangular puro**: silhueta do Piauí extraída da imagem, ajustada
por ICP contra a malha do IBGE (BCIM, `lim_unidade_federacao_a`). O ajuste afim resultante tem
escala 0,00920 °/px em x e 0,00918 °/px em y (razão 0,998) e rotação de −0,21° — ou seja,
escala + translação, sem projeção. Graus 1 e 2 dão o mesmo RMS, o que confirma o modelo.

Aferição independente: os **rios desenhados na própria Figura 3**, transformados para lat/lon,
caem a **1,4 km (mediana)** da drenagem da BCIM. É o número que substitui o RMSE de 5,5 km do
georreferenciamento anterior.

### 3. As léguas do relato (`leguas.py`)

O relato não dá só a ordem: dá a **distância**. Cada entrada termina em "dista da que se segue
3 léguas" — 94 passos legíveis no OCR, o bastante para uma posição acumulada em léguas para
todas as 125 fazendas (a última de cada riacho não tem passo, e não precisa).

O parser localiza as 29 seções pelo cabeçalho em algarismo romano, agrupa as linhas de cada
entrada numerada e lê o passo. Ele valida que a numeração interna de cada seção é 1..n e que o
conjunto final é 1–125. Cuidados que o OCR exigiu:

- dígitos lidos como letras (`O5`, `OS`, `0O8`) — normalizados;
- formas fora do padrão: `desta à debaixo se acham 5 léguas` (#1), `dista da que segue`
  (#119), `e da fazenda que se segue` (#122, o OCR comeu o "dista");
- `dista da barra uma légua` (#111) não é um passo para a próxima fazenda, e sim até a foz;
- a seção XXVIII (as lagoas de sal, fazendas Rio-Grande e Salinas) **não** entra nas 125.

**Digressões.** Duas entradas do rio Piauí não são fazendas do rio: #91 *Curral do Campo* fica
no riacho Inhinhinga, a 10 léguas do Tabuleiro-Alto, e #93 *Sítio das Pimentas* no riachinho do
Buqueirão, a 3 léguas da Fazenda-Grande. Elas não consomem passo — o passo da entrada anterior
aponta para a próxima fazenda **do curso principal**. Sem isso a cadeia do Piauí ficava 44
léguas mais curta.

### 4. Encaixe na hidrografia (`snap_rios.py`)

O relato diz em que riacho está cada fazenda e a que distância da seguinte; a Figura 3 diz onde
o riacho fica. O script cruza as duas coisas:

1. cada corpo d'água de 1697 é associado ao nome correspondente na **BC250** (dicionário `RIOS`);
2. os trechos com esse nome são costurados (`linemerge` + costura gulosa pelos extremos) e o
   tronco do grupo é a **componente conexa** mais longa dentro do alcance — não os trechos
   avulsos mais próximos, que truncavam rios longos (o Gurguéia perdia 250 dos seus 529 km) e
   com isso devolviam ao resultado o erro da própria figura;
3. **espaçamento por léguas**: a posição ao longo do tronco é `s = a + b·légua_acumulada`.
   O relato dá o espaçamento; a Figura 3 fica só com a âncora e o rumo;
4. sem léguas utilizáveis → referenciamento linear + regressão isotônica (o método antigo);
5. sem homônimo na carta → encaixe no curso d'água mais próximo, raio de 6 km, com preferência
   por riachos em vez de rios grandes de outra bacia;
6. cada linha do CSV guarda `metodo`, `desloc_km`, `rio_bcim`, `legua_acum`, `km_por_legua` e
   `ancora` — dá para auditar ponto a ponto.

#### Por que a BC250 e não a BCIM

O encaixe vive do campo `nome` da drenagem, e a BCIM (1:1.000.000) nomeia pouco: fora dos
grandes rios ela deixa o curso anônimo, e onde não há nome não há em que projetar as léguas.
A **BC250 2025** (1:250.000, baixada por WFS em `work/baixa_bc250.py` — 66 mil trechos, 3.910
nomes distintos, contra 18 mil e 1.562 da BCIM) nomeia bem mais **do mesmo rio**:

| grupo | tronco na BCIM | tronco na BC250 |
|---|---|---|
| rio Itaim (tab. 2) | 66 km | **220 km** |
| riacho da Tranqueira (tab. 8) | 72 km | **150 km** |
| rio Poti (tab. 9) | 327 km | **555 km** |
| riacho Iningá (tab. 12) | 30 km | 59 km |
| rio Piauí (tab. 25) | 478 km | 557 km |

Quinze dos vinte e um grupos ganharam tronco. O efeito é o que se queria: **quanto mais rio
nomeado, menos a cadeia depende da Figura 3.** As fazendas #21–23, que a BCIM deixava fora do
trecho nomeado do Itaim e caíam no riacho genérico mais próximo, agora são espaçadas pelas
léguas do texto (a #22 Tábua andou 36 km). O grupo do Iningá pedia **2,7 km/légua** na BCIM —
menos que a légua em linha reta, fisicamente impossível, sinal de que o tronco truncado
comprimia a cadeia; na BC250 pede 10,5.

A BCIM continua sendo a base de **desenho** do mapa (18 mil trechos generalizados é o que cabe
num HTML autocontido). Só os rios que o relato percorre são desenhados a partir da BC250 — que
é onde os pontos foram encaixados, e onde os rótulos correm.

#### A régua: por que o tronco é generalizado antes de medir

Trocar de carta quase estragou a escala. A BC250 traça os meandros que a carta ao milionésimo
generaliza, de modo que **o mesmo percurso mede de 1,10 a 1,21 vez mais quilômetros** — e não
na mesma proporção para todos os rios. Tomada crua, "km de rio por légua" deixaria de medir o
terreno e passaria a medir a resolução da carta: a amostra da escala global abriu de 5,3–13,8
(BCIM) para 4,1–16,8, com quatro grupos batendo no teto da banda.

A correção é `TOL_TRONCO = 0.004` (~445 m): as léguas são projetadas sobre o tronco
**generalizado**, e o ponto é assentado no traçado real só no fim (`assenta()`). A essa
tolerância a régua volta a coincidir com a da BCIM (razão 1,00–1,07) e o ganho de cobertura,
que é o que interessa, permanece. 445 m é muito menos que o passo do relato (uma légua, ~6 km)
e que o erro da Figura 3 (~1,4 km); na escala da carta são 1,5 px.

Resultado: escala global de 7,7 km de rio por légua, contra 7,9 da versão BCIM — a régua não
se mexeu, e é isso que se queria. (Hoje é **8,2**, mas por outro motivo: ver adiante.)

#### Como saem `b` (escala) e `a` (âncora)

**`b`, quilômetros de rio por légua.** Ajuste de `s` contra `légua_acum` por **mínimos
quadrados** — e não por ajuste robusto: num grupo em que a figura acerta as pontas mas erra o
espaçamento interno, a mediana das inclinações par a par segue as pernas do meio e devolve o
dobro da escala verdadeira (Gurguéia: 15,6 contra 6,6 km/légua). Estima-se primeiro uma escala
**global** — mediana dos 10 grupos grandes e bem comportados, **8,2 km de rio por légua** — e
cada grupo só pode afastar-se dela dentro da banda 0,6–1,8× (4,9 a 14,7 km/légua). Assim um
grupo mal desenhado não inventa uma escala impossível.

> A convergência é ela própria um resultado: a légua de sesmaria vale ~6,2 km em linha reta;
> medida ao longo de um curso sinuoso dá ~8,2. A razão, 1,31, é a sinuosidade típica destes
> rios. Os extremos da banda também fazem sentido — o Poti, muito meandrado, pede 14,2.
>
> **A mediana é sensível à amostra.** Com 10 grupos ela é a média dos dois centrais (7,7 e
> 8,6). Até 2026-10-12 eram 9 e dava 7,7; quando a Figura 3 passou a ser lida do JPEG original
> (ver "Ambiente"), o rio Maratoã (tab. 21) ganhou uma fazenda no ajuste — 4 fazendas e 9
> léguas, contra 3 e 5 —, entrou na amostra com 12,1 e levou a escala a 8,2. As posições
> finais mudaram 0,26 km na mediana; só #79–#81, do próprio Maratoã, andaram mais de 10 km.
>
> E há agora uma confirmação de fora: o relato diz que da fazenda do Tabuleiro-Alto à Matriz
> da Vitória (a atual Oeiras) "se contam 60 léguas, povoadas com fazendas de gados pelo mesmo
> riacho do Piauí abaixo". O mapa dá 333 km descendo o rio mais 48 km por terra até a Matriz:
> **6,4 km por légua** contra os 6,2 da légua de sesmaria, 2% de erro — e essa distância não
> entrou na construção do mapa. Ver `work/afere_ancoras.py`.

**`a`, onde a cadeia começa.** Por padrão, o ajuste contra a Figura 3. Mas o relato costuma
dizer que a última fazenda "está na barra" e que a primeira está "na cabeceira": onde isso
vale, e onde a ponta do tronco é mesmo uma **confluência** (e não apenas o ponto em que a BCIM
deixa de nomear o rio), a cadeia é presa ali. A âncora textual só é aceita se não brigar com a
figura mais que o deslocamento máximo do grupo — a figura continua sendo a única fonte de
posição absoluta.

Aferição: as fazendas que o relato põe "na barra" caem **em cima** do rio que o texto nomeia
como receptor — Santa Rosa (#20) e Sítio Real (#125) sobre o Parnaíba, Tapera (#108) e Saco
(#27) sobre o Canindé, Tucano (#33) sobre o Itaim, todas a **0,00 km** (na versão BCIM ficavam
a 0,02–0,23; o assentamento no traçado da BC250 é exato). São Cosme (#51) fica em cima do Poti,
a 6 km da foz medidos ao longo do rio — não é erro de encaixe, é o resíduo da cadeia, que
termina antes da barra. Isso confirma pouco: #125, #108, #27 e #33 são de grupos presos na
barra, e a #20 fecha a cadeia do Canindé, esticada de ponta a ponta do tronco; nelas os 0,00 km
vêm da construção. A única independente é São Cosme (#51), de grupo ancorado pela figura.

Resultado: **101 fazendas** sobre o curso d'água que o relato nomeia (96 espaçadas por léguas,
5 pelo método antigo), **22** sobre o curso mais próximo e **2** afluentes sem nome na carta.
Deslocamento em relação à Figura 3: mediana 10,9 km, média 14,7 km, máximo 74,9 km — bem maior
que os 4,6 km da versão de 1850, porque agora é o relato, e não a figura, que decide o
espaçamento.

#### Onde relato e figura brigam

- **rio Gurguéia (tab. 29).** O relato põe 20 léguas "de rochas e matos" entre #124 e #125; a
  figura põe 41 km. Não há escala que concilie as duas coisas. Adotou-se o relato, com âncora
  na barra: #119–#124 sobem ~50 km em relação à figura. Aferição possível: a fazenda #119
  chama-se *Serra Vermelha* e a serra homônima da BCIM fica a 55 km do ponto novo contra 50 km
  do ponto da figura — empate, nenhum dos dois é decisivo.
- **riacho da Tranqueira (tab. 8)** e **rio Piauí (tab. 25)** continuam com deslocamentos
  grandes; a figura amontoa o primeiro e distorce o meio do segundo.
- **rio Maratoã (tab. 21).** O relato põe a #79 Ginipapo "na cabeceira"; a cadeia é presa na
  ponta de montante do Maratoã nomeado (junto de Campo Maior) e desce para o norte até Barras.
  A figura desenha o grupo uns 30 km a sudeste: deslocamento médio de 25 km, o segundo maior
  depois do Gurguéia.

#### As três âncoras de fora (`afere_ancoras.py`)

O relato dá três distâncias que **não são** de fazenda a fazenda e por isso não entraram na
construção do mapa. Servem para julgá-lo de fora. Ler contra a légua de sesmaria, ~6,2 km em
linha reta:

| âncora | o texto | o mapa | implica |
|---|---|---|---|
| Tabuleiro-Alto → Matriz da Vitória, "pelo riacho do Piauí abaixo" | 60 léguas | 333 km de rio + 48 km por terra | **6,4 km/légua (+2%)** |
| Alongazes → serra da Ibiapaba | 20 léguas | 86 a 187 km (mediana 158) | 7,9 km/légua; os 124 km do texto caem dentro da faixa |
| Tabuleiro-Alto → rio São Francisco | 40 léguas | 93 km | 2,3 km/légua — **não fecha** |

A primeira é a boa: a Matriz de Nossa Senhora da Vitória é a atual **Oeiras**, e o percurso que
o texto descreve (rio abaixo, depois cortando para a igreja) bate a 2% com a légua de sesmaria.
É a confirmação independente que faltava à escala global.

A terceira não fecha, e a explicação mais provável não é o mapa: o relato nomeia o destino do
caminho — "vai sair do rio São Francisco a uma fazenda chamada o Sobrado, 10 léguas acima do
Santo Sé" —, que não é o ponto do rio mais próximo em linha reta, que é o que se mediu.

### Identificações de rio apuradas (não reabrir sem motivo novo)

- "rio Itaim Açu" da Figura 3 = **rio Poti** (a fazenda 48 chama-se *Poti*; a 51, *São Cosme*,
  cai na foz do Poti, onde hoje é Teresina).
- "rio Itaim Mirim" = **rio Itaim** atual. Era o gargalo da versão BCIM, que só nomeava 78 km
  dele e deixava as fazendas 21–23 fora do trecho nomeado; a BC250 nomeia 220 km e as três
  entraram no espaçamento por léguas.
- "riacho Maratauam" = **rio Maratoã** (Marataoã).
- "riacho Moicatá" = **riacho do Mucaitá** (a BC250 tem também um trecho "Rio Mucaitá").
- "riacho das Berlengas" = **rio Berlengas** na BC250; a BCIM grafava "Beriengas", com *i*.
- "riacho Canabrava" = **riacho Iningá** (na BCIM, "Riacho da Iningá") — a segunda fazenda do
  grupo chama-se *Iningas*.
- "riacho Negro" = **riacho da Serra Negra** — a única fazenda do grupo chama-se *Serra Negra*.
- "riachinho da Serra Talhada" = **ribeirão Talhado**.

#### Os oito topônimos perdidos (procurados a fundo; não reabrir)

Cabeça do Tapuio, São Vítor, Santa Catarina, Santo Antônio, das Cobras, Bitorocara, riachinho
do Buriti e Guaribas do sul **não existem mais**. A hipótese de que uma carta de escala maior
os traria de volta foi testada e **não se confirma**: procurados no índice de nomes inteiro da
BC250 (`work/gazetteer_bc250.parquet`, 47 mil topônimos do Piauí e entorno — drenagem,
povoados, aglomerados rurais, serras, lagoas), quatro deles não aparecem em lugar nenhum, e os
outros quatro só aparecem de 70 a 500 km dali, em outra bacia. Não é falta de detalhe da carta:
são nomes que morreram em 330 anos.

Testou-se também o caminho inverso — casar os **nomes das 125 fazendas** com povoados atuais,
na esperança de que a fazenda tivesse virado lugarejo homônimo e desse uma âncora absoluta.
Rende pouco: só *Sussuapara* (#30, a 3,9 km) e *São Nicolau* (#60, a 7,8 km) casam de perto, e
os demais nomes são genéricos demais (Barra, Serra, Tapera, Boqueirão) para valerem como prova.

Esses 23 pontos continuam, portanto, na posição da Figura 3, encaixados no riacho mais próximo,
e é neles que a precisão do mapa é menor. Sair daí exige fonte documental nova — sesmarias,
inventários, cartas do século XVIII —, não outra carta do IBGE.

### Correções de leitura herdadas do trabalho anterior

- Legendas das Tabelas 18–20 do PDF estão deslocadas. Pelo texto: riacho São Vicente = 71–74;
  riacho das Berlengas = 75–77; riacho Santo Antônio = 78 (fazenda **Santo Antônio**).
- A fazenda 88 (riachinho do Buriti) não tem nome no relato: é a "fazenda de Éguas" do
  Capitão Domingos Afonso Sertão, na cabeceira do Canindé, junto da 1.
- Nº 55/56 (Cabeça do Tapuio): "Olho d'Água" e "Sítio da Cruz" podem estar trocados entre si.

## A base cartográfica

- **BCIM 2016** (`bcim_2016_21_11_2018.gpkg`, 1:1.000.000, EPSG:4674) — a base de **desenho**:
  hidrografia de fundo (`hid_trecho_drenagem_l`), massas d'água, terrenos sujeitos a inundação,
  curvas de nível, serras e chapadas nomeadas (`rel_elemento_fisiografico_natural_l`), unidades
  de conservação, extração mineral, cidades.
- **BC250 2025** (1:250.000, EPSG:4674) — a base do **encaixe**, e a fonte dos rios que o relato
  percorre. Não está no repositório como arquivo original: os 824 MB do pacote nacional não
  valem a pena quando só se quer o Piauí, então `work/baixa_bc250.py` e
  `work/baixa_gazetteer.py` puxam o recorte por **WFS** (`geoservicos.ibge.gov.br/geoserver`,
  camadas `CCAR:BC250_2025_hid_trecho_drenagem_l` e `CCAR:BC250_2025_indice_nomes`) e gravam
  dois parquets de poucos MB. O WFS não aceita `sortBy` nessas camadas; a paginação vai por
  `startIndex` e os ids são guardados para conferir que nada se perdeu.
- **Vegetação IBGE 1:5.000.000** (`dados_ibge/veg5000/`, baixada do geoftp) — regiões
  fitoecológicas, agrupadas em caatinga (savana-estépica), cerrado (savana), floresta
  estacional, contatos e formações pioneiras. A BCIM **não** traz vegetação do interior
  (só mangue e restinga do litoral), daí a fonte externa.
- **Geologia:** não entrou. O `geol_area.zip` do IBGE (1:250.000) tem 417 MB — dá para incluir,
  mas exige generalização pesada para caber num HTML leve. Por ora, "rochas" aparecem só como
  relevo (curvas ≥ 400 m, serras e chapadas nomeadas) e pontos de extração mineral.

## O HTML

`descricao_interativa_bcim.html`, 1,4 MB, **autocontido**: nenhuma requisição externa, nenhum
CDN, nenhum tile. O mapa é um **SVG inline** de 4403×3588 px (equirretangular, 390 px/grau,
`x` corrigido por cos φ) — a carta propriamente dita mais a coluna do cartucho à esquerda. A câmera do scroll é a mesma da versão de 1850 — o `transform` do
`#mapwrap` — só que agora sobre o SVG.

- **Não há mais painel de camadas.** O que a carta mostra é fixo: vegetação, relevo, rios do
  relato + nomes, cidades, estados vizinhos, moldura e cartucho. Os grupos que nasciam
  desligados (`g-uc`, `g-uc-txt`, `g-mineral`, `g-mun`) continuam no SVG, escondidos por uma
  regra de CSS — é uma linha para trazê-los de volta, com painel ou sem.
- O índice das seções deixou de ser caixa flutuante e virou **cabeçalho do próprio texto**
  (`#topo`, `position:sticky`), junto do botão `⇄` que troca o painel de lado. O `#legenda`
  (a chave das duas cores de fazenda) voltou a aparecer nas seções com pontos, que é onde ele
  serve; nas de visão geral quem responde é a legenda do cartucho.
- Os rios que o relato percorre são desenhados mais grossos e **rotulados ao longo do curso**
  (`<textPath>`), que era o problema principal das versões sobre carta antiga.
- Marcador laranja = no rio que o relato nomeia; roxo = sem homônimo na BCIM (posição da
  Figura 3). O tooltip mostra o rio da BCIM, a légua acumulada do relato e quantos km o ponto
  andou em relação à Figura 3.
- `fitZoom()` foi trocado para `min(...)` (a tela agora é retrato, não paisagem) e há um
  fallback por evento de `scroll` além do `IntersectionObserver`.
- A câmera é presa à **faixa livre** (`faixa()`/`prendeX`) — a parte da tela que o painel de
  texto não cobre —, e não à janela inteira. Prendê-la à janela obrigava o mapa a preencher
  também o trecho sob o texto, e os grupos do leste do estado (Canindé, Itaim) acabavam
  empurrados para debaixo do painel. O enquadramento de cada grupo deixa `M = 170 px` de tela
  de folga (o rótulo do ponto não escala com o zoom), com teto de zoom 2,4 e piso dado pelo
  próprio `fitZoom()`.
- O mapa pode ser **arrastado com o mouse** a qualquer momento (pointer events no `#viewport`,
  que fica sob o painel — arrastar sobre o texto continua selecionando texto). A folga do
  arrasto é frouxa de propósito, para alcançar o que o painel esconde; o próximo `goTo()`
  reenquadra.
- O painel *Camadas* é **minimizável** (`#camBtn` → `.min`); nasce minimizado em telas ≤ 820 px.
- Há botões **+ / − / ⟲** (`#zoomctl`): aproximar, afastar e reenquadrar a seção. O zoom
  mantém parado o ponto do mapa que está no centro da faixa livre e usa a mesma folga
  frouxa do arrasto. **Não** há zoom pela roda do mouse de propósito — a roda rola o
  texto, e é a rolagem que faz a leitura avançar.

### A moldura e o entorno

- O quadro deixa **~0,95° de folga a leste e a oeste** — é nessa faixa que aparecem os estados
  vizinhos — e só **~0,5° ao norte e ao sul**. A assimetria é deliberada: a folha é em pé e a
  faixa livre da tela é deitada, então **é a altura que limita o zoom de abertura**, e cada grau
  de folga vertical encolhe o Piauí na tela. Carta: 2923 × 3588 px.
- O **entorno** (`#g-viz`) traz o preenchimento dos estados, a vegetação e a drenagem, e
  logo depois um **véu** — um retângulo de papel translúcido sobre a folha inteira. O Piauí
  é repintado *por cima* dele, de modo que só o que está fora fica ofuscado; não é preciso
  clip invertido. Os nomes dos vizinhos vão depois do véu, para não desbotarem.
- Fora do Piauí só entram os cursos d'água cujo homônimo soma **≥ 60 km** dentro do quadro.
  Sem esse corte a faixa dos vizinhos são 11,6 mil trechos e 330 kB — mais peso que o próprio
  Piauí, e concorrência visual com ele.
- A vegetação é desenhada duas vezes (dentro e fora), mas definida **uma vez** em
  `<defs><g id="veg-def">` e instanciada com `<use>`; do contrário custaria 108 kB duas vezes.
- `moldura()` desenha a borda da carta: escada de 15' alternada numa faixa de 38 px, dupla
  linha de contorno, cruzes nos cruzamentos de grau inteiro e os graus escritos por dentro.
  É só geometria — custa ~4 kB.
- O entorno é `#g-viz` + `#g-viz-txt`; a vegetação de fora, `#g-veg-fora`.
- `L["mun"]` agora é filtrado pelos municípios que tocam o Piauí: o desenho é recortado no
  `cpPI` de qualquer forma, e com o quadro maior o resto era só bytes desenhados e escondidos.

### A coluna do cartucho (`cartucho()`)

O vazio das seções de visão geral não era erro de enquadramento: a faixa livre da tela é
**deitada** (1053 × 786 numa janela de 1480, proporção 1,34) e o Piauí é **em pé** (proporção
0,68). Mesmo enquadrando o estado sem margem nenhuma sobrariam ~50% da largura. Ou se preenche
a largura, ou se compõe com ela — e o lugar clássico do título numa carta é justamente essa
margem que sobra.

- `B.PAD = 1480` px de **papel à esquerda da carta**, dentro da linha externa da moldura.
  `B.xy()` soma `PAD` a x, de modo que toda a geometria já nasce deslocada; `moldura()` recebe
  `X0 = B.PAD` e cerca **só a estampa** — a coluna fica ao lado, como um painel de título.
- A coluna leva, de cima para baixo: título, rosa dos ventos (8 pontas; a projeção não tem
  rotação, o norte é reto), legenda (5 classes de vegetação + 7 símbolos), **escala dupla —
  km e léguas** — e a procedência. Custa **9,3 kB**; a moldura, 6,9 kB. A legenda só nomeia o
  que a carta de fato desenha: sem painel de camadas, entrada de legenda para camada
  escondida é promessa que não se cumpre.
- A régua de léguas é a que interessa: a légua de sesmaria vale ~6,2 km em linha reta, e é
  nessa unidade que o relato mede o sertão. Escala verdadeira no paralelo de 7° S
  (1 px = 111,32/390 km ≈ 0,285 km).
- `fitZoom()` deixou de usar o `freeBox()` das seções de fazenda e passou a usar `folha()`,
  que aperta a margem (0,97 da faixa livre, contra 0,86 × 0,80): ali não há rótulo de ponto a
  proteger. Somando a folha mais larga, a margem vertical menor e a margem apertada, o vazio
  lateral caiu de **56% para 3–20%** (conforme a janela) e o Piauí **cresceu ~34%** na abertura.
  Alargar mais a coluna não adianta: a partir de certo ponto a largura passa a ser o lado que
  limita o zoom, e aí quem encolhe é o Piauí.
- Os botões de zoom saíram do canto superior esquerdo — cobriam o título — para junto do painel
  de texto (`right: calc(var(--panelW) + 12px)`).
- Com o painel de camadas fora, `g-cartucho` e `g-moldura` são fixos.

### Os rótulos de rio

O corpo era 19 fixo, e “Ribeirão Talhado” (140 px de texto) era escrito sobre 36 px de rio —
sobrava por cima de tudo o que estivesse ao lado. Agora (`rotulos_rio()`):

- o corpo **sai do comprimento do próprio curso** (`0,90 · P / largura_por_em`), com teto 20
  para os cinco rios grossos e 16 para os demais, e piso 11;
- quem não cabe deitado no rio — Tranqueira, Frade, Talhado — vira **rótulo reto ao lado**,
  em corpo 12;
- a posição é escolhida por tentativa entre uns tantos pontos do curso: vence a que menos
  esbarra nas caixas já colocadas (cidades, serras e os outros rios) e a menos torta —
  curva fechada faz o `<textPath>` **empilhar as letras** no lado de dentro;
- o trilho do rótulo é reamostrado e suavizado (`_reamostra`), justamente contra esse
  empilhamento: ele não precisa ser fiel ao rio, só precisa acompanhá-lo;
- todos ganharam auréola de papel (`paint-order="stroke"`), que era o que faltava para o
  nome sobreviver por cima da drenagem fina e das curvas de nível.

## Arquivos

| Arquivo | Descrição |
|---|---|
| `descricao_interativa_bcim.html` | o mapa (versão atual) |
| `fazendas_1697_bcim.csv` | 125 pontos: `numero, fazenda, corpo_dagua, tabela, lon, lat, lon_fig3, lat_fig3, metodo, desloc_km, rio_bcim, nota_rio, legua_acum, km_por_legua, ancora` |
| `work/leguas_1697.csv` | as léguas lidas do OCR: `numero, tabela, ordem, legua_prox, legua_acum, dist_barra, lateral, ref_numero, ref_legua, na_cabeceira, na_barra` |
| `work/escala_global.json` | a escala global (km de rio por légua), a amostra de grupos e a banda, gravadas por `snap_rios.py` e lidas por `afere_ancoras.py` |
| `work/drenagem_bc250.parquet` | drenagem BC250 do Piauí (66 mil trechos) — a base do encaixe |
| `work/gazetteer_bc250.parquet` | índice de nomes da BC250 (47 mil topônimos) — usado para procurar os oito riachos perdidos |
| `work/` | scripts do pipeline + intermediários (`pi_uf.gpkg`, `drenagem_bbox.parquet`, `qc/`) |
| `dados_ibge/` | vegetação 1:5M baixada do geoftp |
| `descricao_interativa.html`, `descricao_interativa_1.html` | versões antigas sobre a carta de 1850 |
| `.claude/launch.json` | `python -m http.server 8731` para pré-visualizar o HTML |

## Ao editar

- Mexeu nos 125 pontos (posição, nome, agrupamento): a validação 1–125 sem lacuna nem
  repetição tem de continuar valendo — `snap_rios.py` e `monta_mapa.py` têm `assert` para isso.
- `work/snap_rios.py` → `RIOS[tabela] = (nomes na BC250, raio de busca km, deslocamento máximo
  km, nota)`. **Os nomes são os da BC250, que nem sempre coincidem com os da BCIM** — "Rio
  Berlengas" e não "Beriengas", "Riacho Iningá" e não "Riacho da Iningá". O **deslocamento
  máximo** decide duas coisas: se um grupo é puxado para o rio nomeado e se a âncora textual
  ("na barra", "na cabeceira") é aceita. Valores altos (tabela 8 = 45 km, tabela 25 = 80 km)
  são deliberados: nesses grupos o relato é explícito sobre o rio e a Figura 3 é que está
  imprecisa.
- `monta_mapa.py` tem **duas** listas de rio: `RIOS_RELATO` (nomes na BC250, o que se desenha
  grosso e se rotula) e `RIOS_RELATO_BCIM` (os mesmos rios como a BCIM os nomeia, para suprimir
  o traçado fino por baixo). Acrescentou nome numa, veja se precisa na outra — senão o rio sai
  em duas linhas vizinhas e ligeiramente diferentes.
- `TOL_TRONCO` (0,004° ≈ 445 m) é a generalização com que as léguas são medidas. **Não é
  cosmético:** sem ela a escala passa a medir a resolução da carta em vez do terreno. Baixá-la
  infla os km por légua de cada rio na medida da sua sinuosidade; subi-la demais começa a
  cortar curva que o relato percorreu.
- `B_LO`/`B_HI` filtram os grupos que entram na estimativa da escala global; `BANDA` diz quanto
  um grupo pode fugir dela. Mexer em `BANDA` mexe em todo o mapa — a banda atual (0,6–1,8×)
  acomoda o Poti (14,2 km/légua) sem deixar solto o riacho do Cais, que sozinho pediria 31.
- Mexeu no OCR ou no parser: `leguas.py` valida a numeração interna de cada seção **e** o
  conjunto 1–125; se uma seção mudar de tamanho, ele falha alto, é para falhar mesmo.
- Ordem de execução (cada um com `uv run python work/...`): `leguas.py` → `snap_rios.py` →
  `monta_mapa.py` → `qc_mapa.py` → `afere_ancoras.py`, depois `uv run pytest`, e olhar `work/qc/` (círculo vazado = posição da Figura 3, ponto cheio =
  posição final; vermelho = léguas, laranja = rio nomeado sem léguas, azul = afluente, roxo =
  drenagem próxima). As vistas do QC **saem dos próprios pontos** — basta dizer que tabelas
  olhar; as antigas eram viewBox escritos à mão e, depois que a coluna do cartucho deslocou a
  estampa, enquadravam o Maranhão.
- `snap_rios.py` grava em `work/fazendas_1697_bcim.csv`; o `fazendas_1697_bcim.csv` da raiz é a
  cópia publicada, e é preciso atualizá-la à mão.
- O texto do relato vem de `descricao_interativa_1.html` (`monta_mapa.py` lê as `<section>` de
  lá). Correções de texto devem ser feitas naquele arquivo, ou na lista `TROCAS`. As 9
  notas que comentam a carta de 1850 são retiradas no próprio `monta_mapa.py` (com `assert`
  na contagem) — o HTML antigo continua inteiro, porque é o texto da versão de 1850.
- **Não edite o HTML publicado à mão**: a próxima execução de `monta_mapa.py` desfaz a
  edição. O enquadramento das seções sem fazendas está em `CAM` (lon, lat, zoom).
- `monta_mapa.py` é determinístico: duas execuções dão o mesmo arquivo, byte a byte
  (a ordem dos `<path>` dos rótulos vinha de um `set` e mudava a cada execução).

## Próximos passos possíveis

- **Geologia.** Continua de fora. O `geol_area.zip` do IBGE (1:250.000) tem 417 MB; dá para
  incluir, mas exige generalização pesada para caber num HTML leve. Por ora, "rochas" aparecem
  só como relevo (curvas ≥ 400 m, serras e chapadas nomeadas) e pontos de extração mineral.
- **Os 23 pontos sem rio nomeado.** É o que resta de mais frágil no mapa, e não sai por
  cartografia: os oito topônimos foram procurados no índice de nomes inteiro da BC250 e não
  existem mais (ver acima). O caminho agora é documental — sesmarias, inventários, cartas
  setecentistas —, ou aceitar que ali a posição é a da Figura 3.
- **A âncora do São Francisco não fecha.** Das três distâncias externas que o relato dá, duas
  confirmam a escala (a Matriz da Vitória a 2% e a Ibiapaba dentro da faixa) e uma não: o texto
  põe o Tabuleiro-Alto a 40 léguas (~248 km) do rio São Francisco, e o mapa dá 93 km. O ponto
  medido é o trecho de rio mais próximo em linha reta, e não o Sobrado que o relato nomeia como
  fim do caminho — que fica bem mais para jusante. Localizar o Sobrado resolveria a dúvida, e
  de quebra diria se a #90 está no lugar certo.
- **Rever `CAP_GENERICO` à luz da BC250.** O encaixe genérico ainda usa raio de 6 km, calibrado
  quando a drenagem era a da BCIM. Com quatro vezes mais trechos, um raio menor talvez baste e
  evite pendurar a fazenda num riacho qualquer que só está perto por acaso.
