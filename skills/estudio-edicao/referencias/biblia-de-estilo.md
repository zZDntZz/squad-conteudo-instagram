# Bíblia de estilo — formato "explicador de economia/negócios"

Engenharia reversa de um canal de referência do formato (explicador de negócios no YouTube), feita em 10–11/10/2026: 378 vídeos longos e
120 shorts listados (≈76 h); amostra de 18 longos (mais vistos, mais recentes, mais antigos e do meio) e
6 shorts baixados em 360p, com detecção de cena, folhas de contato a cada ~12 s e sequências densas a
4 quadros/s para ver o movimento.

**Copiamos a gramática, não a identidade.** Paleta, fontes, logo, vinhetas e trilhas são da sua marca
(`marca.json`). Nada de reproduzir grafismo, cenário ou material do canal de referência.

## Números medidos (amostra)

| Métrica | Longos (18) | Shorts (6) |
|---|---|---|
| Cortes/min (mediana) | 7,4 (faixa 2,9–16,6) | 13 (faixa 2–18) |
| Duração mediana do plano | 5,3 s | 3,1 s |
| Duração do vídeo | ~20 min (mediana) | 30–60 s |
| Loudness do master | −21 LUFS (nós entregamos −14) | −22,5 |
| Brilho médio (YAVG) | ~93 — imagem baixa, com contraste | ~94 |
| Tempo de tela cheia com grafismo/B-roll | ~50% nos vídeos atuais | B-roll a cada 2–3 s |

## Três fases do canal (para calibrar a ambição)

1. **Início**: talking head simples, texto lateral, quase sem grafismo. 3–5 cortes/min.
2. **Meio**: fundo escuro, mapas coloridos, bandeiras, inserts em P&B para reação, prints de notícia com
   marca-texto amarelo.
3. **Atual**: colagem editorial (recortes de papel, fotos em meio-tom), cards de dados sobre papel claro,
   cor de marca chapada em telas de tópico, várias locações e uma 2ª câmera. 8–12 cortes/min.

Parte da fase 3 é **produção** (locações, figurino, 2ª câmera, B-roll próprio), não edição. Com uma
câmera só no OBS, simulamos: punch-in digital no lugar da 2ª câmera, B-roll de banco, grafismo gerado.

## Gramática (o que o diretor aplica)

**Câmera (A-roll)**
- Jump cut em todo silêncio > 0,3 s. Regravação: fica sempre a última tentativa.
- Alterna **aberto ↔ fechado** (punch-in ~18%) a cada corte que pula conteúdo, com plano mínimo de 2,5 s.
  É isso que esconde o jump cut. Fonte em 1080p aguenta até ~1,25 de zoom; acima disso, gravar em 1440p/4K.
- Imagem "cinema caseiro": fundo mais escuro que o rosto, luz quente prática ao fundo, vinheta leve.

**Grafismos de tela cheia** (≈ metade do tempo)
| Momento da fala | Template |
|---|---|
| Fato de notícia ("o BC anunciou…") | `Manchete` (título citado, veículo, data, marca-texto na frase-chave) ou `Print` do site |
| Número que importa ("37 milhões") | `Numero`; troca de estado por desfoque quando há antes→depois |
| Contraste entre dois lados | `Comparacao` (linha pontilhada que se desenha) |
| Enumeração ("três exigências") | `Lista`, item entrando no tempo da fala |
| Série histórica | `Grafico` com **fonte oficial obrigatória** |
| Frase de efeito / tese | `TextoCinetico` sobre B-roll escurecido, palavra a palavra com a fala |
| Fala de terceiro | `Citacao` (curta, com autor) |

**Sobre a câmera**: `PalavraChave` no terço inferior (o termo técnico ou o número dito), 1,5–3 s, com "pop".

**Ritmo**
- Gancho nos primeiros 30 s: 3–4 grafismos seguidos, a tese do vídeo em texto cinético.
- Nunca mais de ~25 s de câmera sem nenhum elemento visual.
- Grafismo de tela cheia dura o tempo da ideia (3–8 s típico; listas até 15 s).
- Entrada e saída por **desfoque + escala**, nunca mergulho no preto. Corte seco de volta para a câmera.
- Whoosh discreto na entrada de tela cheia; pop na palavra-chave. Trilha baixa (−26 dB) com ducking.

**Shorts**
- Recorte vertical no rosto, legenda grande em caixa alta, 3 palavras por vez, palavra falada em destaque
  amarelo com contorno preto; título fixo no topo.
- Trecho autocontido de 20–60 s com gancho na 1ª frase.

## Fontes e honestidade

- Todo número e toda manchete precisam ser verificáveis: o pesquisador registra URL e data no plano.
- Citação de terceiros só em trecho curto (gate P05) e com crédito.
- Mídia de banco entra com licença em `assets/licencas.json` (gate P06); CC BY/BY-SA gera crédito na descrição.
