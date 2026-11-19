# -*- coding: utf-8 -*-
"""Gate de publicação deste repositório: nada vai para o GitHub público sem exit 0.

Varre os arquivos que seriam publicados (rastreados + novos não ignorados pelo .gitignore; sem git, todos
menos .git e node_modules) e reprova dizendo arquivo:linha e o quê.

Uso: python -I tools/gate-publico.py [--raiz <pasta>] [--lista <arquivo de termos vetados>]

Regras:
  G00 lista de termos vetados ausente (o gate não roda pela metade)
  G01 segredo: chave sk-ant-/sk-/AIza/ghp_/github_pat_/xox*/AKIA, chave privada, password=/token=/senha= com valor
  G02 telefone brasileiro real (o placeholder é (00) 00000-0000)
  G03 e-mail que não é de exemplo (@example.com/.org/.net)
  G04 caminho pessoal (C:\\Users\\<nome>, /c/Users/<nome>, /home/<nome>, /Users/<nome>)
  G05 UUID real (deviceId do Chrome, IDs de sistemas) e ID numérico longo (Meta/Business/Pixel/App: 15–17 dígitos)
  G06 link do VDO.Ninja com senha
  G07 termo vetado da lista local (nomes de clientes, conteúdo de terceiros, IDs de conta), ou termo
      restrito fora dos arquivos permitidos
  G08 preço (R$ seguido de número)
  G09 arquivo binário grande (> 5 MB)
  G10 mídia que pode ser de cliente: vídeo, áudio, JPG/HEIC; PNG/GIF/WEBP fora de assets/ e motor/marcas/exemplo/

A lista local (padrão: tools/termos-vetados.local.txt, ignorada pelo git) tem um termo por linha;
"termo | arq1, arq2" permite o termo só nesses arquivos. A comparação ignora caixa e acento e casa por
palavra inteira (ou sequência de palavras). A lista nunca vai para o repositório: os nomes que ela barra
não podem aparecer nem no gate.
"""
import os, re, subprocess, sys, unicodedata
from pathlib import Path

LIMITE_BYTES = 5 * 1024 * 1024
MIDIA_SEMPRE = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".m4a", ".wav", ".mp3", ".aac", ".flac",
                ".jpg", ".jpeg", ".heic", ".heif", ".dng", ".raw", ".cr2", ".nef", ".pdf"}
IMAGEM_PERMITIDA_EM = ("assets/", "motor/marcas/exemplo/")
IMAGEM = {".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}

SEGREDOS = [
    ("chave Anthropic", re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}")),
    ("chave sk-", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("chave Google", re.compile(r"AIza[0-9A-Za-z_\-]{30,}")),
    ("token GitHub", re.compile(r"\b(ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("token Slack", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("chave AWS", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("chave privada", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----")),
]
# password=/token=/senha=/api_key=/secret= com valor (o valor começa por letra ou dígito: "password=/token="
# do próprio docstring não é valor, falso positivo de 18/11). Não conta: variável (${X}, $X, process.env, os.environ),
# placeholder (<...>, ..., xxx, ***), valor vazio e nome de variável seguido de leitura do ambiente.
ATRIB = re.compile(r"""(?i)\b(password|passwd|senha|token|api[_-]?key|secret|client[_-]?secret)\b["']?\s*[:=]\s*["']?([A-Za-z0-9][^\s"'<>,;)}\]]{5,})""")
VALOR_OK = re.compile(r"""(?i)^(\$|\{|process\.env|os\.environ|env\[|<|\.\.\.|x{3,}|\*{3,}|example|exemplo|sua[-_]|seu[-_]|none|null|true|false|undefined)""")

TEL = [re.compile(r"\(?\b[1-9]\d\)?\s?9\d{4}-?\d{4}\b"), re.compile(r"\b55[1-9]\d9\d{8}\b")]
# domínio com TLD de letras: "black@0.45" e "0x0E261B@0.78" são cor do ffmpeg, não e-mail (falso positivo, 18/11)
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9][A-Za-z0-9\-]*(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}(?![A-Za-z0-9])")
EMAIL_OK = re.compile(r"(?i)@(example\.(com|org|net)|exemplo\.com)$")
CAMINHO = re.compile(r"(?i)(?:\b[A-Z]:[\\/]+Users[\\/]+|/c/Users/|/home/|(?<![\w.])/Users/)(?!%|<|\$|Public\b|Default\b|seu|sua|you|user\b|usuario)[A-Za-z0-9]")
UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
UUID_OK = re.compile(r"^0{8}-0{4}-0{4}-0{4}-0{12}$")
ID_LONGO = re.compile(r"(?<![\w.\-])\d{15,17}(?![\w.\-])")
VDO = re.compile(r"(?i)vdo\.ninja\S*[?&](password|pw|p)=")
PRECO = re.compile(r"R\$\s?\d")


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def ler_lista(arq):
    termos = []
    for linha in Path(arq).read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        termo, _, perm = linha.partition("|")
        palavras = re.findall(r"[a-z0-9]+", norm(termo))
        if palavras:
            termos.append((termo.strip(), re.compile(r"(?<![a-z0-9])" + r"[^a-z0-9]+".join(palavras) + r"(?![a-z0-9])"),
                           {p.strip().replace("\\", "/") for p in perm.split(",") if p.strip()}))
    return termos


def arquivos(raiz):
    if (raiz / ".git").exists():
        r = subprocess.run(["git", "-C", str(raiz), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                           capture_output=True)
        if r.returncode == 0:
            return [raiz / p.decode("utf-8") for p in r.stdout.split(b"\0") if p and (raiz / p.decode("utf-8")).is_file()]
    out = []
    for d, dirs, fs in os.walk(raiz):
        dirs[:] = [x for x in dirs if x not in (".git", "node_modules")]
        out += [Path(d) / f for f in fs]
    return out


def checa(raiz, lista):
    erros = []
    if not lista or not Path(lista).exists():
        return [f"G00 lista de termos vetados não encontrada ({lista}); crie-a (pode ser vazia, se não há nada a vetar)"]
    termos = ler_lista(lista)
    for f in sorted(arquivos(raiz)):
        rel = f.relative_to(raiz).as_posix()
        if Path(lista).resolve() == f.resolve():
            erros.append(f"G07 {rel}: a lista local de termos vetados ia ser publicada (ponha no .gitignore)")
            continue
        tam = f.stat().st_size
        ext = f.suffix.lower()
        if tam > LIMITE_BYTES:
            erros.append(f"G09 {rel}: {tam/1e6:.1f} MB (máx. 5 MB)")
        if ext in MIDIA_SEMPRE:
            erros.append(f"G10 {rel}: mídia ({ext}) não vai para o repositório público")
            continue
        if ext in IMAGEM:
            if not rel.startswith(IMAGEM_PERMITIDA_EM):
                erros.append(f"G10 {rel}: imagem fora de {', '.join(IMAGEM_PERMITIDA_EM)}")
            continue
        dados = f.read_bytes()
        if b"\0" in dados[:8192]:
            continue  # binário: só tamanho e tipo
        texto = dados.decode("utf-8", errors="ignore")
        for n, linha in enumerate(texto.splitlines(), 1):
            onde = f"{rel}:{n}"
            for nome, rx in SEGREDOS:
                if rx.search(linha):
                    erros.append(f"G01 {onde}: {nome}")
            for m in ATRIB.finditer(linha):
                if not VALOR_OK.match(m.group(2)):
                    erros.append(f"G01 {onde}: {m.group(1)} com valor")
            for rx in TEL:
                for m in rx.finditer(linha):
                    erros.append(f"G02 {onde}: telefone {m.group(0)} (use (00) 00000-0000)")
            for m in EMAIL.finditer(linha):
                if not EMAIL_OK.search(m.group(0)):
                    erros.append(f"G03 {onde}: e-mail {m.group(0)} (use @example.com)")
            if CAMINHO.search(linha):
                erros.append(f"G04 {onde}: caminho pessoal ({CAMINHO.search(linha).group(0)}…); use %USERPROFILE%, ~ ou caminho relativo")
            for m in UUID.finditer(linha):
                if not UUID_OK.match(m.group(0)):
                    erros.append(f"G05 {onde}: UUID {m.group(0)[:8]}… (deviceId/ID real?)")
            if not rel.endswith("package-lock.json"):
                for m in ID_LONGO.finditer(linha):
                    erros.append(f"G05 {onde}: ID numérico longo {m.group(0)[:4]}… (conta/página/app?)")
            if VDO.search(linha):
                erros.append(f"G06 {onde}: link do VDO.Ninja com senha")
            nl = norm(linha)
            for termo, rx, perm in termos:
                if rx.search(nl) and rel not in perm:
                    erros.append(f"G07 {onde}: termo vetado \"{termo}\"" + (f" (só pode em {', '.join(sorted(perm))})" if perm else ""))
            if PRECO.search(linha):
                erros.append(f"G08 {onde}: preço ({PRECO.search(linha).group(0)}…)")
    return erros


def main(a):
    raiz = Path(a[a.index("--raiz") + 1]) if "--raiz" in a else Path(__file__).resolve().parents[1]
    lista = a[a.index("--lista") + 1] if "--lista" in a else str(raiz / "tools" / "termos-vetados.local.txt")
    erros = checa(raiz.resolve(), lista)
    n = len(arquivos(raiz.resolve()))
    if erros:
        print(f"GATE PÚBLICO REPROVADO — {len(erros)} problema(s) em {n} arquivos:")
        for e in erros:
            print("  ✗", e)
        return 1
    print(f"GATE PÚBLICO APROVADO — {n} arquivos varridos, {len(ler_lista(lista))} termos vetados conferidos.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
