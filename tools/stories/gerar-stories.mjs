// Stories 1080x1920 com foto de fundo, véu de cor e texto, a partir de um JSON.
// Uso: node gerar-stories.mjs stories.json      (ver stories.exemplo.json)
//
// Lições de 18/11:
//  - o fundo vai EMBUTIDO em base64: com setContent, url('file://...') não carrega e o story sai sem foto;
//  - o texto fica no terço de baixo, acima de ~300 px do rodapé (campo de resposta do Instagram);
//  - enquete, caixa de perguntas e link não dá para agendar pelo Business Suite: a chamada vai no texto
//    ("Responda este story que eu te explico") e a automação de resposta a story do ManyChat faz o resto.
import { mkdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { abrirNavegador, dataUri, lerConfig, esc } from '../_comum/navegador.mjs';

const { cfg, rel } = lerConfig(process.argv[2]);
const C = { veu: '14,35,28', texto: '#F4F6F1', destaque: '#E2B65B', textoCta: '#14231C', ...cfg.cores };
const OUT = rel(cfg.saida || 'saida');
mkdirSync(OUT, { recursive: true });

const css = `*{margin:0;box-sizing:border-box}body{width:1080px;height:1920px;font-family:Arial,sans-serif;background-color:rgb(${C.veu});background-size:cover;background-position:center;position:relative}
.vel{position:absolute;inset:0;background:linear-gradient(180deg,rgba(${C.veu},.15) 0%,rgba(${C.veu},.0) 25%,rgba(${C.veu},.92) 62%)}
.box{position:absolute;left:96px;right:96px;bottom:320px;color:${C.texto}}
.k{font-weight:bold;letter-spacing:3px;font-size:34px;color:${C.destaque};text-transform:uppercase}
h1{font-family:"Arial Black",Arial;font-size:84px;line-height:1.08;margin-top:24px}
p{font-size:46px;line-height:1.42;margin-top:32px}ul{margin-top:28px;padding-left:0;list-style:none}li{font-size:46px;line-height:1.35;margin-top:14px}li:before{content:"• ";color:${C.destaque}}
.cta{margin-top:40px;font-size:46px;font-weight:bold;background:${C.destaque};color:${C.textoCta};padding:22px 28px;border-radius:18px;display:inline-block}`;

const b = await abrirNavegador();
const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
let n = 0;
for (const t of cfg.telas) {
  const fundo = t.fundo ? rel(t.fundo) : null;
  if (fundo && !existsSync(fundo)) { await b.close(); console.error(`fundo não encontrado: ${fundo}`); process.exit(1); }
  const estilo = fundo ? ` style="background-image:url('${dataUri(fundo)}')"` : '';
  const corpo = [
    t.kicker && `<div class="k">${esc(t.kicker)}</div>`,
    t.titulo && `<h1>${esc(t.titulo)}</h1>`,
    t.texto && `<p>${esc(t.texto)}</p>`,
    t.lista && `<ul>${t.lista.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`,
    t.cta && `<div class="cta">${esc(t.cta)}</div>`,
  ].filter(Boolean).join('');
  await p.setContent(`<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><style>${css}</style></head><body${estilo}><div class="vel"></div><div class="box">${corpo}</div></body></html>`, { waitUntil: 'load' });
  await p.waitForTimeout(300);
  // texto que sobe demais encosta no topo (barra de progresso e nome do perfil): para com erro
  const topo = await p.evaluate(() => document.querySelector('.box').getBoundingClientRect().top);
  if (topo < 220) { await b.close(); console.error(`${t.arquivo}: texto começa em y=${Math.round(topo)} (mín. 220); encurte`); process.exit(1); }
  await p.screenshot({ path: join(OUT, t.arquivo), type: 'jpeg', quality: 92 });
  n++;
}
await b.close();
console.log(`ok: ${n} stories em ${OUT}`);
