---
name: estudio-edicao
description: Estúdio de edição automática — pega a gravação crua do OBS (talking head) e entrega o vídeo editado no formato "explicador" (jump cuts, punch-in alternado, grafismos animados de tela cheia, manchetes com marca-texto, números, listas, gráficos com fonte, texto cinético sobre B-roll, trilha com ducking, efeitos) e os shorts/reels verticais com legenda dinâmica, passando por gate executável. Squad: diretor-edicao (líder), pesquisador-imagens, motion-designer, colorista, engenheiro-audio, editor-shorts. Use quando o pedido for "edita esse vídeo", "gravei no OBS", "fazer os cortes/shorts", "grafismo", "B-roll", "trilha", "legenda", "render do vídeo", "o que falta no vídeo X". Para reel curto montado sobre a fala com B-roll por frase, use reel-com-broll-por-fala; para reels de álbum de obra, reels-de-obra.
---

# Estúdio de edição automática

`<repo>` = pasta onde você clonou este repositório (sugestão: `%USERPROFILE%\squad-conteudo-instagram`).
Projetos e biblioteca pesam GB: ficam em `<repo>/motor/` (ignorados pelo git) ou onde `ESTUDIO_DADOS` apontar.

| Pasta | O quê |
|---|---|
| `motor/estudio/` | motor Python: `estudio.py` (CLI), etapas, `gate.py`, `gate_autoteste.py`, `buscar_midia.py` |
| `motor/graficos/` | templates Remotion (React) + `render.mjs` (rode `npm install` aqui uma vez) |
| `motor/projetos/<slug>/` | um vídeo: `projeto.json`, `plano.json`, `trabalho/`, `assets/`, `graficos/`, `final/` |
| `motor/biblioteca/musica/` | trilhas **licenciadas** que você colocar (nome da pasta = clima) |
| `motor/biblioteca/sfx/` | whoosh/pop/impacto sintetizados pelo próprio motor |
| `motor/marcas/<marca>/` | `marca.json` (paleta, fontes, tagline, arroba, diretrizes de texto, correções) + logo oficial. Vem só `exemplo` |

Referências (abrir sob demanda): `referencias/biblia-de-estilo.md` (o formato, com números medidos),
`referencias/plano-json.md` (contrato do plano e props dos templates), `referencias/captacao.md`
(luz, áudio, OBS, como avisar erro com "corta").

## Fluxo (quem grava só grava)

```powershell
cd "<repo>\motor\estudio"
python -I estudio.py novo "<arquivo do OBS>" --marca <pasta em marcas/> --formato video|aula --glossario "nomes próprios"
```

**Marca e formato são obrigatórios** se o pedido não disser ("é pra qual marca? vídeo ou aula?").
O diretor lê `marcas/<marca>/marca.json → diretrizes` antes de escrever qualquer texto.

| Formato | Punch-in | Corte de pausa | Tela cheia (P07) | Capítulos (P10) |
|---|---|---|---|---|
| `video` | alterna 1,0/1,18 | > 0,30 s | 15–80% (meta ~50%) | opcionais |
| `aula` | não (cortaria a tela compartilhada) | > 0,60 s (ritmo didático) | 0–50% | obrigatórios acima de 5 min |

1. **novo** → prepara, transcreve (Whisper large-v3-turbo na GPU; `small` na CPU se não houver), corta
   silêncio/regravação/"corta", mede a cor. Saída: `trabalho/roteiro_editado.txt` com tempos da linha editada.
2. **Tropeços**: `python -I estudio.py tropecos <slug>` → ler `trabalho/tropecos.txt`, cortar via `remover` →
   `recortar`. Não confiar só no roteiro (ver armadilhas).
   **Ler os ALERTAS** no topo do roteiro: fala não transcrita que foi cortada. O Whisper às vezes ignora
   a 2ª tentativa de uma frase repetida. Ouvir o trecho bruto; se era fala boa, ajustar.
3. **Diretor** (agente `diretor-edicao`) lê o roteiro e a bíblia e escreve `plano.json`; pede B-roll,
   fotos, prints e dados ao `pesquisador-imagens` (`buscar_midia.py`, licença registrada sempre).
4. `python -I estudio.py etapa gate-plano <slug>` até passar.
5. `python -I estudio.py render <slug>` → voz → câmera → grafismos → montagem → shorts → **gate final**.
6. QC visual: folha de contato do final (ver `diretor-edicao`), corrigir e rerenderizar (há cache por beat).
7. Entregar: `final/<slug>.mp4`, `final/short_*.mp4`, `final/creditos.txt` e `final/capitulos.txt`.
   **Publicar é do dono do canal.** O squad para no arquivo pronto. Short para o Instagram segue para
   `tools/reel/gate_reel.py` e depois `instagram-agendar`.

**Aula por tópico** (gravação longa → várias aulas curtas): o diretor marca no `plano.json` do pai
`"aulas": [{titulo, ini, fim}]` (tempos editados, fronteira no início de frase) e roda
`python -I estudio.py dividir <slug>` → cria `<slug>-pNN-<titulo>` (mesma transcrição, janela bruta própria,
beats remapeados, rótulo "Parte N · Tópico" na abertura e "A seguir: …" no fim; a última fica com o
`Encerramento`). Depois `python -I estudio.py render-partes <slug>` (gate em cada uma).

Etapa isolada: `python -I estudio.py etapa <preparar|transcrever|cortar|cor|audio|aroll|graficos|montar|shorts|sfx> <slug>`.

## Gate (obrigatório, decide)

`gate.py plano` antes do render e `gate.py final` depois; regras e origem no docstring do arquivo.
O final inclui **F07** (reouve o áudio entregue procurando fala de bastidor) e **F08** (tropeço).
Mexeu no gate → `python -I gate_autoteste.py <projeto aprovado>` (copia o projeto, injeta um defeito por
regra, exige exit 1). F07/F08 precisam de duas falas gravadas por você em `fixtures/` (ver o README de lá);
sem elas o autoteste falha de propósito. Falso positivo corrige a **regra**, nunca pula o gate.

## Armadilhas já vividas

- **Whisper engole repetição**: a 2ª tentativa de frase repetida não vira texto e o trecho seria cortado como
  silêncio. O `cortar` mede energia de voz no que removeu e alerta no roteiro.
- **Fade a partir do preto**: grafismo opaco que entra com opacidade 0 mergulha no preto. Entrada é por
  desfoque+escala, sem opacidade. Texto cinético começa na 1ª palavra (gate F04 pegou 0,6 s de tela morta).
- **Pico após AAC**: limitador em −1 dB deu −0,5 dBTP depois da codificação. Limite em 0,79 (≈ −2 dB).
- **Cache de grafismo**: a chave inclui o código dos templates; sem isso, template corrigido não rerenderiza.
- **Logo com letra escura some no fundo escuro**: o `Encerramento` usa fundo claro sempre.
- **Fonte com um peso só** (Oswald 700): pedir peso não carregado faz o navegador sintetizar e o título sai fino.
- **Legenda sem quebra**: spans encostados não quebram linha; o container é flex com wrap.
- **Regra no-op**: regra de ritmo só valia acima de 60 s e a base de teste tinha 44 s. O autoteste pegou.
- **Sobras do Remotion encheram o disco** (265 cópias de `assets/` no Temp, 68 GB): o `render.mjs` apaga o bundle no fim.
- Console do Windows: `sys.stdout.reconfigure(encoding="utf-8")` em todo script que imprime acento.
- Whisper na GPU precisa de `nvidia-cublas-cu12` e `nvidia-cudnn-cu12==9.*` via pip + `os.add_dll_directory`
  (feito em `comum.cuda_dlls()`).
- **Pedido de corte falado** ("essa parte pode cortar"): só "corta" é automático. O diretor lê o roteiro inteiro
  e põe o trecho em `projeto.json → "remover": [{ini, fim, motivo}]` (tempo bruto) e roda `etapa cortar`.
- **Whisper erra o nome da marca** mesmo com glossário: `marca.json → correcoes` conserta antes do roteiro e das legendas.
- **Cor automática em aula suja o documento** (vinheta + tom quente sobre tela compartilhada): `aula` sai sem
  correção (`cor_auto: false`); só a câmera de `video` é tratada.
- **Short de aula com tela** pegou o documento e perdeu o rosto: `projeto.json → "pilha": {camera, tela}` (px da
  gravação) empilha título/câmera/legenda/tela. Gate **P11** reprova short de aula sem `pilha` ou `short_central: true`.
- **"Corta essa parte." foi ao ar**: o Whisper com VAD pulou a frase. Gate **F07** reouve o áudio do FINAL sem VAD e
  reprova fala de bastidor ("corta/tira essa parte", "pode cortar.", "na edição", "vou regravar").
- **Tropeço de fala é corte, não estilo**: ler o roteiro inteiro e cortar repetição, frase abandonada, gagueira,
  muleta. Depois do `novo`, SEMPRE `estudio.py tropecos <slug>` (transcrição literal sem VAD) → `remover` →
  `recortar` (refaz o corte e remapeia o plano, backup `_vN`). Gate **F08** reprova repetição imediata no final.
- **O corte comeu fala boa**: o VAD não transcreveu uma palavra e o trecho saiu como silêncio (ALERTA). Para
  devolver: `projeto.json → "manter": [{ini, fim, motivo}]` + `recortar`.
- **"Corta" é conteúdo** em aula prática ("se a gente corta essa ponta"): `projeto.json → "palavra_corta": false`
  ANTES do `novo`/`recortar`; bastidor fica com `tropecos` + `remover` e o F07.
- **Troca de tela no meio da aula**: assinatura visual = barra de tarefas do Windows no rodapé. Varredura:
  ffmpeg `fps=1,crop=1920:24:0:1052` → luma > 170 e saturação < 25. Corte da última palavra útil à 1ª depois da tela estável.
- **Rótulo "Parte N" sumindo** em slide escuro: `cenas[] → "cor": "claro"`; em vídeo de tela cheia use `pos` no pé esquerdo.
- **Instrução de edição falada** ("vou colocar na edição umas fotos"): executa o pedido E corta a frase.

## Pendências conhecidas

- Cenário virtual na pós (recorte por IA). Hoje: remoção de fundo no OBS ou tela verde.
- Chave do Pexels/Pixabay em `motor/.env` (sem ela, B-roll em vídeo não baixa; fotos vêm do Wikimedia).
- Trilhas licenciadas em `motor/biblioteca/musica/` (sem elas o vídeo sai sem música, com aviso).
