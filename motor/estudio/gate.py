"""Gate do estúdio: decide se o plano pode ir para render e se o final pode ir ao ar.

Uso:  python gate.py plano <pasta_projeto>
      python gate.py final <pasta_projeto>
Saída 0 = pode; 1 = não pode (lista o que quebrou e onde).

Origem de cada regra entre colchetes: [reels] = defeito real da fábrica de reels
(ago/2026); [preventiva] = risco conhecido do formato, ainda não vivido aqui.
"""
import json, re, subprocess, sys
from pathlib import Path

TEMPLATES = {"TextoCinetico", "Manchete", "Print", "Numero", "Comparacao", "Lista", "Grafico",
             "Citacao", "PalavraChave", "Legenda", "Encerramento"}
FAIXA_TELA_CHEIA = {"video": (0.15, 0.80), "aula": (0.0, 0.50)}  # espelha comum.FORMATOS
# "todo" minúsculo é português ("Biologia em todo o canteiro", aula de solo 13/10, falso positivo):
# marcador de pendência só em caixa alta (TODO/FIXME); o resto continua sem diferenciar caixa.
PLACEHOLDER = re.compile(r"\b(?:(?i:lorem|xxx|exemplo de|placeholder)|TODO|FIXME)\b")
CHAVES_ARQUIVO = ("imagem", "src", "fundoImagem")


def _run(cmd):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="ignore")


def _arquivos(props):
    for k, v in props.items():
        if k in CHAVES_ARQUIVO and isinstance(v, str) and not v.startswith("http"):
            yield v
        elif isinstance(v, dict):
            yield from _arquivos(v)


def _textos(props):
    for v in props.values():
        if isinstance(v, str):
            yield v
        elif isinstance(v, dict):
            yield from _textos(v)
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, dict):
                    yield from _textos(x)
                elif isinstance(x, str):
                    yield x


def gate_plano(p: Path):
    erros = []
    plano = json.loads((p / "plano.json").read_text(encoding="utf-8"))
    cortes = json.loads((p / "trabalho" / "cortes.json").read_text(encoding="utf-8"))
    dur = cortes["duracao_editada"]
    lic_p = p / "assets" / "licencas.json"
    licencas = json.loads(lic_p.read_text(encoding="utf-8")) if lic_p.exists() else {}
    beats = plano.get("beats", [])
    cheios = []
    for b in beats:
        i, props = b.get("id", "?"), b.get("props", {})
        ini, fim = float(b.get("ini", -1)), float(b.get("fim", -1))
        # P01 [preventiva] grafismo fora da linha do tempo ou curto demais pisca e some.
        if not (0 <= ini < fim <= dur + 0.05):
            erros.append(f"P01 {i}: tempo {ini}–{fim} fora de 0–{dur:.2f}s")
        elif fim - ini < 0.8:
            erros.append(f"P01 {i}: dura {fim - ini:.2f}s (mínimo 0,8s)")
        # P03 [preventiva] template inexistente quebra o render no meio do lote.
        if b.get("template") not in TEMPLATES:
            erros.append(f"P03 {i}: template '{b.get('template')}' não existe")
        if b.get("modo", "cheio") == "cheio":
            cheios.append((ini, fim, i))
        # P04 [preventiva] dado sem fonte não vai ao ar.
        if b.get("template") == "Grafico" and not str(props.get("fonte", "")).strip():
            erros.append(f"P04 {i}: gráfico sem 'fonte'")
        if b.get("template") == "Manchete":
            for k in ("veiculo", "data", "url"):
                if not str(props.get(k, "")).strip():
                    erros.append(f"P04 {i}: manchete sem '{k}' (precisa ser verificável)")
        # P05 [preventiva] citar terceiros só em trecho curto, com crédito.
        if b.get("template") == "Manchete" and len(props.get("titulo", "")) > 160:
            erros.append(f"P05 {i}: título citado com {len(props['titulo'])} caracteres (máx. 160)")
        if b.get("template") == "Citacao" and len(props.get("texto", "")) > 240:
            erros.append(f"P05 {i}: citação com {len(props['texto'])} caracteres (máx. 240)")
        # P06 [reels] mídia ausente gerou segmento vazio sem erro visível; e mídia sem licença não entra.
        for a in _arquivos(props):
            if not (p / "assets" / a).exists():
                erros.append(f"P06 {i}: arquivo '{a}' não existe em assets/")
            elif a not in licencas or not licencas[a].get("licenca") or not licencas[a].get("origem"):
                erros.append(f"P06 {i}: '{a}' sem origem/licença em assets/licencas.json")
        # P09 [preventiva] texto de exemplo esquecido no plano.
        for txt in _textos(props):
            if PLACEHOLDER.search(txt):
                erros.append(f"P09 {i}: texto provisório '{txt[:40]}'")
    # P02 [preventiva] dois grafismos de tela cheia ao mesmo tempo: um some atrás do outro.
    cheios.sort()
    for (a0, a1, ia), (b0, b1, ib) in zip(cheios, cheios[1:]):
        if b0 < a1 - 0.01:
            erros.append(f"P02 {ia} e {ib} se sobrepõem ({b0:.2f} < {a1:.2f})")
    projeto = json.loads((p / "projeto.json").read_text(encoding="utf-8")) if (p / "projeto.json").exists() else {}
    formato = projeto.get("formato", "video")
    lo, hi = FAIXA_TELA_CHEIA.get(formato, (0.15, 0.80))
    # P07 [preventiva] ritmo: no vídeo, ~metade do tempo é grafismo; na aula, a tela compartilhada já é o visual.
    if dur > 30:  # vídeo curto (vinheta) não tem ritmo a medir
        frac = sum(f - i for i, f, _ in cheios) / dur
        if not lo <= frac <= hi:
            erros.append(f"P07 tela cheia ocupa {frac:.0%} do vídeo (formato {formato}: {lo:.0%}–{hi:.0%})")
    # P10 [preventiva] capítulos do YouTube só funcionam com 1º em 00:00, 3+ capítulos e 10 s+ cada.
    caps = sorted(float(c["ini"]) for c in plano.get("capitulos", []))
    if caps or (formato == "aula" and dur > 300):
        if len(caps) < 3:
            erros.append(f"P10 {len(caps)} capítulo(s): o YouTube exige 3 ou mais" + (" (aula > 5 min exige capítulos)" if formato == "aula" else ""))
        elif caps[0] != 0:
            erros.append(f"P10 primeiro capítulo em {caps[0]}s (precisa começar em 0)")
        for a, b in zip(caps, caps[1:] + [dur]):
            if b - a < 10:
                erros.append(f"P10 capítulo em {a:.0f}s dura {b - a:.1f}s (mínimo 10 s)")
        if caps and caps[-1] > dur:
            erros.append(f"P10 capítulo em {caps[-1]:.0f}s depois do fim ({dur:.0f}s)")
    # P11 short de aula sem recorte decidido: na cena "Principal + Tela" o recorte central pegou o documento
    #     e perdeu o rosto (aula de curso, 11/10). Aula com short precisa de projeto.json → "pilha"
    #     (câmera + tela empilhadas) ou "short_central": true (aula só de câmera).
    if formato == "aula" and plano.get("shorts") and not (projeto.get("pilha") or projeto.get("short_central")):
        erros.append('P11 short de aula sem recorte decidido: defina projeto.json → "pilha" '
                     '{camera, tela} ou "short_central": true')
    # P08 [preventiva] short fora do formato da plataforma.
    for s in plano.get("shorts", []):
        d = float(s["fim"]) - float(s["ini"])
        if not 15 <= d <= 90 or float(s["fim"]) > dur + 0.05:
            erros.append(f"P08 short {s.get('id')}: {d:.1f}s (15–90s, dentro do vídeo)")
    return erros


def _probe(arq):
    r = _run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
              "stream=width,height,r_frame_rate:format=duration", "-of", "json", arq])
    j = json.loads(r.stdout or "{}")
    s = (j.get("streams") or [{}])[0]
    n, d = (s.get("r_frame_rate") or "0/1").split("/")
    return s.get("width"), s.get("height"), round(float(n) / float(d), 2), float(j.get("format", {}).get("duration", 0))


def gate_final(p: Path):
    erros = []
    slug = p.name
    final = p / "final" / f"{slug}.mp4"
    if not final.exists() or final.stat().st_size == 0:
        return [f"F01 final não existe: {final}"]
    w, h, fps, dur = _probe(final)
    # F01 [preventiva] formato do canal.
    if (w, h) != (1920, 1080) or abs(fps - 30) > 0.01:
        erros.append(f"F01 {w}x{h} {fps}fps (esperado 1920x1080 30fps)")
    # F02 [reels] arquivo truncado por disco cheio ('moov atom not found') saiu sem erro.
    esperado = json.loads((p / "trabalho" / "cortes.json").read_text(encoding="utf-8"))["duracao_editada"]
    if abs(dur - esperado) > 0.5:
        erros.append(f"F02 duração {dur:.2f}s ≠ linha do tempo {esperado:.2f}s")
    # F03 [reels] narração saiu em −20/−22 LUFS, baixa perto dos outros vídeos.
    r = _run(["ffmpeg", "-hide_banner", "-i", final, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
    i = re.findall(r"I:\s+(-?[0-9.]+) LUFS", r.stderr)
    tp = re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", r.stderr)
    if not i:
        erros.append("F03 sem áudio mensurável")
    else:
        lufs, pico = float(i[-1]), float(tp[-1]) if tp else 0
        if abs(lufs + 14) > 1.5:
            erros.append(f"F03 loudness {lufs} LUFS (alvo −14 ±1,5)")
        if pico > -0.9:
            erros.append(f"F03 pico {pico} dBTP (máx. −1)")
    # F04 [reels] clipe ausente virou trecho preto sem erro.
    r = _run(["ffmpeg", "-hide_banner", "-i", final, "-an", "-vf", "blackdetect=d=0.5:pix_th=0.06", "-f", "null", "-"])
    for a, b in re.findall(r"black_start:([0-9.]+) black_end:([0-9.]+)", r.stderr):
        erros.append(f"F04 tela preta {float(a):.1f}–{float(b):.1f}s")
    # F05 [preventiva] buraco de áudio (corte errado ou mixagem perdida).
    r = _run(["ffmpeg", "-hide_banner", "-i", final, "-vn", "-af", "silencedetect=n=-45dB:d=2", "-f", "null", "-"])
    for a in re.findall(r"silence_start: ([0-9.]+)", r.stderr):
        erros.append(f"F05 silêncio de 2s+ em {float(a):.1f}s")
    # F06 [reels] clipe horizontal entrou num vertical.
    for s in (p / "final").glob("short_*.mp4"):
        sw, sh, _, sd = _probe(s)
        if (sw, sh) != (1080, 1920):
            erros.append(f"F06 {s.name}: {sw}x{sh} (esperado 1080x1920)")
        if not 15 <= sd <= 90.5:
            erros.append(f"F06 {s.name}: {sd:.1f}s fora de 15–90s")
    # F07 [aula de curso, 11/10] "Corta essa parte." foi ao ar na Parte 09: o Whisper do motor (com VAD)
    # pulou a frase, então ela nunca entrou no roteiro. O gate reouve o ÁUDIO DO FINAL, sem VAD.
    frases, palavras = _ouvir(final)
    for t, seg in frases:
        # frase a frase: no modo literal o Whisper junta "Etapa. Perfeito. Quase essa parte." num segmento só,
        # e a regra da frase solta ("^… essa parte$") deixava de casar (autoteste, 12/10)
        frase = next((f for f in re.split(r"(?<=[.!?])\s+", seg) if BASTIDOR.search(f)), None)
        if frase:
            erros.append(f"F07 fala de bastidor em {t:.1f}s: \"{frase}\" — cortar via projeto.json → remover")
    # F08 [aula de vasos, 12/10] "uma faixa, uma faixa", "o alimento, o alimento", "1%, 1%" ficaram no ar: o
    # Whisper com VAD funde as duas tentativas e o roteiro sai limpo. Reouve o final em modo literal.
    for t, texto in _repeticoes(palavras):
        erros.append(f"F08 tropeço (repetição) em {t:.1f}s: \"{texto}\" — `estudio.py tropecos` e cortar via remover")
    return erros


# Instrução de edição falada na gravação. "cortar" sozinho é conteúdo em curso de jardinagem
# ("cortar o galho"); só reprova a forma de bastidor.
BASTIDOR = re.compile(
    r"\b(corta|cortar|corte|tira|tirar|apaga|apagar)\s+(essa|esta|esse|este|isso|isto)\s+(parte|trecho|peda[çc]o|fala|frase)\b"
    r"|\b(essa|esta|esse|este)\s+(parte|trecho|peda[çc]o)\s+(a gente\s+|voc[êe]\s+)?(pode\s+)?(corta|cortar|tira|tirar|apaga|apagar)\b"
    r"|\bpode\s+(cortar|tirar|apagar)\s*([.,!?]|$)"
    r"|\b(na|da|pra|para a)\s+edi[çc][ãa]o\b"
    r"|\b(vou\s+regravar|regrava\b|deixa\s+eu\s+(repetir|refazer|come[çc]ar\s+de\s+novo)|vou\s+come[çc]ar\s+de\s+novo)"
    # frase solta "<verbo> essa parte." — o Whisper ouviu "Corta" como "Quase" no autoteste; sozinha, é bastidor
    r"|^\W*\w+\s+(essa|esta|esse|este)\s+(parte|trecho|peda[çc]o)\W*$",
    re.I)


# repetição que é a língua, não tropeço ("o que que é"; "e é" vira "e e" sem acento)
REPETICAO_OK = {("que",), ("e",)}


def _norm(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", t.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in t if not unicodedata.combining(c)))


def _fim_de_frase(w):
    """"." e "?" são fronteira; reticências são hesitação ("uma... uma faixa") e contam como tropeço."""
    w = w.rstrip()
    return w[-1:] in ".?!" and not w.endswith("...")


def _repeticoes(palavras):
    """Repetição imediata de 1–4 palavras. Fronteira de frase ("o vaso. O vaso é…", "o sal? O sal são…")
    não conta: é estilo, e o Whisper só pontua assim quando há pausa de fato."""
    tok = [_norm(w[1]) for w in palavras]
    achados, j = [], 0
    while j < len(tok):
        for n in (4, 3, 2, 1):
            a, b = tok[j:j + n], tok[j + n:j + 2 * n]
            if (j + 2 * n <= len(tok) and a == b and all(a) and tuple(a) not in REPETICAO_OK
                    and not _fim_de_frase(palavras[j + n - 1][1])):
                achados.append((palavras[j][0], " ".join(w[1] for w in palavras[j:j + 2 * n])))
                j += 2 * n - 1
                break
        j += 1
    return achados


PROMPT_LITERAL = ("Então, ãh, é... o o vaso, né, o vaso ele, ele precisa, tipo, hum, a gente a gente vai ver, "
                  "tá certo? Uma faixa, uma faixa ideal.")


def _ouvir(arq):
    """Transcrição literal do final: (frases, palavras) com tempo."""
    import glob, os, site
    for sp in site.getsitepackages():  # DLLs do cuBLAS/cuDNN instaladas via pip (ver comum.cuda_dlls)
        for d in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
    from faster_whisper import WhisperModel
    try:
        m = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")
    except Exception:
        m = WhisperModel("small", device="cpu", compute_type="int8")
    # prompt disfluente: o Whisper imita o estilo do prompt e passa a escrever a repetição em vez de limpá-la
    segs = list(m.transcribe(str(arq), language="pt", vad_filter=False, beam_size=5, word_timestamps=True,
                             condition_on_previous_text=False, initial_prompt=PROMPT_LITERAL)[0])
    return ([(s.start, s.text.strip()) for s in segs],
            [(w.start, w.word.strip()) for s in segs for w in (s.words or []) if w.word.strip()])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3 or sys.argv[1] not in ("plano", "final"):
        print(__doc__); sys.exit(2)
    p = Path(sys.argv[2]).resolve()
    erros = gate_plano(p) if sys.argv[1] == "plano" else gate_final(p)
    if erros:
        print(f"GATE {sys.argv[1].upper()} REPROVADO — {len(erros)} problema(s):")
        for e in erros:
            print("  ✗", e)
        sys.exit(1)
    print(f"GATE {sys.argv[1].upper()} APROVADO")
    sys.exit(0)


if __name__ == "__main__":
    main()
