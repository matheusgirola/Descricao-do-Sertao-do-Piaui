# CLAUDE.md

Contexto para trabalhar neste projeto: mapa interativo das fazendas de gado do Piauí no final
do século XVII, com georreferenciamento em três versões cartográficas (atual, carta de 1828 e
carta de 1850).

## O que é o projeto

Extração, georreferenciamento e visualização interativa dos **125 pontos** da "Figura 3 —
Fazendas de gado do Piauí no final do século XVII conforme padre Miguel de Carvalho" (Baptista,
1986, p. 36, adaptado), publicada no PDF *"Os jesuítas no Piauí"* (p. 29–34). As Tabelas 1 a 29
do mesmo PDF dão os nomes das 125 fazendas, agrupadas por corpo d'água (rio/riacho).

O resultado são **três versões do mesmo site**, todas com os mesmos 125 pontos e o mesmo texto
de 1697, cada uma plotando os pontos sobre uma base cartográfica diferente:

1. **Base atual (Leaflet)** — `descricao_interativa_atual.html`. Usa diretamente o lat/lon do
   georreferenciamento (§ abaixo), sem transformação adicional.
2. **Carta de 1828** — `descricao_interativa_1828_completo.html` (autocontida, imagem em
   base64, ~3,2 MB) e `descricao_interativa_1828.html` (leve, espera `mapa_piauhy_1828.jpg` ao
   lado).
3. **Carta de 1850** — `descricao_interativa_completo.html` / `descricao_interativa.html`,
   mesmo esquema.

## Pipeline de dados (ordem em que tudo foi construído)

1. **Leitura da Figura 3.** Imagem raster embutida no PDF, só 609×916 px — números com ~6 px de
   altura, OCR não funciona. Números foram lidos visualmente em recortes ampliados. Os 125
   pontos laranja foram detectados por segmentação de cor (exatamente 125 componentes) e
   associados aos números. Validação: conjunto contém 1–125, cada um exatamente uma vez.

2. **Georreferenciamento em lat/lon** (a camada que sustenta tudo). Silhueta do estado extraída
   da imagem e ajustada por ICP contra a malha oficial do Piauí (IBGE, API v3 malhas, UF 22), em
   Web Mercator. RMSE ≈ 5,5 px ≈ 5,5 km. Conferido contra Teresina (foz do Poti), Amarante (foz
   do Canindé), Floriano, Picos, Oeiras, Paulistana, Uruçuí, Bom Jesus, Corrente e Parnaíba — e
   os 125 pontos caem dentro do polígono do estado. **A versão Leaflet usa esta camada
   diretamente.**

3. **Grade da carta de 1828**, medida por detecção de linhas:
   - latitude: `y = 164 + 404 · (|lat| − 2)`, de 2°S a 11°S (erro < 0,15° contra vilas medidas).
   - longitude: `x ≈ 566,5 + 410,36 · k`, k = 0 em 49°O e k = 6 em 43°O **a oeste de Paris**
     (Greenwich = k − 46,6628). A grade é regular mas o *conteúdo* da carta não a obedece
     (Oeiras 0,51° a oeste do lugar real, Jerumenha 0,60°, Parnaíba 0,31° a leste).

4. **Posicionamento dos 125 pontos nas cartas antigas** (`place28.py` para 1828, `place.py` para
   1850):
   1. Transformada global (TPS) ajustada só com vilas medidas na própria carta (6 na de 1828,
      10 na de 1850).
   2. Correção por grupo (rio/riacho): fazendas reencontradas *nominalmente* na carta ancoram o
      grupo por similaridade (translação + rotação + escala limitada), preservando a geometria
      interna da Figura 3. 15 âncoras em 1828, 16 em 1850 — dicionário `ANCORAS` no código.
   3. Grupos sem âncora recebem deslocamento interpolado por IDW dos vizinhos.

   Resultado em 1828: 15 pontos exatos sobre o topônimo, 67 em grupos ancorados, 43
   interpolados (coluna `origem_xy1828` do CSV).

## Correções apuradas durante o trabalho (não reabrir sem motivo novo)

- Legendas das Tabelas 18–20 do PDF estão deslocadas. Pelo texto de 1697: riacho São Vicente =
  71–74; riacho das Berlengas = 75–77; riacho Santo Antônio = 78 (resolve o nº 78, órfão de
  tabela — é a fazenda **Santo Antônio**).
- O "rio Itaim Açu" da Figura 3 é o **rio Poti** (nº 48 = fazenda "Poti"; nº 51 "São Cosme" cai
  na foz do Poti; o "R.o dos Caes" da carta de 1828, afluente do Poti, confirma que riacho do
  Cais (52–53), Cabeça do Tapuio (54–56), Canabrava (57–58) e o 78 pertencem a essa bacia).
- Riachinho do Buriti (nº 88) fica na cabeceira do Canindé, a sudeste, junto do nº 1.
- Riacho Vitória (nº 63) **não** é Oeiras — a Figura 3 o coloca ao norte, perto de São Vitor.

## Ressalvas conhecidas

- Nº 55 / 56 (riacho Cabeça do Tapuio): rótulos ilegíveis na resolução original; "Olho D'água" e
  "Sítio da Cruz" podem estar trocados entre si (~17 km de diferença).
- Nas cartas antigas, os pontos interpolados (IDW) são os mais frágeis. Qualquer topônimo novo
  identificado deve ser acrescentado ao dicionário `ANCORAS` — melhora o grupo inteiro.
- Na versão Leaflet esse problema não existe: os pontos são o lat/lon do georreferenciamento
  direto, com precisão uniforme de 5 a 10 km.

## Arquivos

| Arquivo | Descrição |
|---|---|
| `descricao_interativa_atual.html` | Site base, Leaflet 1.9.4 embutido (sem CDN, só tiles pedem internet). Basemaps: CARTO Positron (padrão), Esri World Topo, Esri World Imagery. Contorno do Piauí (IBGE) por cima. |
| `descricao_interativa_1828_completo.html` | Autocontida, carta de 1828 em base64 (~3,2 MB) |
| `descricao_interativa_1828.html` | Leve, espera `mapa_piauhy_1828.jpg` ao lado |
| `descricao_interativa_completo.html` / `descricao_interativa.html` | Idem para a carta de 1850 |
| `fazendas_miguel_de_carvalho.csv` | `numero, fazenda, corpo_dagua, tabela, lat, lon, x_1828, y_1828, origem_xy1828, x_1850, y_1850, x_fig3, y_fig3, obs` |
| `place28.py` / `place.py` | Scripts de posicionamento nas cartas de 1828 / 1850 (TPS + âncoras + IDW) |

## Notas de implementação

- Cada seção com fazendas ganhou `data-grp`; os pontos vivem num bloco
  `<script id="fazendas-json">`. A câmera de cada seção vem da caixa envolvente dos seus pontos
  (não de `data-x`/`data-y` fixo). Seções sem pontos mantêm o mapa colado às bordas; seções com
  pontos priorizam o enquadramento e aceitam mostrar uma nesga de fundo (sem isso, pontos das
  bordas saíam da tela).
- Versão Leaflet: `flyToBounds` com `paddingTopLeft`/`paddingBottomRight` calculados a partir da
  largura do painel, para a constelação ficar centrada na área livre. Roda de rolagem NÃO dá
  zoom (a página precisa rolar); arrastar, duplo clique e botões +/− funcionam. Marcadores são
  `divIcon` 16×16 com âncora no centro. Linha tracejada liga as fazendas na ordem do relato. As
  125 aparecem sempre em cinza claro ao fundo; a seção ativa acende as suas. Hover no parágrafo
  acende o pino e vice-versa. Controles do Leaflet trocam de lado junto com o painel.
- Testado em Chromium a 1440×900, 1024×768 e 390×844: 0 erros de JS, 125/125 pontos enquadrados
  em todas as seções, nas três versões.

## Ao editar

- Qualquer mudança nos 125 pontos (posição, nome, agrupamento) deve manter a validação 1–125
  sem repetição nem lacuna.
- Mudanças no georreferenciamento em lat/lon (§2) propagam para as três versões — é a camada
  raiz. Mudanças nas âncoras `ANCORAS` de 1828/1850 afetam só a carta correspondente.
- Ao testar localmente em sandbox sem rede, os tiles do Leaflet não carregam (fundo aparece
  vazio) — isso é esperado e não indica erro de lógica.
