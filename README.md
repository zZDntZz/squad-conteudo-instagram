# Squad de conteúdo para Instagram

Skills, agentes e ferramentas para o [Claude Code](https://docs.claude.com/claude-code) produzirem e agendarem
conteúdo de Instagram: reels sobre a fala com B-roll, reels a partir de álbuns de obra, carrosséis (inclusive
panorâmicos), stories, agendamento no Meta Business Suite e automação de comentários no ManyChat.

Feito originalmente para a operação de uma empresa de paisagismo (Khalid Ecossistemas) e generalizado: tudo
o que é da marca (nome, cores, logo, telefone, termos vetados, pastas de cliente vetadas) vem de arquivos de
config, não do código.

Cada passo que produz efeito no mundo real passa por um **gate executável** (um script que sai com 0 ou 1),
e cada gate tem um **autoteste** que injeta os defeitos e prova que ele reprova.

Sem promessa de resultado: o repositório organiza o trabalho e barra erros conhecidos. Alcance e venda dependem
do seu conteúdo, do seu público e da plataforma.

## O que tem aqui

### Skills (`skills/`)

| Skill | Para quê |
|---|---|
| `reel-com-broll-por-fala` | Reel 9:16 sobre a gravação original, imagem trocando a cada frase pelo processo falado, Ken Burns em foto, fim colado na última palavra, arquivo de fontes, gate |
| `reels-de-obra` | Reels narrados a partir de álbuns de obra (o vídeo segue a fala), criativos de anúncio, YouTube 16:9 |
| `fabrica-conteudo-obras` | Lote de álbuns: download, extração, curadoria por folha de contato, disco e OneDrive, QC |
| `estudio-edicao` | Gravação crua do OBS → vídeo editado (jump cuts, punch-in, grafismos Remotion, trilha) + shorts, com gate do plano e do final |
| `carrossel-e-stories` | Carrossel 4:5, carrossel panorâmico e stories a partir de JSON (Chrome headless) |
| `instagram-agendar` | Agendar reel, carrossel e stories no Meta Business Suite via Claude in Chrome, com gates antes e conferência no Planner |
| `manychat-automacao` | "Comente X" → respostas públicas → DM com botão → isca; resposta a story; plano grátis |

### Agentes (`agents/`) — o squad de edição

| Agente | Papel |
|---|---|
| `diretor-edicao` | Líder: roda o motor, decupa, escreve o `plano.json`, delega, passa nos gates, faz o QC visual |
| `pesquisador-imagens` | B-roll, fotos, prints e dados só de fonte licenciada/oficial, com licença registrada |
| `motion-designer` | Templates de grafismo (Remotion/React) e identidade em `marca.json` |
| `colorista` | Cor, exposição, enquadramento e orientação de luz |
| `engenheiro-audio` | Voz, loudness (−14 LUFS), trilha licenciada com ducking, efeitos |
| `editor-shorts` | Escolhe trechos autocontidos e gera os cortes 9:16 |

### Ferramentas (`tools/`) e motor (`motor/`)

| Caminho | O quê |
|---|---|
| `tools/post/gate-post-insta.cjs` (+ autoteste) | Gate da legenda: termos vetados, pasta vetada, erro de transcrição, nome da marca, telefone oficial, "Comente X" = palavra da automação, CTA único, tamanho |
| `tools/reel/gate_reel.py` (+ autoteste) | Gate do reel: formato, A/V, fala cortada no fim, silêncio, imagem congelada, tela preta, loudness, bastidor/tropeço, arquivo de upload, fontes/licenças/pastas vetadas, nome na legenda |
| `tools/reel/monta_reel.py` | Montador do reel com B-roll por frase |
| `tools/reel/comprimir_upload.py` | x264 2 passes + `+faststart` abaixo de ~10 MB |
| `tools/agendar/` | Gates + prompts de agendamento para `claude -p --chrome` |
| `tools/manychat/` | Conferência da automação + prompts de rascunho, ativação e resposta a story |
| `tools/carrossel/`, `tools/carrossel-panoramico/`, `tools/stories/` | Geradores de imagem |
| `tools/gate-publico.py` (+ autoteste) | Gate deste repositório: barra segredo, dado pessoal e mídia de cliente antes de publicar |
| `motor/estudio/` | Motor Python do estúdio de edição (`estudio.py`, `gate.py`, `gate_autoteste.py`) |
| `motor/graficos/` | Templates Remotion (legenda karaokê, encerramento, manchete, número, lista…) |
| `motor/marcas/exemplo/` | Marca de exemplo (`marca.json` + logo placeholder) |

## Instalar

Dependências: **Python 3.11+**, **ffmpeg 7+** no PATH, **Node 20+**, Chrome ou Edge, e o Claude Code com a
extensão **Claude in Chrome** (para agendar e para o ManyChat). Para transcrever: `pip install faster-whisper`
(GPU NVIDIA opcional: `pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"`). Para a folha de contato: `pip install pillow`.

```powershell
git clone <url-deste-repo> "$env:USERPROFILE\squad-conteudo-instagram"
cd "$env:USERPROFILE\squad-conteudo-instagram"
npm install                                   # playwright-core (geradores de imagem)
cd motor\graficos; npm install; cd ..\..      # Remotion (grafismos do reel e do estúdio)

# skills e agentes para o Claude Code
Copy-Item -Recurse skills\* "$env:USERPROFILE\.claude\skills\"
Copy-Item agents\*.md "$env:USERPROFILE\.claude\agents\"

# sua marca
Copy-Item config.exemplo.json config.json     # edite: nome, escritas erradas, telefone, termos e pastas vetadas
Copy-Item -Recurse motor\marcas\exemplo motor\marcas\sua-marca   # troque marca.json e logo.png
```

Linux/macOS: mesmos passos com `cp -r skills/* ~/.claude/skills/` e `cp agents/*.md ~/.claude/agents/`.

Nas skills, `<repo>` é a pasta do clone. `config.json`, `motor/marcas/<sua-marca>/`, `motor/projetos/` e
qualquer `.mp4` ficam fora do git (`.gitignore`).

Dados da conta ficam em variáveis de ambiente, nunca em arquivo:
`CLAUDE_CHROME_DEVICE_ID` (qual Chrome o agente usa), `MANYCHAT_CONTA` (trecho da URL da conta),
`PEXELS_API_KEY`/`PIXABAY_API_KEY` (B-roll de banco, em `motor/.env`), `CHROME_PATH` (opcional).

Prove os gates na sua máquina antes de confiar neles:

```powershell
node tools\post\gate-post-insta-autoteste.cjs
python -I tools\reel\gate_reel_autoteste.py
python -I tools\gate-publico-autoteste.py
```

## Fluxo completo de um post

1. **Roteiro.** Gancho nos primeiros 3 s, uma ideia, um CTA. Se o CTA é "Comente X", defina X agora: a mesma
   palavra vai na legenda, no último slide/fala e na automação. Modelo: `skills/reels-de-obra/referencias/roteiro-narracao.md`.
2. **Gravar.** Celular na vertical, microfone a um palmo, errou → pausa e repete a frase inteira.
   Dicas de luz e som: `skills/estudio-edicao/referencias/captacao.md`.
3. **Editar com B-roll** (`reel-com-broll-por-fala`): transcrever, corrigir, uma cena por frase (mídia própria
   primeiro, banco licenciado depois), montar, folha de contato, arquivo de fontes.
4. **Gate do reel**: `python -I tools\reel\gate_reel.py final.mp4 --insta final-insta.mp4 --cenas cenas.json --fontes fontes.md --legenda plano_render.json`.
5. **Comprimir** para o upload pelo navegador (`comprimir_upload.py`, já chamado pelo montador). O gate R9 confere.
6. **Agendar** (`instagram-agendar`): `agendar.py post.json` roda o gate da legenda e o do reel e só então monta
   o prompt; o agente programa no Business Suite (só Instagram) e confere no Planner.
7. **Automação ManyChat** (`manychat-automacao`): rascunho antes; ativação agendada para alguns minutos depois
   do horário do post, procurando o post pela legenda; teste comentando a palavra com outra conta.
   A isca em PDF vai publicada no seu site, por um botão "Abrir site".
8. **Stories** (`carrossel-e-stories` + `instagram-agendar`): imagem ou vídeo com a chamada escrita
   ("Responda este story"), e a automação de resposta a story responde na DM.

## Limites conhecidos

**ManyChat, plano grátis**
- Gatilho de comentário só em **post específico**, que precisa já existir. "Qualquer post" e "Próximo post" são PRO.
- Também PRO: Condição, Randomizador, Coleta de Dados, Atrasar automação, Curtir respostas.
- "Powered by ManyChat" e a página de ~2 s antes de abrir um link só saem no Pro.
- Limite de 1.000 contatos. Título de botão até 20 caracteres.
- O Instagram não anexa PDF na DM: a isca vai por link.
- O ManyChat bloqueia navegador automatizado (Cloudflare); só funciona pelo Chrome real logado.

**Meta Business Suite**
- Upload pelo navegador até ~10,4 MB por arquivo.
- Não dá para trocar o vídeo de um reel já programado: programa o novo, confere, exclui o antigo.
- Stories: agenda imagem e vídeo; **não** agenda enquete, caixa de perguntas nem link/figurinha do reel.
- A etapa de capa do reel às vezes vem desativada.

**Este repositório**
- O agendamento e o ManyChat dependem da interface dessas plataformas, que muda sem aviso. Os prompts dizem o
  que fazer e o que nunca fazer (pagar, aceitar trial, publicar na hora, apagar o que não criou); acompanhe as
  primeiras execuções.
- O autoteste do motor do estúdio precisa de um projeto aprovado seu e de duas falas gravadas por você
  (`motor/estudio/fixtures/README.md`).
- O agendamento de carrossel segue o mesmo padrão do reel, mas ainda não rodou em produção.

## Licença

MIT — veja `LICENSE`. Remotion tem licença própria (gratuita para pessoa física e empresas pequenas; confira os termos).
