"""Etapas 4–5: voz tratada e câmera (A-roll) cortada, enquadrada e corrigida."""
import hashlib, json, re, wave
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from comum import FPS, H, W, gravar, ler, marca_do, proj, run

# ---------------------------------------------------------------- áudio

CADEIA_VOZ = ("highpass=f=80,afftdn=nr=10:nf=-42,deesser=i=0.35,"
              "acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2")


def _ler_wav(p):
    with wave.open(str(p), "rb") as w:
        sr, ch = w.getframerate(), w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch)
    return sr, a.astype(np.float32)


def _gravar_wav(p, sr, a):
    with wave.open(str(p), "wb") as w:
        w.setnchannels(a.shape[1]); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(np.clip(a, -32768, 32767).astype(np.int16).tobytes())


def audio(slug: str):
    p = proj(slug)
    t = p / "trabalho"
    segs = ler(t / "cortes.json")["segmentos"]
    sr, a = _ler_wav(t / "audio48k.wav")
    rampa = int(sr * 0.008)  # 8 ms: some o estalo do corte sem engolir consoante
    partes = []
    for s in segs:
        i0, i1 = round(s["fonte_ini"] * sr), round(s["fonte_fim"] * sr)
        trecho = a[i0:i1].copy()
        n = len(trecho)
        if n < 1:
            continue
        r = min(rampa, n // 2)
        env = np.ones(n, dtype=np.float32)
        env[:r] = np.linspace(0, 1, r); env[n - r:] = np.linspace(1, 0, r)
        partes.append(trecho * env[:, None])
    _gravar_wav(t / "voz_cortada.wav", sr, np.concatenate(partes))

    # loudnorm em duas passadas: a primeira mede, a segunda aplica linear (sem bombear).
    alvo = marca_do(slug).get("loudness_alvo_lufs", -14)
    r = run(["ffmpeg", "-hide_banner", "-i", t / "voz_cortada.wav", "-af",
             f"{CADEIA_VOZ},loudnorm=I={alvo}:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"])
    m = json.loads(re.findall(r"\{[^{}]+\}", r.stderr)[-1])
    ln = (f"loudnorm=I={alvo}:TP=-1.5:LRA=9:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    run(["ffmpeg", "-y", "-v", "error", "-i", t / "voz_cortada.wav", "-af", f"{CADEIA_VOZ},{ln}",
         "-ar", "48000", "-c:a", "pcm_s16le", t / "voz.wav"])
    print("voz.wav pronta (entrada medida:", m["input_i"], "LUFS)")

# ---------------------------------------------------------------- cor

def medir_cor(slug: str) -> str:
    """Colorista automático: lê exposição/saturação da fonte e devolve a correção."""
    p = proj(slug)
    projeto = ler(p / "projeto.json")
    r = run(["ffmpeg", "-hide_banner", "-i", projeto["fonte"], "-an", "-vf",
             "fps=1/15,scale=320:-2,signalstats,metadata=print", "-f", "null", "-"])
    txt = r.stdout + r.stderr
    y = [float(v) for v in re.findall(r"YAVG=([0-9.]+)", txt)]
    s = [float(v) for v in re.findall(r"SATAVG=([0-9.]+)", txt)]
    y = sum(y) / len(y) if y else 110
    s = sum(s) / len(s) if s else 20
    brilho = max(-0.12, min(0.12, (108 - y) / 255 * 0.9))        # mira o meio-tom da referência (~108)
    sat = max(0.95, min(1.35, 1 + (24 - s) / 60))
    gamma = 1.0 + max(-0.1, min(0.2, (108 - y) / 300))
    filtro = (f"eq=brightness={brilho:.3f}:contrast=1.08:gamma={gamma:.3f}:saturation={sat:.2f},"
              "colorbalance=rs=0.03:gs=0.0:bs=-0.04:rh=0.02:bh=-0.03,"   # sombras e altas levemente quentes
              "vignette=angle=PI/5:mode=forward,unsharp=5:5:0.4")
    from comum import FORMATOS
    if not FORMATOS.get(projeto.get("formato", "video"), {}).get("cor_auto", True):
        filtro = "null"  # aula: a tela compartilhada sai como o OBS gravou
    projeto["cor_medida"] = {"yavg": round(y, 1), "satavg": round(s, 1)}
    if not projeto.get("cor"):
        projeto["cor_auto"] = filtro
    gravar(p / "projeto.json", projeto)
    print(f"Exposição média {y:.0f}, saturação {s:.0f} -> {filtro}")
    return projeto.get("cor") or filtro

# ---------------------------------------------------------------- câmera (A-roll)

def _vf(escala, enq, cor):
    cx, cy = enq["cx"], enq["cy"]
    crop = ""
    if escala > 1.001:
        crop = (f"crop=iw/{escala}:ih/{escala}:"
                f"'min(max(iw*{cx}-iw/{escala}/2,0),iw-iw/{escala})':"
                f"'min(max(ih*{cy}-ih/{escala}/2,0),ih-ih/{escala})',")
    return f"{crop}scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS},{cor},format=yuv420p"


def aroll(slug: str, trabalhadores: int = 3):
    p = proj(slug)
    projeto = ler(p / "projeto.json")
    segs = ler(p / "trabalho" / "cortes.json")["segmentos"]
    cor = projeto.get("cor") or projeto.get("cor_auto") or medir_cor(slug)
    pasta = p / "trabalho" / "aroll"
    pasta.mkdir(exist_ok=True)
    fundo = projeto.get("cenario")  # cenário virtual: vídeo já com fundo trocado
    fonte = fundo or projeto["fonte"]

    def um(k_s):
        k, s = k_s
        # cache pelo CONTEÚDO do trecho: chave só pelo índice reaproveitou vídeo do corte anterior depois de
        # um "remover" novo (Parte 09 de um curso, 11/10: aroll 154 s × voz 166,5 s, gate F02 pegou)
        chave = hashlib.sha1(json.dumps([fonte, s["fonte_ini"], s["fonte_fim"], s["escala"],
                                         projeto["enquadramento"], cor], sort_keys=True).encode()).hexdigest()[:10]
        out = pasta / f"{k:04d}-{chave}.mp4"
        n = round((s["fonte_fim"] - s["fonte_ini"]) * FPS)
        if out.exists() and out.stat().st_size > 0:
            return out
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{s['fonte_ini']:.4f}", "-i", fonte, "-an",
             "-vf", _vf(s["escala"], projeto["enquadramento"], cor), "-frames:v", n,
             "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "17", "-b:v", "0", "-g", "60", out])
        return out

    with ThreadPoolExecutor(trabalhadores) as ex:
        arqs = list(ex.map(um, enumerate(segs)))
    lista = pasta / "lista.txt"
    lista.write_text("".join(f"file '{a.name}'\n" for a in arqs), encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", p / "trabalho" / "aroll.mp4"])
    print(f"aroll.mp4: {len(arqs)} trechos")
