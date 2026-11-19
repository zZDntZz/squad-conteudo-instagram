# Identidade visual — o que levantar antes de montar

Preencha uma vez por marca e guarde em `motor/marcas/<marca>/marca.json` (cores, fontes, tagline, arroba,
diretrizes, correções). Os scripts leem de lá; nada de cor ou nome da marca escrito no código.

## Cores

| Token | Uso em vídeo | Exemplo |
|---|---|---|
| escuro | fundo do card de marca, faixa de legenda | `#14231C` |
| destaque | filete, arroba, palavra em foco | `#E2B65B` |
| primária | texto sobre fundo claro | `#1F4D3A` |
| claro | texto sobre fundo escuro | `#F4F6F1` |

Confira contraste: texto pequeno precisa de 4,5:1 sobre o fundo. Cor de marca clara demais sobre creme
(perto de 3:1) vai só em ilustração; para texto, escureça um tom.

## Logo

- Sempre o PNG oficial, de preferência com fundo transparente e grande (≥ 2000 px).
- Se não existe SVG, trate o logo como imagem. Nunca recriar em texto, nunca gerar por IA.
- Logo com letra escura some em fundo escuro: card de encerramento claro, ou versão clara do logo.

## Tipografia

Use as fontes da marca só se você tem o arquivo e a licença. Até lá, Arial Black (gancho e karaokê) e
Arial Bold (card), e avise no relatório.

## Assinatura e mensagens

- Tagline, arroba, assinatura de bio.
- O CTA da casa (um por peça).
- Lista do que a marca **não** diz: claims sem fonte, promessas de resultado, termos técnicos proibidos.
  Isso vira `termos_vetados` no `config.json` e o gate de legenda reprova.

## O que evitar

- Formato quadrado 1:1 (corta no feed) — usar 9:16 ou 4:5.
- Repetir o mesmo elemento visual em dois slides/cenas seguidas.
- Exclamações, "Com certeza!", auto-apresentação.
- Rosto de cliente/terceiro sem autorização.
