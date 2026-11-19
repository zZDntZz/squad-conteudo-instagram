# -*- coding: utf-8 -*-
"""Monta (e, se pedido, executa) o prompt de agendamento no Meta Business Suite via Claude in Chrome,
DEPOIS de passar nos gates. Sem gate aprovado, não sai prompt.

Uso:
  python -I agendar.py post.json                  # roda os gates e imprime o prompt
  python -I agendar.py post.json --executar       # roda os gates e chama: claude -p --chrome "<prompt>"
  python -I agendar.py --descobrir-navegador [--executar]   # prompt de leitura que lista os Chromes conectados

O deviceId do Chrome vem de --device <id> ou da variável CLAUDE_CHROME_DEVICE_ID. Nunca do post.json
(o arquivo pode acabar num repositório; o deviceId identifica a sua máquina).

post.json (ver skills/instagram-agendar/exemplos/post.exemplo.json):
  tipo: reel | carrossel | story
  perfil: "@suamarca"
  midias: [caminhos]           (reel: 1 vídeo; carrossel: 2–10 imagens; story: 1 por item em "stories")
  legenda, palavraManychat     (reel/carrossel)
  data: "AAAA-MM-DD", hora: "HH:MM", fuso: "America/Sao_Paulo"
  stories: [{"midia": ..., "hora": "HH:MM"}]   (story)
  substituir: {"legenda_inicio": "...", "duracao_antiga": "0:42", "duracao_nova": "0:33"}   (opcional, reel)
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
LIMITE_UPLOAD = 10_400_000   # o upload pelo navegador recusa acima de ~10,4 MB (18/11/2026)


def gates(post, arq_post):
    erros = []
    midias = post.get("midias", []) + [s["midia"] for s in post.get("stories", [])]
    for m in midias:
        p = Path(m)
        if not p.exists():
            erros.append(f"mídia não encontrada: {m}")
        elif p.stat().st_size > LIMITE_UPLOAD:
            erros.append(f"{p.name}: {p.stat().st_size/1e6:.1f} MB — o upload pelo navegador aceita ~10,4 MB; "
                         f"rode tools/reel/comprimir_upload.py")
    if erros:
        return erros
    if post["tipo"] in ("reel", "carrossel"):
        tmp = Path(arq_post).with_suffix(".gate.json")
        tmp.write_text(json.dumps({"midia": post["midias"][0], "legenda": post.get("legenda", ""),
                                   "palavraManychat": post.get("palavraManychat")}, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(["node", str(RAIZ / "tools" / "post" / "gate-post-insta.cjs"), str(tmp)],
                           capture_output=True, text=True, encoding="utf-8")
        tmp.unlink(missing_ok=True)
        print(r.stdout + r.stderr, end="")
        if r.returncode:
            erros.append("gate da legenda reprovou")
    if post["tipo"] == "reel":
        v = post["midias"][0]
        r = subprocess.run([sys.executable, "-I", str(RAIZ / "tools" / "reel" / "gate_reel.py"), v, "--insta", v],
                           capture_output=True, text=True, encoding="utf-8")
        print(r.stdout[-2500:], end="")
        if r.returncode:
            erros.append("gate do reel reprovou")
    return erros


def preencher(nome, valores):
    t = (AQUI / "prompts" / nome).read_text(encoding="utf-8")
    for k, v in valores.items():
        t = t.replace("{{" + k + "}}", str(v))
    if "{{" in t:
        raise SystemExit(f"campo sem valor no prompt {nome}: {t[t.index('{{'):t.index('{{') + 40]}")
    return t


def prompt_do_post(post, device):
    base = dict(DEVICE=device, PERFIL=post["perfil"], DATA=post.get("data", ""), HORA=post.get("hora", ""),
                FUSO=post.get("fuso", "America/Sao_Paulo"))
    if post["tipo"] == "reel":
        base.update(MIDIA=post["midias"][0], LEGENDA=post["legenda"])
        if post.get("substituir"):
            s = post["substituir"]
            base.update(LEGENDA_INICIO=s["legenda_inicio"], DURACAO_ANTIGA=s["duracao_antiga"], DURACAO_NOVA=s["duracao_nova"])
            return preencher("reagendar-reel.txt", base)
        return preencher("agendar-reel.txt", base)
    if post["tipo"] == "carrossel":
        base.update(MIDIAS="\n".join(f"   {i+1}. {m}" for i, m in enumerate(post["midias"])), LEGENDA=post["legenda"])
        return preencher("agendar-carrossel.txt", base)
    if post["tipo"] == "story":
        base.update(LISTA="\n".join(f"- {post['data']} {s['hora']} → {s['midia']}" for s in post["stories"]))
        return preencher("agendar-stories.txt", base)
    raise SystemExit(f"tipo desconhecido: {post['tipo']}")


def executar(prompt):
    if not shutil.which("claude"):
        raise SystemExit("claude CLI não encontrado no PATH")
    # Sem --permission-mode: o Claude Code pede permissão como de costume. Para rodar sem supervisão,
    # acrescente o modo que você aceitar, sabendo que ele vai operar o navegador logado na sua conta.
    r = subprocess.run(["claude", "-p", "--chrome", prompt], text=True, encoding="utf-8")
    return r.returncode


def main(a):
    device = None
    if "--device" in a:
        k = a.index("--device"); device = a[k + 1]; del a[k:k + 2]
    device = device or os.environ.get("CLAUDE_CHROME_DEVICE_ID")
    exe = "--executar" in a
    a = [x for x in a if x != "--executar"]
    if "--descobrir-navegador" in a:
        p = (AQUI / "prompts" / "descobrir-navegador.txt").read_text(encoding="utf-8")
        print(p)
        return executar(p) if exe else 0
    if not a:
        print(__doc__); return 2
    post = json.loads(Path(a[0]).read_text(encoding="utf-8"))
    if "deviceId" in json.dumps(post):
        raise SystemExit("tire o deviceId do post.json (use --device ou CLAUDE_CHROME_DEVICE_ID)")
    if not device:
        raise SystemExit("sem deviceId: rode --descobrir-navegador e passe --device <id> ou CLAUDE_CHROME_DEVICE_ID")
    erros = gates(post, a[0])
    if erros:
        print("NÃO AGENDAR:"); [print("  ✗", e) for e in erros]
        return 1
    prompt = prompt_do_post(post, device)
    print("\n---- prompt ----\n" + prompt)
    return executar(prompt) if exe else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
