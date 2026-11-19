"""Autoteste do gate: cada regra precisa ser VISTA reprovando.

Copia um projeto aprovado (padrão: projetos/teste-01) para uma pasta temporária,
confirma exit 0 e depois injeta um defeito por regra, exigindo exit 1 com o código certo.
Uso: python gate_autoteste.py [pasta_projeto_aprovado]
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

AQUI = Path(__file__).parent
GATE = AQUI / "gate.py"
BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI.parents[1] / "projetos" / "teste-01"


def gate(modo, p):
    r = subprocess.run([sys.executable, "-I", GATE, modo, p], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout


def copia(tmp, nome):
    d = Path(tmp) / nome / BASE.name   # o gate acha o final pelo nome da pasta
    shutil.copytree(BASE, d, ignore=shutil.ignore_patterns("aroll", "graficos", "*.wav", "aroll.mp4"))
    return d


def plano_com(d, mudar):
    pj = d / "plano.json"
    pl = json.loads(pj.read_text(encoding="utf-8"))
    mudar(pl)
    pj.write_text(json.dumps(pl, ensure_ascii=False), encoding="utf-8")


def ffmpeg(*a):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, a)], check=True)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    falhas = []
    with tempfile.TemporaryDirectory() as tmp:
        d = copia(tmp, "ok")
        for modo in ("plano", "final"):
            code, out = gate(modo, d)
            if code != 0:
                print(f"Base não passa no gate {modo} — o autoteste precisa de uma base aprovada:\n{out}")
                sys.exit(2)
        final = d / "final" / f"{d.name}.mp4"

        def b(i):
            return lambda pl: pl["beats"][i]

        casos_plano = {
            "P01": lambda pl: pl["beats"][0].update(fim=9999),
            "P02": lambda pl: pl["beats"][3].update(ini=15.0),
            "P03": lambda pl: pl["beats"][0].update(template="NaoExiste"),
            "P04": lambda pl: pl["beats"].append({"id": "x", "ini": 34.0, "fim": 36.0, "template": "Grafico",
                                                   "props": {"titulo": "t", "tipo": "linha", "pontos": [{"x": "a", "y": 1}]}}),
            "P05": lambda pl: pl["beats"].append({"id": "x", "ini": 34.0, "fim": 36.0, "template": "Citacao",
                                                   "props": {"texto": "palavra " * 40, "autor": "Fulano"}}),
            "P06": lambda pl: pl["beats"].append({"id": "x", "ini": 34.0, "fim": 36.0, "template": "Print",
                                                   "props": {"imagem": "nao_existe.png", "largura": 10, "altura": 10}}),
            "P07": lambda pl: pl.update(beats=[x for x in pl["beats"] if x.get("modo") == "sobre"]),
            "P08": lambda pl: pl["shorts"][0].update(fim=5.0),
            "P09": lambda pl: pl["beats"][4]["props"].update(texto="TODO trocar"),
            "P10": lambda pl: pl.update(capitulos=[{"ini": 2, "titulo": "A"}, {"ini": 15, "titulo": "B"}, {"ini": 18, "titulo": "C"}]),
        }
        for cod, mudar in casos_plano.items():
            dd = copia(tmp, cod)
            plano_com(dd, mudar)
            code, out = gate("plano", dd)
            ok = code == 1 and cod in out
            print(f"{'✓' if ok else '✗'} {cod} {'reprovou como devia' if ok else 'NÃO reprovou: ' + out[:200]}")
            if not ok:
                falhas.append(cod)

        # P09 não pode acusar o "todo" do português (falso positivo da aula de solo, 13/10).
        dd = copia(tmp, "P09-ok")
        plano_com(dd, lambda pl: pl["beats"][4]["props"].update(texto="Biologia em todo o canteiro"))
        code, out = gate("plano", dd)
        ok = "P09" not in out
        print(f"{'✓' if ok else '✗'} P09-ok {'não acusou o português' if ok else 'ERRADO: ' + out[:200]}")
        if not ok:
            falhas.append("P09-ok")

        # P11 depende do projeto.json: aula com short e sem recorte reprova; com "pilha" não pode acusar P11.
        for nome, pilha in (("P11", None), ("P11-ok", {"camera": [0, 0, 16, 9], "tela": [0, 0, 16, 9]})):
            dd = copia(tmp, nome)
            pj = dd / "projeto.json"
            pr = json.loads(pj.read_text(encoding="utf-8"))
            pr["formato"] = "aula"
            if pilha:
                pr["pilha"] = pilha
            pj.write_text(json.dumps(pr, ensure_ascii=False), encoding="utf-8")
            code, out = gate("plano", dd)
            ok = (code == 1 and "P11" in out) if not pilha else "P11" not in out
            print(f"{'✓' if ok else '✗'} {nome} {'comportou-se como devia' if ok else 'ERRADO: ' + out[:200]}")
            if not ok:
                falhas.append(nome)

        # Defeitos no arquivo final: gerados a partir do próprio final aprovado.
        def f01(f, o): ffmpeg("-i", f, "-vf", "scale=1280:720", "-c:a", "copy", o)
        def f02(f, o): ffmpeg("-i", f, "-t", 20, "-c", "copy", o)
        def f03(f, o): ffmpeg("-i", f, "-c:v", "copy", "-af", "volume=-12dB", o)
        def f04(f, o): ffmpeg("-i", f, "-vf", "drawbox=c=black:t=fill:enable='between(t,20,22)'", "-c:a", "copy", o)
        def f05(f, o): ffmpeg("-i", f, "-c:v", "copy", "-af", "volume=enable='between(t,20,23.5)':volume=0", o)
        # F07: a fala real que foi ao ar ("Corta essa parte.", Parte 09 de um curso) colada em 20 s.
        fala = AQUI / "fixtures" / "fala_corta_essa_parte.wav"
        def f07(f, o): ffmpeg("-i", f, "-i", fala, "-filter_complex",
                              "[1:a]adelay=20000|20000[s];[0:a]volume=enable='between(t,20,23.6)':volume=0[a];"
                              "[a][s]amix=inputs=2:normalize=0:duration=first[m]",
                              "-map", "0:v", "-map", "[m]", "-c:v", "copy", "-c:a", "aac", o)
        # F08: o tropeço real que ficou no ar ("manter uma faixa, uma faixa ideal", aula de vasos) colado em 20 s.
        trop = AQUI / "fixtures" / "fala_uma_faixa_uma_faixa.wav"
        def f08(f, o): ffmpeg("-i", f, "-i", trop, "-filter_complex",
                              "[1:a]adelay=20000|20000[s];[0:a]volume=enable='between(t,20,26)':volume=0[a];"
                              "[a][s]amix=inputs=2:normalize=0:duration=first[m]",
                              "-map", "0:v", "-map", "[m]", "-c:v", "copy", "-c:a", "aac", o)
        casos_final = {"F01": f01, "F02": f02, "F03": f03, "F04": f04, "F05": f05, "F07": f07, "F08": f08}
        # As duas falas não vêm no repositório (é voz de gente). Grave as suas (ver fixtures/README.md).
        # Sem elas o autoteste FALHA: regra que não foi vista reprovando não vale.
        for cod, wav in (("F07", fala), ("F08", trop)):
            if not wav.exists():
                print(f"✗ {cod} fixture ausente: {wav.name} (ver fixtures/README.md)")
                falhas.append(cod)
                casos_final.pop(cod)
        for cod, fazer in casos_final.items():
            dd = copia(tmp, cod)
            alvo = dd / "final" / f"{dd.name}.mp4"
            fazer(final, alvo.with_suffix(".tmp.mp4"))
            alvo.with_suffix(".tmp.mp4").replace(alvo)
            code, out = gate("final", dd)
            ok = code == 1 and cod in out
            print(f"{'✓' if ok else '✗'} {cod} {'reprovou como devia' if ok else 'NÃO reprovou: ' + out[:200]}")
            if not ok:
                falhas.append(cod)
        dd = copia(tmp, "F06")
        s = next((dd / "final").glob("short_*.mp4"))
        ffmpeg("-i", s, "-vf", "scale=1920:1080", "-c:a", "copy", s.with_suffix(".tmp.mp4"))
        s.with_suffix(".tmp.mp4").replace(s)
        code, out = gate("final", dd)
        ok = code == 1 and "F06" in out
        print(f"{'✓' if ok else '✗'} F06 {'reprovou como devia' if ok else 'NÃO reprovou: ' + out[:200]}")
        if not ok:
            falhas.append("F06")
    if falhas:
        print("AUTOTESTE FALHOU:", ", ".join(falhas)); sys.exit(1)
    print("AUTOTESTE OK — todas as regras foram vistas reprovando.")


if __name__ == "__main__":
    main()
