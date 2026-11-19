---
name: reel-com-broll-por-fala
description: Monta um reel 9:16 sobre a gravação original de alguém falando para a câmera, trocando a imagem a cada frase pelo B-roll do processo que está sendo dito (mídia própria primeiro, banco licenciado depois), com Ken Burns em foto, legenda karaokê, card final, arquivo de fontes, compressão para upload e gate do reel. Use quando o pedido for "monta o reel com B-roll", "cobre a fala com imagens da obra", "cada coisa que eu falo tem que aparecer", "o reel ficou com imagem parada", "o vídeo continua depois que eu paro de falar", ou refazer um reel reprovado no gate.
---

# Reel com B-roll por fala

A base é **a gravação original** (fala e câmera em sincronia). O vídeo dura o que a fala dura. Cada frase que
descreve um processo ganha a imagem daquele processo; o resto volta para a câmera.

Ferramentas (em `<repo>/tools/reel/`, `<repo>` = onde o repositório foi clonado):

| Arquivo | O quê |
|---|---|
| `monta_reel.py` | transcreve, renderiza cena a cena, grafismos (legenda + card), final, versão de upload, folha de contato, fontes |
| `gate_reel.py` | o gate: decide se o reel pode ser agendado (R1–R11) |
| `gate_reel_autoteste.py` | prova que cada regra do gate reprova |
| `comprimir_upload.py` | x264 2 passes + `+faststart`, abaixo do limite do upload pelo navegador |

Exemplos nesta pasta: `exemplos/projeto-reel.exemplo.json` e `exemplos/cenas.exemplo.json`.

## Regras (cada uma nasceu de um defeito real, 18/11/2026)

1. **Base é a gravação original.** Não remonte a fala em cima de outro vídeo; a câmera volta no mesmo instante
   da fala (`tipo: "cam"`, sincronia labial preservada).
2. **B-roll por frase.** Leia a transcrição frase a frase e marque o que é processo: "descompacta" → enxada
   abrindo o solo; "cobre o solo" → palhada. Imagem genérica de "jardim bonito" em cima de um processo é defeito.
3. **Nenhuma imagem parada por mais de 1 s.** Foto entra com Ken Burns alternando entrada/saída; vídeo com
   push-in leve. O gate R5 (`freezedetect`) reprova.
4. **O vídeo termina até 0,7 s depois da última palavra.** O primeiro reel ia 9,5 s além da fala, com a boca
   mexendo sem som. Marque `fim` em `cenas.json` pela última palavra da transcrição. Gate R3.
5. **Mídia própria primeiro.** Acervo da marca (obras, bastidores) antes de banco. Banco só licenciado:
   Pexels, Pixabay, Wikimedia Commons (CC0, CC BY, CC BY-SA). Toda cena de terceiro leva `origem` e `licenca`;
   mídia sua leva `"propria": true`. Gate R10.
6. **Arquivo de fontes sempre.** `monta_reel.py ... fontes` escreve `<nome>-fontes.md` (cena, fala, arquivo,
   origem, licença). Sem ele o gate reprova.
7. **Pastas vetadas por config.** Obra de cliente que não autorizou entra em `config.json → pastas_vetadas`.
   O montador recusa e o gate R10 reprova.
8. **Nome da marca escrito certo.** O Whisper escreve o nome como ouviu; as escritas erradas ficam em
   `config.json → marca.escritas_erradas` e em `marca.json → correcoes`. A legenda é corrigida e o gate R11 confere.
9. **Upload pelo navegador aceita ~10,4 MB.** Gere a versão `-insta.mp4` com `comprimir_upload.py`
   (o `monta_reel.py ... insta` já chama) e passe-a no gate com `--insta`.
10. **Gate antes de agendar.** Reprovou, corrige o vídeo, nunca a regra sem motivo.

## Fluxo

```powershell
cd "<repo>\tools\reel"
python -I monta_reel.py projeto-reel.json transcrever     # palavras com tempo → transcricao.json
#  leia a transcrição; corrija palavras erradas no JSON; marque o fim (última palavra)
#  escreva cenas.json: uma cena por frase (ini = início da 1ª palavra da frase)
python -I monta_reel.py projeto-reel.json tudo            # cenas → grafismos → final → insta → folha → fontes
python -I gate_reel.py saida\<nome>.mp4 --insta saida\<nome>-insta.mp4 --cenas cenas.json `
       --fontes saida\<nome>-fontes.md --legenda saida\_trabalho\grafismos\trabalho\plano_render.json
```

Olhe a folha de contato (`<nome>-folha.jpg`) antes de dar como pronto: exit 0 não é prova. Procure imagem sem
relação com a frase, rosto de terceiro, obra de pasta vetada, horizontal deitado.

Refazer só algumas cenas: `python -I monta_reel.py projeto-reel.json cenas 3 7` e depois `final insta folha fontes`.

## `cenas.json`

```json
{"fim": 33.5, "card_ini": 30.75,
 "cenas": [
  {"ini": 0.0,  "fala": "Você já comprou grama duas vezes pro mesmo lugar?", "tipo": "cam"},
  {"ini": 3.4,  "fala": "Plantou,", "tipo": "v", "path": "acervo/placas-de-grama.mp4", "ss": 0.0, "propria": true, "o_que": "placas sendo assentadas"},
  {"ini": 10.25,"fala": "tá no solo compactado", "tipo": "v", "path": "broll/solo-rachado.mp4", "ss": 11.0,
   "origem": "Pixabay, autor X, https://pixabay.com/videos/id-000000/", "licenca": "Pixabay Content License"},
  {"ini": 13.3, "fala": "sem matéria orgânica", "tipo": "f", "path": "acervo/terra-nua.jpg", "propria": true},
  {"ini": 30.75,"fala": "(card)", "tipo": "card"}
 ]}
```

- `tipo`: `cam` (gravação no mesmo instante), `v` (vídeo, `ss` = início no arquivo), `f` (foto, Ken Burns), `card`.
- Cada cena vai de `ini` até o `ini` da próxima; a última até `fim`.
- Cena curta demais (< 1 s) cansa; frase longa pode ter duas imagens.
- Acervo grande: um `catalogo.json` (`{"<id>": {"caminho": ..., "data": ...}}`) e cenas com `"id"` no lugar de `"path"`.

## Ritmo que funcionou

- Gancho na câmera nos primeiros ~3 s, com o texto do gancho grande no terço de cima.
- Troca de imagem a cada 1,0–2,5 s nos trechos de processo; volta para a câmera nas frases de opinião.
- Card final de ~2,7 s com logo, tagline e a chamada; a legenda karaokê para quando o card entra.
- Trilha licenciada baixa, com ducking pela voz (opcional).
