"""Utilidades compartilhadas pelo motor do estúdio."""
import glob, json, os, site, subprocess, unicodedata, re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]          # motor/
# Projetos e biblioteca pesam GB: por padrão ficam em motor/ (ignorados pelo git); ESTUDIO_DADOS muda o lugar.
DADOS = Path(os.environ.get("ESTUDIO_DADOS") or RAIZ)
PROJETOS = DADOS / "projetos"
BIBLIOTECA = DADOS / "biblioteca"
GRAFICOS = RAIZ / "graficos"
FPS = 30
W, H = 1920, 1080


MARCAS = RAIZ / "marcas"

# Parâmetros que mudam entre vídeo de YouTube e aula (ver bíblia de estilo).
FORMATOS = {
    # punch-in alternado, corte justo, ~50% de tela cheia
    "video": {"punch_in": 1.18, "pausa_corte": 0.30, "tela_cheia": [0.15, 0.80], "capitulos_obrigatorios": False, "cor_auto": True},
    # sem punch-in (cortaria a tela compartilhada), pausa didática, menos grafismo, capítulos sempre
    "aula": {"punch_in": 1.0, "pausa_corte": 0.60, "tela_cheia": [0.0, 0.50], "capitulos_obrigatorios": True,
             "cor_auto": False},  # tela compartilhada: vinheta/tom quente sujariam o documento
}


def marca(nome="exemplo"):
    p = MARCAS / nome / "marca.json"
    if not p.exists():
        raise SystemExit(f"Marca '{nome}' não existe. Disponíveis: {[d.name for d in MARCAS.iterdir() if d.is_dir()]}")
    m = json.loads(p.read_text(encoding="utf-8"))
    m["_pasta"] = str(p.parent)
    return m


def marca_do(slug):
    return marca((ler(proj(slug) / "projeto.json") or {}).get("marca", "exemplo"))


def props_marca(m):
    """O que os templates recebem da marca."""
    return {k: m.get(k) for k in ("cores", "raio", "arroba", "nome", "fonte_titulo", "fonte_texto")}


def proj(slug) -> Path:
    p = PROJETOS / slug
    if not p.exists():
        raise SystemExit(f"Projeto não existe: {p}")
    return p


def ler(p, padrao=None):
    p = Path(p)
    if not p.exists():
        return padrao
    return json.loads(p.read_text(encoding="utf-8"))


def gravar(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def run(cmd, check=True):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if check and r.returncode != 0:
        raise RuntimeError(f"Falhou ({r.returncode}): {' '.join(map(str, cmd))[:400]}\n{r.stderr[-1500:]}")
    return r


def duracao(p) -> float:
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", p])
    return float(r.stdout.strip().replace(",", "."))


def video_info(p):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate", "-of", "json", p])
    s = json.loads(r.stdout)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return {"largura": s["width"], "altura": s["height"], "fps": round(float(n) / float(d), 3)}


def quadro(t: float) -> float:
    """Arredonda para a borda de quadro: áudio e vídeo cortam no mesmo instante."""
    return round(round(t * FPS) / FPS, 4)


def cuda_dlls():
    """faster-whisper na GPU precisa das DLLs do cuBLAS/cuDNN instaladas via pip."""
    for sp in site.getsitepackages():
        for d in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]


def normaliza(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", "", s).strip()


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normaliza(s)).strip("-")[:60] or "video"


def hms(t: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:04.1f}"
