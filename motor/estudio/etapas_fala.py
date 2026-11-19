"""Etapas 1–3: preparar o projeto, transcrever a fala e decidir os cortes."""
import datetime as dt
import difflib
import re
from pathlib import Path

from comum import (FORMATOS, FPS, PROJETOS, marca, cuda_dlls, duracao, gravar, hms, ler, normaliza, proj, quadro, run,
                   slugify, video_info)

# ---------------------------------------------------------------- preparar

def preparar(fonte: str, slug: str | None = None, glossario: str = "", marca_nome: str = "pessoal",
             formato: str = "video") -> str:
    if formato not in FORMATOS:
        raise SystemExit(f"Formato inválido: {formato} (use {list(FORMATOS)})")
    m = marca(marca_nome)
    fonte = Path(fonte).resolve()
    if not fonte.exists():
        raise SystemExit(f"Gravação não encontrada: {fonte}")
    slug = slug or f"{dt.date.today():%Y-%m-%d}-{slugify(fonte.stem)}"
    p = PROJETOS / slug
    for sub in ("trabalho", "assets", "graficos", "final"):
        (p / sub).mkdir(parents=True, exist_ok=True)
    info = video_info(fonte)
    projeto = ler(p / "projeto.json", {}) or {}
    projeto.update({
        "slug": slug, "fonte": str(fonte), "duracao_bruta": round(duracao(fonte), 2), **info,
        "criado": projeto.get("criado") or dt.datetime.now().isoformat(timespec="seconds"),
    })
    projeto.setdefault("marca", marca_nome)
    projeto.setdefault("formato", formato)
    f = FORMATOS[projeto["formato"]]
    projeto.setdefault("enquadramento", {"cx": 0.5, "cy": 0.38})   # centro do rosto (fração)
    projeto.setdefault("punch_in", f["punch_in"])                    # escala do plano fechado
    projeto.setdefault("pausa_corte", f["pausa_corte"])              # silêncio maior que isso vira corte
    projeto.setdefault("glossario", glossario)
    projeto.setdefault("cor", None)                                  # None = automático (colorista)
    gravar(p / "projeto.json", projeto)
    t = p / "trabalho"
    _logo_no_projeto(p, m)
    run(["ffmpeg", "-y", "-v", "error", "-i", fonte, "-vn", "-ac", "1", "-ar", "16000", t / "audio16k.wav"])
    run(["ffmpeg", "-y", "-v", "error", "-i", fonte, "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", t / "audio48k.wav"])
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(min(30, projeto["duracao_bruta"] / 2)), "-i", fonte,
         "-frames:v", "1", "-vf", "format=yuvj420p", t / "quadro_ref.jpg"])
    print(f"Projeto {slug} [{projeto['marca']} / {projeto['formato']}]: {info['largura']}x{info['altura']} {info['fps']}fps, {hms(projeto['duracao_bruta'])}")
    if m.get("provisoria"):
        print("AVISO: identidade da marca é PROVISÓRIA (marcas/" + marca_nome + "/marca.json) — confirmar antes de publicar.")
    if info["largura"] < 1920:
        print("AVISO: fonte abaixo de 1080p — o punch-in vai perder nitidez.")
    return slug

def _logo_no_projeto(p, m):
    """Copia o logo oficial da marca para assets/marca/ e registra como mídia própria."""
    if not m.get("logo"):
        return
    import shutil
    src = Path(m["_pasta"]) / m["logo"]
    dst = p / "assets" / "marca" / "logo.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    lic = ler(p / "assets" / "licencas.json", {}) or {}
    lic["marca/logo.png"] = {"origem": str(src), "autor": m.get("nome"), "licenca": "marca própria"}
    gravar(p / "assets" / "licencas.json", lic)

# ---------------------------------------------------------------- transcrever

def transcrever(slug: str, modelo: str = "large-v3-turbo"):
    p = proj(slug)
    projeto = ler(p / "projeto.json")
    cuda_dlls()
    from faster_whisper import WhisperModel
    try:
        m = WhisperModel(modelo, device="cuda", compute_type="float16")
    except Exception as e:  # sem GPU: modelo menor na CPU
        print("GPU indisponível, caindo para CPU:", str(e)[:120])
        m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(p / "trabalho" / "audio16k.wav"), language="pt", word_timestamps=True,
                           vad_filter=True, vad_parameters={"min_silence_duration_ms": 300},
                           beam_size=5, initial_prompt=projeto.get("glossario") or None,
                           condition_on_previous_text=False)
    palavras, frases = [], []
    for s in segs:
        idx = []
        for w in s.words or []:
            t = w.word.strip()
            if not t:
                continue
            idx.append(len(palavras))
            palavras.append({"t": t, "ini": round(w.start, 3), "fim": round(w.end, 3), "p": round(w.probability, 3)})
        if idx:
            frases.append({"texto": s.text.strip(), "ini": palavras[idx[0]]["ini"], "fim": palavras[idx[-1]]["fim"], "palavras": idx})
    gravar(p / "trabalho" / "transcricao.json", {"palavras": palavras, "frases": frases})
    print(f"{len(palavras)} palavras, {len(frases)} frases")

# ---------------------------------------------------------------- cortar

FOLGA_INI = 0.06       # respiro antes da primeira palavra do trecho
FOLGA_FIM = 0.14       # respiro depois da última
PAUSA_BLOCO = 0.55     # pausa que separa "tentativas" (para detectar regravação)
SALTO_PLANO = 0.45     # corte que remove mais que isso troca aberto/fechado
PLANO_MIN = 2.5        # plano não troca de escala antes disso


def _blocos(palavras):
    """Agrupa palavras em blocos separados por pausas longas (uma 'tentativa' de frase)."""
    blocos, atual = [], []
    for i, w in enumerate(palavras):
        if atual and w["ini"] - palavras[atual[-1]]["fim"] > PAUSA_BLOCO:
            blocos.append(atual)
            atual = []
        atual.append(i)
    if atual:
        blocos.append(atual)
    return blocos


def _fala_nos_cortes(wav, segs, dur, removidos=(), janela=0.05, inicio=0.0):
    import wave
    import numpy as np
    with wave.open(str(wav), "rb") as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    n = int(sr * janela)
    rms = np.sqrt(np.mean(a[: len(a) // n * n].reshape(-1, n) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    falado = []
    for s in segs:
        i0, i1 = int(s["fonte_ini"] / janela), int(s["fonte_fim"] / janela)
        falado.extend(db[i0:i1])
    limiar = (np.percentile(falado, 50) - 14) if falado else -35   # 14 dB abaixo da voz típica
    buracos, ant = [], inicio
    for s in segs + [{"fonte_ini": dur, "fonte_fim": dur}]:
        if s["fonte_ini"] - ant > 0.8:
            buracos.append((ant, s["fonte_ini"]))
        ant = s["fonte_fim"]
    alertas = []
    for ini, fim in buracos:
        i0 = int(ini / janela)
        trecho = db[i0:int(fim / janela)].copy()
        for r in removidos:  # remoção intencional (corta/regravação) não é alerta
            a, b = max(0, int((r["ini"] - 0.15) / janela) - i0), int((r["fim"] + 0.25) / janela) - i0
            if b > 0:
                trecho[a:b] = -120
        voz = float((trecho > limiar).sum() * janela)
        if voz >= 0.6:
            alertas.append({"ini": round(ini, 2), "fim": round(fim, 2), "voz_s": round(voz, 1)})
    return alertas


def _corrigir_grafia(pal, projeto):
    """Nomes que o Whisper erra mesmo com glossário (ex.: nome da marca escrito errado).
    marca.json → "correcoes": {"errado": "certo"}; casa a palavra sem pontuação, sem caixa."""
    from comum import marca
    # projeto.json → "correcoes" soma às da marca (ex.: sigla de um curso que só vale naquele projeto)
    fontes = {**(marca(projeto.get("marca", "pessoal")).get("correcoes") or {}), **(projeto.get("correcoes") or {})}
    corr = {normaliza(k): v for k, v in fontes.items()}
    for w in pal:
        nucleo = re.sub(r"^\W+|\W+$", "", w["t"])
        if nucleo and normaliza(nucleo) in corr:
            w["t"] = w["t"].replace(nucleo, corr[normaliza(nucleo)])


def cortar(slug: str):
    p = proj(slug)
    projeto = ler(p / "projeto.json")
    tr = ler(p / "trabalho" / "transcricao.json")
    pal = tr["palavras"]
    # 0) "manter" (tempos brutos): fala que o Whisper com VAD não transcreveu e o corte tomou por silêncio
    #    ("E a argila", aula de solo, 13/10 — veio dos ALERTAS). Usa as palavras da transcrição literal.
    lit_p = p / "trabalho" / "literal.json"
    for m in projeto.get("manter", []):
        lit = [w for w in (ler(lit_p) if lit_p.exists() else []) if w["ini"] >= m["ini"] - 0.05 and w["fim"] <= m["fim"] + 0.05]
        if lit:
            pal = [w for w in pal if w["fim"] <= m["ini"] or w["ini"] >= m["fim"]] + [{"t": w["t"], "ini": w["ini"], "fim": w["fim"]} for w in lit]
            pal.sort(key=lambda w: w["ini"])
    _corrigir_grafia(pal, projeto)
    fora, removidos = set(), []
    blocos = _blocos(pal)
    texto = lambda b: " ".join(pal[i]["t"] for i in b)

    # 1) Palavra-código "corta": descarta a tentativa em que foi dita (ou a anterior, se dita sozinha).
    #    Aula de podas (15/10): "se a gente corta essa ponta" é conteúdo e a regra comeu 25 s de aula.
    #    projeto.json → "palavra_corta": false desliga; bastidor fica com tropecos/remover e o gate F07.
    for bi, b in enumerate(blocos if projeto.get("palavra_corta", True) else []):
        cods = [i for i in b if normaliza(pal[i]["t"]) == "corta"]
        if not cods:
            continue
        ultimo = cods[-1]
        alvo = [i for i in b if i <= ultimo]
        if all(normaliza(pal[i]["t"]) == "corta" for i in alvo) and bi > 0:
            alvo = blocos[bi - 1] + alvo
        fora.update(alvo)
        removidos.append({"motivo": "palavra 'corta'", "texto": " ".join(pal[i]["t"] for i in alvo),
                          "ini": pal[alvo[0]]["ini"], "fim": pal[alvo[-1]]["fim"]})

    # 1b) Remoção pedida pelo diretor (tempos da gravação bruta), p.ex. "essa parte pode cortar" dito
    #     em voz, ou repetição que o detector não pegou. projeto.json → "remover": [{ini, fim, motivo}].
    for r in projeto.get("remover", []):
        alvo = [i for i, w in enumerate(pal) if w["ini"] >= r["ini"] - 0.05 and w["fim"] <= r["fim"] + 0.05]
        if alvo:
            fora.update(alvo)
            removidos.append({"motivo": r.get("motivo", "diretor"), "texto": texto(alvo),
                              "ini": pal[alvo[0]]["ini"], "fim": pal[alvo[-1]]["fim"]})

    # 2) Regravação sem aviso: bloco seguinte começa igual ao atual -> fica a última tentativa.
    vivos = [b for b in blocos if not all(i in fora for i in b)]
    for a, b in zip(vivos, vivos[1:]):
        na, nb = normaliza(texto(a)).split(), normaliza(texto(b)).split()
        if len(na) < 2 or len(nb) < 2:
            continue
        k = min(len(na), len(nb), 6)
        inicio_igual = na[:3] == nb[:3] or difflib.SequenceMatcher(None, na[:k], nb[:k]).ratio() >= 0.8
        if inicio_igual and len(na) <= len(nb) + 2:
            fora.update(a)
            removidos.append({"motivo": "regravação", "texto": texto(a), "ini": pal[a[0]]["ini"], "fim": pal[a[-1]]["fim"]})

    # 3) Trechos de fala mantidos, cortando silêncios. Parte de aula dividida: só a janela dela.
    dur = projeto["duracao_bruta"]
    j0, j1 = projeto.get("janela") or (0.0, dur)
    pausa_corte = projeto.get("pausa_corte", 0.30)
    manter = [i for i in range(len(pal)) if i not in fora and pal[i]["ini"] >= j0 and pal[i]["fim"] <= j1]
    trechos = []
    for i in manter:
        w = pal[i]
        ini, fim = max(j0, w["ini"] - FOLGA_INI), min(j1, w["fim"] + FOLGA_FIM)
        if trechos:
            t = trechos[-1]
            seguida = t["ult"] == i - 1 and w["ini"] - pal[i - 1]["fim"] <= pausa_corte
            if seguida or ini <= t["fim"]:
                t["fim"], t["ult"] = max(t["fim"], fim), i
                continue
        trechos.append({"ini": ini, "fim": fim, "pri": i, "ult": i})

    # 3b) "remover" corta o ÁUDIO do intervalo, não só as palavras que couberem nele: o Whisper com VAD
    #     funde as duas tentativas de "uma faixa, uma faixa" numa palavra só, e o tropeço ficava no ar
    #     (aula de vasos, 12/10). Sobra menor que 0,12 s entre dois cortes vira estalo — sai também.
    for a, b in sorted((r["ini"], r["fim"]) for r in projeto.get("remover", [])):
        trechos = [{**t, "ini": x, "fim": y} for t in trechos
                   for x, y in ((t["ini"], min(t["fim"], a)), (max(t["ini"], b), t["fim"])) if y - x >= 0.12]

    # 4) Alterna aberto/fechado nos cortes que de fato pulam algo (esconde o jump cut).
    escala_f = projeto.get("punch_in", 1.18)
    if escala_f <= 1.001:
        escala_f = 1.0  # aula: plano único
    segs, acc, escala, desde = [], 0.0, 1.0, 0.0
    for k, t in enumerate(trechos):
        ini, fim = quadro(t["ini"]), quadro(t["fim"])
        if fim - ini < 1 / FPS:
            continue
        if segs:
            pulo = ini - segs[-1]["fonte_fim"]
            regravou = any(segs[-1]["ult"] < j < t["pri"] for j in fora)
            if (pulo > SALTO_PLANO or regravou) and acc - desde >= PLANO_MIN:
                escala = escala_f if escala == 1.0 else 1.0
                desde = acc
        segs.append({"fonte_ini": ini, "fonte_fim": fim, "ed_ini": round(acc, 4), "escala": escala,
                     "pri": t["pri"], "ult": t["ult"]})
        acc += fim - ini

    # 5) Remapeia a fala para a linha do tempo editada.
    def remap(t):
        for s in segs:
            if s["fonte_ini"] - 0.001 <= t <= s["fonte_fim"] + 0.001:
                return round(s["ed_ini"] + (t - s["fonte_ini"]), 3)
        return None
    pal_ed = []
    for i in manter:
        a, b = remap(pal[i]["ini"]), remap(pal[i]["fim"])
        if a is not None and b is not None:
            pal_ed.append({"t": pal[i]["t"], "ini": a, "fim": b, "fonte": i})
    frases_ed, cur = [], []
    for w in pal_ed:
        cur.append(w)
        if w["t"][-1:] in ".?!" or (len(cur) >= 28):
            frases_ed.append(cur)
            cur = []
    if cur:
        frases_ed.append(cur)

    # 6) Fala não transcrita dentro do que foi cortado. O Whisper às vezes ignora a 2ª tentativa
    #    de uma frase repetida; sem esta checagem, fala válida sai do vídeo sem aviso.
    alertas = _fala_nos_cortes(p / "trabalho" / "audio16k.wav", segs, j1, removidos, inicio=j0)

    gravar(p / "trabalho" / "cortes.json", {
        "duracao_editada": round(acc, 3), "segmentos": segs, "removidos": removidos, "palavras": pal_ed,
        "alertas": alertas,
    })
    linhas = [f"[{hms(f[0]['ini'])} → {hms(f[-1]['fim'])}] ({f[0]['ini']:.2f}s) " + " ".join(w["t"] for w in f) for f in frases_ed]
    if alertas:
        linhas = ["# ALERTAS — fala não transcrita removida (ouvir o trecho na gravação bruta):"] + \
                 [f"#   bruto {hms(a['ini'])}–{hms(a['fim'])}: {a['voz_s']}s com voz" for a in alertas] + [""] + linhas
    (p / "trabalho" / "roteiro_editado.txt").write_text("\n".join(linhas), encoding="utf-8")
    bruta = j1 - j0
    print(f"{len(segs)} trechos; {hms(bruta)} -> {hms(acc)} ({100 * (1 - acc / bruta):.0f}% removido); "
          f"{len(removidos)} regravações/erros tirados")
    for r in removidos:
        print(f"  - [{r['motivo']}] {hms(r['ini'])}: {r['texto'][:90]}")
