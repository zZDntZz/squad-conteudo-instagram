"""Tropeço de fala: achar pelo que foi DITO, não pelo que o Whisper resumiu.

O `transcrever` usa VAD e devolve texto limpo: a repetição ("uma faixa, uma faixa"), a frase abandonada e a
autocorreção ("70%, digamos, 60%") somem do texto mas ficam no áudio. Aula de vasos (12/10): o autor
ouviu vários tropeços no vídeo que o roteiro dizia estarem cortados.

  literal    transcrição sem VAD, com prompt disfluente (o Whisper imita o estilo do prompt e passa a escrever
             a repetição) -> trabalho/literal.json, tempo bruto
  tropecos   cruza o literal com o que o corte manteve -> trabalho/tropecos.txt (+ .json) para o diretor
             ler; com --aplicar, a repetição exata entra sozinha em projeto.json → remover
  recortar   guarda cortes/plano _vN, roda o cortar e remapeia o plano (editado antigo -> bruto -> novo)
"""
import json, re, shutil, wave
import numpy as np

from comum import cuda_dlls, gravar, hms, ler, normaliza, proj
import etapas_fala as fala
from etapas_dividir import _para_bruto, _para_editado

PROMPT_LITERAL = ("Então, ãh, é... o o vaso, né, o vaso ele, ele precisa, tipo, hum, a gente a gente vai ver, "
                  "tá certo? Uma faixa, uma faixa ideal.")
# repetição que é a língua, não tropeço: "o que que é", "pra que que serve"
REPETICAO_OK = {("que",), ("e",)}   # "e é" sem acento vira "e e"
AUTOCORRECAO = re.compile(r"\b(digamos|quer dizer|ou melhor|ali[aá]s|na verdade n[aã]o|desculpa)\b", re.I)
MULETA = re.compile(r"^(ãh|hã|hum|hm|eh|é\.\.\.|ah)\W*$", re.I)


def literal(slug: str, forcar: bool = False):
    p = proj(slug)
    out = p / "trabalho" / "literal.json"
    if out.exists() and not forcar:
        return ler(out)
    projeto = ler(p / "projeto.json")
    pai = projeto.get("pai")
    if pai and (proj(pai) / "trabalho" / "literal.json").exists():   # parte de aula: mesma gravação do pai
        return ler(proj(pai) / "trabalho" / "literal.json")
    cuda_dlls()
    from faster_whisper import WhisperModel
    m = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")
    segs, _ = m.transcribe(str(p / "trabalho" / "audio16k.wav"), language="pt", vad_filter=False, beam_size=5,
                           word_timestamps=True, condition_on_previous_text=False,
                           initial_prompt=PROMPT_LITERAL + " " + (projeto.get("glossario") or ""))
    pal = [{"t": w.word.strip(), "ini": round(w.start, 3), "fim": round(w.end, 3), "p": round(w.probability, 3)}
           for s in segs for w in (s.words or []) if w.word.strip()]
    gravar(out, pal)
    print(f"literal.json: {len(pal)} palavras")
    return pal


def _vale(db, t, janela=0.01, raio=0.12):
    """Leva a fronteira do corte para o ponto mais silencioso perto dela (o tempo do Whisper erra ±0,1 s)."""
    i0, i1 = max(0, int((t - raio) / janela)), int((t + raio) / janela)
    return round((i0 + int(np.argmin(db[i0:i1 + 1]))) * janela, 3) if i1 > i0 else t


def _energia(wav, janela=0.01):
    with wave.open(str(wav), "rb") as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    n = int(sr * janela)
    return 20 * np.log10(np.sqrt(np.mean(a[: len(a) // n * n].reshape(-1, n) ** 2, axis=1) + 1e-12))


def achar(lit, segs):
    """Tropeços nas palavras literais que caem dentro do que o corte manteve (ordem da linha editada)."""
    dentro = lambda w: any(s["fonte_ini"] <= (w["ini"] + w["fim"]) / 2 <= s["fonte_fim"] for s in segs)
    seq = [w for w in lit if dentro(w)]
    tok = [normaliza(w["t"]) for w in seq]
    achados, usados = [], set()
    for j in range(len(seq)):
        for n in (4, 3, 2, 1):
            a, b = tok[j:j + n], tok[j + n:j + 2 * n]
            if j + 2 * n > len(seq) or a != b or not all(a) or tuple(a) in REPETICAO_OK or j in usados:
                continue
            # com fronteira de frase ("o vaso. O vaso é…", "o sal? O sal são…") pode ser estilo: vai para leitura
            w_fim = seq[j + n - 1]["t"].rstrip()
            fronteira = w_fim[-1:] in ".?!" and not w_fim.endswith("...")
            achados.append({"tipo": "repetição", "auto": not fronteira, "j": j, "ini": seq[j]["ini"], "fim": seq[j + n]["ini"],
                            "texto": " ".join(w["t"] for w in seq[j:j + 2 * n])})
            usados.update(range(j, j + n))
            break
        w = seq[j]
        if AUTOCORRECAO.search(w["t"]):
            achados.append({"tipo": "autocorreção", "auto": False, "j": j, "ini": w["ini"], "fim": w["fim"], "texto": w["t"]})
        if MULETA.match(w["t"]):
            achados.append({"tipo": "muleta", "auto": True, "j": j, "ini": w["ini"], "fim": w["fim"], "texto": w["t"]})
    # frase solta de 1–2 palavras ("Vegetal.") costuma ser sobra de tentativa cortada pela metade
    k = 0
    while k < len(seq):
        f = k
        while f < len(seq) - 1 and not seq[f]["t"][-1:] in ".?!":
            f += 1
        if f - k + 1 <= 2 and seq[f]["t"].endswith(".") and not tok[k] in ("sempre", "beleza", "enfim", "isso", "entendeu"):
            achados.append({"tipo": "frase solta", "auto": False, "j": k, "ini": seq[k]["ini"], "fim": seq[f]["fim"],
                            "texto": " ".join(w["t"] for w in seq[k:f + 1])})
        k = f + 1
    for x in achados:
        x["contexto"] = " ".join(w["t"] for w in seq[max(0, x["j"] - 10):x["j"] + 14])
    return sorted(achados, key=lambda x: x["ini"])


def tropecos(slug: str, aplicar: bool = False):
    p = proj(slug)
    projeto = ler(p / "projeto.json")
    cortes = ler(p / "trabalho" / "cortes.json")
    segs = cortes["segmentos"]
    achados = achar(literal(slug), segs)
    db = _energia(p / "trabalho" / "audio16k.wav")
    linhas = [f"# Tropeços em {slug} — tempo BRUTO (editado entre parênteses). auto = repetição exata.", ""]
    for x in achados:
        x["ini"], x["fim"] = _vale(db, x["ini"]), _vale(db, x["fim"])
        ed = _para_editado(segs, x["ini"])
        linhas.append(f"[{x['tipo']}{' · auto' if x['auto'] else ''}] bruto {x['ini']:.2f}–{x['fim']:.2f}"
                      f" (ed {hms(ed or 0)}): «{x['texto']}»\n      … {x['contexto']} …")
    (p / "trabalho" / "tropecos.txt").write_text("\n".join(linhas), encoding="utf-8")
    gravar(p / "trabalho" / "tropecos.json", achados)
    print(f"{len(achados)} tropeços ({sum(x['auto'] for x in achados)} automáticos) -> trabalho/tropecos.txt")
    if aplicar:
        rem = projeto.setdefault("remover", [])
        novos = [x for x in achados if x["auto"]
                 and not any(r["ini"] <= x["ini"] and x["fim"] <= r["fim"] for r in rem)]
        rem += [{"ini": x["ini"], "fim": x["fim"], "motivo": f"{x['tipo']}: {x['texto'][:60]}"} for x in novos]
        gravar(p / "projeto.json", projeto)
        print(f"{len(novos)} entraram em projeto.json → remover; rode `recortar`")
    return achados


def recortar(slug: str):
    """Corte novo sem perder o plano: beats, shorts, aulas e capítulos seguem a fala, não o relógio."""
    p = proj(slug)
    t = p / "trabalho"
    v = 1
    while (t / f"cortes_v{v}.json").exists() or (p / f"plano_v{v}.json").exists():
        v += 1
    shutil.copy2(t / "cortes.json", t / f"cortes_v{v}.json")
    antigos = ler(t / "cortes.json")["segmentos"]
    fala.cortar(slug)
    novos = ler(t / "cortes.json")["segmentos"]
    if not (p / "plano.json").exists():
        return
    shutil.copy2(p / "plano.json", p / f"plano_v{v}.json")
    plano = ler(p / "plano.json")

    fim = lambda segs: segs[-1]["ed_ini"] + segs[-1]["fonte_fim"] - segs[-1]["fonte_ini"]

    def m(x):
        # depois da última fala (o Encerramento) o _para_bruto cairia no INÍCIO do último trecho: conta do fim
        if x >= fim(antigos) - 0.5:
            return round(max(0.0, fim(novos) - (fim(antigos) - x)), 2)
        e = _para_editado(novos, _para_bruto(antigos, x))
        return round(e if e is not None else fim(novos), 2)

    for chave in ("beats", "shorts", "aulas"):
        for x in plano.get(chave, []):
            x["ini"], x["fim"] = m(x["ini"]), m(x["fim"])
    for c in plano.get("capitulos", []):
        c["ini"] = m(c["ini"]) if c["ini"] > 0 else 0
    gravar(p / "plano.json", plano)
    print(f"plano remapeado (backup plano_v{v}.json, cortes_v{v}.json)")
