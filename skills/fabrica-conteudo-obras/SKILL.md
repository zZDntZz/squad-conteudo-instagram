---
name: fabrica-conteudo-obras
description: Fábrica de conteúdo em vídeo a partir de álbuns de obras (Google Fotos, OneDrive, pastas locais) — baixa, extrai, cura por folha de contato e monta reels verticais, criativos de campanha para Meta Ads e vídeos horizontais de YouTube com ffmpeg, cuidando de disco, arquivos online-only e QC. Use quando o pedido for processar álbuns de fotos e vídeos de obras em lote, "baixar o álbum", "fazer os reels de todos os clientes", "criativos da campanha", "cortes para YouTube", "16:9", "9:16". O método de montagem sobre a narração está em reels-de-obra; esta skill cobre o lote, a infraestrutura e os três produtos.
---

# Fábrica de conteúdo em vídeo (lote de obras)

Pipeline testado para virar mídia bruta de obra em conteúdo publicável. Leia na ordem do trabalho; as
armadilhas no fim já custaram horas.

## 0. Antes de qualquer coisa: espaço em disco

**Causa nº 1 de falha silenciosa.** Sem espaço, o OneDrive não materializa arquivos e o ffmpeg gera
segmentos vazios *sem erro claro*.

```powershell
Get-PSDrive C | Select-Object @{n='LivreGB';e={[math]::Round($_.Free/1GB,2)}}
```

- Exija **≥ 15 GB livres** antes de começar; aborte e avise se não houver.
- Cheque de novo a cada lote. Um álbum de 200 itens pesa 3–8 GB; vídeos longos passam de 7 GB sozinhos.
- Nunca apague arquivos do usuário. Só remova o que o próprio pipeline baixou/gerou, e diga o que removeu.

## 1. Onde está a mídia

Mapeie as origens uma vez e escreva num arquivo de projeto (não no código):

| Origem | Uso |
|---|---|
| Álbuns online por obra (Google Fotos etc.) | acervo principal |
| Pasta de mídia extra por obra (drone, câmera) | **muitas vezes melhor**; sempre olhe antes de montar |
| `_midia-bruta/<obra>/` | onde o pipeline extrai o que baixa |

Download de álbum do Google Fotos: página do álbum no Chrome → menu **⋮ → "Fazer o download de tudo"**.
**A janela precisa estar visível** — aba oculta/minimizada não processa o comando e o Google nem prepara o zip.

## 2. Extração

- Zips com arquivo > 4 GB são **ZIP64**: `Expand-Archive` do PowerShell 5.1 falha com "Cabeçalho de arquivo
  local corrompido". Use `tar -xf` (nativo do Windows).
- **Valide antes de apagar o zip**: conte arquivos extraídos e confirme que nenhum tem 0 byte.
- HEIC → JPG com ffmpeg (`-frames:v 1 -q:v 2`), em `_conv/`.

## 3. Curadoria (nunca monte às cegas)

- Folha de contato: 1 quadro por foto e 2 por vídeo (30% e 70% da duração), 200×356, `tile=NxM`.
- Escolha por conteúdo, não por nome de arquivo.
- **Orientação real**: `ffprobe -show_entries stream_side_data=rotation`. `1920x1080` com `rot=-90` é vertical;
  com `rot=0` é **horizontal de verdade** — descarte ou trate com fundo desfocado.
- Descarte planos técnicos feios fora de contexto, fotos borradas e rosto de terceiro/criança sem autorização.
- Obra de cliente que não autorizou: pasta em `config.json → pastas_vetadas`; o gate do reel reprova.

## 4. Montagem (motor ffmpeg)

- **Cenas de 3,0–3,6 s** em peça muda; peça narrada segue a fala (ver `reels-de-obra`).
- **Transições** `xfade` de 0,35–0,4 s alternando `fade`, `smoothleft`, `wipeleft`, `dissolve`.
- **Push-in sutil**: `zoompan z='min(zoom+0.0004,1.06)'` em vídeo; Ken Burns em foto.
- **Exposição adaptativa**: meça `signalstats YAVG` de cada trecho (**inclusive fotos**) e corrija — >170 puxa para baixo, <95 levanta.
- **Look vivo**: `eq=contrast≈1.12:saturation≈1.26` + `vibrance=0.18` + leve calor via `colorbalance` + `unsharp`.
  Lavado é reprovado; escurecer o fim para "dar contraste" também.
- **Fechamento**: card sólido na cor da marca com o **logo oficial** — nunca escurecer a imagem da obra.

## 5. Três produtos, três regras de texto

- **Reels de conteúdo**: narrados (ver `reels-de-obra`) ou mudos com um `<slug>-ROTEIRO.md` ao lado
  (3 ganchos, fala em blocos com timecode, CTA, legenda pronta, instruções de gravação).
- **Criativos de campanha** (Meta Ads): **legenda embutida obrigatória**, 9:16, 25–35 s, estrutura
  *E / Mas / Por isso*, resultado no primeiro quadro. Nome do arquivo = nome da campanha.
- **YouTube**: 16:9 1920×1080, cartela de título por obra e fechamento de marca; vertical entra com fundo
  desfocado, nunca tarja preta.

Casting já validado: **uma peça, uma obra** e a obra **pronta** na abertura.

## 6. Áudio e rosto

- Sem lip-sync gerado. Se o dono quiser aparecer falando, ele grava e a gente encaixa.
- Áudio bruto de obra tem "Valendo", "de novo", palavrão e conversa de bastidor. Transcreva antes de aproveitar
  qualquer fala — e prefira remover o áudio.

## 7. Armadilhas técnicas (todas já aconteceram)

| Sintoma | Causa / solução |
|---|---|
| Segmento sai com 0 byte, sem erro | Arquivo **online-only** no OneDrive. Detecte com `st_file_attributes` (bits 0x400000, 0x100000, 0x1000) — **nunca** com `getsize()==0`, que retorna o tamanho lógico. Materialize lendo os bytes |
| `Error opening input: Invalid argument` | Mesmo caso acima, ou disco cheio |
| `Could not open encoder before EOF` | Erro de expressão no filtro. Em `drawtext` a altura é `h`; `ih` só existe em `drawbox` |
| `Option not found` no drawtext | Interpolação PowerShell comeu o nome da variável: use `${var}:enable` |
| Acentos viram mojibake | PS 5.1 lê `.ps1` UTF-8 sem BOM como ANSI. Escreva os textos em `.txt` e use `drawtext=textfile=` |
| `ffprobe` retorna duração e o parse quebra | Locale pt-BR devolve vírgula: `float(x.replace(",", "."))` |
| Zoompan roda infinito | Em foto, fixe `-frames:v` = duração × fps |
| Processo morre junto com o comando | Render longo: `Start-Process cmd /c script.cmd -WindowStyle Hidden` e logue em arquivo |
| "moov atom not found" | Arquivo cortado no meio. Rode desacoplado e valide antes de publicar |

## 8. QC obrigatório antes de entregar

1. Quadros a cada ~2 s numa folha de contato (`format=yuvj420p` para o mjpeg).
2. QC automático de `YAVG`/`SATAVG`: cena escura (<55), estourada (>205), sem cor (<12).
3. Olhe a folha: quadro borrado, obra pela metade, rosto indevido, vídeo horizontal deitado.
4. Duração e card final inteiro. Reel que vai para o Instagram passa no `tools/reel/gate_reel.py`.

## 9. Organização

Mantenha um `_producao.md` com o índice do que existe e registre a curadoria em texto antes de apagar
qualquer cópia — foi assim que uma seleção inteira sobreviveu a uma limpeza de disco.
