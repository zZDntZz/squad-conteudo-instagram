# Narração, transcrição e legenda karaokê

## Captação (o que dizer a quem narra)

A narração foi gravada pelo gravador de voz do iPhone. O material de ago/2026 saiu com **nível baixo, não distorcido**: −20 a −22 dB médio, picos em −3,5 dB. Isso é distância do microfone, não erro de configuração — e tem conserto na origem:

- Celular na horizontal, **a um palmo da boca**, ligeiramente de lado (de frente estoura os "p" e "t").
- O microfone principal do iPhone fica na **base**, perto do conector — a mão apoiada ali abafa tudo.
- Ambiente pequeno com pano por perto (quarto com cama e guarda-roupa). Sem geladeira, ar-condicionado ou ventilador ligado.
- Errou no meio? Não parar: 2 s de silêncio e repetir a frase.
- Não cronometrar — o vídeo é que se ajusta à fala.
- **O CTA sai acelerado** porque ele já sabe de cor, e é justamente onde o Whisper erra. Pedir micropausa: "Peça... um orçamento."

Nomes de arquivo: o gravador nomeia pelo local (`<Local>`, `<Local> 2`, …). O **primeiro não tem sufixo** e é o 01. `prep_audios.py` resolve isso detectando o prefixo comum (o menor nome do lote) — não dá para procurar dígitos, porque o prefixo já tem números dentro.

## Transcrição

```python
modelo = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = modelo.transcribe(audio, language="pt", vad_filter=True,
                            word_timestamps=True, beam_size=5,
                            vad_parameters={"min_silence_duration_ms": 350})
```

`word_timestamps=True` é obrigatório: os tempos por palavra alimentam **as duas coisas** — o corte de cena na pausa e o karaokê.

Guardar `frases` (para o plano de cenas) e `palavras` (para a legenda) no mesmo JSON.

**PyAV não aceita acento no caminho** no Windows, e nome de arquivo do iPhone vem em NFD. Copiar para caminho ASCII antes:

```python
plano = unicodedata.normalize("NFKD", nome)
plano = "".join(c for c in plano if not unicodedata.combining(c)).lower()
```

## Correção obrigatória antes de queimar

`correcoes.py` roda sobre a sequência de palavras preservando os tempos (quando N palavras viram M, redistribui proporcionalmente). Erros confirmados em produção:

| Saiu | Era |
|---|---|
| Péssimo orçamento / Péssimo lançamento | Peça um orçamento |
| sem independência de veneno | sem depender de veneno |
| o que cabra em seu espaço | o que cabe no seu espaço |
| pádio | pátio |

Sempre rodar `lista_ctas.py` e **ler as 42 linhas** antes de queimar legenda em lote. O detector de termos suspeitos não pega erro novo — só o olho pega.

Erros que **não** são erro: frase cortada em duas pela pausa ("…jardim de alto padrão se / mantém"). Na legenda isso não aparece, porque o agrupamento é por palavra.

## Legenda karaokê (ASS, não drawtext)

Usar arquivo `.ass` + filtro `subtitles` do libass. Fica mais leve e mais bonito que empilhar `drawtext` — e o karaokê (`\k`) é nativo.

```
Style: Fala,Arial Black,72,&H0000D4FF,&H00FFFFFF,&H00000000,&H00000000,
       0,0,0,0,100,100,0,0,1,5,2,2,60,60,430,1
```

- `PrimaryColour` = amarelo `&H0000D4FF` (#FFD400) — palavra em foco
- `SecondaryColour` = branco — ainda não falada
- `OutlineColour` = preto, `Outline 5` — o contorno grosso é a assinatura do canal
- `MarginV 430` com `Alignment 2`: sobe o texto acima da UI do Instagram
- Cores ASS são **&HAABBGGRR** (BGR invertido), não RGB

Regras de leitura:
- **3 palavras por linha**, cortando também em pausa > 0,45 s
- palavra órfã (linha de 1 palavra) se junta à vizinha, se não houver pausa longa entre elas
- **cortar a legenda quando o card entra** (`ate=inicio_card`), senão ela escreve o CTA por cima do card que já traz o CTA

Fonte 72 em 1080×1920. Testado em 58 e ficou tímido perto do canal.

## Tratamento do áudio na mixagem

```
[1:a]aresample=48000,highpass=f=95,afftdn=nr=14:nf=-28,adeclick,
     acompressor=threshold=-18dB:ratio=3.5:attack=8:release=200,
     loudnorm=I=-16:TP=-1.5:LRA=11[a]
```

`afftdn` só é necessário porque a gravação distante exige ganho, e o ganho sobe o ruído junto. Com captação de perto, dá para tirar. `loudnorm I=-16` é o alvo das plataformas.

Queimar a legenda **na mesma passada** da mixagem evita um encode a mais:

```
-filter_complex "<CADEIA_AUDIO>;[0:v]subtitles='<caminho>'[v]" -map "[v]" -map "[a]"
```
