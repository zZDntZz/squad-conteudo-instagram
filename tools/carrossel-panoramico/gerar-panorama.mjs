// Carrossel panorâmico: UMA imagem larga (N x 1080 por 1350) cortada em N slides de 1080x1350.
// Quem arrasta vê uma cena contínua; os elementos atravessam as bordas entre slides.
// Uso: node gerar-panorama.mjs panorama.json      (ver panorama.exemplo.json)
//
// O fundo vem de uma de três fontes (campo "cena"):
//   {"tipo": "modulo", "arquivo": "cenas/solo-vivo.mjs"}  desenho em código (SVG), determinístico
//   {"tipo": "imagem", "arquivo": "minha-arte-larga.png"}  arte pronta na largura total (embutida em base64)
//   {"tipo": "gradiente", "de": "#EEE0C2", "para": "#E4F3E8"}  só cor, para testar o texto
// Texto e paleta vêm do config. O script mede cada bloco no navegador e PARA com erro se algum texto
// cruzar a margem do próprio slide: texto cortado entre dois slides não se lê no feed.
import { writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { abrirNavegador, dataUri, lerConfig, esc } from '../_comum/navegador.mjs';

const { cfg, rel } = lerConfig(process.argv[2]);
const N = cfg.slides || 9, SW = cfg.largura_slide || 1080, H = cfg.altura || 1350, M = cfg.margem ?? 80;
const W = N * SW;
const COR = { escuro: '#14231C', creme: '#F4F6F1', destaque: '#1F6B45', acento: '#E2B65B', rodape: '#D9CCB6', ...cfg.cores };
const OUT = rel(cfg.saida || 'saida');
mkdirSync(OUT, { recursive: true });

// ---------- fundo ----------
let fundo;
const cena = cfg.cena || { tipo: 'gradiente' };
if (cena.tipo === 'modulo') {
  const mod = await import(pathToFileURL(rel(cena.arquivo)).href);
  if (mod.slides && mod.slides !== N) throw new Error(`a cena ${cena.arquivo} foi desenhada para ${mod.slides} slides (config pede ${N})`);
  fundo = mod.desenhar({ W, H, SW, cores: cena.cores || {} });
} else if (cena.tipo === 'imagem') {
  fundo = `<img src="${dataUri(rel(cena.arquivo))}" width="${W}" height="${H}" style="display:block;object-fit:cover">`;
} else {
  fundo = `<div style="width:${W}px;height:${H}px;background:linear-gradient(90deg,${cena.de || '#EEE0C2'},${cena.para || '#E4F3E8'})"></div>`;
}

// ---------- texto ----------
const X = (s) => (s - 1) * SW + M;
const emblema = cfg.assinatura?.emblema ? dataUri(rel(cfg.assinatura.emblema)) : null;
const blocos = cfg.blocos.map((b) => {
  let h = b.html ?? '';
  if (b.assinatura) h += `<div class="assin">${emblema ? `<img src="${emblema}" alt="">` : ''}<span>${esc(cfg.assinatura?.arroba || '')}</span></div>`;
  return { ...b, html: h };
});
const rodapes = (cfg.numerar === false ? '' : Array.from({ length: N }, (_, i) => `<div class="rod" style="left:${X(i + 1)}px">${i + 1}/${N}</div>`).join(''))
  + (cfg.arraste ? `<div class="rod arraste" style="left:${SW - M - 400}px;width:400px">${esc(cfg.arraste)}</div>` : '');

const css = `*{margin:0;padding:0;box-sizing:border-box}
html,body{width:${W}px;height:${H}px;overflow:hidden;background:${COR.creme}}
.cena{position:absolute;left:0;top:0}
.blk{position:absolute;width:${SW - 2 * M}px;color:${COR.escuro};font-family:Arial,Helvetica,sans-serif}
.blk.claro{color:${COR.creme}}
.kick{font:700 40px/1.2 Arial,sans-serif;color:${COR.destaque};margin-bottom:24px}
h1{font:900 88px/1.04 "Arial Black",Arial,sans-serif;letter-spacing:-1px}
h2{font:900 70px/1.08 "Arial Black",Arial,sans-serif;letter-spacing:-0.5px}
h3{font:900 54px/1.12 "Arial Black",Arial,sans-serif}
p{font:700 40px/1.45 Arial,sans-serif;margin-top:16px}
.n,.dest{color:${COR.destaque}}
.claro .n{color:${COR.acento}}
mark{background:${COR.acento};color:${COR.escuro};padding:0 10px;border-radius:8px}
.assin{display:flex;align-items:center;gap:16px;margin-top:24px;font:700 40px/1 Arial,sans-serif}
.assin img{width:104px;height:104px;object-fit:contain}
.rod{position:absolute;top:${H - 88}px;font:700 40px/1 Arial,sans-serif;color:${COR.rodape}}
.arraste{text-align:right;color:${COR.acento}}`;

const html = `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>${esc(cfg.nome || 'panorama')}</title><style>${css}</style></head><body>
<div class="cena">${fundo}</div>
${blocos.map((b, i) => `<div class="blk ${b.cls || ''}" id="b${i}" style="left:${X(b.s)}px;top:${b.top ?? M}px">${b.html}</div>`).join('\n')}
${rodapes}
</body></html>`;
const htmlPath = join(OUT, `${cfg.nome || 'panorama'}.html`);
writeFileSync(htmlPath, html);

// ---------- render e conferência ----------
const b = await abrirNavegador();
const p = await b.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await p.goto(pathToFileURL(htmlPath).href, { waitUntil: 'load' });
await p.evaluate(() => document.fonts.ready);
const medidas = await p.evaluate(({ SW, M, H }) => [...document.querySelectorAll('.blk, .rod')].map((el) => {
  const r = el.getBoundingClientRect();
  const rg = document.createRange(); rg.selectNodeContents(el); const rr = rg.getBoundingClientRect();
  const s = Math.floor(r.left / SW) + 1;
  return { id: el.id || el.textContent.trim(), s, left: rr.left, right: rr.right, top: rr.top, bottom: rr.bottom,
    ok: rr.left >= (s - 1) * SW + M - 0.5 && rr.right <= s * SW - M + 0.5 && rr.bottom <= H - 0.5 };
}), { SW, M, H });
for (const m of medidas.filter((m) => m.id.startsWith('b'))) console.log(`slide ${m.s} ${m.id}: x ${Math.round(m.left)}-${Math.round(m.right)}  y ${Math.round(m.top)}-${Math.round(m.bottom)}`);
const ruins = medidas.filter((m) => !m.ok);
if (ruins.length) { console.error('TEXTO FORA DA MARGEM DO SLIDE:', ruins); await b.close(); process.exit(1); }
const full = join(OUT, `${cfg.nome || 'panorama'}-completo.png`);
await p.screenshot({ path: full, clip: { x: 0, y: 0, width: W, height: H } });
await b.close();

for (let i = 0; i < N; i++) {
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', full, '-vf', `crop=${SW}:${H}:${i * SW}:0`, join(OUT, `${cfg.nome || 'panorama'}-${i + 1}.png`)]);
}
console.log(`ok: ${cfg.nome || 'panorama'}-completo.png + ${N} slides em ${OUT}`);
