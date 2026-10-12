# NOTA METODOLÓGICA: CONVERSÃO DAS DISTÂNCIAS EM LÉGUAS DO RELATO DE 1697 EM POSIÇÕES SOBRE A HIDROGRAFIA DO IBGE

**Resumo** — Esta nota descreve como as distâncias em léguas registradas por Miguel de Carvalho
na *Descrição do sertão do Piauí* (1697) foram convertidas em posições, medidas em quilômetros,
ao longo da drenagem da Base Cartográfica Contínua do Brasil 1:250.000 (BC250) do IBGE. O
procedimento combina três fontes de natureza distinta: o relato, que fornece a ordem e o
espaçamento das fazendas ao longo de cada curso d'água; a Figura 3 de Baptista (1986), que
fornece a única posição absoluta disponível; e a carta do IBGE, que fornece o traçado atual dos
rios. A nota cobre a extração das léguas, o referenciamento linear sobre o rio, a generalização
cartográfica que torna a régua estável, a estimação da escala (km de rio por légua) com
restrição de banda, a ancoragem textual e a aferição externa do resultado.

**Palavras-chave:** Cartografia histórica. Referenciamento linear. Légua. Sinuosidade fluvial.
Generalização cartográfica. Piauí colonial.

---

## 1 INTRODUÇÃO

O relato de 1697 percorre 29 corpos d'água e, para cada um, enumera as fazendas de gado na
ordem em que aparecem ao longo do curso. Quase toda entrada termina com a mesma fórmula:
"dista da que se segue *N* léguas". O texto, portanto, não é apenas uma lista nominal: é um
itinerário medido. A Figura 3 de Baptista (1986, p. 36) posiciona as 125 fazendas num mapa
mudo do Piauí, mas sem escala interna confiável — ela amontoa alguns grupos e espalha outros.

O problema metodológico é transformar uma medida histórica de comprimento (a légua, contada
ao longo de um caminho que acompanha o rio) numa posição sobre uma linha cartográfica moderna,
de modo que **o relato decida o espaçamento entre as fazendas** e a figura decida apenas
**onde a cadeia começa e para que lado corre**. Esta nota descreve as decisões teóricas e
formais desse procedimento, implementado em `work/leguas.py` e `work/snap_rios.py`; não
descreve o software em si, nem o georreferenciamento da Figura 3 (que precede esta etapa: os
grandes rios do relato na BC250 ficam a 5,7 km, em mediana, das linhas da figura, contra 13,9 km
para pontos sorteados ao acaso no estado), nem a montagem do mapa interativo.

## 2 FUNDAMENTAÇÃO TEÓRICA

### 2.1 A légua como medida de percurso

A légua luso-brasileira não era uma unidade única. Os dois valores que importam aqui são a
**légua de 18 ao grau**, ≈ 6,17 km (1/18 de grau de meridiano), e a **légua de sesmaria**,
de 3.000 braças, ≈ 6,6 km *(referência metrológica a ser completada conforme a fonte
primária)*. O projeto adota ~6,2 km como valor de referência em linha reta.

Mais importante que o valor nominal é o **modo de medir**. No sertão de 1697 a distância
entre duas fazendas do mesmo riacho era contada pelo caminho, que acompanhava o curso d'água.
Ao projetar essas léguas sobre o traçado de um rio, mede-se, por construção, um comprimento
**ao longo de uma linha sinuosa**, e a razão entre esse comprimento e a distância em linha reta
é o que a geomorfologia fluvial chama de **índice de sinuosidade** (LEOPOLD; WOLMAN; MILLER,
1964). Por isso a grandeza a estimar não é "quilômetros por légua", mas **quilômetros de rio por
légua** — um valor que se espera maior que 6,2 e que carrega a sinuosidade típica da rede. Essa
distinção justifica a estimação empírica da escala na seção 6, em vez de fixá-la a priori.

### 2.2 O comprimento de um rio depende da escala da carta

Mandelbrot (1967) mostrou que o comprimento medido de uma linha natural irregular cresce à
medida que a régua encurta: quanto mais detalhada a representação, mais longa a linha. Uma
carta 1:250.000 desenha meandros que a carta 1:1.000.000 suprime, e o mesmo rio passa a medir
mais. No projeto, o mesmo percurso mede de **1,10 a 1,21 vez mais** na BC250 que na BCIM — e
não na mesma proporção para todos os rios. Tomado cru, o coeficiente "km de rio por légua"
passaria a medir a resolução da carta, não o terreno. Esse efeito motiva a generalização do
tronco antes da medida (seção 5).

### 2.3 Generalização de linhas

O algoritmo de Douglas e Peucker (1973) remove vértices de uma polilinha cujo afastamento da
corda seja inferior a uma tolerância ε, preservando a forma geral da linha. Aplicado ao tronco
de cada rio, ele estabelece uma **régua de resolução fixa e conhecida**, independentemente do
nível de detalhe da carta de origem. É o instrumento usado na seção 5.

### 2.4 Referenciamento linear

Em vez de coordenadas planas, uma posição sobre uma rede linear pode ser expressa pela
distância *s* percorrida desde a origem da linha (referenciamento linear). É a forma natural
de representar o relato, que diz "a tantas léguas da anterior", e permite separar o problema em
duas partes: estimar *s* para cada fazenda (seção 6) e, depois, converter *s* em coordenadas
(seção 8).

---

## 3 BASE DE DADOS E DEFINIÇÕES OPERACIONAIS

**Unidade de análise.** A fazenda (*i* = 1, …, 125), agrupada no corpo d'água *g* a que o relato
a atribui (tabelas 1–29 de *Os Jesuítas no Piauí*).

**Fontes.**

- relato de 1697, em OCR (`descricao_cap2_ocr.txt`);
- Figura 3 georreferenciada (`work/pontos_fig3_bruto.csv`): posição (λᵢᶠ, φᵢᶠ) de cada fazenda;
- drenagem da BC250 2025, recortada para o Piauí por WFS (`work/drenagem_bc250.parquet`,
  66 mil trechos, 3.910 nomes distintos), em SIRGAS 2000 geográfico (EPSG:4674).

**Correspondência de nomes.** Cada corpo d'água de 1697 foi associado ao(s) nome(s) atuais da
BC250 (dicionário `RIOS` em `snap_rios.py`) — por exemplo, o "Itaim Açu" da Figura 3 é o rio
Poti, porque a fazenda 48 se chama *Poti* e a 51, *São Cosme*, cai na foz do Poti. Oito
topônimos de 1697 não existem mais em nenhum ponto do índice de nomes da BC250; seus grupos
não entram no espaçamento por léguas.

**Conversão de graus em quilômetros.** As geometrias permanecem em coordenadas geográficas; os
comprimentos são calculados no plano (λ, φ) e convertidos por uma constante:

$$ K = 111{,}32\ \text{km}/\text{grau} \tag{1} $$

Essa simplificação é discutida nas limitações (seção 11).

---

## 4 EXTRAÇÃO DAS LÉGUAS DO RELATO

### 4.1 Leitura dos passos

O parser (`leguas.py`) localiza as 29 seções do relato pelo cabeçalho em algarismo romano,
agrupa as linhas de cada entrada numerada e procura o passo até a fazenda seguinte. A forma
canônica é "dista da que se segue *N* léguas", mas o OCR e a própria redação exigiram aceitar
variantes — "desta à debaixo se acham 5 léguas" (#1), "dista da que segue" (#119), "e da
fazenda que se segue" (#122, onde o OCR suprimiu "dista") — e normalizar dígitos lidos como
letras (`O5`, `OS`, `0O8`). Numerais por extenso ("uma", "duas", …, "dez") são convertidos.

Duas validações tornam a extração falha-alto em vez de falha-silenciosa: a numeração interna
de cada seção tem de ser exatamente 1…*n*, e o conjunto final tem de ser 1–125, sem lacuna nem
repetição. Uma entrada perdida pelo OCR desloca todas as seguintes; sem essa trava, o erro
chegaria ao mapa sem ser notado.

Resultado: **94 passos legíveis**, de 1 a 20 léguas (mediana 3; 72% das ocorrências são de 2
ou 3 léguas). A última fazenda de cada riacho não tem passo, e não precisa.

Uma ocorrência foi deliberadamente excluída da cadeia: "dista da barra uma légua" (#111) não é
um passo até a fazenda seguinte, mas até a foz; é registrada à parte (`dist_barra`).

### 4.2 Légua acumulada

Seja *pᵢ* o passo, em léguas, da fazenda *i* até a seguinte do mesmo curso, e seja *Pg* o
conjunto das fazendas do curso principal do grupo *g*, na ordem do relato. A posição de cada
fazenda ao longo do curso, em léguas, é a soma dos passos anteriores:

$$ L_i = \sum_{\substack{j \in P_g \\ j < i}} p_j, \qquad L_{\text{primeira}} = 0 \tag{2} $$

*Lᵢ* é a coordenada do relato: diz quantas léguas separam a fazenda *i* da primeira fazenda
do seu riacho, medidas pelo caminho. É a única informação de espaçamento que entra no método;
tudo o que vem depois serve para traduzi-la em quilômetros e prendê-la ao rio certo.

### 4.3 Digressões

Duas entradas do rio Piauí não são fazendas do curso principal: #91 *Curral do Campo* fica no
riacho Inhinhinga, "10 léguas" do Tabuleiro-Alto (#90), e #93 *Sítio das Pimentas* no
riachinho do Buqueirão, "3 léguas" da Fazenda-Grande (#92). O texto as mede a partir de uma
fazenda nomeada, não da anterior. Elas **não consomem passo**:

$$ L_i^{\text{digressão}} = L_{\text{ref}(i)} \tag{3} $$

e o passo da entrada que as precede aponta para a próxima fazenda do curso principal. Tratá-las
como elos da cadeia encurtaria o rio Piauí em 44 léguas — cerca de 270 km de rio na escala
adotada. Por não estarem sobre o tronco, essas duas fazendas ficam fora do ajuste das seções
5 a 8 (método `afluente`).

---

## 5 O TRONCO DE CADA RIO E A RÉGUA GENERALIZADA

### 5.1 Montagem do tronco

Os trechos da BC250 com o nome associado ao grupo são unidos e costurados (`linemerge`, seguido
de encadeamento guloso pelos extremos com tolerância de 0,03°). Isso produz uma ou mais
componentes conexas — homônimos em bacias diferentes saem separados. O **tronco** do grupo é a
componente conexa **mais longa** entre as que estão a até *R*g km dos pontos do grupo na
Figura 3 (raio de busca, 25 a 85 km conforme o grupo).

A escolha da componente inteira, e não dos trechos avulsos mais próximos dos pontos, tem uma
razão substantiva: filtrar trecho a trecho pela distância à figura truncava rios longos — o
Gurguéia perdia 250 km — e, ao truncar o rio, devolvia ao resultado o erro da própria figura,
que é exatamente o que o método quer evitar.

### 5.2 Generalização antes de medir

Seja Γg o traçado completo do tronco na BC250. As léguas não são projetadas sobre Γg, e sim
sobre a sua versão generalizada por Douglas–Peucker:

$$ \tilde{\Gamma}_g = \mathrm{DP}(\Gamma_g;\ \varepsilon), \qquad \varepsilon = 0{,}004^\circ \approx 445\ \text{m} \tag{4} $$

Com essa tolerância, a razão entre o comprimento do mesmo percurso na BC250 generalizada e na
BCIM cai de 1,10–1,21 para **1,00–1,07**: a régua volta a medir o terreno, e o ganho que
motivou a troca de carta — mais quilômetros de rio **nomeado**, portanto mais fazendas
espaçadas pelo texto — permanece. Na prática, a generalização encurta os troncos entre 6% (rio
Canindé, 448 → 421 km) e 19% (rio Gurguéia, 768 → 619 km), proporção que acompanha a
sinuosidade de cada um.

O valor de ε foi escolhido por estar muito abaixo das duas incertezas que governam o problema:
o passo mínimo do relato (uma légua, ~6 km) e o erro do georreferenciamento da Figura 3
(~5 km). Uma tolerância menor reintroduz o efeito de Mandelbrot (seção 2.2) e infla a escala
de cada rio na medida da sua sinuosidade; uma tolerância muito maior começa a cortar curvas que
o caminho de 1697 de fato percorria.

### 5.3 Projeção da Figura 3 sobre o tronco

Cada ponto da Figura 3 é projetado ortogonalmente sobre o tronco generalizado, o que dá sua
posição linear observada:

$$ s_i^{\,f} = \mathrm{proj}_{\tilde{\Gamma}_g}\big(\lambda_i^f, \varphi_i^f\big) \in [0, \ell_g] \tag{5} $$

em que ℓg é o comprimento de Γ̃g. Entram no ajuste apenas as fazendas do curso principal cuja
distância ao tronco não excede o deslocamento máximo *D*g aceito para o grupo (20 a 80 km);
os demais pontos são considerados fora do rio nomeado. O sentido do relato ao longo do tronco
(montante → jusante ou o inverso) é dado pelo sinal da correlação entre a ordem das fazendas e
*sᵢᶠ*:

$$ \sigma_g = \mathrm{sinal}\big(\mathrm{corr}(i, s_i^{\,f})\big) \in \{-1, +1\} \tag{6} $$

O grupo só é espaçado por léguas se tiver pelo menos duas fazendas aproveitáveis, todas com *Lᵢ*
conhecido e com amplitude de *L* positiva. Quinze grupos cumprem o critério, somando 96
fazendas.

---

## 6 A ESCALA: QUILÔMETROS DE RIO POR LÉGUA

### 6.1 Modelo

A posição de cada fazenda ao longo do tronco é modelada como função linear da légua acumulada:

$$ s_i = a_g + b_g \, L_i \tag{7} $$

O coeficiente *b*g, multiplicado por *K*, é a **escala do grupo em km de rio por légua**; *a*g é
a âncora, isto é, onde a primeira fazenda cai no tronco. O modelo é linear porque o relato não
dá razão para supor que a légua variasse ao longo de um mesmo rio: o que varia entre rios é a
sinuosidade, absorvida em *b*g.

### 6.2 Estimação por grupo

A inclinação de cada grupo é estimada por mínimos quadrados ordinários de *sᵢᶠ* contra *Lᵢ*:

$$ \hat{b}_g = \frac{\mathrm{cov}(L, s^f)}{\mathrm{var}(L)} \tag{8} $$

A alternativa óbvia seria um estimador robusto, como a mediana das inclinações par a par
(SEN, 1968). Ela foi testada e rejeitada por uma razão específica deste problema: quando a
Figura 3 acerta as pontas de um grupo mas erra o espaçamento interno, o estimador robusto
segue as pernas do meio e devolve uma escala espúria — no Gurguéia, 15,6 km/légua contra 6,6
por mínimos quadrados. Os mínimos quadrados dão mais peso às pontas e recuperam a escala que o
vão total do grupo implica, que é a informação mais confiável da figura.

### 6.3 Escala global

Mesmo assim, grupos pequenos ou mal desenhados podem pedir escalas impossíveis — o rio do Cais,
com duas fazendas e três léguas, pediria 31 km de rio por légua. Para conter isso, estima-se
primeiro uma escala **global**, a mediana dos grupos grandes e bem comportados:

$$ b^{*} = \operatorname{mediana}\big\{\, K|\hat{b}_g| \;:\; n_g \ge 4,\ \ \max L - \min L \ge 5,\ \ 4 \le K|\hat{b}_g| \le 18 \,\big\} \tag{9} $$

em que *n*g é o número de fazendas do grupo aproveitadas no ajuste. Dez grupos entram na
amostra (Tabela 1), e a mediana — a média do quinto e do sexto valores, 7,69 e 8,61 —
resulta em:

$$ b^{*} = 8{,}15\ \text{km de rio por légua} \tag{10} $$

A mediana, e não a média, porque a amostra é pequena e assimétrica: três grupos (Itaim,
Tranqueira, Poti) pedem 14–16 km/légua, e a média seria arrastada por eles.

**Interpretação.** Dividido pela légua em linha reta (~6,2 km), *b*\* dá **1,31** — um índice de
sinuosidade de rio sinuoso, abaixo do limiar de 1,5 com que Leopold, Wolman e Miller (1964)
caracterizam os canais meandrantes. A escala que emerge dos dados tem, portanto, a ordem de grandeza física esperada
para uma medida feita pelo caminho ao longo do rio, e não foi imposta ao modelo.

### 6.4 Banda de tolerância por grupo

Cada grupo pode afastar-se da escala global apenas dentro de uma banda multiplicativa:

$$ b_g = \sigma_g \cdot \frac{\min\!\big(\max(K|\hat{b}_g|,\ 0{,}6\,b^*),\ 1{,}8\,b^*\big)}{K}, \qquad 0{,}6\,b^* = 4{,}89,\quad 1{,}8\,b^* = 14{,}67 \tag{11} $$

A banda é larga o bastante para acomodar diferenças reais de sinuosidade — o Poti, muito
meandrado, pede 14,2 e cabe nela — e estreita o bastante para que um grupo mal posicionado
na figura não invente uma escala fisicamente impossível. Há ainda uma restrição de
consistência: a cadeia não pode ser mais longa que o próprio tronco,

$$ |b_g| \cdot (\max L - \min L) \le \ell_g \;\Rightarrow\; \text{caso contrário } |b_g| = \frac{\ell_g}{\max L - \min L} \tag{12} $$

restrição que, na prática, só atuou no rio Canindé (59 léguas sobre 421 km de tronco: 7,7 → 7,1
km/légua).

**Tabela 1 — Escala estimada e adotada por grupo**

| Tab. | Rio (BC250) | Fazendas no ajuste | Amplitude (léguas) | *K*·*b̂*g (km/légua) | Na amostra de *b*\* | *b*g adotado | Âncora |
|---:|---|---:|---:|---:|:---:|---:|---|
| 1 | Rio Canindé | 20 | 59 | 7,7 | sim | 7,14 ¹ | cabeceira |
| 2 | Rio Itaim | 6 | 10 | 15,8 | sim | 14,67 ² | barra |
| 3 | Rio Guaribas | 6 | 11 | 8,6 | sim | 8,61 | barra |
| 8 | Ribeirão da Tranqueira | 5 | 9 | 14,8 | sim | 14,67 ² | barra |
| 9 | Rio Poti | 9 | 21 | 14,2 | sim | 14,22 | figura |
| 10 | Rio do Cais | 2 | 3 | 31,2 | não | 14,67 ² | figura |
| 12 | Riacho Iningá | 2 | 3 | 10,5 | não | 10,45 | barra |
| 13 | Rio São Nicolau | 3 | 12 | 6,7 | não | 6,66 | barra |
| 18 | Rio São Vicente | 4 | 10 | 4,1 | sim | 4,89 ³ | figura |
| 19 | Rio Berlengas | 3 | 7 | 11,5 | não | 11,53 | figura |
| 21 | Rio Maratoã | 4 | 9 | 12,1 | sim | 12,11 | cabeceira |
| 25 | Rio Piauí | 18 | 62 | 7,7 | sim | 7,66 | barra |
| 26 | Riacho do Mucaitá | 3 | 8 | 10,2 | não | 10,20 | figura |
| 27 | Rio Itaueira | 4 | 9 | 4,9 ⁴ | sim | 4,89 ³ | figura |
| 29 | Rio Gurguéia | 7 | 32 | 6,8 | sim | 6,82 | barra |

Fonte: elaboração própria a partir de `work/snap_rios.py` e `work/fazendas_1697_bcim.csv`.
Notas: ¹ limitado pelo comprimento do tronco, eq. (12); ² limitado pelo teto da banda, eq. (11);
³ limitado pelo piso da banda; ⁴ 4,889, a 0,002 abaixo do piso (4,891).

Cinco dos quinze grupos batem num dos limites da banda — três no teto, dois no piso. Isso não é
defeito do método, mas o seu funcionamento previsto: são grupos em que a figura sozinha pediria
uma escala que o restante da rede desmente.

---

## 7 A ÂNCORA: ONDE A CADEIA COMEÇA

### 7.1 Âncora pela figura

Fixado *b*g, o intercepto que minimiza a soma dos quadrados dos resíduos em relação à Figura 3 é

$$ a_g^{\,f} = \frac{1}{n_g}\sum_{i}\big(s_i^{\,f} - b_g L_i\big) \tag{13} $$

isto é, a cadeia de léguas é deslizada ao longo do rio até ficar, em média, sobre os pontos da
figura. É a âncora padrão: a Figura 3 é a única fonte de **posição absoluta** do método.

### 7.2 Âncora textual

O relato frequentemente diz que a última fazenda de um riacho "está na barra" (na confluência)
ou que a primeira está "na cabeceira". Quando isso ocorre, a cadeia pode ser presa à ponta
correspondente do tronco. Com σg = +1, as âncoras candidatas são

$$ a_g^{\,\text{barra}} = \ell_g - b_g\,L_{\text{última}}, \qquad a_g^{\,\text{cab}} = 0 - b_g\,L_{\text{primeira}} \tag{14} $$

(com as pontas trocadas quando σg = −1). A âncora da barra só é aceita se duas condições forem
satisfeitas simultaneamente:

$$ K\,\big|a_g^{\,\text{barra}} - a_g^{\,f}\big| \le D_g \quad\text{e}\quad \exists\ \text{curso de outro nome a} \le 2\ \text{km da ponta de jusante} \tag{15} $$

A primeira condição impede que a âncora textual brigue com a figura mais que o deslocamento
máximo aceito para o grupo: o texto pode corrigir a figura, mas não a ignorar. A segunda
distingue uma confluência verdadeira do mero ponto em que a carta deixa de nomear o rio — sem
ela, "na barra" poderia prender a fazenda no meio de um curso cujo nome simplesmente acaba. A
âncora da cabeceira exige só a primeira condição.

A âncora textual foi aceita em nove grupos: sete pela barra (Itaim, Guaribas, Tranqueira,
Iningá, São Nicolau, Piauí, Gurguéia) e dois pela cabeceira (Canindé e Maratoã). Nos outros
seis prevaleceu a figura.

### 7.3 Encaixe no tronco

As posições finais são

$$ \hat{s}_i = a_g + b_g\,L_i \tag{16} $$

transladadas, se necessário, para caber em [0, ℓg] e, em último caso, truncadas nos extremos.

---

## 8 DE VOLTA AO TRAÇADO REAL

A posição *ŝᵢ* está sobre o tronco generalizado Γ̃g, que é a régua, mas não é a linha desenhada
no mapa. O ponto final é o ponto do traçado completo mais próximo da posição interpolada:

$$ (\lambda_i, \varphi_i) = \arg\min_{q \in \Gamma_g} \big\| q - \tilde{\Gamma}_g(\hat{s}_i) \big\| \tag{17} $$

A separação entre "onde se mede" e "onde se assenta" é o que permite usar a régua estável da
seção 5 sem que o ponto caia fora do rio que o leitor vê. A diferença entre as duas posições é,
por construção, no máximo da ordem de ε — cerca de 445 m, ou 1,5 px na escala da carta.

O deslocamento de cada fazenda em relação à Figura 3 é registrado no CSV com correção do
paralelo:

$$ d_i = K \sqrt{\big[(\lambda_i - \lambda_i^f)\cos\varphi_i\big]^2 + (\varphi_i - \varphi_i^f)^2} \tag{18} $$

Mediana de 10,9 km, média de 14,7 km e máximo de 74,9 km nas 125 fazendas. Esses valores são
bem maiores que os 4,6 km da versão anterior do mapa, e é isso que se esperava: agora é o
relato, e não a figura, que decide o espaçamento.

---

## 9 GRUPOS SEM LÉGUAS UTILIZÁVEIS

Os grupos que não podem ser espaçados por léguas seguem métodos subsidiários, registrados na
coluna `metodo` de cada fazenda:

a) **`rio_nomeado`** (5 fazendas) — há tronco nomeado, mas não léguas suficientes. As posições
   *sᵢᶠ* são projetadas no tronco e forçadas a respeitar a ordem do relato por regressão
   isotônica (*pool adjacent violators*; BARLOW et al., 1972); posições empatadas são então
   afastadas por um espaçamento mínimo. Grupos de uma só fazenda não podem encostar nos 8%
   finais de cada ponta do tronco, onde vários cursos costumam se tocar.

b) **`drenagem_próxima`** (22 fazendas) — sem homônimo na carta, o ponto da figura é levado ao
   curso d'água mais próximo num raio de 6 km, com preferência por riachos sobre os rios
   grandes de outra bacia.

c) **`afluente`** (2 fazendas) — as digressões da seção 4.3, que ficam na posição da figura,
   encaixadas na drenagem mais próxima.

Nesses 29 pontos não há conversão de léguas em quilômetros, e é neles que a precisão do mapa é
menor.

---

## 10 AFERIÇÃO EXTERNA

O relato dá três distâncias que **não** ligam uma fazenda à seguinte e, por isso, não entraram
em nenhuma das equações acima. Elas servem para julgar o mapa de fora (`work/afere_ancoras.py`).

**Tabela 2 — Distâncias do relato não usadas na construção, medidas sobre o mapa**

| Âncora | Texto | Mapa | km por légua | vs. 6,2 km |
|---|---:|---:|---:|---:|
| Tabuleiro-Alto (#90) → Matriz da Vitória (Oeiras), "pelo riacho do Piauí abaixo" | 60 léguas | 333 km de rio + 48 km por terra | 6,4 | +2% |
| fazendas dos Alongazes (tab. 21–23) → serra da Ibiapaba | 20 léguas | 86 a 187 km (mediana 158) | 7,9 | faixa contém os 124 km do texto |
| Tabuleiro-Alto (#90) → rio São Francisco | 40 léguas | 93 km | 2,3 | não fecha |

Fonte: elaboração própria a partir de `work/afere_ancoras.py`.

A primeira aferição é a mais forte, porque reproduz o percurso que o texto descreve — rio abaixo
e depois por terra até a igreja — e chega a 6,4 km por légua, a 3% da légua de 18 ao grau (e a
cerca de 4% abaixo da légua de sesmaria de 6,6 km). Ela confirma, de forma independente, que a
escala ao longo do rio Piauí (7,66 km de rio por légua) está calibrada. A terceira não fecha, e
a explicação mais provável está na medida, não no mapa: o texto nomeia como destino a fazenda
do Sobrado, "10 léguas acima do Santo Sé", ao passo que o script mede até o ponto do São
Francisco mais próximo em linha reta.

---

## 11 PARÂMETROS CONSOLIDADOS

| Parâmetro | Valor adotado |
|---|---|
| Conversão grau → km (`KM`) | 111,32 km/grau, sem correção de cos φ nos comprimentos ao longo do rio |
| Légua de referência em linha reta | ~6,2 km |
| Passos de légua lidos | 94, de 1 a 20 léguas |
| Digressões excluídas da cadeia | #91 (10 léguas de #90) e #93 (3 léguas de #92) |
| Tolerância de costura dos trechos | 0,03° |
| Tolerância de generalização do tronco (`TOL_TRONCO`, ε) | 0,004° ≈ 445 m (Douglas–Peucker) |
| Raio de busca do tronco (*R*g) | 25 a 85 km, por grupo |
| Deslocamento máximo aceito (*D*g) | 20 a 80 km, por grupo |
| Estimador da inclinação por grupo | mínimos quadrados ordinários |
| Critério de entrada na amostra global | *n*g ≥ 4, amplitude ≥ 5 léguas, 4 ≤ *K*·*b̂*g ≤ 18 km/légua (`B_LO`, `B_HI`) |
| Escala global *b*\* | 8,15 km de rio por légua (mediana de 10 grupos) |
| Banda por grupo (`BANDA`) | 0,6 a 1,8 × *b*\* = 4,89 a 14,67 km/légua |
| Teste de confluência para âncora "na barra" | outro curso a ≤ 2 km da ponta |
| Raio do encaixe genérico (`CAP_GENERICO`) | 6 km |
| Afastamento de pontos coincidentes | 0,0063° ≈ 700 m |
| Fazendas espaçadas por léguas | 96 de 125, em 15 grupos |

---

## 12 LIMITAÇÕES

**Comprimentos em graus planos.** Os comprimentos ao longo do rio são medidos no plano (λ, φ) e
multiplicados por 111,32 km, sem o fator cos φ na componente leste–oeste. Entre 2,7° e 11° S,
isso superestima trechos leste–oeste de 0,1% a 1,9%, e não afeta trechos norte–sul. O efeito é
pequeno diante das demais incertezas, mas é sistemático e poderia ser eliminado medindo os
troncos numa projeção equivalente ou geodesicamente.

**Valor da légua.** O valor de referência de ~6,2 km corresponde à légua de 18 ao grau; a légua
de sesmaria, de 3.000 braças, vale ~6,6 km. A escolha não altera nenhuma posição — a escala do
mapa é estimada dos próprios dados, eq. (9) —, mas altera a leitura das aferições e do índice de
sinuosidade (1,31 com 6,2 km; 1,23 com 6,6 km).

**Linearidade dentro do grupo.** O modelo (7) supõe a mesma escala ao longo de todo o rio. Rios
que mudam de padrão — encaixados nas cabeceiras e meandrantes no baixo curso — violam essa
hipótese, e o erro se acumula para o meio da cadeia.

**Dependência residual da Figura 3.** A figura ainda decide a âncora em seis grupos, o sentido
da cadeia em todos e a própria seleção do tronco (raio *R*g). Nos grupos em que a âncora vem da
figura, um erro de posição dela se transfere integralmente à cadeia. O próprio
georreferenciamento tem um viés: deslizando a figura em grade, a distância mediana dos rios da
BC250 às linhas da figura cai de 5,7 para 3,2 km com um deslocamento de ~5 km para leste —
menos que o RMS do ajuste do contorno (5,0 km), mas sistemático.

**Grupos pequenos.** Com duas ou três fazendas, o ajuste (8) tem um ou dois graus de liberdade, e
a escala adotada é, em boa medida, a da banda. A Tabela 1 mostra que três grupos ficam no teto e
dois no piso; para eles, a escala é mais uma restrição do que uma estimativa.

**Sensibilidade de *b*\* à composição da amostra.** Com dez grupos, a mediana é a média dos
dois centrais (7,69 e 8,61), e a entrada ou saída de um único grupo a desloca de meio intervalo.
Foi o que ocorreu quando a Figura 3 passou a ser lida do JPEG embutido no PDF sem
recodificação: o georreferenciamento mudou menos de 1 km (mediana), mas o rio Maratoã passou a
ter quatro fazendas e nove léguas no ajuste, entrou na amostra e levou *b*\* de 7,73 (mediana de
nove) para 8,15. As posições finais mudaram 0,26 km na mediana; só três fazendas andaram mais de 10 km,
todas do Maratoã, agora ancorado na cabeceira (#79 Ginipapo, 31 km).

**Generalização como parâmetro não neutro.** ε = 0,004° foi calibrado para devolver a régua da
BCIM. Outro valor mudaria *b*\* e, portanto, todas as posições. A escolha é justificada (seção
5.2), mas não é a única defensável.

**Leitura do OCR.** Um passo mal lido (por exemplo, "8" lido como "3") desloca todas as fazendas
seguintes do grupo. As travas de numeração detectam entradas perdidas, mas não valores trocados.

**Fazendas sem conversão.** 29 das 125 fazendas não passam pela conversão de léguas em
quilômetros (seção 9), e oito dos topônimos de 1697 não existem mais em nenhuma fonte
cartográfica do IBGE. Para esses pontos, o caminho é documental (sesmarias, inventários,
cartografia setecentista), não cartográfico.

---

## REFERÊNCIAS

BAPTISTA, [prenome]. *(referência a ser completada: obra de 1986 que contém a Figura 3,
p. 36, reproduzida em* Os Jesuítas no Piauí*)*.

BARLOW, R. E.; BARTHOLOMEW, D. J.; BREMNER, J. M.; BRUNK, H. D. **Statistical inference under
order restrictions**: the theory and application of isotonic regression. London: Wiley, 1972.

CARVALHO, Miguel de. Descrição do sertão do Piauí [1697]. *(edição utilizada a ser completada
conforme a fonte primária)*.

DOUGLAS, David H.; PEUCKER, Thomas K. Algorithms for the reduction of the number of points
required to represent a digitized line or its caricature. **The Canadian Cartographer**,
Toronto, v. 10, n. 2, p. 112-122, 1973.

INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA. **Base Cartográfica Contínua do Brasil ao
Milionésimo – BCIM**: versão 2016. Rio de Janeiro: IBGE, 2016.

INSTITUTO BRASILEIRO DE GEOGRAFIA E ESTATÍSTICA. **Base Cartográfica Contínua do Brasil, escala
1:250.000 – BC250**: versão 2025. Rio de Janeiro: IBGE, 2025.

LEOPOLD, Luna B.; WOLMAN, M. Gordon; MILLER, John P. **Fluvial processes in geomorphology**.
San Francisco: W. H. Freeman, 1964.

MANDELBROT, Benoit. How long is the coast of Britain? Statistical self-similarity and
fractional dimension. **Science**, Washington, v. 156, n. 3775, p. 636-638, 1967.

SEN, Pranab Kumar. Estimates of the regression coefficient based on Kendall's tau. **Journal
of the American Statistical Association**, v. 63, n. 324, p. 1379-1389, 1968.
