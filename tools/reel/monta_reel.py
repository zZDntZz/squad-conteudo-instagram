# -*- coding: utf-8 -*-
"""Reel vertical montado SOBRE a gravação original (fala e câmera em sincronia), com B-roll por frase.

Cada processo falado ganha a imagem dele ("descompacta" → enxada abrindo o solo; "cobre o solo" →
palhada). Foto entra com Ken Burns (nunca parada), vídeo com push-in leve, horizontal com fundo
desfocado. A legenda karaokê e o card final saem do motor de grafismos (motor/graficos).

Uso: python -I monta_reel.py <projeto-reel.json> <etapa> [índices de cena...]
  etapas: transcrever | cenas | graficos | final | insta | folha | fontes | tudo
  (tudo = cenas → graficos → final → insta → folha → fontes; o gate vem depois, à parte)

projeto-reel.json (ver skills/reel-com-broll-por-fala/exemplos/projeto-reel.exemplo.json):
  nome, gravacao, saida, marca (pasta em motor/marcas), musica (pasta de trilhas licenciadas ou null),
  gancho, chamada, cenas (cenas.json), transcricao (gerada por `transcrever`), catalogo (opcional),
  trocas_legenda (opcional): [{"de": "Está", "para": "Tá", "entre": [10, 11]}]
As pastas vetadas e as escritas erradas do nome da marca vêm do config.json da raiz do repositório.
"""
import json, os, re, subprocess, sys, zlib
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
W, H, FPS = 1080, 1920, 30
GANCHO_DUR = 3.4
CADEIA_AUDIO = ("aresample=48000,highpass=f=90,afftdn=nr=12:nf=-30,adeclick,"
                "acompressor=threshold=-18dB:ratio=3:attack=8:release=180,"
                "loudnorm=I=-12.6:TP=-1.5:LRA=9")


def carregar(arq_proj):
    P = json.loads(Path(arq_proj).read_text(encoding="utf-8"))
    base = Path(arq_proj).resolve().parent
    rel = lambda k: (base / P[k]).resolve() if P.get(k) else None  # noqa: E731
    cfg_p = RAIZ / "config.json"
    cfg = json.loads((cfg_p if cfg_p.exists() else RAIZ / "config.exemplo.json").read_text(encoding="utf-8"))
    ctx = dict(P=P, cfg=cfg, base=base,
               GRAV=Path(P["gravacao"]) if Path(P["gravacao"]).is_absolute() else rel("gravacao"),
               OUT=rel("saida"), CENAS=rel("cenas"), TRANSC=rel("transcricao"),
               MUSICA=rel("musica"), CAT=rel("catalogo"),
               MARCA_DIR=RAIZ / "motor" / "marcas" / P.get("marca", "exemplo"))
    ctx["OUT"].mkdir(parents=True, exist_ok=True)
    ctx["WORK"] = ctx["OUT"] / "_trabalho"; ctx["WORK"].mkdir(exist_ok=True)
    ctx["PROJ"] = ctx["WORK"] / "grafismos"; (ctx["PROJ"] / "assets").mkdir(parents=True, exist_ok=True)
    ctx["MARCA"] = json.loads((ctx["MARCA_DIR"] / "marca.json").read_text(encoding="utf-8"))
    ctx["VETO"] = tuple(x.lower() for x in cfg.get("pastas_vetadas", []))
    return ctx


def sh(a, quiet=False):
    r = subprocess.run([str(x) for x in a], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode and not quiet:
        print("ERRO:", (r.stderr or "")[-900:])
    return r


def cfg_cenas(ctx):
    return json.loads(ctx["CENAS"].read_text(encoding="utf-8"))


def caminho(ctx, c):
    if c.get("path"):
        p = Path(c["path"])
        return p if p.is_absolute() else (ctx["base"] / p).resolve()
    cat = json.loads(ctx["CAT"].read_text(encoding="utf-8"))
    return Path(cat[c["id"]]["caminho"])


def probe(p):
    r = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=width,height:stream_side_data=rotation", "-of", "json", p])
    st = json.loads(r.stdout)["streams"][0]
    w, h = int(st["width"]), int(st["height"])
    rot = next((int(sd["rotation"]) for sd in st.get("side_data_list", []) if "rotation" in sd), 0)
    return (h, w) if abs(rot) in (90, 270) else (w, h)


def medir(src, ss, foto):
    a = ["ffmpeg", "-v", "error"] + (["-i", src, "-frames:v", "1"] if foto else ["-ss", f"{ss}", "-t", "1.2", "-i", src])
    a += ["-vf", "scale=320:-2,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"]
    v = [float(l.split("=")[1]) for l in (sh(a, True).stderr or "").splitlines() if "YAVG=" in l]
    return sum(v) / len(v) if v else 120.0


def grade(y):
    """Correção neutra pela exposição medida (YAVG). Medir foto também, senão sai escura."""
    if y > 165:   eq = "eq=brightness=-0.07:contrast=1.10:gamma=0.90:saturation=1.08"
    elif y > 140: eq = "eq=brightness=-0.03:contrast=1.08:gamma=0.96:saturation=1.10"
    elif y < 75:  eq = "eq=brightness=0.10:contrast=1.06:gamma=1.22:saturation=1.08"
    elif y < 100: eq = "eq=brightness=0.05:contrast=1.07:gamma=1.10:saturation=1.10"
    else:         eq = "eq=contrast=1.07:gamma=1.02:saturation=1.10"
    return eq + ",vibrance=intensity=0.06,unsharp=3:3:0.35:3:3:0.0"


def faixas(ctx):
    C = cfg_cenas(ctx)
    cs, fim_total = C["cenas"], C["fim"]
    out = []
    for i, c in enumerate(cs):
        fim = cs[i + 1]["ini"] if i + 1 < len(cs) else fim_total
        f0, f1 = round(c["ini"] * FPS), round(fim * FPS)
        out.append({**c, "f0": f0, "nf": f1 - f0, "fim": fim})
    return out


def render_cena(ctx, i, c):
    out = ctx["WORK"] / f"cena{i:02d}.mp4"
    nf = c["nf"]; dur = nf / FPS
    if c["tipo"] == "card":
        return None
    if c["tipo"] == "cam":
        src, ss = ctx["GRAV"], c["ini"]
        # câmera: mesmo instante da fala (sincronia labial), push-in leve
        z = "zoompan=z='min(zoom+0.0006,1.06)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
        vf = f"scale=1296:2304,setsar=1,fps=30,{z},{grade(medir(src, ss, False))}"
        a = ["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.3f}", "-i", src]
    else:
        src = caminho(ctx, c)
        if any(v in str(src).lower() for v in ctx["VETO"]):
            raise SystemExit(f"pasta vetada na cena {c['ini']}s: {src.parent.name}/{src.name}")
        foto = c["tipo"] == "f"
        y = medir(src, c.get("ss", 0), foto)
        if foto:  # Ken Burns alternando entrada e saída: nenhuma foto fica parada
            zi = "z='min(zoom+0.0016,1.20)'" if i % 2 == 0 else "z='if(eq(on,1),1.20,max(zoom-0.0016,1.0))'"
            vf = (f"scale={W*3//2}:{H*3//2}:force_original_aspect_ratio=increase,crop={W*3//2}:{H*3//2},"
                  f"zoompan={zi}:d={nf}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},setsar=1,{grade(y)}")
            a = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", src]
        else:
            w, h = probe(src)
            z = ("zoompan=z='min(zoom+0.0009,1.10)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                 f"s={W}x{H}:fps={FPS}")
            if w > h and h < 1800:   # horizontal 1080p: fundo desfocado + 4:5 por cima (nunca tarja preta)
                alt = int(W * 5 / 4)
                vf = (f"fps={FPS},split[bg][fg];[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                      f"boxblur=30:2,eq=brightness=-0.12[b];[fg]scale={W}:{alt}:force_original_aspect_ratio=increase,"
                      f"crop={W}:{alt}[f];[b][f]overlay=(W-w)/2:(H-h)/2,setsar=1,{z},{grade(y)}")
            else:
                vf = (f"fps={FPS},scale={int(W*1.2)}:{int(H*1.2)}:force_original_aspect_ratio=increase,"
                      f"crop={int(W*1.2)}:{int(H*1.2)},setsar=1,{z},{grade(y)}")
            a = ["ffmpeg", "-v", "error", "-y", "-ss", f"{c.get('ss', 0):.3f}", "-i", src]
    a += ["-an", "-vf", vf + ",format=yuv420p", "-frames:v", str(nf), "-r", str(FPS),
          "-c:v", "libx264", "-preset", "fast", "-crf", "14", out]
    sh(a)
    r = sh(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
            "stream=nb_read_frames", "-of", "csv=p=0", out])
    got = int(((r.stdout or "0").strip().split(",")[0]) or 0)
    print(f"cena {i:02d} {c['ini']:6.2f}-{c['fim']:6.2f} ({dur:.2f}s) {c.get('id', ''):10s} frames {got}/{nf} {'' if got == nf else 'FALTANDO'}")
    return out


def transcrever(ctx):
    """Palavras com tempo (faster-whisper, word_timestamps). Corrija o JSON à mão antes de queimar a legenda."""
    import glob, site
    for sp in site.getsitepackages():
        for d in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
            os.add_dll_directory(d); os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
    from faster_whisper import WhisperModel
    try:
        m = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")
    except Exception:
        m = WhisperModel("small", device="cpu", compute_type="int8")
    nome = ctx["cfg"].get("marca", {}).get("nome", "")
    segs = list(m.transcribe(str(ctx["GRAV"]), language="pt", vad_filter=True, word_timestamps=True, beam_size=5,
                             initial_prompt=nome or None)[0])
    pal = [{"p": w.word.strip(), "ini": round(w.start, 3), "fim": round(w.end, 3)} for s in segs for w in s.words or []]
    ctx["TRANSC"].write_text(json.dumps({"texto": " ".join(s.text.strip() for s in segs), "palavras": pal},
                                        ensure_ascii=False, indent=1), encoding="utf-8")
    print("transcrição:", ctx["TRANSC"], "·", len(pal), "palavras · última termina em", pal[-1]["fim"] if pal else "-")


def palavras_legenda(ctx):
    T = json.loads(ctx["TRANSC"].read_text(encoding="utf-8"))
    marca = ctx["cfg"].get("marca", {})
    erradas = marca.get("escritas_erradas", []) + list(ctx["MARCA"].get("correcoes", {}).keys())
    trocas = ctx["P"].get("trocas_legenda", [])
    out = []
    for p in T["palavras"]:
        t = p["p"]
        for e in erradas:  # nome da marca como o Whisper ouviu → nome certo
            certo = ctx["MARCA"].get("correcoes", {}).get(e) or marca.get("nome", "")
            t = re.sub(re.escape(e), certo, t, flags=re.I) if certo else t
        for tr in trocas:
            a, b = tr.get("entre", [0, 1e9])
            if t == tr["de"] and a <= p["ini"] <= b:
                t = tr["para"]
        out.append({"t": t, "ini": round(p["ini"], 3), "fim": round(p["fim"], 3)})
    return out


def graficos(ctx):
    C = cfg_cenas(ctx); FIM, CARD_INI = C["fim"], C["card_ini"]
    M = ctx["MARCA"]
    logo = ctx["MARCA_DIR"] / (M.get("logo") or "logo.png")
    if logo.exists():
        (ctx["PROJ"] / "assets" / "logo.png").write_bytes(logo.read_bytes())
    m = json.loads(json.dumps(M)); m["cores"]["destaque"] = ctx["P"].get("cor_karaoke", "#FFD400")
    pal = [p for p in palavras_legenda(ctx) if p["ini"] < CARD_INI]
    print("legenda:", " ".join(p["t"] for p in pal))
    itens = [
        {"id": "leg", "template": "Legenda", "alfa": True, "ini": 0, "fim": CARD_INI,
         "props": {"vertical": True, "duracao": round(CARD_INI, 2), "marca": m, "palavras": pal, "baixo": 520}},
        {"id": "enc", "template": "Encerramento", "alfa": False, "ini": 0, "fim": round(FIM - CARD_INI, 2),
         "props": {"vertical": True, "duracao": round(FIM - CARD_INI + 0.05, 2), "marca": M,
                   "logo": "logo.png" if logo.exists() else None, "tagline": M.get("tagline", ""),
                   "chamada": ctx["P"].get("chamada", "")}},
    ]
    (ctx["PROJ"] / "trabalho").mkdir(parents=True, exist_ok=True)
    (ctx["PROJ"] / "trabalho" / "plano_render.json").write_text(json.dumps({"itens": itens}, ensure_ascii=False, indent=1),
                                                                encoding="utf-8")
    g = RAIZ / "motor" / "graficos"
    r = subprocess.run(["node", str(g / "render.mjs"), str(ctx["PROJ"])], cwd=str(g),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-800:], r.stderr[-800:])


def saida(ctx, id_):
    pr = json.loads((ctx["PROJ"] / "trabalho" / "plano_render.json").read_text(encoding="utf-8"))
    return next(i["saida"] for i in pr["itens"] if i["id"] == id_)


def final(ctx):
    C = cfg_cenas(ctx); FIM, CARD_INI = C["fim"], C["card_ini"]
    fx = faixas(ctx)
    W_ = ctx["WORK"]
    partes = [W_ / f"cena{i:02d}.mp4" for i, c in enumerate(fx) if c["tipo"] != "card"]
    partes.append(Path(saida(ctx, "enc")))
    leg = saida(ctx, "leg")
    nf_card = fx[-1]["nf"]
    ins = []
    for p in partes:
        ins += ["-i", p]
    k = len(partes)
    fc = "".join(f"[{j}:v]setpts=PTS-STARTPTS,fps={FPS},format=yuv420p,scale={W}:{H},setsar=1[c{j}];" for j in range(k - 1))
    fc += f"[{k-1}:v]setpts=PTS-STARTPTS,fps={FPS},trim=end_frame={nf_card},format=yuv420p,setsar=1[c{k-1}];"
    fc += "".join(f"[c{j}]" for j in range(k)) + f"concat=n={k}:v=1:a=0[base]"
    # gancho tipográfico nos primeiros segundos (fonte em motor/graficos ou do sistema)
    gancho = ctx["P"].get("gancho", "")
    if gancho:
        (W_ / "gancho.txt").write_text(gancho, encoding="utf-8")
        alpha = f"if(lt(t,0.3),t/0.3,if(lt(t,{GANCHO_DUR-0.4}),1,max(0,({GANCHO_DUR}-t)/0.4)))"
        maior = max(len(l) for l in gancho.split("\n"))
        corpo = int(min(96, 960 / (0.5 * maior)))
        fonte = ctx["P"].get("fonte_gancho", "arialbd.ttf")
        g = (f"drawtext=textfile=gancho.txt:fontfile='{fonte}':fontsize={corpo}:fontcolor=white:borderw=9:"
             f"bordercolor=black:line_spacing=6:text_align=center:x=(w-text_w)/2:y=h*0.13:alpha='{alpha}':enable='lt(t,{GANCHO_DUR})'")
    else:
        g = "null"
    ins += ["-i", leg]; kl = k
    fc += f";[{kl}:v]format=yuva420p[leg];[base][leg]overlay=eof_action=pass:enable='lt(t,{CARD_INI:.3f})'[v1];[v1]{g},format=yuv420p[v]"
    # áudio: a própria gravação, 0 → FIM, tratada + trilha licenciada com ducking pela voz
    ka = kl + 1
    ins += ["-i", ctx["GRAV"]]
    trilha = sorted(ctx["MUSICA"].glob("*.mp3")) if ctx["MUSICA"] and ctx["MUSICA"].exists() else []
    tr = trilha[zlib.crc32(ctx["P"]["nome"].encode()) % len(trilha)] if trilha else None
    fc += f";[{ka}:a]atrim=0:{FIM},asetpts=PTS-STARTPTS,{CADEIA_AUDIO},apad=whole_dur={FIM},atrim=0:{FIM}"
    if tr:
        km = ka + 1
        ins += ["-stream_loop", "-1", "-i", tr]
        fc += (f",asplit=2[voz][sc];[{km}:a]aresample=48000,loudnorm=I=-23:TP=-6:LRA=11,atrim=0:{FIM},"
               f"afade=t=in:st=0:d=1.5,afade=t=out:st={FIM-1.2:.2f}:d=1.2[mus];"
               f"[mus][sc]sidechaincompress=threshold=0.02:ratio=8:attack=30:release=450:makeup=1[musd];"
               f"[voz][musd]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.75:attack=2:release=50:level=false,atrim=0:{FIM}[a]")
        print("trilha:", tr.name)
    else:
        fc += "[a]"
        print("sem trilha (pasta de música vazia ou ausente)")
    dst = ctx["OUT"] / f"{ctx['P']['nome']}.mp4"
    (W_ / "fc.txt").write_text(fc, encoding="utf-8")
    os.chdir(W_)
    sh(["ffmpeg", "-v", "error", "-y"] + ins + ["-/filter_complex", "fc.txt", "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-r", FPS,
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
        "-frames:v", round(FIM * FPS), "-t", f"{FIM:.3f}", dst])
    print("final:", dst, f"{dst.stat().st_size / 1e6:.1f} MB")
    return tr


def insta(ctx):
    sys.path.insert(0, str(AQUI))
    import comprimir_upload
    src = ctx["OUT"] / f"{ctx['P']['nome']}.mp4"
    comprimir_upload.comprimir(src, ctx["OUT"] / f"{ctx['P']['nome']}-insta.mp4", 9.5)


def folha(ctx):
    """Folha de contato com um quadro por cena: o QC olha a imagem, não o exit 0."""
    from PIL import Image, ImageDraw, ImageFont
    fx = faixas(ctx)
    src = ctx["OUT"] / f"{ctx['P']['nome']}.mp4"
    try:
        F = ImageFont.truetype("arialbd.ttf", 22)
    except OSError:
        F = ImageFont.load_default()
    th = []
    for i, c in enumerate(fx):
        t = c["ini"] + min(0.6, (c["fim"] - c["ini"]) / 2) if c["tipo"] != "card" else c["fim"] - 0.4
        q = ctx["WORK"] / f"q{i:02d}.png"
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1", "-vf", "scale=270:480", q])
        th.append((q, f"{i+1:02d} {c['ini']:.1f}s {c.get('id', c['tipo'])}"))
    cols = 6; rows = (len(th) + cols - 1) // cols
    T = Image.new("RGB", (cols * 280, rows * 520), "white"); d = ImageDraw.Draw(T)
    for j, (q, lab) in enumerate(th):
        x, y = (j % cols) * 280 + 5, (j // cols) * 520
        T.paste(Image.open(q), (x, y + 32)); d.text((x, y + 4), lab, fill="black", font=F)
    dst = ctx["OUT"] / f"{ctx['P']['nome']}-folha.jpg"
    T.save(dst, quality=85); print("folha:", dst)


def fontes(ctx):
    """Arquivo de fontes: de onde veio cada imagem, com licença. O gate R10 confere contra ele."""
    C = cfg_cenas(ctx); fx = faixas(ctx)
    cat = json.loads(ctx["CAT"].read_text(encoding="utf-8")) if ctx["CAT"] else {}
    L = [f"# {ctx['P']['nome']} — fontes de cada imagem", "",
         f"Base (fala e câmera): `{ctx['GRAV'].name}` — gravação própria. Vídeo final {C['fim']:.2f} s.",
         "Trilha: " + (f"`{ctx['MUSICA'].name}/` (ver LICENCA.txt na pasta)" if ctx["MUSICA"] and ctx["MUSICA"].exists() else "nenhuma"),
         "", "| # | Entra (s) | Sai (s) | Fala | Imagem | Arquivo | Origem | Licença |", "|---|---|---|---|---|---|---|---|"]
    for i, c in enumerate(fx):
        if c["tipo"] == "cam":
            img, arq, org, lic = "câmera (quem fala)", f"`{ctx['GRAV'].name}` (mesmo instante da fala)", "gravação própria", "própria"
        elif c["tipo"] == "card":
            img, arq, org, lic = "card de encerramento", "motor/graficos `Encerramento`", "estúdio", "própria"
        else:
            p = caminho(ctx, c)
            img = c.get("o_que", "")
            arq = f"`{p.name}`" + (f" a partir de {c.get('ss', 0)} s" if c["tipo"] == "v" else " (foto, Ken Burns)")
            v = cat.get(c.get("id"), {})
            org = c.get("origem") or (f"acervo próprio (álbum `{p.parent.name}`, {v.get('data') or 's/ data'})" if c.get("propria") else "")
            lic = c.get("licenca") or ("própria" if c.get("propria") else "")
        L.append(f"| {i+1} | {c['ini']:.2f} | {c['fim']:.2f} | {c.get('fala', '')} | {img} | {arq} | {org} | {lic} |")
    if ctx["VETO"]:
        L += ["", "Pastas vetadas (config.json → pastas_vetadas) não foram usadas; o gate do reel confere (R10)."]
    dst = ctx["OUT"] / f"{ctx['P']['nome']}-fontes.md"
    dst.write_text("\n".join(L) + "\n", encoding="utf-8"); print("fontes:", dst)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    ctx = carregar(sys.argv[1])
    etapa = sys.argv[2]
    if etapa == "transcrever":
        transcrever(ctx); sys.exit(0)
    if etapa in ("cenas", "tudo"):
        so = [int(x) for x in sys.argv[3:]]
        for i, c in enumerate(faixas(ctx)):
            if not so or i in so:
                render_cena(ctx, i, c)
    if etapa in ("graficos", "tudo"):
        graficos(ctx)
    if etapa in ("final", "tudo"):
        final(ctx)
    if etapa in ("insta", "tudo"):
        insta(ctx)
    if etapa in ("folha", "tudo"):
        folha(ctx)
    if etapa in ("fontes", "tudo"):
        fontes(ctx)
