# Contrato `plano.json` — o que o diretor escreve

Arquivo: `<repo>/motor/projetos/<slug>/plano.json`. Tempos em **segundos da linha editada**
(os mesmos de `trabalho/roteiro_editado.txt` e `trabalho/cortes.json → palavras`).

```json
{
 "titulo": "Título de trabalho",
 "beats": [
  {"id": "b01", "ini": 1.2, "fim": 6.6, "modo": "cheio", "template": "TextoCinetico",
   "props": {"palavrasDaFala": true, "destaque": ["perder"],
             "fundo": {"tipo": "video", "src": "broll/dinheiro-1.mp4", "inicio": 0}}},
  {"id": "b02", "ini": 7.2, "fim": 9.4, "modo": "sobre", "template": "PalavraChave",
   "props": {"texto": "Inflação", "cor": "destaque", "lado": "esquerda"}}
 ],
 "musica": {"clima": "calmo", "volume_db": -26},
 "capitulos": [{"ini": 0, "titulo": "Introdução"}, {"ini": 95.0, "titulo": "Primeiro ponto"}, {"ini": 240.0, "titulo": "Fechamento"}],
 "shorts": [{"id": "s1", "ini": 0.0, "fim": 42.0, "titulo": "Gancho curto"}],
 "aulas": [{"titulo": "Tópico 1", "ini": 0, "fim": 115.5}, {"titulo": "Tópico 2", "ini": 115.5, "fim": 304.3}]
}
```

- `modo`: `cheio` substitui a câmera (H.264 opaco); `sobre` vai por cima da câmera (ProRes com alfa).
- Tempos internos das props (`em`, `destaqueEm`) são **relativos ao início do beat**.
- Caminhos de mídia são relativos a `projetos/<slug>/assets/`, e cada um precisa de entrada em
  `assets/licencas.json` (o `buscar_midia.py` já registra).

## Templates e props

| Template | Props |
|---|---|
| `TextoCinetico` | `palavrasDaFala: true` (sincroniza sozinho) **ou** `palavras: [{t, em}]`; `destaque: [..]`; `fundo: {tipo: video\|imagem\|cor, src, inicio}`; `posicao: centro\|baixo` |
| `Manchete` | `veiculo`, `data`, `url` (obrigatórios, gate P04), `titulo` (≤160, P05), `destaque` (trecho do título), `destaqueEm`, `linhaFina`, `imagem` |
| `Print` | `imagem`, `largura`, `altura` (px do print), `destaques: [{x,y,w,h,em}]`, `foco: {x,y}` |
| `Numero` | `estados: [{valor, rotulo, em, cor: destaque\|alerta\|primaria\|tinta}]`, `fundoImagem`, `escuro` |
| `Comparacao` | `titulo`, `linhas: [{rotulo, valor, em, cor}]` |
| `Lista` | `titulo`, `itens: [{texto, em}]`, `escuro` (padrão true = fundo na cor primária) |
| `Grafico` | `titulo`, `tipo: linha\|barras`, `pontos: [{x, y}]`, `unidade`, `fonte` (obrigatória, P04) |
| `Citacao` | `texto` (≤240, P05), `autor`, `fonte`, `destaque` |
| `PalavraChave` | `texto`, `lado: esquerda\|direita\|centro\|coluna` (coluna = faixa livre da cena "Principal + Tela"), `cor: destaque\|alerta\|claro\|primaria` (sempre `modo: sobre`) |
| `Encerramento` | `chamada` (ex.: "Inscreva-se"); `tagline` e `logo` vêm da marca sozinhos. Fundo claro sempre |

Para achar o `em` de um item: procure a palavra em `cortes.json → palavras` e subtraia o `ini` do beat.

## Regras do gate sobre o plano

P01 tempo dentro do vídeo e ≥ 0,8 s · P02 dois `cheio` sem sobreposição · P03 template existe ·
P04 gráfico com fonte e manchete com veículo/data/url · P05 citação curta · P06 mídia existe e tem licença ·
P07 tela cheia na faixa do formato (vídeo 15–80%, aula 0–50%) · P08 short de 15–90 s · P09 sem texto provisório ·
P10 capítulos: 1º em 0, 3 ou mais, 10 s+ cada (obrigatório em aula > 5 min).

`aulas` (opcional) é lido por `estudio.py dividir` — uma aula por tópico; ver SKILL.md.

`capitulos` gera `final/capitulos.txt` no formato que o YouTube reconhece na descrição.
