---
name: reels-de-obra
description: Fábrica de reels de obra — transforma álbuns de mídia bruta de obras e serviços (fotos, vídeos de celular, drone) em reels 9:16 montados sobre a narração gravada pelo dono, com legenda karaokê, criativos de campanha para Meta Ads e vídeos horizontais de YouTube, tudo com ffmpeg via script. Use quando o pedido envolver "reels do álbum", "aproveitar as mídias da obra", "antes e depois", "criativo de anúncio", "vídeo pro YouTube a partir do álbum", edição em lote com ffmpeg, transcrição de narração ou legenda queimada. Quando a base é uma gravação falando para a câmera, use reel-com-broll-por-fala.
---

# Fábrica de reels de obra

Método validado em produção (ago/2026): 22 álbuns de obras → 38 reels narrados + 4 criativos de campanha +
peça de antes/depois, com ffmpeg via script, sem editor manual. Feito originalmente para uma empresa de
paisagismo; vale para qualquer serviço que gera foto e vídeo de obra (reforma, marcenaria, pintura, energia solar).

## As duas gerações do produto

Houve uma virada de conceito no meio da produção. Saber disso evita refazer o caminho errado:

**v2 (superado):** reel de tempo fixo, ~20 s, cenas de 3,4 s, mudo, sem texto, com um `-ROTEIRO.md` ao lado para o dono narrar depois.

**v3 (atual):** o dono grava a narração ANTES, e o vídeo é montado **em cima da fala**. A duração do reel é a
duração do áudio (tipicamente 35–58 s), o corte de cena cai na pausa entre frases, e a legenda karaokê é
queimada por cima. Encaixar fala em vídeo de tempo fixo soa solto — o vídeo é que segue a voz.

## Regras de ouro (feedback direto do dono)

1. **O vídeo segue a fala, não o contrário.** Número de cenas = duração do áudio ÷ ~6,5 s (anúncio: ÷ 4,8 s). Teto de 9 s por cena no orgânico, 6,5 s no anúncio.
2. **A última cena é sempre o fecho.** Distribuir as cenas ao longo de TODA a peça (`round(i*(N-1)/(n-1))`), nunca em sequência a partir do início: com fala curta o rodízio sequencial para nos primeiros clipes e o resultado nunca entra.
3. **O fecho precisa de respiro.** ~2,6 s do resultado na tela depois que a fala acaba, antes do card.
4. **Abre com a obra PRONTA e RECENTE.** Conferir a **data de filmagem** (ver armadilha de datas). Abrir com obra pela metade foi reprovado duas vezes.
5. **Áudio original do bruto sai fora.** Os brutos têm "Valendo!", conversa de bastidor e direção. Entra só a narração gravada.
6. **Legenda karaokê em tudo que é narrado.** Nos anúncios ela **substitui** a legenda estática; as duas juntas brigam pelo mesmo terço da tela.
7. **Uma peça, uma obra**, salvo quando o plano necessário não existe no álbum.
8. **Nada de escurecer imagem pra caber texto.** O fechamento é card sólido na cor da marca com o logo oficial.
9. **CTA único**, com ângulo no **custo de errar**, não no preço de contratar. Nunca declarar faixa de preço na peça.
10. **Sem rosto de terceiros** sem autorização. Equipe uniformizada pode. Pasta de cliente que não autorizou vai para `pastas_vetadas` no `config.json`.
11. Tom: de sócio explicando para um cliente. Sem exclamação, sem euforia de propaganda.

## Fluxo v3

1. **Inventariar** o álbum: nº de itens, tipo, orientação, **data real de filmagem**, se tem drone.
2. **Curar por folha de contato** — escolher plano por intenção narrativa, nunca por ordem de arquivo.
3. **Escrever a receita**: segmentos `{clip, ss, dur, fx}` + roteiro de narração (`referencias/roteiro-narracao.md`).
4. **Kit de gravação**: página de teleprompter que o dono abre no celular (alternativas fechadas atrás de `<details>`).
5. **Gravar** a narração (`referencias/narracao-e-legenda.md`).
6. **Transcrever** (faster-whisper, pt, `word_timestamps=True`).
7. **CORRIGIR a transcrição** — obrigatório antes de queimar legenda.
8. **Conferir as frases finais** de todas as peças, uma a uma (o CTA é onde o Whisper mais erra).
9. **Montar**: plano de cenas pela fala, render, card, karaokê e mixagem numa passada (`referencias/pipeline-tecnico.md`).
10. **QC** por folha de contato e **gate do reel** (`tools/reel/gate_reel.py`) antes de agendar.

## Duração e ritmo

| | Cena alvo | Teto | Duração final |
|---|---|---|---|
| Reel orgânico narrado | 6,5 s | 9,0 s | 35–58 s (= o áudio) |
| Criativo de anúncio | 4,8 s | 6,5 s | 30–50 s |

Transição xfade de 0,35 s, variando o tipo. Talking head aguenta ~10 s por corte; B-roll aguenta menos, daí 6,5 s.

## Armadilhas que custaram retrabalho

**Data de filmagem, não data do arquivo.** Na pasta de download todos os arquivos têm a data do download. A real
está no `creation_time` do container (vídeo) ou no EXIF `DateTimeOriginal` (foto — o ffprobe não expõe, precisa
ler os bytes). Escolher clipe sem conferir isso colocou obra de janeiro representando resultado de maio.

**O Whisper erra o CTA sistematicamente.** "Peça um" vira "Péssimo" — apareceu como "péssimo orçamento". Também
inverteu sentido: "sem depender de veneno" virou "sem independência de veneno". Legenda queimada com erro é
inaceitável em anúncio. Tabela de correções conhecidas + **sempre listar as frases finais** antes de queimar.

**Teleprompter com alternativas à vista faz o narrador lê-las todas.** Em 4 de 42 gravações as três aberturas
foram lidas em sequência. Manter alternativas fechadas atrás de `<details>`.

**PyAV quebra com acento no caminho** (Windows), e nome vindo do iPhone usa acento decomposto (NFD). Localizar
por `unicodedata.normalize` e trabalhar sobre cópia em caminho ASCII.

**Fonte 4K horizontal não precisa de fundo desfocado.** Recortada em 9:16 ainda dá 1215×2160. Só embaçar quando a altura for < 1800.

Demais armadilhas (OneDrive, disco, ZIP64, PowerShell, drawtext) em `referencias/pipeline-tecnico.md`.

## Arquivos de referência

- `referencias/pipeline-tecnico.md` — comandos, filtros e armadilhas de infraestrutura.
- `referencias/identidade-visual.md` — o que levantar da marca antes de montar (modelo para preencher).
- `referencias/roteiro-narracao.md` — modelo do roteiro e como escrever para serviço de ticket alto.
- `referencias/narracao-e-legenda.md` — transcrição, correção, karaokê ASS e captação de áudio.
- `referencias/canal-instagram.md` — como ler o próprio canal antes de decidir formato.

## O que NÃO tentar

- **Sincronia labial** gerada: resultado ruim em vertical.
- Baixar fontes da marca sem licença — usar Arial Black (gancho/karaokê) e Arial Bold (card) até ter os arquivos.
- Gerar logo por IA — usar sempre o PNG oficial.
- **yt-dlp para Instagram**: suporte quebrado.
