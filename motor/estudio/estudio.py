"""Estúdio de edição automática — linha de comando.

  python estudio.py novo <gravacao_obs> --marca <pasta em marcas/> --formato video|aula [--slug X] [--glossario "..."]
        preparar + transcrever + cortar  (depois disso o diretor escreve plano.json)
  python estudio.py render <slug>
        gate do plano -> áudio -> câmera -> grafismos -> montagem -> shorts -> gate final
  python estudio.py dividir <slug>
        uma aula por tópico: lê "aulas" do plano.json do pai e cria os projetos-filhos (plano incluso)
  python estudio.py render-partes <slug>
        render de cada parte criada pelo dividir
  python estudio.py tropecos <slug> [--aplicar]
        transcrição literal (sem VAD) -> trabalho/tropecos.txt; --aplicar põe a repetição exata em "remover"
  python estudio.py recortar <slug>
        refaz o corte depois de mexer em "remover" e remapeia o plano.json (backup _vN)
  python estudio.py etapa <nome> <slug>
        roda uma etapa isolada: preparar|transcrever|cortar|cor|audio|aroll|graficos|montar|shorts|sfx
"""
import subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))
from comum import proj  # noqa: E402
import etapas_av as av  # noqa: E402
import etapas_fala as fala  # noqa: E402
import etapas_montagem as mt  # noqa: E402
import etapas_dividir as dv  # noqa: E402
import etapas_tropeco as tr  # noqa: E402

GATE = Path(__file__).parent / "gate.py"


def gate(modo, slug):
    r = subprocess.run([sys.executable, "-I", GATE, modo, proj(slug)], text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"Parado no gate do {modo}. Corrija e rode de novo.")


def main(a):
    if not a or a[0] in ("-h", "--help"):
        print(__doc__); return
    cmd = a[0]
    if cmd == "novo":
        opt = {a[i]: a[i + 1] for i in range(2, len(a) - 1, 2)}
        if "--marca" not in opt:
            raise SystemExit("Diga a marca: --marca <nome> (uma pasta em marcas/, ex.: exemplo)")
        slug = fala.preparar(a[1], opt.get("--slug"), opt.get("--glossario", ""), opt["--marca"],
                             opt.get("--formato", "video"))
        fala.transcrever(slug)
        fala.cortar(slug)
        av.medir_cor(slug)
        print(f"\nPróximo: o diretor lê projetos/{slug}/trabalho/roteiro_editado.txt e escreve plano.json")
        print(f"Slug: {slug}")
    elif cmd == "tropecos":
        tr.tropecos(a[1], aplicar="--aplicar" in a)
    elif cmd == "recortar":
        tr.recortar(a[1])
    elif cmd == "dividir":
        dv.dividir(a[1])
    elif cmd == "render-partes":
        from comum import PROJETOS
        resultado = {}
        for q in sorted(PROJETOS.glob(f"{a[1]}-p[0-9][0-9]-*")):
            print(f"\n=== {q.name}")
            try:
                main(["render", q.name])
                resultado[q.name] = "aprovada"
            except SystemExit as e:  # uma parte reprovada não segura as outras
                resultado[q.name] = f"REPROVADA ({e})"
        print("\nPartes:")
        for k, v in resultado.items():
            print(f"  {v:10} {k}")
        if any(v != "aprovada" for v in resultado.values()):
            raise SystemExit(1)
    elif cmd == "render":
        slug = a[1]
        gate("plano", slug)
        av.audio(slug)
        av.aroll(slug)
        mt.graficos(slug)
        mt.montar(slug)
        mt.shorts(slug)
        gate("final", slug)
    elif cmd == "etapa":
        nome, slug = a[1], a[2] if len(a) > 2 else None
        f = {"preparar": lambda: fala.preparar(slug), "transcrever": lambda: fala.transcrever(slug),
             "cortar": lambda: fala.cortar(slug), "cor": lambda: av.medir_cor(slug), "audio": lambda: av.audio(slug),
             "aroll": lambda: av.aroll(slug), "graficos": lambda: mt.graficos(slug), "montar": lambda: mt.montar(slug),
             "shorts": lambda: mt.shorts(slug), "sfx": mt.gerar_sfx,
             "gate-plano": lambda: gate("plano", slug), "gate-final": lambda: gate("final", slug)}[nome]
        f()
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
