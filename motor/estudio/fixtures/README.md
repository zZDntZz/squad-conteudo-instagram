# Falas de teste do autoteste do gate

O `gate_autoteste.py` cola duas falas curtas no meio de um vídeo aprovado e exige que o gate final reprove.
Os arquivos não vêm no repositório porque são gravações de voz. Grave os seus (celular ou OBS, WAV mono
48 kHz, 3 a 6 s, fala natural):

| Arquivo | O que dizer | Regra que testa |
|---|---|---|
| `fala_corta_essa_parte.wav` | "Corta essa parte." | F07: fala de bastidor que não pode ir ao ar |
| `fala_uma_faixa_uma_faixa.wav` | "manter uma faixa, uma faixa ideal" | F08: tropeço (repetição imediata) |

Converta com `ffmpeg -i entrada.m4a -ac 1 -ar 48000 fala_corta_essa_parte.wav`.
Sem os dois arquivos o autoteste falha de propósito: regra que ninguém viu reprovar não protege nada.
