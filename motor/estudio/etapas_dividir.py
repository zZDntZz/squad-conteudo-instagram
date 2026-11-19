"""Dividir uma gravação longa em aulas por tópico.

O diretor marca no plano.json do projeto-pai:
  "aulas": [{"titulo": "Boas-vindas", "ini": 0, "fim": 115.5}, ...]   (tempos da linha editada do pai)

Cada aula vira um projeto-filho `<pai>-pNN-<titulo>` com a mesma gravação e uma `janela` em tempo
bruto. O filho reaproveita a transcrição e o áudio (sem novo Whisper), passa de novo pelo `cortar`
e ganha o próprio plano: os beats do pai que cabem nele (tempos remapeados), o rótulo do tópico na
abertura, "A seguir: …" no fim (ou o Encerramento do pai na última) e os shorts que cabem nele.
Depois disso cada filho é um projeto comum: gate-plano, render, gate final.
"""
import shutil

from comum import PROJETOS, gravar, hms, ler, proj, slugify
import etapas_fala as fala

ROTULO_S = 5.0  # duração do rótulo de abertura e do "A seguir"


def _para_bruto(segs, t):
    """Tempo da linha editada -> tempo da gravação bruta."""
    for s in segs:
        fim_ed = s["ed_ini"] + (s["fonte_fim"] - s["fonte_ini"])
        if s["ed_ini"] - 0.001 <= t <= fim_ed + 0.001:
            return s["fonte_ini"] + (t - s["ed_ini"])
    # caiu num corte: vai para o início do trecho seguinte
    seg = next((s for s in segs if s["ed_ini"] >= t), segs[-1])
    return seg["fonte_ini"]


def _para_editado(segs, b):
    for s in segs:
        if s["fonte_ini"] - 0.001 <= b <= s["fonte_fim"] + 0.001:
            return s["ed_ini"] + (b - s["fonte_ini"])
    seg = next((s for s in segs if s["fonte_ini"] >= b), None)
    return seg["ed_ini"] if seg else None


def _janela(cortes_pai, ini, fim):
    """Janela bruta da aula: da 1ª palavra que começa em `ini` até a última que termina em `fim`."""
    pal = [w for w in cortes_pai["palavras"] if w["ini"] >= ini - 0.05 and w["fim"] <= fim + 0.05]
    if not pal:
        raise SystemExit(f"Aula {hms(ini)}–{hms(fim)} não tem fala.")
    segs = cortes_pai["segmentos"]
    a = _para_bruto(segs, pal[0]["ini"]) - fala.FOLGA_INI
    b = _para_bruto(segs, pal[-1]["fim"]) + fala.FOLGA_FIM
    return round(max(0, a), 3), round(b, 3)


def dividir(slug: str):
    p = proj(slug)
    projeto = ler(p / "projeto.json")
    plano = ler(p / "plano.json")
    cortes = ler(p / "trabalho" / "cortes.json")
    aulas = plano.get("aulas") or []
    if len(aulas) < 2:
        raise SystemExit('plano.json precisa de "aulas": [{titulo, ini, fim}, ...] com 2 ou mais.')
    filhos = []
    base = int(plano.get("parte_inicial", 1))   # continuação de uma aula já dividida (ex.: app = partes 7+)
    for n, aula in enumerate(aulas, base):
        filho = f"{slug}-p{n:02d}-{slugify(aula['titulo'])[:40]}"
        q = PROJETOS / filho
        for sub in ("trabalho", "graficos", "final"):
            (q / sub).mkdir(parents=True, exist_ok=True)
        if (p / "assets").exists():
            shutil.copytree(p / "assets", q / "assets", dirs_exist_ok=True)
        for f in ("audio16k.wav", "audio48k.wav", "quadro_ref.jpg", "transcricao.json"):
            shutil.copy2(p / "trabalho" / f, q / "trabalho" / f)
        j0, j1 = _janela(cortes, float(aula["ini"]), float(aula["fim"]))
        pf = {k: v for k, v in projeto.items() if k not in ("slug",)}
        pf.update({"slug": filho, "pai": slug, "parte": n, "partes": len(aulas), "titulo_aula": aula["titulo"],
                   "janela": [j0, j1]})
        gravar(q / "projeto.json", pf)
        fala.cortar(filho)
        filhos.append((filho, aula, float(aula["ini"]), float(aula["fim"])))

    for i, (filho, aula, a, b) in enumerate(filhos):
        q = PROJETOS / filho
        cf = ler(q / "trabalho" / "cortes.json")
        dur = cf["duracao_editada"]

        def mapa(t):
            e = _para_editado(cf["segmentos"], _para_bruto(cortes["segmentos"], t))
            return None if e is None else round(min(max(e, 0.0), dur), 2)

        beats, fora = [], []
        for bt in plano.get("beats", []):
            if bt["ini"] >= a - 0.01 and bt["fim"] <= b + 0.01:
                ini, fim = mapa(bt["ini"]), mapa(bt["fim"])
                if ini is not None and fim is not None and fim - ini >= 0.8:
                    beats.append({**bt, "ini": ini, "fim": fim})
                    continue
            if bt["fim"] > a and bt["ini"] < b:
                fora.append(bt["id"])
        ultima = i == len(filhos) - 1
        # rótulo do tópico na abertura; "A seguir" no fim (a última fica com o Encerramento do pai)
        # a 1ª parte abre na cena de título do próprio OBS (logo + nome da aula): rótulo ali disputa com ela
        extras = [] if i + base == 1 else [
            {"id": "abre", "ini": 0.3, "fim": 0.3 + ROTULO_S, "modo": "sobre", "template": "PalavraChave",
             "props": {"rotulo": f"Parte {i + base}", "texto": aula["titulo"], "lado": "coluna", "cor": "primaria"}}]
        if not ultima:
            extras.append({"id": "seguir", "ini": round(dur - ROTULO_S - 0.2, 2), "fim": round(dur - 0.2, 2),
                           "modo": "sobre", "template": "PalavraChave",
                           "props": {"rotulo": "A seguir", "texto": filhos[i + 1][1]["titulo"], "lado": "coluna",
                                     "cor": "primaria"}})
        # mesma coluna não comporta dois textos: o rótulo da parte vence; tela cheia some no rótulo
        livres = []
        for bt in beats:
            if bt["template"] == "Encerramento" and not ultima:
                fora.append(bt["id"]); continue
            choca = any(bt["ini"] < x["fim"] and x["ini"] < bt["fim"] for x in extras)
            if choca and (bt.get("props", {}).get("lado") == "coluna" or bt["modo"] == "cheio"):
                fora.append(bt["id"]); continue
            livres.append(bt)
        caps = [{"ini": 0 if k == 0 else mapa(c["ini"]), "titulo": c["titulo"]}
                for k, c in enumerate([c for c in plano.get("capitulos", []) if a - 0.01 <= c["ini"] < b])]
        shorts = []
        for s in plano.get("shorts", []):
            if s["ini"] >= a - 0.01 and s["fim"] <= b + 0.01:
                shorts.append({**s, "ini": mapa(s["ini"]), "fim": mapa(s["fim"])})
        pl = {"titulo": f"{plano.get('titulo', '')} · Parte {i + base} — {aula['titulo']}".strip(" ·"),
              "beats": sorted(livres + extras, key=lambda x: x["ini"]), "shorts": shorts}
        if "musica" in plano:
            pl["musica"] = plano["musica"]
        if len(caps) >= 3:
            pl["capitulos"] = caps
        gravar(q / "plano.json", pl)
        print(f"Parte {i + base}: {filho}  {hms(dur)}  ({len(livres)} beats do pai"
              + (f", fora: {', '.join(fora)}" if fora else "") + ")")
    return [f[0] for f in filhos]
