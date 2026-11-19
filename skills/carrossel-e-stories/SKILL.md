---
name: carrossel-e-stories
description: Gera carrossel 1080x1350 (slide a slide), carrossel panorâmico (uma cena contínua cortada em N slides) e stories 1080x1920 com foto de fundo, a partir de um JSON de texto e paleta, renderizando no Chrome headless. Use quando o pedido for "faz o carrossel", "carrossel panorâmico", "slides do post", "arte dos stories", "story com a foto da obra", ou quando um slide sair com texto cortado ou fundo em branco.
---

# Carrossel e stories

Geradores em `<repo>/tools/` (`<repo>` = onde o repositório foi clonado). Rode `npm install` na raiz uma vez
(instala só o `playwright-core`; o navegador é o Chrome/Edge da máquina, ou `CHROME_PATH`).

| Peça | Comando | Exemplo de config |
|---|---|---|
| Carrossel 4:5 | `node tools/carrossel/gerar-carrossel.mjs carrossel.json` | `tools/carrossel/carrossel.exemplo.json` |
| Carrossel panorâmico | `node tools/carrossel-panoramico/gerar-panorama.mjs panorama.json` | `tools/carrossel-panoramico/panorama.exemplo.json` |
| Stories | `node tools/stories/gerar-stories.mjs stories.json` | `tools/stories/stories.exemplo.json` |

Texto, paleta, arroba e emblema vêm do JSON. O emblema é a logo da marca em PNG (o repositório traz só
`assets/logo-placeholder.png`).

## Antes de desenhar: trave o sistema

Escala tipográfica, espaçamento e paleta decididos antes do primeiro slide, com o porquê de cada número.
O que o panorama de exemplo usou:
- **Tipo: 40 · 54 · 70 · 88 px** (passos de ~1,3). 40 é o piso no feed; nada abaixo disso.
- **Espaço: 16 · 24 · 48 · 80.** 80 nas laterais e no topo de cada slide (o Instagram corta as bordas);
  16 entre título e corpo (são um grupo); blocos separados a mais de 48.
- **Contraste**: cor de marca clara sobre creme fica perto de 3:1 — vai só na ilustração. Para texto, um tom
  mais escuro que passe de 4,5:1.

## Carrossel panorâmico

- Uma imagem de `N × 1080` por 1350, cortada em N slides. Os elementos **atravessam as bordas** (raiz, água,
  caminho), e é isso que faz a pessoa arrastar.
- **Texto nunca cruza a borda**: o script mede cada bloco no navegador e **para com erro** se algum passar da
  margem do próprio slide.
- Fundo: módulo que desenha em SVG (`cenas/solo-vivo.mjs` é o exemplo: solo morto → solo vivo em 9 slides,
  determinístico), uma arte larga pronta (embutida em base64) ou gradiente para testar o texto.
- Contrato de uma cena nova: `export function desenhar({ W, H, SW, cores }) { return "<svg …>" }` e
  `export const slides = N`.

## Stories

- **Imagem de fundo embutida em base64.** Com `page.setContent()` a página não tem origem de arquivo e
  `url('file://…')` não carrega: o story sai com o fundo liso, sem erro nenhum (18/11).
- Texto no terço de baixo, terminando ~320 px acima do rodapé (campo de resposta do Instagram) e começando
  abaixo de 220 px (barra de progresso e nome do perfil). O script para com erro se o texto subir demais.
- Enquete, caixa de perguntas e link não dá para agendar pelo Business Suite: a chamada vai escrita
  ("Responda este story que eu te explico") e a automação de resposta a story do ManyChat responde.

## Depois de gerar

Olhe os PNGs (exit 0 não é prova): texto legível no celular, nada cortado, emblema certo, numeração `i/N`.
O "Comente X" do último slide tem que bater com a legenda e com a automação — o gate da legenda confere.
