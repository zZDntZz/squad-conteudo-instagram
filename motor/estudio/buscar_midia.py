"""Pesquisa e baixa mídia licenciada para assets/ do projeto, registrando a licença.

  python buscar_midia.py <slug> video "money counting" [--n 3]
  python buscar_midia.py <slug> foto  "banco central brasilia" [--n 3]
  python buscar_midia.py <slug> print "https://site/noticia" [--largura 1280]

Fontes: Pexels (vídeo/foto, chave PEXELS_API_KEY), Pixabay (vídeo/foto, PIXABAY_API_KEY),
Wikimedia Commons (foto, sem chave — só licenças livres). Chaves ficam em motor/.env (ou no ambiente).
Print de página: Chrome headless local; usar só trecho curto, sempre com crédito ao veículo.
Toda mídia baixada entra em assets/licencas.json — sem isso o gate P06 reprova o plano.
"""
import json, os, re, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comum import RAIZ, ler, gravar, proj, slugify  # noqa: E402

UA = {"User-Agent": "squad-conteudo-instagram/1.0 (uso pessoal)"}


def env():
    e = {}
    f = RAIZ / ".env"
    if f.exists():
        for l in f.read_text(encoding="utf-8").splitlines():
            if "=" in l and not l.startswith("#"):
                k, v = l.split("=", 1)
                e[k.strip()] = v.strip()
    return {**e, **os.environ}


def get(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def baixar(url, destino: Path):
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(get(url))
    return destino


def registrar(p: Path, rel: str, **info):
    lic = ler(p / "assets" / "licencas.json", {}) or {}
    lic[rel] = info
    gravar(p / "assets" / "licencas.json", lic)


def pexels(chave, tipo, q, n):
    if tipo == "video":
        j = json.loads(get(f"https://api.pexels.com/videos/search?query={urllib.parse.quote(q)}&per_page={n}&orientation=landscape",
                           {"Authorization": chave}))
        for v in j.get("videos", []):
            arqs = sorted([f for f in v["video_files"] if (f.get("width") or 0) >= 1280 and f.get("file_type") == "video/mp4"],
                          key=lambda f: abs((f.get("width") or 0) - 1920))
            if arqs:
                yield arqs[0]["link"], "mp4", {"origem": v["url"], "autor": v["user"]["name"], "licenca": "Pexels License"}
    else:
        j = json.loads(get(f"https://api.pexels.com/v1/search?query={urllib.parse.quote(q)}&per_page={n}&orientation=landscape",
                           {"Authorization": chave}))
        for f in j.get("photos", []):
            yield f["src"]["large2x"], "jpg", {"origem": f["url"], "autor": f["photographer"], "licenca": "Pexels License"}


def pixabay(chave, tipo, q, n):
    base = "https://pixabay.com/api/videos/" if tipo == "video" else "https://pixabay.com/api/"
    j = json.loads(get(f"{base}?key={chave}&q={urllib.parse.quote(q)}&per_page={max(3, n)}&safesearch=true"))
    for h in j.get("hits", [])[:n]:
        if tipo == "video":
            v = h["videos"].get("large") or h["videos"].get("medium")
            if v and v.get("url"):
                yield v["url"], "mp4", {"origem": h["pageURL"], "autor": h["user"], "licenca": "Pixabay Content License"}
        else:
            yield h["largeImageURL"], "jpg", {"origem": h["pageURL"], "autor": h["user"], "licenca": "Pixabay Content License"}


LIVRES = re.compile(r"^(cc0|cc[ -]by(-sa)?|public domain|pd)", re.I)


def commons(q, n):
    api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6"
           f"&gsrlimit={n * 3}&gsrsearch={urllib.parse.quote(q)}&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=1920")
    j = json.loads(get(api))
    achados = 0
    for pg in (j.get("query", {}).get("pages", {}) or {}).values():
        ii = (pg.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        if not LIVRES.match(lic) or not ii.get("thumburl"):
            continue
        autor = re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()
        ext = "png" if ii["thumburl"].lower().endswith(".png") else "jpg"
        yield ii["thumburl"], ext, {"origem": ii.get("descriptionurl"), "autor": autor, "licenca": lic, "exige_credito": not lic.lower().startswith(("cc0", "public", "pd"))}
        achados += 1
        if achados >= n:
            break


def chrome():
    for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if Path(c).exists():
            return c
    raise SystemExit("Chrome/Edge não encontrado para print de página.")


def printar(p, url, largura=1280, altura=1600):
    nome = f"prints/{slugify(urllib.parse.urlparse(url).netloc + '-' + urllib.parse.urlparse(url).path)[:50]}.png"
    destino = p / "assets" / nome
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={largura},{altura}",
                    f"--screenshot={destino}", "--virtual-time-budget=8000", url], capture_output=True, timeout=90)
    if not destino.exists():
        raise SystemExit("Print falhou: " + url)
    registrar(p, nome, origem=url, autor=urllib.parse.urlparse(url).netloc, licenca="print citado com crédito ao veículo (trecho curto)",
              largura=largura, altura=altura)
    print(nome)


def main(a):
    sys.stdout.reconfigure(encoding="utf-8")
    if len(a) < 3:
        print(__doc__); return
    slug, tipo, q = a[0], a[1], a[2]
    opt = {a[i]: a[i + 1] for i in range(3, len(a) - 1, 2)}
    p = proj(slug)
    if tipo == "print":
        return printar(p, q, int(opt.get("--largura", 1280)))
    n = int(opt.get("--n", 3))
    e = env()
    fontes = []
    if e.get("PEXELS_API_KEY"):
        fontes.append(pexels(e["PEXELS_API_KEY"], tipo, q, n))
    if e.get("PIXABAY_API_KEY"):
        fontes.append(pixabay(e["PIXABAY_API_KEY"], tipo, q, n))
    if tipo == "foto":
        fontes.append(commons(q, n))
    if not fontes:
        raise SystemExit("Sem fonte de vídeo: configure PEXELS_API_KEY ou PIXABAY_API_KEY em motor/.env")
    k = 0
    for gen in fontes:
        try:
            for url, ext, info in gen:
                if k >= n:
                    break
                rel = f"{'broll' if tipo == 'video' else 'fotos'}/{slugify(q)}-{k + 1}.{ext}"
                baixar(url, p / "assets" / rel)
                registrar(p, rel, consulta=q, **info)
                print(rel, "—", info["licenca"], "—", info["origem"])
                k += 1
        except Exception as ex:  # uma fonte fora do ar não derruba as outras
            print("fonte falhou:", str(ex)[:150])
        if k >= n:
            break


if __name__ == "__main__":
    main(sys.argv[1:])
