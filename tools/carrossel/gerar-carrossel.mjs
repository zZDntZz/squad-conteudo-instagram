// Carrossel de slides 1080x1350 (4:5) a partir de um JSON: capa, um slide por item e CTA.
// Uso: node gerar-carrossel.mjs carrossel.json
// Ver carrossel.exemplo.json. Texto e paleta vêm do config; o emblema é a logo da marca (PNG).
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { abrirNavegador, dataUri, lerConfig, esc } from '../_comum/navegador.mjs';

const { cfg, rel } = lerConfig(process.argv[2]);
const W = cfg.largura || 1080, H = cfg.altura || 1350;
const C = { fundo: '#14231C', texto: '#F4F6F1', destaque: '#E2B65B', linha: '#2C4A3B', rodape: '#C9D6CE', ...cfg.cores };
const OUT = rel(cfg.saida || 'saida');
mkdirSync(OUT, { recursive: true });
const emblema = cfg.emblema ? dataUri(rel(cfg.emblema)) : null;
const N = cfg.slides.length;

const css = `*{margin:0;box-sizing:border-box}body{width:${W}px;height:${H}px;background:${C.fundo};color:${C.texto};font-family:Arial,Helvetica,sans-serif;padding:96px;display:flex;flex-direction:column}
.kick{color:${C.destaque};font-weight:bold;letter-spacing:3px;font-size:30px;text-transform:uppercase}
h1{font-family:"Arial Black",Arial,sans-serif;font-size:104px;line-height:1.08;margin-top:48px}
h2{font-family:"Arial Black",Arial,sans-serif;font-size:76px;line-height:1.12;margin-top:40px}
p{font-size:44px;line-height:1.6;margin-top:56px}
.num{font-family:"Arial Black",Arial,sans-serif;color:${C.destaque};font-size:200px;line-height:1;margin-top:40px}
.cresce{flex:1}.rod{border-top:2px solid ${C.linha};padding-top:40px;font-size:32px;color:${C.rodape};display:flex;justify-content:space-between}
.emb{width:220px;margin-top:40px}.dest{color:${C.destaque}}`;

const corpo = (s) => {
  const t = s.html ?? esc(s.texto);
  const k = s.kicker ? `<div class="kick">${esc(s.kicker)}</div>` : '';
  if (s.tipo === 'capa') return `${k}<h1>${esc(s.titulo)}</h1>${emblema ? `<img class="emb" src="${emblema}">` : ''}${t ? `<p style="margin-top:24px">${t}</p>` : ''}`;
  if (s.tipo === 'item') return `${k}${s.numero != null ? `<div class="num">${esc(s.numero)}</div>` : ''}<h2>${esc(s.titulo)}</h2>${t ? `<p>${t}</p>` : ''}`;
  return `${k}<h1>${esc(s.titulo)}</h1>${t ? `<p>${t}</p>` : ''}${s.cta_html ? `<p>${s.cta_html}</p>` : ''}`;
};
const pagina = (s, i) => `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><style>${css}</style></head><body>${corpo(s)}<div class="cresce"></div><div class="rod"><span>${esc(cfg.arroba || '')}</span><span>${i}/${N}</span></div></body></html>`;

const b = await abrirNavegador();
const p = await b.newPage({ viewport: { width: W, height: H } });
for (let i = 0; i < N; i++) {
  await p.setContent(pagina(cfg.slides[i], i + 1), { waitUntil: 'load' });
  await p.evaluate(() => document.fonts.ready);
  // texto que estoura a página some no feed: para com erro em vez de entregar cortado
  const estouro = await p.evaluate(() => document.body.scrollHeight > window.innerHeight + 1);
  if (estouro) { await b.close(); console.error(`slide ${i + 1}: texto passou da altura do slide; encurte`); process.exit(1); }
  await p.screenshot({ path: join(OUT, `${cfg.nome || 'carrossel'}-${i + 1}.png`) });
}
await b.close();
console.log(`ok: ${N} slides em ${OUT}`);
