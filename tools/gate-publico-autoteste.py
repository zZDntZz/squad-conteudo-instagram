# -*- coding: utf-8 -*-
"""Autoteste do gate-publico: cada regra precisa ser VISTA reprovando ("exit 0 não é prova").

Monta um repositório limpo numa pasta temporária, confirma exit 0, e injeta um defeito por caso
(cada um numa cópia nova), exigindo exit 1 com o código certo. Os defeitos são montados por concatenação
para que este arquivo não contenha, ele mesmo, nada que o gate barraria.

Uso: python -I tools/gate-publico-autoteste.py
"""
import shutil, subprocess, sys, tempfile
from pathlib import Path

GATE = Path(__file__).resolve().parent / "gate-publico.py"

LIMPO = {
    "README.md": "# Projeto\n\nTelefone de exemplo: (00) 00000-0000. Contato: alguem@example.com.\n"
                 "Instale em %USERPROFILE%\\projeto ou ~/projeto.\nCor do ffmpeg: color=black@0.45\n"
                 "TermoRestrito pode aparecer aqui.\n",
    "tools/script.py": "import os\nTOKEN = os.environ.get('API_TOKEN')\npassword = '<sua senha>'\n"
                       "token = process.env.TOKEN\nID = '00000000-0000-0000-0000-000000000000'\n",
    "assets/logo.png": b"\x89PNG\r\n\x1a\n" + b"\0" * 100,
    "tools/termos.local.txt": "# lista de teste\nFulano de Tal\nClientevetado\nTermoRestrito | README.md\n",
}


def montar(dest, extra=None, sem_lista=False):
    for rel, cont in {**LIMPO, **(extra or {})}.items():
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        (p.write_bytes if isinstance(cont, bytes) else lambda c: p.write_text(c, encoding="utf-8"))(cont)
    if sem_lista:
        (dest / "tools" / "termos.local.txt").unlink()
    # a lista fica fora do que se publica: num repo sem git, fica fora da raiz
    lista = dest.parent / f"{dest.name}-termos.txt"
    if not sem_lista:
        shutil.move(str(dest / "tools" / "termos.local.txt"), lista)
    return lista


def gate(raiz, lista):
    r = subprocess.run([sys.executable, "-I", str(GATE), "--raiz", str(raiz), "--lista", str(lista)],
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    S = "sk-" + "ant-" + "a1" * 12
    casos = [
        ("G01 chave Anthropic", {"x.py": f"k = '{S}'\n"}, "G01"),
        ("G01 chave sk-", {"x.py": "k = 'sk-" + "Ab3" * 8 + "'\n"}, "G01"),
        ("G01 chave Google", {"x.js": "const k = 'AI" + "za" + "B" * 35 + "'\n"}, "G01"),
        ("G01 token GitHub", {"x.sh": "export T=gh" + "p_" + "x" * 36 + "\n"}, "G01"),
        ("G01 chave privada", {"id": "-----BEGIN " + "OPENSSH PRIVATE KEY-----\nabc\n"}, "G01"),
        ("G01 password=valor", {"x.env.txt": "pass" + "word=Segredo123\n"}, "G01"),
        ("G01 token: valor", {"cfg.json": '{"to' + 'ken": "abcd1234efgh"}\n'}, "G01"),
        ("G02 telefone real", {"a.md": "Chame (6" + "1) 98888-7777\n"}, "G02"),
        ("G02 telefone com DDI", {"a.md": "wa.me/556" + "19888" + "87777\n"}, "G02"),
        ("G03 e-mail real", {"a.md": "fulano" + "@" + "gmail.com\n"}, "G03"),
        ("G04 caminho Windows", {"a.md": "C:" + "\\Users\\fulano\\Desktop\n"}, "G04"),
        ("G04 caminho bash", {"a.sh": "cd /c/" + "Users/fulano/x\n"}, "G04"),
        ("G05 UUID real", {"a.txt": "device " + "3f2a9c41" + "-8b7d-4e21-a6f0-5d9c2e7b1a84\n"}, "G05"),
        ("G05 ID longo", {"a.txt": "pagina " + "1234567" + "890123456\n"}, "G05"),
        ("G06 VDO.Ninja com senha", {"a.md": "https://vdo." + "ninja/?view=x&" + "password=abc\n"}, "G06"),
        ("G07 termo vetado", {"a.md": "Obra do Clientevetado\n"}, "G07"),
        ("G07 termo com acento e caixa", {"a.md": "FULANO DE TÁL esteve aqui\n"}, "G07"),
        ("G07 termo separado por ponto", {"a.md": "fulano.de.tal\n"}, "G07"),
        ("G07 termo restrito fora do lugar", {"tools/b.py": "# TermoRestrito\n"}, "G07"),
        ("G08 preço", {"a.md": "Custa R" + "$ 1.500\n"}, "G08"),
        ("G09 binário grande", {"modelo.bin": b"\0" * (6 * 1024 * 1024)}, "G09"),
        ("G10 vídeo", {"obra.mp4": b"\0" * 100}, "G10"),
        ("G10 foto JPG", {"fotos/obra.jpg": b"\xff\xd8" + b"\0" * 100}, "G10"),
        ("G10 PNG fora de assets", {"fotos/obra.png": b"\x89PNG" + b"\0" * 100}, "G10"),
        ("G10 PDF", {"isca.pdf": b"%PDF-1.4" + b"\0" * 100}, "G10"),
    ]
    falhas = []
    with tempfile.TemporaryDirectory() as tmp:
        T = Path(tmp)
        base = T / "limpo"; lista = montar(base)
        code, out = gate(base, lista)
        if code != 0:
            print("O repositório limpo não passa — autoteste sem base:\n" + out); sys.exit(2)
        print("✓ limpo aprovado")
        # G00: sem lista, o gate não roda pela metade
        d = T / "g00"; montar(d, sem_lista=True)
        code, out = gate(d, T / "nao-existe.txt")
        ok = code == 1 and "G00" in out
        print(f"{'✓' if ok else '✗'} G00 lista ausente"); falhas += [] if ok else ["G00"]
        # G07: a lista dentro do que seria publicado
        d = T / "g07lista"; montar(d)
        (d / "tools" / "termos.local.txt").write_text("Fulano de Tal\n", encoding="utf-8")
        code, out = gate(d, d / "tools" / "termos.local.txt")
        ok = code == 1 and "G07" in out and "lista local" in out
        print(f"{'✓' if ok else '✗'} G07 lista seria publicada"); falhas += [] if ok else ["G07 lista"]
        for i, (nome, extra, cod) in enumerate(casos):
            d = T / f"c{i:02d}"; lst = montar(d, extra)
            code, out = gate(d, lst)
            ok = code == 1 and f"{cod} " in out
            print(f"{'✓' if ok else '✗'} {nome}{'' if ok else ' NÃO reprovou: ' + out[-300:]}")
            if not ok:
                falhas.append(nome)
        # modo git: o que o .gitignore exclui não é publicado; o resto é
        if shutil.which("git"):
            d = T / "git"; lst = montar(d, {".gitignore": "segredo-local.txt\n", "segredo-local.txt": f"k = '{S}'\n"})
            subprocess.run(["git", "init", "-q", str(d)], check=True)
            code, out = gate(d, lst)
            ok = code == 0
            print(f"{'✓' if ok else '✗'} git: arquivo ignorado não conta{'' if ok else ': ' + out[-200:]}")
            falhas += [] if ok else ["git ignorado"]
            (d / "novo.txt").write_text(f"k = '{S}'\n", encoding="utf-8")
            code, out = gate(d, lst)
            ok = code == 1 and "G01 novo.txt" in out
            print(f"{'✓' if ok else '✗'} git: arquivo novo não ignorado conta"); falhas += [] if ok else ["git novo"]
    if falhas:
        print("AUTOTESTE FALHOU:", ", ".join(falhas)); sys.exit(1)
    print(f"AUTOTESTE OK — {len(casos) + 2} defeitos vistos reprovando, base limpa aprovada.")


if __name__ == "__main__":
    main()
