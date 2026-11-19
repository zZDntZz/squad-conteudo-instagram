---
name: manychat-automacao
description: Automação de comentários ("Comente X" → resposta pública → DM com botão → isca) e de resposta a story no ManyChat, plano grátis, operada pelo Chrome real do usuário via Claude in Chrome. Cobre o limite do grátis (só post específico, que precisa existir), rascunho antes do post e ativação depois que ele sai (com tarefa agendada que tenta de novo), isca em PDF por link "Abrir site", e o que só sai no Pro. Use quando o pedido for "monta a automação do comente X", "ativa o ManyChat no reel novo", "manda o PDF na DM", "responde quem responder o story", "automação de comentários".
---

# Automação de comentários e de story no ManyChat (plano grátis)

Ferramentas em `<repo>/tools/manychat/`: `manychat.py` (confere a automação, monta o prompt e executa)
e `prompts/*.txt`. Exemplo: `exemplos/automacao.exemplo.json`.

Dados da conta ficam no ambiente, nunca em arquivo do repositório:
`CLAUDE_CHROME_DEVICE_ID` (ver `instagram-agendar`), `MANYCHAT_CONTA` (o trecho da URL
`app.manychat.com/<ESTE>/dashboard`) e, opcional, `NOTIFICAR_CMD` (recebe o resultado no stdin).

## Fluxo padrão de um post com "Comente X"

1. **Legenda e automação com a mesma palavra.** O gate de legenda (`tools/post/gate-post-insta.cjs`) reprova se
   a palavra do "Comente X" for diferente de `palavraManychat`. O "Comente X" pode ficar no **início** da legenda
   (aparece antes do "mais") ou no fim: o gate não exige posição.
2. **Antes do post sair: rascunho.**
   `python -I tools\manychat\manychat.py rascunho automacao.json --executar`
   Fluxo: gatilho palavra-chave → **3 respostas públicas** (sorteadas) → **DM com botão** → **DM com a isca**.
3. **Depois que o post sai: ativar.** No grátis o gatilho precisa de um post que já exista. Tarefa agendada
   alguns minutos depois do horário do post, procurando o post pela legenda e tentando de novo a cada 15 min:
   `python -I tools\manychat\manychat.py ativar automacao.json --esperar 19:03 --executar`
   (Windows: Agendador de Tarefas; Linux/macOS: `at`/cron. Deixe o PC ligado e o Chrome aberto.)
4. **Testar de verdade**: comentar a palavra no post com outra conta e ver a DM chegar com o botão funcionando.

## Resposta a story

`python -I tools\manychat\manychat.py story automacao.json --executar`

- Gatilho "O usuário responde ao seu Story", todos os stories: **é grátis**.
- É o par do story que pede "Responda este story" (enquete e caixa de perguntas não dá para agendar pelo
  Business Suite).
- A mensagem tem que ser **específica**: pergunte o problema, o lugar, peça uma foto. "Recebi sua mensagem,
  já te respondo" não puxa conversa.

## O que aprendemos (18/11/2026)

- **Cloudflare bloqueia navegador automatizado** (Playwright/headless) no ManyChat. Funciona pelo **Chrome real
  do usuário**, já logado, via Claude in Chrome.
- **No grátis, "Qualquer post ou reel" e "Próximo post ou reel" são PRO.** Clicar abre o pop-up de trial de
  14 dias. Só "Post específico" — e ele precisa existir. Daí o rascunho + ativação depois.
- Para o assistente avançar no rascunho, ele exige escolher um post: fica um post antigo **provisório** no
  gatilho. Publicar assim responde no post errado; por isso o rascunho fica DRAFT até a ativação.
- Também são PRO: Condição, Randomizador, Coleta de Dados, Atrasar automação, Curtir respostas. Não fazem falta.
- Limite do grátis: 1.000 contatos.
- **Isca em PDF**: o Instagram **não anexa PDF** na DM. Publique o PDF no seu site e mande um botão
  **"Abrir site"** com o link. Imagem anexada funciona, mas PDF por link é o que o usuário salva no celular.
- **Título de botão: máximo 20 caracteres** ("Baixar o teste em PDF" tem 21 e foi recusado). O `manychat.py` confere.
- **"Powered by ManyChat"** na mensagem e a **página de ~2 s do ManyChat antes de abrir o link** só saem no Pro.
- **Nunca aceite trial nem cadastre cartão**: todo prompt manda fechar o pop-up.
- Numa ativação o editor mostrou "Conteúdo publicado!" com status STOPPED e, segundos depois, LIVE, sem o
  clique em Publicar. O prompt manda recarregar e conferir o status de novo.

## Pronto quando

Status LIVE conferido depois de recarregar, gatilho no post certo, palavra certa, os três blocos lá, e um
comentário de teste recebeu a DM com o link abrindo.
