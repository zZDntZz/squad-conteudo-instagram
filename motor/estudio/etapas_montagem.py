"""Etapas 6–8: grafismos, montagem final e shorts."""
import random
from pathlib import Path

from comum import (BIBLIOTECA, FPS, GRAFICOS, H, W, gravar, hms, ler, marca_do, props_marca, proj, run)

# ---------------------------------------------------------------- efeitos sonoros próprios

def gerar_sfx():
    """Whoosh, pop e impacto sintetizados — próprios, sem licença de terceiros."""
    d = BIBLIOTECA / "sfx"
    d.mkdir(parents=True, exist_ok=True)
    receitas = {
        "whoosh.wav": "anoisesrc=d=0.55:c=pink:a=0.6,bandpass=f=1800:w=2600,afade=t=in:d=0.3:curve=exp,afade=t=out:st=0.3:d=0.25,volume=0.9",
        "pop.wav": "sine=f=880:d=0.09,afade=t=out:st=0.01:d=0.08,volume=0.5",
        "impacto.wav": "sine=f=55:d=0.5,afade=t=out:st=0.05:d=0.45,volume=1.2",
    }
    for nome, f in receitas.items():
        if not (d / nome).exists():
            run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f, "-ar", "48000", "-ac", "2", d / nome])
    return d

# ---------------------------------------------------------------- plano -> itens de render

def expandir_plano(slug: str):
    """Valida tempos e preenche o que dá para derivar da fala (texto cinético, durações)."""
    p = proj(slug)
    plano = ler(p / "plano.json")
    if not plano:
        raise SystemExit("Falta plano.json — é o diretor quem escreve (ver skill estudio-edicao).")
    cortes = ler(p / "trabalho" / "cortes.json")
    pal, dur = cortes["palavras"], cortes["duracao_editada"]
    m = marca_do(slug)
    projeto = ler(p / "projeto.json")
    aula = projeto.get("formato") == "aula"
    # Gravação com mais de uma cena do OBS (ex.: tablet no centro e depois tablet à esquerda): cada uma tem
    # a sua área livre. projeto.json → "cenas": [{"desde": seg_bruto, "pos": {x, y, w}}].
    cenas = sorted(projeto.get("cenas") or [], key=lambda c: c["desde"])
    from etapas_dividir import _para_bruto
    itens = []
    for b in plano["beats"]:
        ini, fim = float(b["ini"]), min(float(b["fim"]), dur)
        props = dict(b.get("props", {}))
        if b.get("template") == "TextoCinetico" and aula and not props.get("fundo"):
            props["fundo"] = {"tipo": "claro"}  # cenário claro da aula: verde quase preto vira tela morta (F04)
        if b.get("template") == "TextoCinetico" and props.get("palavrasDaFala"):
            # começa na primeira palavra: fundo escuro sem texto é tela morta (gate F04)
            dentro = [w for w in pal if ini <= w["ini"] < fim]
            if dentro and props.get("fundo", {}).get("tipo") in (None, "cor", "claro"):
                ini = max(ini, round(dentro[0]["ini"] - 0.1, 3))
            props["palavras"] = [{"t": w["t"].strip(".,;:!?"), "em": round(w["ini"] - ini, 3)}
                                 for w in pal if ini <= w["ini"] < fim]
            props.pop("palavrasDaFala")
        if b.get("template") == "PalavraChave" and props.get("lado") == "coluna" and "pos" not in props and cenas:
            bruto = _para_bruto(cortes["segmentos"], ini)
            cena = [c for c in cenas if c["desde"] <= bruto + 0.01][-1] if cenas[0]["desde"] <= bruto + 0.01 else cenas[0]
            props["pos"] = cena["pos"]
            # cena escura (slide preto, vídeo de terceiro em tela cheia): o verde-escuro "primaria" do rótulo
            # "Parte N"/"A seguir" some (aula de podas, 15/10). cenas[].cor troca a cor escura pela legível.
            if cena.get("cor") and props.get("cor", "claro") == "primaria":
                props["cor"] = cena["cor"]
        if b.get("template") == "Encerramento":
            props.setdefault("tagline", m.get("tagline"))
            props.setdefault("logo", "marca/logo.png" if m.get("logo") else None)
        props.update({"marca": props_marca(m), "duracao": round(fim - ini, 3)})
        itens.append({"id": b["id"], "template": b["template"], "ini": round(ini, 3), "fim": round(fim, 3),
                      "modo": b.get("modo", "cheio"), "alfa": b.get("modo") == "sobre", "props": props})
    gravar(p / "trabalho" / "plano_render.json", {"itens": itens})
    return itens


def graficos(slug: str):
    p = proj(slug)
    expandir_plano(slug)
    r = run(["node", GRAFICOS / "render.mjs", p], check=False)
    if r.returncode != 0:  # Chrome headless às vezes cai sem mensagem (parte 4, 11/10); o cache poupa o que já saiu
        print("render dos grafismos falhou; tentando de novo uma vez")
        r = run(["node", GRAFICOS / "render.mjs", p], check=False)
    print(r.stdout[-3000:])
    if r.returncode != 0:
        raise RuntimeError("Render dos grafismos falhou:\n" + (r.stderr or "")[-3000:] + (r.stdout or "")[-1500:])

# ---------------------------------------------------------------- montagem

def _trilha(plano, dur):
    """Trilha: a do plano ou sorteada da biblioteca (licenciada) pelo clima pedido."""
    t = plano.get("musica")
    if t and t.get("arquivo"):
        a = Path(t["arquivo"])
        return a if a.is_absolute() else BIBLIOTECA / "musica" / a
    clima = (t or {}).get("clima", "")
    pasta = BIBLIOTECA / "musica"
    op = [a for a in pasta.glob("**/*") if a.suffix.lower() in (".mp3", ".wav", ".m4a") and clima in a.as_posix().lower()]
    return random.Random(plano.get("semente", 7)).choice(op) if op else None


def montar(slug: str, lote: int = 30):
    p = proj(slug)
    t = p / "trabalho"
    plano = ler(p / "plano.json")
    itens = ler(t / "plano_render.json")["itens"]
    dur = ler(t / "cortes.json")["duracao_editada"]
    sfx = gerar_sfx()

    # 1) Vídeo: câmera + grafismos em passadas de até `lote` camadas (limita memória do ffmpeg).
    base = t / "aroll.mp4"
    for n0 in range(0, len(itens), lote):
        grupo = itens[n0:n0 + lote]
        ent, filt, ult = ["-i", base], [], "0:v"
        for k, it in enumerate(grupo, start=1):
            ent += ["-i", it["saida"]]
            fmt = "format=yuva420p," if it["alfa"] else ""
            filt.append(f"[{k}:v]{fmt}setpts=PTS-STARTPTS+{it['ini']}/TB[g{k}]")
            filt.append(f"[{ult}][g{k}]overlay=eof_action=pass:enable='between(t,{it['ini']},{it['fim']})'[v{k}]")
            ult = f"v{k}"
        destino = t / f"video_passada{n0 // lote}.mp4"
        run(["ffmpeg", "-y", "-v", "error", *ent, "-filter_complex", ";".join(filt), "-map", f"[{ult}]",
             "-c:v", "h264_nvenc", "-preset", "p6", "-rc", "vbr", "-cq", "16", "-b:v", "0", "-r", FPS, destino])
        base = destino

    # 2) Áudio: voz + trilha com ducking pela voz + efeitos nos grafismos de tela cheia.
    ent = ["-i", t / "voz.wav"]
    filt = ["[0:a]asplit=2[voz][chave]"]
    mix = ["[voz]"]
    trilha = _trilha(plano, dur)
    if trilha:
        vol = (plano.get("musica") or {}).get("volume_db", marca_do(slug).get("musica_volume_db", -26))
        ent += ["-stream_loop", "-1", "-i", trilha]
        filt.append(f"[1:a]atrim=0:{dur},asetpts=N/SR/TB,aresample=48000,volume={vol}dB,"
                    f"afade=t=in:d=1.5,afade=t=out:st={max(0, dur - 3)}:d=3[mus]")
        filt.append("[mus][chave]sidechaincompress=threshold=0.04:ratio=6:attack=20:release=400[musd]")
        mix.append("[musd]")
    else:
        filt[0] = "[0:a]anull[voz]"
        print("AVISO: sem trilha (biblioteca/musica vazia ou clima sem correspondência).")
    k = len(ent) // 2 if "-stream_loop" not in ent else 2
    efeitos = []
    for it in itens:
        if it["modo"] == "cheio":
            efeitos.append(("whoosh.wav", max(0, it["ini"] - 0.18)))
        elif it["template"] == "PalavraChave":
            efeitos.append(("pop.wav", it["ini"]))
    for i, (nome, quando) in enumerate(efeitos):
        ent += ["-i", sfx / nome]
        ms = int(quando * 1000)
        filt.append(f"[{k + i}:a]adelay={ms}|{ms},volume=0.35[s{i}]")
        mix.append(f"[s{i}]")
    filt.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.79:level=false[a]")
    run(["ffmpeg", "-y", "-v", "error", *ent, "-filter_complex", ";".join(filt), "-map", "[a]",
         "-t", dur, "-ar", "48000", "-c:a", "pcm_s16le", t / "mix.wav"])

    # 3) Final.
    final = p / "final" / f"{slug}.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", base, "-i", t / "mix.wav", "-map", "0:v", "-map", "1:a",
         "-c:v", "h264_nvenc", "-preset", "p6", "-rc", "vbr", "-cq", "18", "-b:v", "12M", "-maxrate", "20M",
         "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
         "-shortest", final])
    creditos(slug)
    capitulos(slug)
    for f in t.glob("video_passada*.mp4"):
        if f != base:
            f.unlink()
    print("Final:", final)
    return final

def capitulos(slug: str):
    """Capítulos do YouTube (cole na descrição): 00:00 Título, um por linha."""
    p = proj(slug)
    caps = (ler(p / "plano.json") or {}).get("capitulos", [])
    if not caps:
        return
    linhas = []
    for c in sorted(caps, key=lambda c: float(c["ini"])):
        t = int(float(c["ini"]))
        h, r = divmod(t, 3600)
        stamp = f"{h}:{r // 60:02d}:{r % 60:02d}" if h else f"{r // 60:02d}:{r % 60:02d}"
        linhas.append(f"{stamp} {c['titulo']}")
    (p / "final" / "capitulos.txt").write_text("\n".join(linhas), encoding="utf-8")
    print(f"capitulos.txt: {len(linhas)} capítulos")


def creditos(slug: str):
    """Bloco de créditos para a descrição do YouTube (mídia CC BY/BY-SA e veículos citados)."""
    p = proj(slug)
    lic = ler(p / "assets" / "licencas.json", {}) or {}
    usados = set()
    def varre(o):
        if isinstance(o, dict):
            for v in o.values(): varre(v)
        elif isinstance(o, list):
            for v in o: varre(v)
        elif isinstance(o, str) and o in lic:
            usados.add(o)
    varre(ler(p / "plano.json"))
    linhas = []
    for a in sorted(usados):
        i = lic[a]
        if i.get("exige_credito") or a.startswith("prints/"):
            linhas.append(f"- {i.get('autor', '')} — {i.get('licenca', '')} — {i.get('origem', '')}")
    txt = "Créditos de imagens e fontes:\n" + "\n".join(linhas) if linhas else ""
    (p / "final" / "creditos.txt").write_text(txt, encoding="utf-8")
    if linhas:
        print(f"creditos.txt: {len(linhas)} crédito(s) para a descrição")

# ---------------------------------------------------------------- shorts

def shorts(slug: str):
    """Cortes verticais: câmera recortada no rosto + legenda dinâmica + título."""
    p = proj(slug)
    t = p / "trabalho"
    plano = ler(p / "plano.json")
    projeto = ler(p / "projeto.json")
    pal = ler(t / "cortes.json")["palavras"]
    m = marca_do(slug)
    lista = plano.get("shorts", [])
    if not lista:
        print("plano.json sem shorts."); return
    # Cena com tela compartilhada: o recorte central pega o documento e perde o rosto (aula de curso,
    # 11/10). projeto.json → "pilha": {"camera": [x,y,w,h], "tela": [x,y,w,h]} (px da gravação) empilha
    # título / câmera / legenda / tela sobre o papel da marca.
    pilha = projeto.get("pilha")
    Y_CAM, Y_TELA = 400, 1240
    itens = []
    for s in lista:
        ini, fim = float(s["ini"]), float(s["fim"])
        palavras = [{"t": w["t"], "ini": round(w["ini"] - ini, 3), "fim": round(w["fim"] - ini, 3)}
                    for w in pal if ini <= w["ini"] < fim]
        itens.append({"id": s["id"], "template": "Legenda", "alfa": True, "ini": ini, "fim": fim,
                      "props": {"vertical": True, "palavras": palavras, "titulo": s.get("titulo"),
                                **({"fundoClaro": True, "baixo": 1920 - Y_TELA + 20} if pilha else {}),
                                "marca": props_marca(m), "duracao": round(fim - ini, 3)}})
    gravar(t / "plano_render.json", {"itens": itens})
    r = run(["node", GRAFICOS / "render.mjs", p], check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    itens = ler(t / "plano_render.json")["itens"]
    cx = projeto["enquadramento"]["cx"]
    for it in itens:
        out = p / "final" / f"short_{it['id']}.mp4"
        dur = it["fim"] - it["ini"]
        if pilha:
            (cx_, cy_, cw, ch), (tx, ty, tw, th) = pilha["camera"], pilha["tela"]
            papel = m["cores"].get("claro", "#FFFFFF").lstrip("#")
            vf = (f"color=c=0x{papel}:s=1080x1920:r=30:d={dur:.3f}[bg];"
                  f"[0:v]split[a][b];[a]crop={cw}:{ch}:{cx_}:{cy_},scale=1080:-2:flags=lanczos,setsar=1[cam];"
                  # tela quase quadrada (lousa do tablet) em largura cheia passava do pé do 9:16: cabe na faixa
                  f"[b]crop={tw}:{th}:{tx}:{ty},scale=1080:{1920 - Y_TELA - 20}:force_original_aspect_ratio=decrease"
                  f":force_divisible_by=2:flags=lanczos,setsar=1[tela];"
                  f"[bg][cam]overlay=0:{Y_CAM}[x1];[x1][tela]overlay=(W-w)/2:{Y_TELA}:shortest=1[x2];"
                  f"[1:v]format=yuva420p[leg];[x2][leg]overlay=eof_action=pass[v]")
        else:
            vf = (f"[0:v]crop=ih*9/16:ih:'min(max(iw*{cx}-ih*9/32,0),iw-ih*9/16)':0,scale=1080:1920:flags=lanczos,setsar=1[cam];"
                  f"[1:v]format=yuva420p[leg];[cam][leg]overlay=eof_action=pass[v]")
        run(["ffmpeg", "-y", "-v", "error", "-ss", it["ini"], "-t", dur, "-i", t / "aroll.mp4", "-i", it["saida"],
             "-ss", it["ini"], "-t", dur, "-i", t / "voz.wav", "-filter_complex", vf, "-map", "[v]", "-map", "2:a",
             "-c:v", "h264_nvenc", "-preset", "p6", "-cq", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart", "-shortest", out])
        print("Short:", out)
    # devolve o plano de render do vídeo longo para o estado do longo
    expandir_plano(slug)
