# -*- coding: utf-8 -*-
"""Comprime um vídeo para upload pelo navegador (Meta Business Suite via Claude in Chrome).

Por quê: a ferramenta de upload do navegador aceita no máximo ~10,4 MB por arquivo. Um reel de 40 s
renderizado em CRF 20 passa de 70 MB e o upload é recusado sem enviar nada (18/11/2026).

Uso: python -I comprimir_upload.py <entrada.mp4> [saida.mp4] [--alvo-mb 9.5]

Faz x264 em 2 passes com o bitrate calculado pela duração, AAC 128k, -movflags +faststart
(o moov vai para o início do arquivo), e confere o tamanho no fim; se passou do alvo, refaz com 90%.
O comando equivalente, para quem quiser rodar na mão (VB = bitrate de vídeo em kbit/s):

  ffmpeg -y -i final.mp4 -c:v libx264 -preset slow -b:v ${VB}k -maxrate 4000k -bufsize 6000k \
         -pix_fmt yuv420p -r 30 -g 60 -pass 1 -an -f mp4 NUL        (Linux/macOS: /dev/null)
  ffmpeg -y -i final.mp4 -c:v libx264 -preset slow -b:v ${VB}k -maxrate 4000k -bufsize 6000k \
         -pix_fmt yuv420p -r 30 -g 60 -pass 2 -c:a aac -b:a 128k -ar 48000 -ac 2 \
         -movflags +faststart final-insta.mp4

  VB ≈ (alvo_MB × 8000 / duração_s) − 128 − 3%   (ex.: 9,5 MB em 33,5 s → ~2.050 kbit/s)

Depois rode o gate do reel com --insta apontando para a saída (regra R9).
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

AUDIO_K = 128


def duracao(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(p)],
                       capture_output=True, text=True, encoding="utf-8")
    return float(json.loads(r.stdout)["format"]["duration"].replace(",", "."))


def comprimir(src, dst, alvo_mb=9.5):
    dur = duracao(src)
    nulo = "NUL" if os.name == "nt" else "/dev/null"
    fator = 1.0
    with tempfile.TemporaryDirectory() as tmp:
        log = str(Path(tmp) / "x264pass")
        for _ in range(4):
            vb = int((alvo_mb * 8000 / dur - AUDIO_K) * 0.97 * fator)
            if vb < 300:
                raise SystemExit(f"vídeo longo demais para {alvo_mb} MB ({dur:.1f}s → {vb} kbit/s); corte ou suba por outro caminho")
            base = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:v", "libx264", "-preset", "slow", "-b:v", f"{vb}k",
                    "-maxrate", f"{max(vb * 2, 1000)}k", "-bufsize", f"{max(vb * 3, 1500)}k", "-pix_fmt", "yuv420p",
                    "-r", "30", "-g", "60", "-passlogfile", log]
            subprocess.run(base + ["-pass", "1", "-an", "-f", "mp4", nulo], check=True)
            subprocess.run(base + ["-pass", "2", "-c:a", "aac", "-b:a", f"{AUDIO_K}k", "-ar", "48000", "-ac", "2",
                                   "-movflags", "+faststart", str(dst)], check=True)
            tam = Path(dst).stat().st_size
            print(f"{Path(dst).name}: {tam / 1e6:.2f} MB a {vb} kbit/s ({dur:.1f}s)")
            if tam <= alvo_mb * 1e6:
                return tam
            fator *= 0.9
    raise SystemExit("não coube no alvo depois de 4 tentativas")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    alvo = 9.5
    if "--alvo-mb" in a:
        k = a.index("--alvo-mb"); alvo = float(a[k + 1]); del a[k:k + 2]
    if not a:
        print(__doc__); sys.exit(2)
    src = Path(a[0])
    dst = Path(a[1]) if len(a) > 1 else src.with_name(src.stem + "-insta.mp4")
    comprimir(src, dst, alvo)
