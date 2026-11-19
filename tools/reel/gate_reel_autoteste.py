# -*- coding: utf-8 -*-
"""Autoteste do gate_reel: cada regra precisa ser VISTA reprovando ("exit 0 não é prova").

Gera um reel sintético aprovado (1080x1920, 30 fps, imagem em movimento, tom contínuo em −14 LUFS),
confirma que passa e injeta um defeito por regra, exigindo o código certo na saída.

A transcrição (R3, R8) é substituída por uma fala falsa: o que se testa aqui é a regra, não o Whisper.
Para provar a escuta de verdade, use o autoteste do motor (motor/estudio/gate_autoteste.py, F07/F08).

Uso: python -I gate_reel_autoteste.py
"""
import json, subprocess, sys, tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import gate_reel as GR  # noqa: E402

DUR = 6.0
CFG = {
    "marca": {"nome": "Marca Teste", "escritas_erradas": ["Marka Teste"]},
    "pastas_vetadas": ["pasta-vetada"],
    "reel": {"largura": 1080, "altura": 1920, "fps": 30, "folga_fim_fala_s": 0.7, "loudness_lufs": -14,
             "loudness_tolerancia": 1.5, "pico_max_dbtp": -1.0, "upload_max_bytes": 10_000_000,
             "exigir_nome_na_legenda": True},
}
FALA_OK = ([(0.2, "Plantou, pegou bonito e secou.")],
           [(0.2, 0.6, "Plantou,"), (0.7, 1.0, "pegou"), (1.1, 1.5, "bonito"), (1.6, 1.8, "e"), (1.9, DUR - 0.3, "secou.")])


def ff(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, a)], check=True)


def base(dst, dur=DUR, w=1080, h=1920, fps=30, faststart=True, extra_v="", extra_a=""):
    v = f"testsrc2=size={w}x{h}:rate={fps}:duration={dur}" + (f",{extra_v}" if extra_v else "")
    a = f"sine=frequency=440:sample_rate=48000:duration={dur},volume=-6dB" + (f",{extra_a}" if extra_a else "")
    args = ["-f", "lavfi", "-i", v, "-f", "lavfi", "-i", a, "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest"]
    if faststart:
        args += ["-movflags", "+faststart"]
    ff(*args, dst)


def normaliza(src, dst):
    """Leva o tom para −14 LUFS (o alvo da R7) em duas medidas."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-vn", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    import re
    i = float(re.findall(r"I:\s+(-?[0-9.]+) LUFS", r.stderr)[-1])
    ff("-i", src, "-c:v", "copy", "-af", f"volume={-14 - i:.2f}dB", "-c:a", "aac", "-b:a", "128k",
       "-movflags", "+faststart", dst)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    falhas = []
    with tempfile.TemporaryDirectory() as tmp:
        T = Path(tmp)
        bruto = T / "bruto.mp4"; ok = T / "ok.mp4"
        base(bruto); normaliza(bruto, ok)
        (T / "pasta-vetada").mkdir()
        midia_ok = T / "broll-solo.mp4"; midia_ok.write_bytes(b"x")
        midia_vet = T / "pasta-vetada" / "foto-obra.jpg"; midia_vet.write_bytes(b"x")
        fontes = T / "fontes.md"; fontes.write_text("| 1 | broll-solo.mp4 | Pixabay | Pixabay Content License |\n", encoding="utf-8")
        cenas_ok = {"cenas": [{"ini": 0, "tipo": "cam"},
                              {"ini": 2, "tipo": "v", "path": str(midia_ok), "licenca": "Pixabay Content License"}]}
        leg_ok = {"itens": [{"template": "Legenda", "props": {"palavras": [{"t": "Aqui"}, {"t": "na"}, {"t": "Marca"}, {"t": "Teste"}]}},
                            {"template": "Encerramento", "props": {"chamada": "Peça um orçamento"}}]}

        def js(nome, obj):
            p = T / nome; p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8"); return p

        def rodar(final, fala=FALA_OK, cfg=CFG, **kw):
            GR.ouvir = lambda f: fala
            e, *_ = GR.checa(str(final), cfg, **kw)
            return e

        # arquivo de upload feito pelo próprio compressor do repositório (prova ele junto)
        import comprimir_upload
        insta = T / "ok-insta.mp4"
        comprimir_upload.comprimir(ok, insta, 9.5)
        padrao = dict(insta=str(insta), fontes=str(fontes), cenas=str(js("cenas.json", cenas_ok)),
                      legenda=str(js("leg.json", leg_ok)))
        e = rodar(ok, **padrao)
        if e:
            print("Base sintética não passa — o autoteste precisa de uma base aprovada:\n  " + "\n  ".join(e))
            sys.exit(2)
        print("✓ base aprovada")

        def arq(nome, **kw):
            b = T / f"{nome}-bruto.mp4"; p = T / f"{nome}.mp4"
            base(b, **kw); normaliza(b, p); return p

        casos = []
        casos.append(("R1 resolução", lambda: rodar(arq("r1", w=1080, h=1350), **{**padrao, "insta": None}), "R1"))
        casos.append(("R1 fps", lambda: rodar(arq("r1b", fps=25), **{**padrao, "insta": None}), "R1"))

        def r2():
            p = T / "r2.mp4"
            ff("-i", ok, "-i", ok, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "apad=pad_dur=2", "-c:a", "aac", p)
            return rodar(p, **{**padrao, "insta": None})
        casos.append(("R2 áudio maior que vídeo", r2, "R2"))
        casos.append(("R3 vídeo segue 3 s depois da fala",
                      lambda: rodar(ok, fala=(FALA_OK[0], FALA_OK[1][:-1] + [(1.9, DUR - 3.0, "secou.")]), **padrao), "R3"))
        casos.append(("R4 silêncio", lambda: rodar(arq("r4", extra_a="volume=enable='between(t,2,3.6)':volume=0"),
                                                  **{**padrao, "insta": None}), "R4"))

        def r5():
            p = T / "r5.mp4"; b = T / "r5-bruto.mp4"
            ff("-f", "lavfi", "-i", f"testsrc2=size=1080x1920:rate=30:duration={DUR}", "-f", "lavfi", "-i",
               f"sine=frequency=440:sample_rate=48000:duration={DUR},volume=-6dB",
               "-filter_complex", "[0:v]trim=0:2,setpts=PTS-STARTPTS[a];[0:v]trim=2:2.04,setpts=PTS-STARTPTS,"
               "tpad=stop_mode=clone:stop_duration=1.6[b];[0:v]trim=3.64:6,setpts=PTS-STARTPTS[c];[a][b][c]concat=n=3:v=1:a=0[v]",
               "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-shortest", b)
            normaliza(b, p)
            return rodar(p, **{**padrao, "insta": None})
        casos.append(("R5 imagem congelada", r5, "R5"))
        casos.append(("R6 tela preta", lambda: rodar(arq("r6", extra_v="drawbox=c=black:t=fill:enable='between(t,2,3)'"),
                                                    **{**padrao, "insta": None}), "R6"))

        def r7():
            p = T / "r7.mp4"
            ff("-i", ok, "-c:v", "copy", "-af", "volume=-10dB", "-c:a", "aac", p)
            return rodar(p, **{**padrao, "insta": None})
        casos.append(("R7 baixo demais", r7, "R7"))
        casos.append(("R8 bastidor", lambda: rodar(ok, fala=([(1.0, "Plantou. Corta essa parte.")], FALA_OK[1]), **padrao), "R8"))
        casos.append(("R8 tropeço", lambda: rodar(ok, fala=(FALA_OK[0], [(0.2, 0.4, "uma"), (0.5, 0.7, "faixa,"), (0.8, 1.0, "uma"),
                                                                           (1.1, 1.3, "faixa"), (1.4, DUR - 0.3, "ideal.")]), **padrao), "R8"))

        def r9_tam():
            cfg = json.loads(json.dumps(CFG)); cfg["reel"]["upload_max_bytes"] = 1000
            return rodar(ok, cfg=cfg, **padrao)
        casos.append(("R9 maior que o limite", r9_tam, "R9"))

        def r9_fs():
            p = T / "r9-sem-faststart.mp4"
            ff("-i", insta, "-c", "copy", p)  # sem +faststart o moov fica no fim
            return rodar(ok, **{**padrao, "insta": str(p)})
        casos.append(("R9 sem faststart", r9_fs, "R9"))
        casos.append(("R9 duração diferente", lambda: rodar(ok, **{**padrao, "insta": str(arq("r9d", dur=4.0))}), "R9"))
        casos.append(("R10 sem fontes", lambda: rodar(ok, **{**padrao, "fontes": str(T / "nao-existe.md")}), "R10"))
        casos.append(("R10 pasta vetada", lambda: rodar(ok, **{**padrao, "cenas": str(js("c2.json", {"cenas": [
            {"ini": 0, "tipo": "f", "path": str(midia_vet), "propria": True}]}))}), "R10"))
        casos.append(("R10 fora das fontes", lambda: rodar(ok, **{**padrao, "cenas": str(js("c3.json", {"cenas": [
            {"ini": 0, "tipo": "v", "path": str(T / "outro.mp4"), "licenca": "CC0"}]}))}), "R10"))
        casos.append(("R10 sem licença", lambda: rodar(ok, **{**padrao, "cenas": str(js("c4.json", {"cenas": [
            {"ini": 0, "tipo": "v", "path": str(midia_ok)}]}))}), "R10"))
        casos.append(("R11 sem o nome", lambda: rodar(ok, **{**padrao, "legenda": str(js("l2.json", {"itens": [
            {"template": "Legenda", "props": {"palavras": [{"t": "Aqui"}, {"t": "na"}, {"t": "empresa"}]}}]}))}), "R11"))
        casos.append(("R11 nome errado", lambda: rodar(ok, **{**padrao, "legenda": str(js("l3.json", {"itens": [
            {"template": "Legenda", "props": {"palavras": [{"t": "Marca"}, {"t": "Teste"}, {"t": "Marka"}, {"t": "Teste"}]}}]}))}), "R11"))

        for nome, fazer, cod in casos:
            e = fazer()
            ok_ = any(x.startswith(cod + " ") for x in e)
            print(f"{'✓' if ok_ else '✗'} {nome}{'' if ok_ else ' NÃO reprovou: ' + '; '.join(e)[:300]}")
            if not ok_:
                falhas.append(nome)
    if falhas:
        print(f"AUTOTESTE FALHOU: {', '.join(falhas)}"); sys.exit(1)
    print(f"AUTOTESTE OK — {len(casos)} defeitos vistos reprovando.")


if __name__ == "__main__":
    main()
