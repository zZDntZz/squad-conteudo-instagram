# -*- coding: utf-8 -*-
"""Gate de reel vertical (Instagram). Nada é agendado sem exit 0.

Nasceu dos defeitos de um reel real (18/11/2026): a fala acabava em 32,9 s e o vídeo ia até 42,4 s
(boca mexendo sem som), cenas com imagem parada, e a legenda com o nome da marca escrito como o
Whisper ouviu. Depois, o upload pelo navegador recusou o arquivo de 72 MB (limite ~10,4 MB).

Uso:
  python -I gate_reel.py <final.mp4> [--insta <arquivo-de-upload.mp4>] [--cenas cenas.json]
                         [--fontes fontes.md] [--legenda plano_render.json] [--catalogo catalogo.json]
                         [--config config.json]

Saída 0 = pode ir; 1 = não pode (diz o que quebrou e onde).

Regras:
  R1  formato 1080x1920, 30 fps
  R2  áudio e vídeo com a mesma duração
  R3  o vídeo termina até `folga_fim_fala_s` depois da última palavra (+ tolerância do Whisper)
  R4  silêncio de 1 s ou mais (fim ou meio)
  R5  imagem congelada por 1 s ou mais (foto sem Ken Burns, cena parada)
  R6  tela preta
  R7  loudness (−14 LUFS ±1,5) e pico (≤ −1 dBTP)
  R8  fala de bastidor ("corta essa parte") e tropeço ("uma, uma") — regras do motor do estúdio
  R9  arquivo de upload: abaixo do limite, com +faststart, mesma duração e formato do final
  R10 toda mídia listada no arquivo de fontes; nenhuma de pasta vetada; mídia de terceiro com licença
  R11 nome da marca escrito certo na legenda (e presente, se `exigir_nome_na_legenda`)
"""
import json, re, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "motor" / "estudio"))
import gate as G  # noqa: E402  BASTIDOR e _repeticoes do gate do estúdio

TOLERANCIA_WHISPER = 0.2  # o fim de palavra do Whisper erra ~0,1–0,2 s


def carregar_config(arq=None):
    cand = [Path(arq)] if arq else [RAIZ / "config.json", RAIZ / "config.exemplo.json"]
    for c in cand:
        if c.exists():
            if not arq and c.name == "config.exemplo.json":
                print("aviso: usando config.exemplo.json (crie o seu config.json)", file=sys.stderr)
            return json.loads(c.read_text(encoding="utf-8"))
    raise SystemExit(f"config não encontrado: {cand}")


def run(a):
    return subprocess.run([str(x) for x in a], capture_output=True, text=True, encoding="utf-8", errors="ignore")


def streams(f):
    j = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,duration",
                        "-show_entries", "format=duration", "-of", "json", f]).stdout or "{}")
    v = next((s for s in j.get("streams", []) if s["codec_type"] == "video"), {})
    a = next((s for s in j.get("streams", []) if s["codec_type"] == "audio"), {})
    return v, a, float(j.get("format", {}).get("duration", 0))


def ouvir(f):
    """Transcrição literal (sem VAD): frases [(ini, texto)] e palavras [(ini, fim, texto)]."""
    import glob, os, site
    for sp in site.getsitepackages():
        for d in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
    from faster_whisper import WhisperModel
    try:
        m = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")
    except Exception:
        m = WhisperModel("small", device="cpu", compute_type="int8")
    segs = list(m.transcribe(str(f), language="pt", vad_filter=False, word_timestamps=True, beam_size=5,
                             condition_on_previous_text=False, initial_prompt=G.PROMPT_LITERAL)[0])
    frases = [(s.start, s.text.strip()) for s in segs]
    palavras = [(w.start, w.end, w.word.strip()) for s in segs for w in (s.words or []) if w.word.strip()]
    return frases, palavras


def checa(final, cfg, insta=None, fontes=None, cenas=None, legenda=None, catalogo=None):
    rc = cfg.get("reel", {})
    W, H, FPS = rc.get("largura", 1080), rc.get("altura", 1920), rc.get("fps", 30)
    e = []
    nome = Path(final).name
    v, a, dur = streams(final)
    # R1
    if (v.get("width"), v.get("height")) != (W, H):
        e.append(f"R1 {nome}: {v.get('width')}x{v.get('height')} (esperado {W}x{H})")
    n, d = (v.get("r_frame_rate") or "0/1").split("/")
    fps = float(n) / float(d or 1)
    if abs(fps - FPS) > 0.01:
        e.append(f"R1 {nome}: {fps:.2f} fps (esperado {FPS})")
    # R2
    if not a:
        e.append(f"R2 {nome}: sem faixa de áudio")
    elif abs(float(v.get("duration", 0)) - float(a.get("duration", 0))) > 0.06:
        e.append(f"R2 {nome}: vídeo {float(v['duration']):.2f}s ≠ áudio {float(a['duration']):.2f}s")
    # R3
    frases, palavras = ouvir(final)
    fim_fala = palavras[-1][1] if palavras else 0.0
    folga = dur - fim_fala
    lim = rc.get("folga_fim_fala_s", 0.7) + TOLERANCIA_WHISPER
    if folga > lim:
        e.append(f"R3 {nome}: última palavra em {fim_fala:.2f}s e o vídeo vai até {dur:.2f}s ({folga:.2f}s sem fala; máx. {lim:.1f}s)")
    # R4
    r = run(["ffmpeg", "-hide_banner", "-i", final, "-vn", "-af", "silencedetect=n=-45dB:d=1", "-f", "null", "-"])
    for s in re.findall(r"silence_start: (-?[0-9.]+)", r.stderr):
        e.append(f"R4 {nome}: silêncio de 1s+ começando em {max(0.0, float(s)):.2f}s")
    # R5
    r = run(["ffmpeg", "-hide_banner", "-i", final, "-an", "-vf", "freezedetect=n=-60dB:d=1", "-f", "null", "-"])
    for s in re.findall(r"freeze_start: ([0-9.]+)", r.stderr):
        e.append(f"R5 {nome}: imagem congelada 1s+ a partir de {float(s):.2f}s")
    # R6
    r = run(["ffmpeg", "-hide_banner", "-i", final, "-an", "-vf", "blackdetect=d=0.3:pix_th=0.06", "-f", "null", "-"])
    for s in re.findall(r"black_start:([0-9.]+)", r.stderr):
        e.append(f"R6 {nome}: tela preta em {float(s):.2f}s")
    # R7
    alvo, tol, pico = rc.get("loudness_lufs", -14), rc.get("loudness_tolerancia", 1.5), rc.get("pico_max_dbtp", -1.0)
    r = run(["ffmpeg", "-hide_banner", "-i", final, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
    i = re.findall(r"I:\s+(-?[0-9.]+) LUFS", r.stderr)
    tp = re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", r.stderr)
    if not i or abs(float(i[-1]) - alvo) > tol:
        e.append(f"R7 {nome}: loudness {i[-1] if i else '?'} LUFS (alvo {alvo} ±{tol})")
    if tp and float(tp[-1]) > pico + 0.1:
        e.append(f"R7 {nome}: pico {tp[-1]} dBTP (máx. {pico})")
    # R8
    for t, seg in frases:
        frase = next((x for x in re.split(r"(?<=[.!?])\s+", seg) if G.BASTIDOR.search(x)), None)
        if frase:
            e.append(f"R8 {nome}: fala de bastidor em {t:.1f}s: \"{frase}\"")
    for t, tx in G._repeticoes([(p[0], p[2]) for p in palavras]):
        e.append(f"R8 {nome}: tropeço em {t:.1f}s: \"{tx}\"")
    # R9
    if insta:
        ni = Path(insta).name
        limite = rc.get("upload_max_bytes", 10_000_000)
        tam = Path(insta).stat().st_size
        if tam >= limite:
            e.append(f"R9 {ni}: {tam/1e6:.2f} MB (limite {limite/1e6:.1f} MB do upload pelo navegador)")
        head = open(insta, "rb").read(200_000)
        moov, mdat = head.find(b"moov"), head.find(b"mdat")
        if moov < 0 or (mdat >= 0 and moov > mdat):
            e.append(f"R9 {ni}: sem +faststart (moov depois do mdat)")
        vi, ai, di = streams(insta)
        if (vi.get("width"), vi.get("height")) != (W, H) or abs(di - dur) > 0.1:
            e.append(f"R9 {ni}: {vi.get('width')}x{vi.get('height')} {di:.2f}s (final {dur:.2f}s)")
        if ai and abs(float(vi.get("duration", 0)) - float(ai.get("duration", 0))) > 0.06:
            e.append(f"R9 {ni}: vídeo {vi['duration']} ≠ áudio {ai['duration']}")
    # R10
    if cenas:
        cfg_c = json.loads(Path(cenas).read_text(encoding="utf-8"))
        md = Path(fontes).read_text(encoding="utf-8") if fontes and Path(fontes).exists() else ""
        if not md:
            e.append("R10 arquivo de fontes ausente (toda mídia precisa de origem e licença registradas)")
        cat = json.loads(Path(catalogo).read_text(encoding="utf-8")) if catalogo else {}
        vetadas = [x.lower() for x in cfg.get("pastas_vetadas", [])]
        for c in cfg_c["cenas"]:
            if c["tipo"] in ("cam", "card"):
                continue
            p = c.get("path") or (cat.get(c.get("id"), {}) or {}).get("caminho")
            if not p:
                e.append(f"R10 cena {c['ini']}s: sem caminho (nem 'path' nem id no catálogo)")
                continue
            if any(x in p.lower() for x in vetadas):
                e.append(f"R10 cena {c['ini']}s usa pasta vetada: {Path(p).parent.name}/{Path(p).name}")
            if md and Path(p).name not in md:
                e.append(f"R10 {Path(p).name} (cena {c['ini']}s) não está no arquivo de fontes")
            if not c.get("propria") and not c.get("licenca"):
                e.append(f"R10 {Path(p).name} (cena {c['ini']}s): sem licença registrada (mídia sua? marque \"propria\": true)")
    # R11
    if legenda:
        # Só o que vai para a tela: palavras da Legenda e os textos do card. O marca.json embutido no plano
        # traz a tabela de correções com os erros de propósito (falso positivo na 1ª execução, 18/11).
        itens = json.loads(Path(legenda).read_text(encoding="utf-8"))["itens"]
        txt = " ".join(p["t"] for it in itens if it["template"] == "Legenda" for p in it["props"].get("palavras", []))
        txt += " " + " ".join(str(it["props"].get(k, "")) for it in itens for k in ("chamada", "titulo", "tagline"))
        marca = cfg.get("marca", {})
        if rc.get("exigir_nome_na_legenda") and marca.get("nome") and marca["nome"].lower() not in txt.lower():
            e.append(f"R11 a legenda não escreve '{marca['nome']}' (o nome é falado no vídeo?)")
        for errado in marca.get("escritas_erradas", []):
            if errado.lower() in txt.lower():
                e.append(f"R11 legenda com '{errado}' (é '{marca.get('nome')}')")
    texto = " ".join(s for _, s in frases)
    return e, fim_fala, dur, texto


def main(argv):
    def opt(k):
        return argv[argv.index(k) + 1] if k in argv else None
    if not argv or argv[0].startswith("--"):
        print(__doc__)
        return 2
    cfg = carregar_config(opt("--config"))
    erros, fim_fala, dur, texto = checa(argv[0], cfg, opt("--insta"), opt("--fontes"), opt("--cenas"),
                                        opt("--legenda"), opt("--catalogo"))
    print(f"fala ouvida: {texto}\núltima palavra termina em {fim_fala:.2f}s · vídeo {dur:.2f}s")
    if erros:
        print(f"GATE REEL REPROVADO — {len(erros)} problema(s):")
        for x in erros:
            print("  ✗", x)
        return 1
    print("GATE REEL APROVADO")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
