# Pipeline técnico — ffmpeg, scripts e armadilhas

ffmpeg/ffprobe 7+ no PATH (Windows: instalado com `winget install --id Gyan.FFmpeg -e`)

## Armadilhas que já custaram retrabalho

### 1. OneDrive "online-only" — a pior de todas
`os.path.getsize()` retorna o tamanho **lógico** mesmo quando o arquivo só existe na nuvem. Testar tamanho NÃO detecta placeholder → o ffmpeg gera segmento vazio e o reel sai incompleto **sem erro visível**.

O atributo é o único indicador confiável — e são **três** bits, não um. Usar só `RECALL_ON_DATA_ACCESS` foi o bug que encheu o disco: arquivo dehidratado vira `RECALL_ON_OPEN`, o motor achava que estava local, não devolvia pra nuvem depois de usar, e o disco caía ~0,6 GB por reel até travar o lote.

```python
RECALL_DATA = 0x400000   # FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
RECALL_OPEN = 0x100000   # FILE_ATTRIBUTE_RECALL_ON_OPEN  <- o esquecido
OFFLINE     = 0x1000     # FILE_ATTRIBUTE_OFFLINE
NUVEM = RECALL_DATA | RECALL_OPEN | OFFLINE

def online_only(p):
    return bool(os.stat(p).st_file_attributes & NUVEM)
```

Em PowerShell, `$_.Attributes.ToString() -match 'Offline'` **não funciona** (o .NET não nomeia esses bits) e `$_.Length` é tamanho lógico — medir ocupação real de pasta OneDrive por PowerShell dá número inventado. Medir sempre em Python com `st_file_attributes`.

Para materializar, `attrib +P -U` dispara o download mas é **assíncrono**: esperar em laço até `online_only()` virar falso. Ler os bytes força recall síncrono e é mais confiável:
```python
with open(p, "rb") as fh:
    while fh.read(8 << 20): pass
```

### 1b. Ciclo hidrata → usa → devolve
A mídia bruta de todos os álbuns não cabe no disco (~20 GB só de clipes usados). O motor tem que hidratar **por peça**, e devolver pra nuvem (`attrib -P +U`) num `finally` assim que terminar aquele render. Sem isso o lote morre no meio.

Cuidado com o inverso também: `attrib +P` (pin) faz o OneDrive baixar **e manter para sempre**. Um pin acidental numa pasta de vídeos de drone materializou 26 GB e foi a causa real do disco cheio — não a mídia bruta, que o OneDrive já tinha dehidratado sozinha.

Dehidratar só funciona em arquivo **já sincronizado**. Se o upload ainda está pendente, o `attrib` retorna sucesso e nada acontece; não adianta insistir, só esperar.

### 2. Disco cheio quebra tudo silenciosamente
Com 0 byte livre: OneDrive não baixa (`Errno 22`), ffmpeg escreve arquivo truncado (`moov atom not found`), e nem dá pra escrever script (`ENOSPC`). **Checar espaço antes de cada lote** e limpar temporários de render (`_v2`, `_camp`, `_yt`) entre etapas. Nunca apagar arquivos do usuário (instaladores em Downloads etc.) — apagar só o que o pipeline criou.

Salvaguardas que valem a pena no motor: abortar abaixo de 1,5 GB, e uma *faxina de emergência* abaixo de 4 GB que devolve toda a mídia bruta pra nuvem antes de continuar. E um `_feitos.txt` de retomada — lote de 42 reels leva mais de uma hora e vai ser interrompido alguma vez; refazer tudo do zero é caro.

Em máquina com Docker parado, `wsl --shutdown` costuma devolver vários GB na hora. O `docker_data.vhdx` (~20 GB) só encolhe com prune **e** compactação do vhdx — e o daemon não sobe se o disco estiver muito cheio, então isso não é saída de emergência.

### 3. ZIP64 (zip com entrada > 4 GB)
`System.IO.Compression` do PowerShell 5.1 falha com "Cabeçalho de arquivo local corrompido". Usar o `tar` nativo do Windows:
```powershell
tar -xf "arquivo.zip" -C "$destino"
```
E **validar antes de apagar o zip**: contar arquivos extraídos e checar que nenhum tem 0 byte.

### 4. PowerShell 5.1
- Lê `.ps1` UTF-8 sem BOM como ANSI → acento vira mojibake. Escrever textos de legenda via `printf` no bash (UTF-8) e ler com `textfile=`.
- `$var:enable` é interpretado como variável com escopo → usar `${var}:enable`.
- `ffprobe` devolve duração com **vírgula** decimal em pt-BR → `[double]($s -replace ',','.')`.
- Não tem `&&`/`||`; sem `-Priority` em `Start-Process` (usar `$p.PriorityClass`).
- Processos longos morrem junto com a sessão → disparar via `Start-Process cmd /c script.cmd -WindowStyle Hidden` e logar em arquivo.

### 5. drawtext vs drawbox
Em `drawtext` a altura é `h`; `ih` **não existe** ali (erro "Undefined constant"). Em `drawbox`, `ih`/`iw` funcionam. Erro aparece como "Could not open encoder before EOF".

### 6. zoompan
Precisa de `-frames:v <n>` no output, senão gera vídeo com duração errada (ou infinito). `d=` é em frames.

### 7. Extração de frame pra QC
`mjpeg` recusa YUV não-full-range → acrescentar `,format=yuvj420p` no `-vf`.

## Look de obra (cor)

Medir o brilho médio antes (signalstats YAVG) e escolher a correção:
```
YAVG > 170  eq=brightness=-0.09:contrast=1.16:gamma=0.85:saturation=1.30
YAVG > 150  eq=brightness=-0.05:contrast=1.13:gamma=0.92:saturation=1.28
YAVG < 70   eq=brightness=0.14:contrast=1.10:gamma=1.30:saturation=1.24
YAVG < 95   eq=brightness=0.08:contrast=1.12:gamma=1.16:saturation=1.26
padrão      eq=contrast=1.12:gamma=1.03:saturation=1.26
```
Depois, sempre:
```
,vibrance=intensity=0.18,colorbalance=rs=0.03:gs=0.02:bs=-0.04:rm=0.03:bm=-0.03,unsharp=5:5:0.6:5:5:0.0
```
Medir foto também (`-frames:v 1`), senão slideshow sai escuro.

## Enquadramento

```
vídeo 9:16 : scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30
push-in    : ,zoompan=z='min(zoom+0.0004,1.06)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30
foto (Ken Burns): scale=1620:2880:...,crop=1620:2880,zoompan=z='min(zoom+0.0012,1.14)':d=<frames>:...
YouTube 16:9 de fonte vertical: fundo desfocado, nunca tarja preta
   split[a][b];[a]scale=1920:1080:...increase,crop=1920:1080,boxblur=28:2,eq=brightness=-0.12[bg];
   [b]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:0
```

## Checar orientação (essencial)

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x  arq
ffprobe -v error -select_streams v:0 -show_entries stream_side_data=rotation -of default=nw=1:nk=1  arq
```
`1920x1080 rot=-90` → vertical (ok). `1920x1080 rot=0` → **horizontal**, evitar em 9:16: o `crop` para 1080×1920 amplia 1,78× e o enquadramento fica claustrofóbico — foi exatamente o que o dono pegou na revisão de uma peça ("tem um clip no final que tá na horizontal").

Rodar `checa_orientacao.py` sobre **todas** as receitas antes de renderizar, não depois. Um clipe horizontal costuma estar em mais de uma peça (um deles estava em três).

**Nunca aplicar `transpose` manualmente**: o ffmpeg já auto-rotaciona pelo metadado. Girar de novo deixa tudo deitado — inclusive nas folhas de contato de QC, o que leva a descartar material bom por engano.

## Transições

Cadeia de `xfade` com offset acumulado (duração de cada parte menos a transição):
```
[0:v][1:v]xfade=transition=fade:duration=0.4:offset=<acc>[v1];
[v1][2:v]xfade=transition=smoothleft:duration=0.4:offset=<acc2>[v2]; ...
```
Tipos que funcionam bem: fade, fadeblack, smoothleft, smoothup, wipeleft, dissolve. Fallback: concat simples se o filtro falhar.

## Card final de marca

Fundo na cor escura da marca + logo oficial + tagline + arroba, com `fade=t=in:st=0:d=0.4`:
```
[1:v]scale=<0.86*W>:-1[lg];[0:v][lg]overlay=(W-w)/2:H*0.22:format=auto,
drawtext=...fontcolor=0xF2FBF5:fontsize=48:y=h*0.665,
drawtext=text='@suamarca':fontcolor=0x3AA56F:fontsize=40:y=h*0.735
```
Card com áudio (para concatenar com vídeo que tem som): incluir `-f lavfi -t <dur> -i anullsrc=channel_layout=stereo:sample_rate=48000` **antes** do `-filter_complex` e mapear `-map "[v]" -map 2:a`.

## Legenda de anúncio (estilo da marca)

Faixa verde translúcida + filete verde-claro + texto creme com sombra (nada de caixa preta):
```
drawbox=x=0:y=ih*<y0>:w=iw:h=ih*<alt>:color=0x0E261B@0.78:t=fill,
drawbox=x=0:y=ih*<y0>:w=iw:h=5:color=0x3AA56F@0.95:t=fill,
drawtext=textfile='...':fontcolor=0xF2FBF5:fontsize=54:x=(w-text_w)/2:y=h*<y0+0.035>:
line_spacing=14:shadowcolor=black@0.45:shadowx=2:shadowy=2
```

## Scripts que valeram a pena (escreva os seus no mesmo espírito)

| Script | Função |
|---|---|
| `prep_album.ps1` | sonda durações, converte HEIC, gera folhas de contato |
| `forca_download.py` | materializa clipes online-only lendo bytes (ThreadPool) |
| `verifica_fontes.py` | testa leitura real de cada clipe usado e sugere alternativas |
| `motor_v2.py` | renderiza reels a partir de `receitas_v2*.py` |
| `campanha_aquecimento.py` | criativos de anúncio com legenda embutida |
| `youtube_16x9.py` | converte seleção pra horizontal com intro/outro |
| `gera_roteiros.py` | gera os `-ROTEIRO.md` a partir das receitas |
| `qc_lote.py` | QC automático (frame escuro/estourado/sem cor) |
| `limpa_brutos.py` | devolve pra nuvem o que nenhuma peça usa (não apaga: a pasta vive no OneDrive) |
| `checa_orientacao.py` | varre receitas/campanhas e aponta clipe horizontal antes do render |
| `folha_tempo.py` | folha de contato com o tempo marcado em cada quadro, pra escolher trecho |

Transcrição de fala (pra virar legenda/roteiro): `faster-whisper` local, modelo `base`, `language="pt"`, `vad_filter=True` — já instalado.
