# -*- coding: utf-8 -*-
"""Automação de comentários e de resposta a story no ManyChat (plano grátis) via Claude in Chrome.

No plano grátis o gatilho de comentário só aceita POST ESPECÍFICO, que precisa existir. Então:
  1. `rascunho` antes de o post sair: monta o fluxo inteiro como DRAFT (gatilho provisório num post antigo);
  2. `ativar` depois que o post sai: procura o post pela legenda, troca o gatilho e publica.
     `ativar --esperar HH:MM` dorme até lá e tenta de novo a cada 15 min (até 12 vezes) enquanto o post não aparece.
  3. `story`: automação de resposta a story (qualquer story) — grátis.

Uso:
  python -I manychat.py rascunho automacao.json [--executar]
  python -I manychat.py ativar   automacao.json [--esperar 19:03] [--executar]
  python -I manychat.py story    automacao.json [--executar]

Variáveis de ambiente (dados da sua conta; nunca em arquivo do repositório):
  CLAUDE_CHROME_DEVICE_ID  deviceId do Chrome logado (ver instagram-agendar → descobrir navegador)
  MANYCHAT_CONTA           o trecho da URL da conta, ex.: https://app.manychat.com/<ESTE>/dashboard
  NOTIFICAR_CMD            (opcional) comando que recebe o resultado no stdin (ex.: script que manda no seu WhatsApp)
"""
import datetime as dt, json, os, shutil, subprocess, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MAX_TITULO_BOTAO = 20  # o ManyChat recusa título de botão com mais de 20 caracteres (18/11/2026)


def checar(a):
    e = []
    for k in ("nome", "perfil", "palavra", "legenda_inicio", "respostas_publicas", "dm_abertura", "botao_dm", "isca"):
        if k not in a:
            e.append(f"falta '{k}'")
    if e:
        return e
    if len(a["respostas_publicas"]) != 3:
        e.append("use 3 respostas públicas (o ManyChat sorteia; uma só parece robô)")
    for t in [a["botao_dm"], a["isca"].get("botao", "")]:
        if len(t) > MAX_TITULO_BOTAO:
            e.append(f"título de botão com {len(t)} caracteres (máx. {MAX_TITULO_BOTAO}): \"{t}\"")
    url = a["isca"].get("url", "")
    if url and not url.startswith("https://"):
        e.append(f"isca com URL que não é https: {url}")
    if a["isca"].get("tipo") == "pdf" and not url.lower().endswith(".pdf"):
        e.append("isca tipo pdf precisa de URL terminando em .pdf (publique o PDF no seu site)")
    return e


def preencher(nome, v):
    t = (AQUI / "prompts" / nome).read_text(encoding="utf-8")
    for k, x in v.items():
        t = t.replace("{{" + k + "}}", str(x))
    if "{{" in t:
        raise SystemExit(f"campo sem valor em {nome}: {t[t.index('{{'):t.index('{{') + 40]}")
    return t


def valores(a):
    device = os.environ.get("CLAUDE_CHROME_DEVICE_ID")
    conta = os.environ.get("MANYCHAT_CONTA")
    if not device or not conta:
        raise SystemExit("defina CLAUDE_CHROME_DEVICE_ID e MANYCHAT_CONTA no ambiente")
    r = a["respostas_publicas"]
    i = a["isca"]
    return dict(DEVICE=device, CONTA=conta, NOME=a["nome"], PERFIL=a["perfil"], PALAVRA=a["palavra"].lower(),
                LEGENDA_INICIO=a["legenda_inicio"], R1=r[0], R2=r[1], R3=r[2],
                DM=a["dm_abertura"], BOTAO=a["botao_dm"], ISCA_TEXTO=i["texto"], ISCA_BOTAO=i["botao"],
                ISCA_URL=i["url"], STORY_MSG=a.get("resposta_story", ""))


def claude(prompt):
    if not shutil.which("claude"):
        raise SystemExit("claude CLI não encontrado no PATH")
    r = subprocess.run(["claude", "-p", "--chrome", prompt], capture_output=True, text=True, encoding="utf-8")
    print(r.stdout[-3000:], r.stderr[-500:])
    return r.stdout


def notificar(msg):
    cmd = os.environ.get("NOTIFICAR_CMD")
    if cmd:
        subprocess.run(cmd, input=msg, text=True, shell=True)


def ativar_esperando(prompt, hora, nome):
    alvo = dt.datetime.combine(dt.date.today(), dt.time.fromisoformat(hora))
    if dt.datetime.now() < alvo:
        print(f"esperando até {hora}…"); time.sleep((alvo - dt.datetime.now()).total_seconds())
    saida = ""
    for n in range(1, 13):
        print(f"=== tentativa {n} {dt.datetime.now():%H:%M}")
        saida = claude(prompt)
        if "AINDA_NAO_PUBLICADO" not in saida[-400:]:
            break
        time.sleep(15 * 60)
    fim = saida[-400:]
    if "ATIVADO" in fim:
        msg = f"ManyChat: automação '{nome}' ATIVA no post novo."
    elif "AINDA_NAO_PUBLICADO" in fim:
        msg = f"ManyChat: o post não apareceu em 3 h; '{nome}' segue em rascunho."
    else:
        msg = f"ManyChat: não consegui ativar '{nome}'. Fim do relatório: {fim[-250:]}"
    print(msg); notificar(msg)


def main(a):
    if len(a) < 2:
        print(__doc__); return 2
    acao, arq = a[0], a[1]
    exe = "--executar" in a
    auto = json.loads(Path(arq).read_text(encoding="utf-8"))
    if acao != "story":
        erros = checar(auto)
        if erros:
            print("AUTOMAÇÃO REPROVADA:"); [print("  ✗", e) for e in erros]; return 1
    v = valores(auto)
    if acao == "rascunho":
        p = preencher("rascunho-comentario.txt", v)
    elif acao == "ativar":
        p = preencher("ativar-comentario.txt", v)
    elif acao == "story":
        if not auto.get("resposta_story"):
            raise SystemExit("falta 'resposta_story' (mensagem específica: pergunte o problema, o lugar, peça foto)")
        p = preencher("resposta-story.txt", v)
    else:
        raise SystemExit(f"ação desconhecida: {acao}")
    print(p)
    if not exe:
        return 0
    if acao == "ativar" and "--esperar" in a:
        ativar_esperando(p, a[a.index("--esperar") + 1], auto["nome"])
    else:
        claude(p)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
