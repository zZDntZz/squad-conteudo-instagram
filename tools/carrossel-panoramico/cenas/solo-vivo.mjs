// Cena de exemplo para o carrossel panorâmico: corte lateral do terreno, do solo morto (slides 1-5)
// à virada (6-7) e ao solo vivo (8-9). Desenhada toda em código (SVG), sem clip-art e sem foto.
// Coordenadas pensadas para 9 slides de 1080x1350 (9720x1350). Determinística: mesmo seed, mesma imagem.
// Contrato de uma cena: export function desenhar({ W, H, SW }) => string SVG do tamanho W x H.
export const slides = 9;
export function desenhar({ W = 9720, H = 1350, SW = 1080, cores = {} } = {}) {
  const COR = { escuro: "#0E261B", creme: "#F2FBF5", verde: "#3AA56F", dourado: "#E2B65B", ...cores };
// ---------- utilidades ----------
let seed = 20261118;
const rnd = () => { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const R = (a, b) => a + (b - a) * rnd();
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
const f = (n) => (Math.round(n * 10) / 10).toString();
const ss = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const bump = (x, c, hw) => (Math.abs(x - c) < hw ? 0.5 * (1 + Math.cos(Math.PI * (x - c) / hw)) : 0);
const vivo = (x) => ss(6200, 8000, x);                  // 0 = solo morto, 1 = solo vivo

// linha do chão: uma função só para os 9 slides -> continuidade garantida por construção
const g = (x) => 600 + 5 * Math.sin(x / 170) + 3 * Math.sin(x / 47 + 1.3)
  + 34 * bump(x, 1640, 320)                              // poça (slide 2)
  + 16 * bump(x, 3240, 120) + 16 * bump(x, 3600, 120)    // sulcos de pneu (slides 3-4)
  - 12 * vivo(x);
const b1 = (x) => g(x) + 105 + 195 * vivo(x);            // fundo da camada superficial
const b2 = (x) => g(x) + 280 + 280 * vivo(x);            // fundo da camada compactada / subsolo

const linha = (fn, x0, x1, step = 6) => { const p = []; for (let x = x0; x <= x1; x += step) p.push([x, fn(x)]); if (p[p.length - 1][0] !== x1) p.push([x1, fn(x1)]); return p; };
const pts2d = (p) => p.map(([x, y]) => `${f(x)} ${f(y)}`).join(' L');
const faixa = (top, bot, x0 = 0, x1 = W) => { const a = linha(top, x0, x1), b = linha(bot, x0, x1).reverse(); return `M${pts2d(a)} L${pts2d(b)} Z`; };

// polígono afinando (raiz, minhoca, haste)
function taper(p, w0, w1) {
  const L = [], Rr = [], n = p.length;
  for (let i = 0; i < n; i++) {
    const a = p[Math.max(0, i - 1)], b = p[Math.min(n - 1, i + 1)];
    const dx = b[0] - a[0], dy = b[1] - a[1], d = Math.hypot(dx, dy) || 1, nx = -dy / d, ny = dx / d;
    const w = (w0 + (w1 - w0) * i / (n - 1)) / 2;
    L.push([p[i][0] + nx * w, p[i][1] + ny * w]); Rr.push([p[i][0] - nx * w, p[i][1] - ny * w]);
  }
  return `M${pts2d(L)} L${pts2d(Rr.reverse())} Z`;
}
// caminhada de raiz: ângulo puxado para um alvo (horizontal no solo morto, vertical no vivo)
function marcha(x, y, a, len, { alvo, k = 0.08, wig = 0.18, ymax = () => 1215, step = 7, para = false }) {
  const p = [[x, y]];
  for (let s = 0; s < len; s += step) {
    a += (alvo - a) * k + R(-wig, wig);
    x += Math.cos(a) * step; y += Math.sin(a) * step;
    const lim = ymax(x);
    if (y > lim) { if (para) break; y = lim; a = Math.cos(a) >= 0 ? R(-0.05, 0.08) : Math.PI - R(-0.05, 0.08); }
    if (y < g(x) + 4) { y = g(x) + 4; }
    p.push([x, y]);
  }
  return p;
}
function raiz(out, x, y, a, len, w, op) {
  const p = marcha(x, y, a, len, op);
  if (p.length < 3) return p;
  out.push(`<path d="${taper(p, w, Math.max(0.8, w * 0.15))}" fill="${op.cor}" opacity="${op.alpha ?? 1}"/>`);
  if ((op.nivel ?? 0) < (op.niveis ?? 2)) {
    const nb = op.ramos ?? 4;
    for (let i = 0; i < nb; i++) {
      const j = Math.floor(R(0.15, 0.85) * (p.length - 1));
      const [bx, by] = p[j];
      const pa = Math.atan2(p[Math.min(p.length - 1, j + 1)][1] - by, p[Math.min(p.length - 1, j + 1)][0] - bx);
      const side = rnd() < 0.5 ? -1 : 1;
      raiz(out, bx, by, pa + side * R(0.5, 1.1), len * R(0.25, 0.5), w * R(0.35, 0.55), { ...op, nivel: (op.nivel ?? 0) + 1, ramos: Math.max(1, nb - 1), alvo: op.alvoRamo ?? op.alvo });
    }
  }
  return p;
}
// folha/lâmina de capim
const lamina = (x0, y0, x1, y1, cx, cy, w) => `M${f(x0 - w)} ${f(y0)} Q${f(cx - w * 0.4)} ${f(cy)} ${f(x1)} ${f(y1)} Q${f(cx + w * 0.4)} ${f(cy)} ${f(x0 + w)} ${f(y0)} Z`;
function touceira(out, x, h, cores, n, w = 3.2, abertura = 1.0) {
  const y = g(x);
  for (let i = 0; i < n; i++) {
    const a = R(-abertura, abertura), L = h * R(0.55, 1), ox = R(-10, 10);
    const tx = x + ox + Math.sin(a) * L * 0.9, ty = y - Math.cos(a) * L;
    const cx = x + ox + Math.sin(a) * L * 0.25, cy = y - L * 0.65;
    out.push(`<path d="${lamina(x + ox, y + 2, tx, ty, cx, cy, w)}" fill="${pick(cores)}"/>`);
  }
}

// ---------- camadas de desenho ----------
const ceu = [], fundo = [], solo = [], vida = [], superficie = [], plantas = [], frente = [];

// horizonte (colinas distantes)
const morro = (x) => 538 + 14 * Math.sin(x / 610 + 0.4) + 9 * Math.sin(x / 230 + 2) + 4 * Math.sin(x / 90);
fundo.push(`<path d="${faixa(morro, (x) => g(x) + 2)}" fill="url(#gMorro)"/>`);
for (let x = 6900; x < W; x += R(110, 260)) { // arvoretas do Cerrado ao longe
  const y = morro(x) + 4, h = R(26, 44);
  fundo.push(`<path d="M${f(x)} ${f(y)} L${f(x + 2)} ${f(y - h * 0.55)}" stroke="#A9CDB4" stroke-width="3" opacity="${f(vivo(x))}"/>`);
  fundo.push(`<ellipse cx="${f(x + 2)}" cy="${f(y - h * 0.65)}" rx="${f(h * 0.55)}" ry="${f(h * 0.32)}" fill="#B5D6BE" opacity="${f(vivo(x))}"/>`);
}
// nuvens suaves (só no lado vivo) e poeira seca (lado morto)
for (let i = 0; i < 9; i++) { const x = R(6900, 9600), y = R(120, 420); ceu.push(`<ellipse cx="${f(x)}" cy="${f(y)}" rx="${f(R(140, 260))}" ry="${f(R(26, 44))}" fill="#FFFFFF" opacity="0.55" filter="url(#blur12)"/>`); }
for (let i = 0; i < 7; i++) { const x = R(100, 5200), y = R(440, 540); ceu.push(`<ellipse cx="${f(x)}" cy="${f(y)}" rx="${f(R(260, 420))}" ry="${f(R(20, 34))}" fill="#E3CFA4" opacity="0.35" filter="url(#blur12)"/>`); }

ceu.push(`<circle cx="2960" cy="430" r="120" fill="#F6D58E" opacity="0.35" filter="url(#blur12)"/><circle cx="2960" cy="430" r="52" fill="#F3CF7E"/><circle cx="2960" cy="430" r="52" fill="none" stroke="#E2B65B" stroke-width="3"/>`);
// solo: subsolo, camada compactada, camada superficial
solo.push(`<path d="${faixa(g, () => H)}" fill="url(#gFundo)"/>`);
solo.push(`<path d="${faixa(g, b2)}" fill="url(#gCompacta)"/>`);
solo.push(`<path d="${faixa(g, b1)}" fill="url(#gSuperf)"/>`);
// sombreamento vertical + grão
solo.push(`<rect x="0" y="560" width="${W}" height="${H - 560}" fill="url(#gSombra)" clip-path="url(#cSolo)"/>`);
solo.push(`<rect x="0" y="560" width="${W}" height="${H - 560}" filter="url(#graoEsc)" opacity="0.55" clip-path="url(#cSolo)"/>`);
solo.push(`<rect x="0" y="560" width="${W}" height="${H - 560}" filter="url(#graoClaro)" opacity="0.35" clip-path="url(#cSolo)"/>`);
// transição suave entre camadas (borda difusa)
solo.push(`<path d="${linha(b1, 0, W, 12).map(([x, y], i) => `${i ? 'L' : 'M'}${f(x)} ${f(y)}`).join(' ')}" stroke="#2A1D14" stroke-width="5" fill="none" opacity="0.25" filter="url(#blur3)"/>`);
solo.push(`<path d="${linha(b2, 0, W, 12).map(([x, y], i) => `${i ? 'L' : 'M'}${f(x)} ${f(y)}`).join(' ')}" stroke="#1E140E" stroke-width="6" fill="none" opacity="0.3" filter="url(#blur3)"/>`);

// zonas de texto no subsolo (slides 5 e 6) e rodapé: nada de pedra atrás
const zonasLivres = [[4 * SW + 50, 880, 5 * SW - 50, 1250], [5 * SW + 50, 880, 6 * SW - 50, 1250]];
const livre = (x, y) => y < 1225 && !zonasLivres.some(([a, b, c, d]) => x > a && x < c && y > b && y < d);

// estrutura laminar da camada compactada (só no lado morto) - riscos horizontais
for (let k = 1; k <= 7; k++) {
  let d = '', x = 0;
  while (x < 6150) {
    const len = R(40, 140), y0 = (xx) => b1(xx) + (b2(xx) - b1(xx)) * (k / 8) + 3 * Math.sin(xx / 37 + k);
    if (rnd() < 0.78) d += `M${f(x)} ${f(y0(x))} L${f(x + len)} ${f(y0(x + len))} `;
    x += len + R(8, 26);
  }
  solo.push(`<path d="${d}" stroke="${k % 2 ? '#3A2E25' : '#B9A38C'}" stroke-width="${k % 2 ? 2.4 : 1.4}" opacity="${k % 2 ? 0.38 : 0.22}" fill="none"/>`);
}
// pedras e cascalho
for (let i = 0; i < 300; i++) {
  const x = R(0, W), y = R(b1(x) + 14, 1220);
  if (!livre(x, y)) continue;
  const rx = R(5, 22) * (y > b2(x) ? 1.2 : 0.8), ry = rx * R(0.5, 0.75), v = vivo(x);
  const cor = v > 0.5 ? pick(['#6B4733', '#7A5238', '#5C3D2B']) : pick(['#6E6359', '#7D7166', '#5E544C', '#887B6E']);
  solo.push(`<g transform="rotate(${f(R(-25, 25))} ${f(x)} ${f(y)})"><ellipse cx="${f(x)}" cy="${f(y)}" rx="${f(rx)}" ry="${f(ry)}" fill="${cor}"/><ellipse cx="${f(x - rx * 0.25)}" cy="${f(y - ry * 0.35)}" rx="${f(rx * 0.5)}" ry="${f(ry * 0.3)}" fill="#FFFFFF" opacity="0.12"/><ellipse cx="${f(x)}" cy="${f(y + ry * 0.55)}" rx="${f(rx * 0.9)}" ry="${f(ry * 0.35)}" fill="#000" opacity="0.15"/></g>`);
}

// crosta superficial (espessa no lado morto, some onde o garfo quebra)
const crosta = (x) => g(x) + 16 * (1 - ss(5900, 6500, x));
solo.push(`<path d="${faixa(g, crosta, 0, 6500)}" fill="#D6B37C"/>`);
solo.push(`<path d="${linha(g, 0, 6500, 8).map(([x, y], i) => `${i ? 'L' : 'M'}${f(x)} ${f(y + 1.5)}`).join(' ')}" stroke="#EBD3A2" stroke-width="3" fill="none" opacity="${0.9}"/>`);
// rachaduras: muitas e fundas no slide 3; esparsas no resto do lado morto
const racha = (x, d, w) => {
  const y = g(x), mx = x + R(-6, 6);
  solo.push(`<path d="M${f(x - w)} ${f(y - 0.5)} L${f(mx - w * 0.3)} ${f(y + d * 0.5)} L${f(mx + R(-4, 4))} ${f(y + d)} L${f(mx + w * 0.3)} ${f(y + d * 0.5)} L${f(x + w)} ${f(y - 0.5)} Z" fill="#4E3826"/>`);
  if (d > 40) solo.push(`<path d="M${f(mx)} ${f(y + d * 0.6)} q${f(R(-18, 18))} ${f(d * 0.3)} ${f(R(-26, 26))} ${f(d * 0.55)}" stroke="#4E3826" stroke-width="1.6" fill="none"/>`);
};
for (let x = 2170; x < 3235; x += R(48, 82)) racha(x, R(40, 92), R(5, 9));
racha(2160, 70, 7); racha(3236, 54, 6); racha(1080, 36, 5); racha(4320, 30, 5);
for (let x = 60; x < 5900; x += R(110, 210)) { if (x > 2150 && x < 3250) continue; if (Math.abs(x - 1640) < 280) continue; racha(x, R(14, 38), R(3, 6)); }

// sulcos de pneu de caminhão de obra + bulbos de pressão
for (const c of [3240, 3600]) {
  for (const [rx, ry, op] of [[95, 60, 0.42], [140, 105, 0.32], [190, 160, 0.22], [240, 220, 0.14]]) {
    solo.push(`<path d="M${f(c - rx)} ${f(g(c) + 6)} A${rx} ${ry} 0 0 0 ${f(c + rx)} ${f(g(c) + 6)}" stroke="#2B211A" stroke-width="2.6" stroke-dasharray="10 8" fill="none" opacity="${op}"/>`);
  }
  // lente compactada logo abaixo do sulco
  solo.push(`<path d="${faixa((x) => g(x), (x) => g(x) + 26 * bump(x, c, 110), c - 110, c + 110)}" fill="#6A584A" opacity="0.75"/>`);
  // perfil da banda de rodagem (garras) marcado no fundo do sulco
  let d = '';
  for (let x = c - 78; x <= c + 78; x += 13) d += `M${f(x)} ${f(g(x) + 1)} l5 6 l8 0 `;
  superficie.push(`<path d="${d}" stroke="#5C4634" stroke-width="3" fill="none" stroke-linejoin="round"/>`);
}

// poça (slide 2): água parada em cima do solo que não absorve
{
  const yw = 616, p = [];
  for (let x = 1300; x <= 1980; x += 4) if (g(x) > yw) p.push([x, g(x)]);
  const x0 = p[0][0], x1 = p[p.length - 1][0];
  superficie.push(`<path d="M${f(x0)} ${yw} L${pts2d(p)} L${f(x1)} ${yw} Z" fill="url(#gAgua)"/>`);
  superficie.push(`<path d="M${f(x0 + 6)} ${yw + 0.5} L${f(x1 - 6)} ${yw + 0.5}" stroke="#E4F3F8" stroke-width="3" opacity="0.9"/>`);
  for (let i = 0; i < 5; i++) { const x = R(x0 + 60, x1 - 60); superficie.push(`<path d="M${f(x)} ${yw + 7 + i * 3} l${f(R(30, 70))} 0" stroke="#FFFFFF" stroke-width="2" opacity="0.45"/>`); }
  // barreira: a água não passa da crosta
  solo.push(`<path d="${linha((x) => g(x) + 18, x0 - 20, x1 + 20, 8).map(([x, y], i) => `${i ? 'L' : 'M'}${f(x)} ${f(y)}`).join(' ')}" stroke="#7FB0C4" stroke-width="2" stroke-dasharray="4 10" fill="none" opacity="0.7"/>`);
}
// enxurrada: faixa de água escorrendo por cima da superfície, atravessando os slides 1-3
for (const [a, b] of [[380, 1350], [1930, 2780]]) {
  const p = linha((x) => g(x) - 3, a, b, 6);
  const d = p.map(([x, y], i) => `${i ? 'L' : 'M'}${f(x)} ${f(y)}`).join(' ');
  superficie.push(`<path d="${d}" stroke="#7DB2C7" stroke-width="8" fill="none" stroke-linecap="round"/>`);
  superficie.push(`<path d="${p.map(([x, y], i) => `${i ? 'L' : 'M'}${f(x)} ${f(y - 2.5)}`).join(' ')}" stroke="#D8EEF5" stroke-width="2" fill="none" stroke-dasharray="26 18" stroke-linecap="round"/>`);
}
for (let x = 2790; x < 2900; x += 18) superficie.push(`<circle cx="${f(x)}" cy="${f(g(x) - 3)}" r="${f(R(2.5, 4.5))}" fill="#7DB2C7"/>`);

// ---------- plantas do lado morto (raiz rasa e horizontal, presa acima da camada compactada) ----------
const secos = ['#CDB57A', '#BFA163', '#D9C38C', '#A98E57', '#B8A06A'];
const corRaizMorta = '#F1E3C6';
const limRaso = (x) => b1(x) - 18;
function raizesRasas(x, alcance, n = 4) {
  for (let i = 0; i < n; i++) {
    const dir = i % 2 ? 0 : Math.PI, alvo = dir === 0 ? 0.05 : Math.PI - 0.05;
    raiz(solo, x + R(-6, 6), g(x) + 6, dir === 0 ? R(0.3, 0.7) : Math.PI - R(0.3, 0.7), alcance * R(0.6, 1), R(3.5, 5), { alvo, k: 0.12, wig: 0.14, ymax: limRaso, cor: corRaizMorta, niveis: 1, ramos: 3, alpha: 0.95 });
  }
}
// slide 1: touceira seca com raiz que atravessa para o slide 2
touceira(plantas, 820, 86, secos, 16, 3); raiz(solo, 826, g(826) + 6, 0.35, 420, 5.5, { alvo: 0.03, k: 0.12, wig: 0.12, ymax: limRaso, cor: corRaizMorta, niveis: 1, ramos: 4 }); raizesRasas(820, 200, 3);
touceira(plantas, 300, 60, secos, 10, 2.6); raizesRasas(300, 160, 3);
// slide 2
touceira(plantas, 2080, 58, secos, 10, 2.6); raizesRasas(2080, 180, 3);
// slide 3: só um toco seco
plantas.push(`<path d="M2830 ${f(g(2830) + 2)} l-3 -46 l4 -10 l3 8 l2 48 Z" fill="#9A8257"/>`); raizesRasas(2832, 150, 2);
// slide 4: folha caída intacta (ninguém decompõe) + touceira com raiz cruzando a borda 4|5
superficie.push(`<g transform="translate(3880 ${f(g(3880) - 6)}) rotate(-8)"><path d="M-46 0 Q-10 -26 46 -2 Q6 16 -46 0 Z" fill="#B58A4A"/><path d="M-46 0 Q0 -4 46 -2" stroke="#8C6534" stroke-width="2" fill="none"/><path d="M-20 -1 l10 -8 M0 -2 l10 -9 M18 -2 l9 -7" stroke="#8C6534" stroke-width="1.4"/></g>`);
touceira(plantas, 4150, 72, secos, 13, 2.8); raiz(solo, 4156, g(4156) + 6, 0.4, 360, 5, { alvo: 0.04, k: 0.12, wig: 0.12, ymax: limRaso, cor: corRaizMorta, niveis: 1, ramos: 3 }); raizesRasas(4150, 170, 3);
// slide 5: um tipo só de mato (clones da mesma touceira) + adubo que não fica
const mato = ['#A3B04F', '#8F9D40', '#B4BE62'];
for (const x of [4440, 4600, 4760, 4920, 5080, 5240, 5390]) {
  const s0 = seed; seed = 777; touceira(plantas, x, 100, mato, 14, 3.4, 0.8); seed = s0; // mesma semente = mesma planta
  raizesRasas(x, 150, 4);
}
for (let i = 0; i < 26; i++) { const x = R(4350, 4720), y = g(x) - R(1, 5); superficie.push(`<circle cx="${f(x)}" cy="${f(y)}" r="${f(R(3, 5))}" fill="#EEF2F3" stroke="#9AA9AE" stroke-width="1"/>`); }
for (let i = 0; i < 40; i++) { const x = R(4420, 5100), y = R(g(x) + 30, b1(x) - 8); solo.push(`<circle cx="${f(x)}" cy="${f(y)}" r="${f(R(1.5, 3))}" fill="#E3ECEE" opacity="${f(R(0.35, 0.7))}"/>`); }
// slide 6: arbusto de raiz rasa (cruza a borda 5|6)
{
  const x = 5560, y = g(x);
  plantas.push(`<path d="M${x} ${f(y)} q-2 -30 -8 -52 M${x} ${f(y)} q4 -26 14 -44" stroke="#7A6440" stroke-width="5" fill="none" stroke-linecap="round"/>`);
  for (let i = 0; i < 22; i++) { const lx = x + R(-40, 44), ly = y - R(36, 78); plantas.push(`<ellipse cx="${f(lx)}" cy="${f(ly)}" rx="${f(R(9, 14))}" ry="${f(R(5, 7))}" transform="rotate(${f(R(-40, 40))} ${f(lx)} ${f(ly)})" fill="${pick(['#8E9B55', '#7F8C4A', '#9DA862'])}"/>`); }
  raiz(solo, x - 4, y + 6, Math.PI - 0.4, 330, 6, { alvo: Math.PI - 0.03, k: 0.12, wig: 0.12, ymax: limRaso, cor: corRaizMorta, niveis: 1, ramos: 4 });
  raiz(solo, x + 4, y + 6, 0.4, 230, 5, { alvo: 0.03, k: 0.12, wig: 0.12, ymax: limRaso, cor: corRaizMorta, niveis: 1, ramos: 3 });
}

// ---------- a virada (slides 6-7) ----------
// chave de fenda que não entra
{
  const x = 5880, y = g(x);
  frente.push(`<g transform="rotate(6 ${x} ${f(y)})">
    <rect x="${x - 3}" y="${f(y - 70)}" width="6" height="${f(78)}" fill="url(#gMetal)"/>
    <path d="M${x - 3} ${f(y + 8)} L${x} ${f(y + 16)} L${x + 3} ${f(y + 8)} Z" fill="#8E979C"/>
    <rect x="${x - 15}" y="${f(y - 150)}" width="30" height="84" rx="12" fill="${COR.dourado}"/>
    <rect x="${x - 15}" y="${f(y - 150)}" width="10" height="84" rx="5" fill="#FFFFFF" opacity="0.25"/>
    <path d="M${x - 9} ${f(y - 138)} v60 M${x} ${f(y - 138)} v60 M${x + 9} ${f(y - 138)} v60" stroke="#B98A30" stroke-width="2.5"/>
    <rect x="${x - 11}" y="${f(y - 72)}" width="22" height="8" rx="3" fill="#B98A30"/></g>`);
  for (const dx of [-16, 14]) frente.push(`<path d="M${x + dx} ${f(y - 2)} l${dx > 0 ? 9 : -9} -7" stroke="#8C6E48" stroke-width="2.5" stroke-linecap="round"/>`);
}
// garfo (forcado) descompactando
{
  const top = [6440, 330], cb = [6300, 588];
  const d = Math.hypot(cb[0] - top[0], cb[1] - top[1]), ux = (cb[0] - top[0]) / d, uy = (cb[1] - top[1]) / d, nx = -uy, ny = ux;
  // fraturas e torrões soltos em volta dos dentes
  for (let i = 0; i < 14; i++) {
    let x = cb[0] + ux * R(60, 190) + R(-50, 50), y = cb[1] + uy * R(60, 190), p = `M${f(x)} ${f(y)}`;
    const a0 = R(0, Math.PI * 2);
    for (let s = 0; s < 6; s++) { x += Math.cos(a0 + R(-0.6, 0.6)) * R(10, 22); y += Math.sin(a0 + R(-0.6, 0.6)) * R(8, 18); p += ` L${f(x)} ${f(y)}`; }
    solo.push(`<path d="${p}" stroke="#3A2A1E" stroke-width="1.8" fill="none" opacity="0.55"/>`);
  }
  solo.push(`<ellipse cx="${f(cb[0] + ux * 120)}" cy="${f(cb[1] + uy * 110)}" rx="150" ry="120" fill="#C9A47A" opacity="0.16" filter="url(#blur12)"/>`);
  for (let i = 0; i < 30; i++) { const x = cb[0] + R(-150, 150), y = cb[1] + R(30, 230); solo.push(`<ellipse cx="${f(x)}" cy="${f(y)}" rx="${f(R(3, 8))}" ry="${f(R(2, 5))}" fill="#2A1C12" opacity="0.55"/>`); }
  for (let i = 0; i < 8; i++) { const x = cb[0] + R(-120, 90), y = g(x); superficie.push(`<path d="M${f(x)} ${f(y + 2)} l${f(R(6, 12))} ${f(-R(8, 16))} l${f(R(10, 18))} ${f(R(2, 6))} l2 ${f(R(6, 12))} Z" fill="${pick(['#B08654', '#9C7448', '#C79B63'])}"/>`); }
  // dentes
  const tines = [];
  for (let t = -1.5; t <= 1.5; t++) {
    const bx = cb[0] + nx * t * 22, by = cb[1] + ny * t * 22;
    tines.push(`<path d="M${f(bx - 3)} ${f(by)} L${f(bx + ux * 175 - 1)} ${f(by + uy * 175)} L${f(bx + 3)} ${f(by)} Z" fill="#9AA4A9" stroke="#6E777C" stroke-width="1"/>`);
  }
  solo.push(...tines);
  frente.push(`<path d="M${f(cb[0] - nx * 40)} ${f(cb[1] - ny * 40)} Q${f(cb[0] - ux * 16)} ${f(cb[1] - uy * 16)} ${f(cb[0] + nx * 40)} ${f(cb[1] + ny * 40)}" stroke="#8E979C" stroke-width="9" fill="none" stroke-linecap="round"/>`);
  frente.push(`<path d="M${f(cb[0] - ux * 14)} ${f(cb[1] - uy * 14)} L${f(top[0])} ${f(top[1])}" stroke="url(#gMadeira)" stroke-width="13" stroke-linecap="round"/>`);
  frente.push(`<path d="M${f(cb[0] - ux * 14 - nx * 3)} ${f(cb[1] - uy * 14 - ny * 3)} L${f(top[0] - nx * 3)} ${f(top[1] - ny * 3)}" stroke="#E0B27A" stroke-width="3" opacity="0.6" stroke-linecap="round"/>`);
  frente.push(`<path d="M${f(top[0] - nx * 22)} ${f(top[1] - ny * 22)} L${f(top[0] + nx * 22)} ${f(top[1] + ny * 22)}" stroke="#7C5530" stroke-width="12" fill="none" stroke-linecap="round"/>`);
}
// composto incorporado: manchas escuras e grumos misturados na camada de cima (slide 7)
for (let i = 0; i < 26; i++) {
  const x = R(6560, 7540), y = g(x) + R(30, 150) * (0.6 + vivo(x));
  solo.push(`<ellipse cx="${f(x)}" cy="${f(y)}" rx="${f(R(40, 90))}" ry="${f(R(18, 40))}" fill="#2E1B0E" opacity="${f(R(0.25, 0.45))}" filter="url(#blur12)"/>`);
}
for (let i = 0; i < 160; i++) {
  const x = R(6560, 7540), y = R(g(x) + 8, g(x) + 190);
  solo.push(`<ellipse cx="${f(x)}" cy="${f(y)}" rx="${f(R(2, 6))}" ry="${f(R(1.5, 4))}" transform="rotate(${f(R(-60, 60))} ${f(x)} ${f(y)})" fill="${pick(['#2A170B', '#3B2414', '#5E7D3A', '#8B5A2B'])}" opacity="0.85"/>`);
}
// monte de composto
{
  const x0 = 6640, x1 = 6960, c = (x0 + x1) / 2;
  const topo = (x) => g(x) - 74 * Math.pow(Math.sin(Math.PI * (x - x0) / (x1 - x0)), 0.8);
  superficie.push(`<path d="${faixa(topo, (x) => g(x) + 2, x0, x1)}" fill="url(#gComposto)"/>`);
  for (let i = 0; i < 90; i++) { const x = R(x0 + 14, x1 - 14), y = R(topo(x) + 4, g(x) - 2); superficie.push(`<ellipse cx="${f(x)}" cy="${f(y)}" rx="${f(R(2, 6))}" ry="${f(R(1.2, 3))}" transform="rotate(${f(R(-60, 60))} ${f(x)} ${f(y)})" fill="${pick(['#5E7D3A', '#8B5A2B', '#A0703C', '#2A170B', '#E8DCC2'])}"/>`); }
  superficie.push(`<path d="M${c - 90} ${f(topo(c - 90) + 10)} Q${c} ${f(topo(c) + 4)} ${c + 80} ${f(topo(c + 80) + 12)}" stroke="#7A5634" stroke-width="3" fill="none" opacity="0.5"/>`);
}
// enxada misturando
{
  const bx = 7120, by = g(7120) + 6, top = [7310, 470];
  frente.push(`<path d="M${bx - 4} ${f(by - 16)} L${top[0]} ${top[1]}" stroke="url(#gMadeira)" stroke-width="12" stroke-linecap="round"/>`);
  frente.push(`<path d="M${bx - 40} ${f(by - 4)} L${bx + 22} ${f(by - 10)} L${bx + 18} ${f(by - 30)} L${bx - 12} ${f(by - 26)} Z" fill="#5F686D" stroke="#3E4549" stroke-width="2"/>`);
  for (let i = 0; i < 10; i++) { const x = bx + R(-70, 40); frente.push(`<circle cx="${f(x)}" cy="${f(g(x) - R(4, 26))}" r="${f(R(2.5, 5))}" fill="${pick(['#3B2414', '#5A3A22'])}"/>`); }
}
// muda nova plantada na virada (raiz já desce)
{
  const x = 7430, y = g(x);
  plantas.push(`<path d="M${x} ${f(y)} q2 -26 0 -44" stroke="#3F7F4F" stroke-width="4" fill="none"/>`);
  for (const [dx, dy, a] of [[-14, -40, -30], [14, -46, 30], [-10, -24, -45], [12, -28, 40]]) plantas.push(`<ellipse cx="${x + dx}" cy="${f(y + dy)}" rx="14" ry="6" transform="rotate(${a} ${x + dx} ${f(y + dy)})" fill="${COR.verde}"/>`);
  raiz(solo, x, y + 6, Math.PI / 2, 300, 6, { alvo: Math.PI / 2, k: 0.06, wig: 0.16, cor: '#F3E6CC', niveis: 2, ramos: 3, alvoRamo: Math.PI / 2, para: true });
}

// ---------- solo vivo (slides 7-9) ----------
// agregados e poros (estrutura grumosa)
for (let i = 0; i < 900; i++) {
  const x = R(6500, W), v = vivo(x); if (rnd() > v + 0.15) continue;
  const y = R(g(x) + 20, b1(x) - 6);
  solo.push(`<circle cx="${f(x)}" cy="${f(y)}" r="${f(R(2.5, 9))}" fill="${pick(['#6B4A2E', '#3A2313', '#7A5636', '#2C190C'])}" opacity="${f(R(0.4, 0.8))}"/>`);
}
// micélio: rede fina de fungos atravessando as bordas 7|8 e 8|9
{
  let d = '';
  const fio = (x, y, a, n) => {
    for (let s = 0; s < n; s++) {
      const nx2 = x + Math.cos(a) * R(10, 22), ny2 = y + Math.sin(a) * R(8, 18);
      d += `M${f(x)} ${f(y)} Q${f((x + nx2) / 2 + R(-5, 5))} ${f((y + ny2) / 2 + R(-5, 5))} ${f(nx2)} ${f(ny2)} `;
      x = nx2; y = ny2; a += R(-0.7, 0.7);
      if (rnd() < 0.18 && n > 4) fio(x, y, a + R(-1.4, 1.4), Math.floor(n / 2));
    }
  };
  for (let i = 0; i < 110; i++) { const x = R(7250, 9700); fio(x, R(g(x) + 50, Math.min(1120, b1(x) + 200)), R(0, Math.PI * 2), Math.floor(R(8, 16))); }
  for (const bx of [7560, 8640]) for (let i = 0; i < 8; i++) fio(bx - R(60, 120), R(700, 1050), R(-0.4, 0.4), 14);
  vida.push(`<path d="${d}" stroke="#F4EEDD" stroke-width="1.3" fill="none" opacity="0.55" stroke-linecap="round"/>`);
}
// água infiltrando: gotas descendo com rastro
for (let i = 0; i < 46; i++) {
  const x = R(7000, 9690), y = R(g(x) + 40, 1120); if (rnd() > vivo(x) + 0.2) continue;
  vida.push(`<path d="M${f(x)} ${f(y - 70)} L${f(x)} ${f(y - 16)}" stroke="#9FD0E3" stroke-width="2.5" stroke-dasharray="3 9" stroke-linecap="round" opacity="0.8"/>`);
  vida.push(`<path d="M${f(x)} ${f(y - 14)} C${f(x + 9)} ${f(y - 2)} ${f(x + 8)} ${f(y + 9)} ${f(x)} ${f(y + 9)} C${f(x - 8)} ${f(y + 9)} ${f(x - 9)} ${f(y - 2)} ${f(x)} ${f(y - 14)} Z" fill="#8FC8DE"/><circle cx="${f(x - 2.5)}" cy="${f(y + 1)}" r="2.2" fill="#FFFFFF" opacity="0.7"/>`);
}
// raízes fibrosas do gramado (densas e verticais)
{
  let d = '';
  for (let x = 7620; x < W; x += R(7, 14)) {
    let y = g(x) + 4, xx = x, a = Math.PI / 2; const L = R(120, 300) * vivo(x);
    d += `M${f(xx)} ${f(y)} `;
    for (let s = 0; s < L; s += 12) { a += (Math.PI / 2 - a) * 0.2 + R(-0.3, 0.3); xx += Math.cos(a) * 12; y += Math.sin(a) * 12; d += `L${f(xx)} ${f(y)} `; }
  }
  solo.push(`<path d="${d}" stroke="#EEDFC2" stroke-width="1.3" fill="none" opacity="0.5"/>`);
}
// raízes profundas das plantas do Cerrado
const corRaizViva = '#F3E6CC';
const raizFunda = (x, w, len, laterais) => {
  raiz(solo, x, g(x) + 4, Math.PI / 2, len, w, { alvo: Math.PI / 2, k: 0.05, wig: 0.12, cor: corRaizViva, niveis: 2, ramos: 5, alvoRamo: Math.PI / 2 - 0.2, para: true });
  for (const [a, l, ww] of laterais) raiz(solo, x, g(x) + R(20, 60), a, l, ww, { alvo: a > Math.PI / 2 ? Math.PI * 0.62 : Math.PI * 0.38, k: 0.02, wig: 0.1, cor: corRaizViva, niveis: 1, ramos: 3, alpha: 0.95, para: true });
};
raizFunda(7800, 12, 600, [[Math.PI - 0.35, 430, 7], [0.5, 260, 5]]);                  // canela-de-ema, lateral cruza 7|8
raizFunda(8330, 20, 640, [[0.32, 620, 10], [Math.PI - 0.4, 380, 8], [0.9, 300, 6]]); // ipê, lateral cruza 8|9
raizFunda(8780, 8, 520, [[Math.PI - 0.5, 200, 4]]);
raizFunda(9060, 9, 560, [[0.6, 220, 4]]);
raizFunda(9340, 11, 590, [[Math.PI - 0.6, 240, 5], [0.5, 220, 5]]);
raizFunda(9590, 8, 520, [[Math.PI - 0.5, 200, 4]]);

// minhocas (com galeria), larva e besouro
function minhoca(p, w = 13) {
  vida.push(`<path d="${p.map(([x, y], i) => `${i ? 'L' : 'M'}${f(x)} ${f(y)}`).join(' ')}" stroke="#24150B" stroke-width="${w + 12}" stroke-linecap="round" stroke-linejoin="round" fill="none" opacity="0.55"/>`);
  vida.push(`<path d="${taper(p, w, w * 0.75)}" fill="#C97F72"/>`);
  vida.push(`<path d="${p.map(([x, y], i) => `${i ? 'L' : 'M'}${f(x)} ${f(y - w * 0.22)}`).join(' ')}" stroke="#EBB2A5" stroke-width="2.4" fill="none" stroke-linecap="round" opacity="0.8"/>`);
  for (let i = 2; i < p.length - 1; i += 2) {
    const [x, y] = p[i], [x2, y2] = p[i + 1], a = Math.atan2(y2 - y, x2 - x) + Math.PI / 2;
    vida.push(`<path d="M${f(x + Math.cos(a) * w * 0.45)} ${f(y + Math.sin(a) * w * 0.45)} L${f(x - Math.cos(a) * w * 0.45)} ${f(y - Math.sin(a) * w * 0.45)}" stroke="#A0574D" stroke-width="1.6" opacity="0.7"/>`);
  }
  const k = Math.floor(p.length * 0.3); vida.push(`<circle cx="${f(p[k][0])}" cy="${f(p[k][1])}" r="${f(w * 0.62)}" fill="#D9958A"/>`);
}
const onda = (x0, y0, x1, y1, amp, per) => { const p = []; const n = 34; for (let i = 0; i <= n; i++) { const t = i / n; const x = x0 + (x1 - x0) * t, y = y0 + (y1 - y0) * t + amp * Math.sin(t * Math.PI * per); p.push([x, y]); } return p; };
minhoca(onda(7330, 690, 7470, 740, 10, 2), 10);          // primeira minhoca chegando (slide 7)
minhoca(onda(7470, 800, 7680, 760, 14, 2.4), 13);        // cruza a borda 7|8
minhoca(onda(8540, 930, 8760, 975, 15, 2.6), 13);        // cruza a borda 8|9
minhoca(onda(9230, 740, 9300, 900, 10, 2.2), 12);
minhoca(onda(9500, 1000, 9660, 960, 12, 2), 12);
// larva (bicho-bolo) enrolada
{
  const cx = 8060, cy = 1040, r = 26;
  const p = []; for (let i = 0; i <= 24; i++) { const a = Math.PI * 0.15 + i / 24 * Math.PI * 1.45; p.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]); }
  vida.push(`<path d="${p.map(([x, y], i) => `${i ? 'L' : 'M'}${f(x)} ${f(y)}`).join(' ')}" stroke="#24150B" stroke-width="40" fill="none" opacity="0.5" stroke-linecap="round"/>`);
  vida.push(`<path d="${taper(p, 16, 24)}" fill="#F0E8D4"/>`);
  for (let i = 3; i < 24; i += 3) { const [x, y] = p[i]; const a = Math.atan2(y - cy, x - cx); vida.push(`<path d="M${f(cx + Math.cos(a) * (r - 9))} ${f(cy + Math.sin(a) * (r - 9))} L${f(cx + Math.cos(a) * (r + 10))} ${f(cy + Math.sin(a) * (r + 10))}" stroke="#CDBE9C" stroke-width="1.8"/>`); }
  vida.push(`<circle cx="${f(p[24][0])}" cy="${f(p[24][1])}" r="11" fill="#B5652E"/><circle cx="${f(p[24][0] + 3)}" cy="${f(p[24][1] - 3)}" r="3" fill="#FFFFFF" opacity="0.5"/>`);
}
// besouro na palhada (slide 9) e cogumelos
const besouro = (x, y) => frente.push(`<g transform="translate(${x} ${f(y)})"><path d="M-14 -2 l-8 6 M-6 0 l-6 9 M6 0 l6 9 M14 -2 l8 6" stroke="#1B1A14" stroke-width="2"/><ellipse cx="0" cy="-8" rx="16" ry="11" fill="#1F3A2A"/><path d="M0 -19 V3" stroke="#0B1A12" stroke-width="1.5"/><ellipse cx="-5" cy="-12" rx="5" ry="3" fill="#7FD0A0" opacity="0.5"/><circle cx="17" cy="-8" r="6" fill="#1B1A14"/></g>`);
const cogumelo = (x, h, r) => { const y = g(x) - 8; frente.push(`<path d="M${x - 4} ${f(y)} L${x - 3} ${f(y - h)} L${x + 3} ${f(y - h)} L${x + 4} ${f(y)} Z" fill="#EFE6D2"/><path d="M${x - r} ${f(y - h + 2)} Q${x} ${f(y - h - r * 1.1)} ${x + r} ${f(y - h + 2)} Z" fill="#C8763E"/><circle cx="${x - r * 0.35}" cy="${f(y - h - r * 0.3)}" r="${f(r * 0.16)}" fill="#F4E3C4"/><circle cx="${x + r * 0.3}" cy="${f(y - h - r * 0.45)}" r="${f(r * 0.12)}" fill="#F4E3C4"/>`); };

// palhada cobrindo o solo (começa no slide 7 e segue até o 9)
{
  superficie.push(`<path d="${faixa((x) => g(x) - 10 * ss(6980, 7160, x), (x) => g(x) + 3, 6980, W)}" fill="#B98E45"/>`);
  const cores = ['#E2B65B', '#D4A84E', '#C69440', '#EBCB7E', '#B88A3C', '#F0D48E'];
  let porCor = Object.fromEntries(cores.map((c) => [c, '']));
  for (let i = 0; i < 2600; i++) {
    const x = R(6980, W); if (rnd() > ss(6980, 7200, x)) continue;
    const y = g(x) - R(0, 15), L = R(14, 34), a = R(-0.4, 0.4);
    const c = pick(cores);
    porCor[c] += `M${f(x)} ${f(y)} L${f(x + Math.cos(a) * L)} ${f(y + Math.sin(a) * L)} `;
  }
  for (const c of cores) superficie.push(`<path d="${porCor[c]}" stroke="${c}" stroke-width="2.8" stroke-linecap="round" fill="none"/>`);
}
// gramado verde (slides 8-9)
{
  const cores = ['#3AA56F', '#2F8F5D', '#4DB57E', '#25784B', '#62C08B'];
  const porCor = Object.fromEntries(cores.map((c) => [c, '']));
  for (let x = 7560; x < W; x += R(3, 6)) {
    const v = ss(7560, 7900, x); if (rnd() > v) continue;
    const y = g(x) - 8, h = R(16, 44), a = R(-0.35, 0.35), c = pick(cores);
    porCor[c] += lamina(x, y + 4, x + Math.sin(a) * h, y - Math.cos(a) * h, x + Math.sin(a) * h * 0.3, y - h * 0.6, 2.2) + ' ';
  }
  for (const c of cores) plantas.push(`<path d="${porCor[c]}" fill="${c}"/>`);
}
// plantas do Cerrado
function canelaDeEma(x) {
  const y = g(x) - 6;
  plantas.push(`<path d="${taper([[x, y], [x - 2, y - 50], [x - 4, y - 96]], 18, 12)}" fill="#4A3B2C"/>`);
  plantas.push(`<path d="${taper([[x - 3, y - 70], [x + 18, y - 110], [x + 34, y - 132]], 11, 8)}" fill="#4A3B2C"/>`);
  for (let i = 0; i < 12; i++) plantas.push(`<path d="M${x - 6 + i * 1.2} ${f(y - 8 - i * 7)} q-8 -3 -10 -9" stroke="#2E241A" stroke-width="1.6" fill="none"/>`);
  for (const [cx, cy] of [[x - 4, y - 100], [x + 34, y - 136]]) {
    for (let i = 0; i < 26; i++) { const a = -Math.PI / 2 + R(-1.5, 1.5), L = R(34, 62); plantas.push(`<path d="${lamina(cx, cy, cx + Math.cos(a) * L, cy + Math.sin(a) * L, cx + Math.cos(a) * L * 0.5, cy + Math.sin(a) * L * 0.5 - 4, 2)}" fill="${pick(['#4F7F55', '#3E6E4A', '#6A9A64'])}"/>`); }
    for (let k = 0; k < 6; k++) { const a = k / 6 * Math.PI * 2; plantas.push(`<ellipse cx="${f(cx + Math.cos(a) * 9)}" cy="${f(cy - 44 + Math.sin(a) * 9)}" rx="9" ry="5" transform="rotate(${f(a * 180 / Math.PI)} ${f(cx + Math.cos(a) * 9)} ${f(cy - 44 + Math.sin(a) * 9)})" fill="#9B7BC4"/>`); }
    plantas.push(`<circle cx="${f(cx)}" cy="${f(cy - 44)}" r="5" fill="${COR.dourado}"/>`);
  }
}
function ipe(x) {
  const y = g(x) - 6;
  plantas.push(`<path d="${taper([[x, y + 4], [x - 6, y - 60], [x + 8, y - 120], [x - 2, y - 180], [x + 6, y - 222]], 34, 18)}" fill="url(#gTronco)"/>`);
  for (const [ex, ey, w] of [[x - 100, y - 290, 10], [x + 110, y - 286, 10], [x - 30, y - 330, 9], [x + 50, y - 334, 9]]) plantas.push(`<path d="${taper([[x + 4, y - 200], [(x + ex) / 2, (y - 220 + ey) / 2 + 6], [ex, ey]], w + 6, w * 0.5)}" fill="#4E3828"/>`);
  for (let i = 0; i < 9; i++) plantas.push(`<path d="M${x - 10} ${f(y - 20 - i * 22)} q8 -6 16 -2" stroke="#2F2219" stroke-width="2" fill="none" opacity="0.7"/>`);
  for (let i = 0; i < 70; i++) {
    const a = R(0, Math.PI * 2), rr = Math.sqrt(rnd()), cx = x + 5 + Math.cos(a) * rr * 190, cy = y - 290 + Math.sin(a) * rr * 80;
    const r0 = R(14, 26), sombra = (cy - (y - 290)) / 80;
    const base = sombra > 0.3 ? '#C99A3A' : pick(['#E2B65B', '#EFC96A', '#F5D886']);
    plantas.push(`<circle cx="${f(cx)}" cy="${f(cy)}" r="${f(r0)}" fill="${base}"/>`);
    for (let k = 0; k < 3; k++) plantas.push(`<circle cx="${f(cx + R(-r0, r0) * 0.6)}" cy="${f(cy + R(-r0, r0) * 0.6)}" r="${f(r0 * R(0.2, 0.34))}" fill="${pick(['#F8E3A0', '#D9A441', '#FBEAB5'])}"/>`);
  }
  for (let i = 0; i < 14; i++) { const fx = x + R(-200, 220); frente.push(`<circle cx="${f(fx)}" cy="${f(g(fx) - R(8, 14))}" r="${f(R(4, 7))}" fill="${pick(['#E2B65B', '#F0CD72'])}"/>`); }
}
function capimDourado(x) {
  const y = g(x) - 8;
  touceira(plantas, x, 26, ['#5E8C4A', '#4C7A3E'], 10, 2.4, 1.3);
  for (let i = 0; i < 9; i++) { const a = R(-0.45, 0.45), L = R(70, 104), tx = x + Math.sin(a) * L, ty = y - Math.cos(a) * L; plantas.push(`<path d="M${x} ${f(y)} Q${f(x + Math.sin(a) * L * 0.3)} ${f(y - L * 0.6)} ${f(tx)} ${f(ty)}" stroke="#D6A93F" stroke-width="2.4" fill="none"/><circle cx="${f(tx)}" cy="${f(ty)}" r="5" fill="#F7EFD8" stroke="#C9A24A" stroke-width="1.2"/>`); }
}
function chuveirinho(x) {
  const y = g(x) - 8;
  touceira(plantas, x, 30, ['#3E7A4C', '#2F6A3F', '#4E8C5A'], 14, 3, 1.4);
  for (let i = 0; i < 13; i++) { const a = R(-0.9, 0.9), L = R(66, 100), tx = x + Math.sin(a) * L, ty = y - Math.cos(a) * L; plantas.push(`<path d="M${x} ${f(y - 10)} Q${f(x + Math.sin(a) * L * 0.2)} ${f(y - L * 0.6)} ${f(tx)} ${f(ty)}" stroke="#9DB06A" stroke-width="1.8" fill="none"/><circle cx="${f(tx)}" cy="${f(ty)}" r="7.5" fill="#FBFAF2" stroke="#C8CDB8" stroke-width="1.2"/>`); }
}
function murici(x) {
  const y = g(x) - 6;
  plantas.push(`<path d="M${x} ${f(y)} q-4 -30 -20 -52 M${x} ${f(y)} q6 -34 24 -58 M${x} ${f(y)} q0 -40 2 -70" stroke="#5A4330" stroke-width="5" fill="none" stroke-linecap="round"/>`);
  for (let i = 0; i < 40; i++) { const lx = x + R(-62, 62), ly = y - R(40, 100); plantas.push(`<ellipse cx="${f(lx)}" cy="${f(ly)}" rx="${f(R(10, 16))}" ry="${f(R(6, 9))}" transform="rotate(${f(R(-50, 50))} ${f(lx)} ${f(ly)})" fill="${pick(['#3AA56F', '#2F8F5D', '#25784B', '#4DB57E'])}"/>`); }
  for (let i = 0; i < 12; i++) plantas.push(`<circle cx="${f(x + R(-55, 55))}" cy="${f(y - R(50, 104))}" r="4.5" fill="${COR.dourado}"/>`);
}
canelaDeEma(7800); ipe(8330); capimDourado(8780); chuveirinho(9060); murici(9340); capimDourado(9590);
cogumelo(8050, 18, 14); cogumelo(8072, 12, 9); besouro(8960, g(8960) - 10);

// linha do chão nítida (uma só, contínua nos 9 slides)
superficie.push(`<path d="${linha(g, 0, W, 6).map(([x, y], i) => `${i ? 'L' : 'M'}${f(x)} ${f(y)}`).join(' ')}" stroke="#5E4330" stroke-width="2" fill="none" opacity="0.55"/>`);

// ---------- defs ----------
const defs = `
<linearGradient id="gCeu" x1="0" y1="0" x2="${W}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#EEE0C2"/><stop offset="0.58" stop-color="#F1E6CF"/><stop offset="0.76" stop-color="#EFF7EE"/><stop offset="1" stop-color="#E4F3E8"/></linearGradient>
<linearGradient id="gCeuV" x1="0" y1="0" x2="0" y2="620" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0.45"/></linearGradient>
<linearGradient id="gMorro" x1="0" y1="0" x2="${W}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#E2CFA6"/><stop offset="0.6" stop-color="#E0D0AE"/><stop offset="0.8" stop-color="#CBE3D0"/><stop offset="1" stop-color="#C2DFCA"/></linearGradient>
<linearGradient id="gSuperf" x1="0" y1="0" x2="${W}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#B98C57"/><stop offset="0.6" stop-color="#AC8250"/><stop offset="0.7" stop-color="#6F4B2E"/><stop offset="0.82" stop-color="#4C2F1B"/><stop offset="1" stop-color="#452A18"/></linearGradient>
<linearGradient id="gCompacta" x1="0" y1="0" x2="${W}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#8C7967"/><stop offset="0.62" stop-color="#857260"/><stop offset="0.74" stop-color="#6E5038"/><stop offset="0.86" stop-color="#5E4330"/><stop offset="1" stop-color="#5A402D"/></linearGradient>
<linearGradient id="gFundo" x1="0" y1="0" x2="${W}" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#4C4036"/><stop offset="0.62" stop-color="#4A3C31"/><stop offset="0.86" stop-color="#3B2A1E"/><stop offset="1" stop-color="#38271A"/></linearGradient>
<linearGradient id="gSombra" x1="0" y1="560" x2="0" y2="${H}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#140A04" stop-opacity="0"/><stop offset="0.55" stop-color="#140A04" stop-opacity="0.18"/><stop offset="1" stop-color="#140A04" stop-opacity="0.5"/></linearGradient>
<linearGradient id="gAgua" x1="0" y1="610" x2="0" y2="640" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#A9D3E1"/><stop offset="1" stop-color="#5E93A8"/></linearGradient>
<linearGradient id="gComposto" x1="0" y1="520" x2="0" y2="600" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#5A3A22"/><stop offset="1" stop-color="#2A170B"/></linearGradient>
<linearGradient id="gMadeira" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#B98249"/><stop offset="1" stop-color="#8A5A30"/></linearGradient>
<linearGradient id="gMetal" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#7E878C"/><stop offset="0.5" stop-color="#D6DCDF"/><stop offset="1" stop-color="#80898E"/></linearGradient>
<linearGradient id="gTronco" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3E2C20"/><stop offset="0.5" stop-color="#6B4C36"/><stop offset="1" stop-color="#3A291D"/></linearGradient>
<filter id="blur12" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="12"/></filter>
<filter id="blur3" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3"/></filter>
<filter id="graoEsc" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4"/><feColorMatrix type="matrix" values="0 0 0 0 0.08  0 0 0 0 0.05  0 0 0 0 0.03  2.2 0 0 0 -1.15"/></filter>
<filter id="graoClaro" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="1" seed="11"/><feColorMatrix type="matrix" values="0 0 0 0 0.95  0 0 0 0 0.9  0 0 0 0 0.8  2.4 0 0 0 -1.45"/></filter>
<clipPath id="cSolo"><path d="${faixa(g, () => H)}"/></clipPath>`;

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><defs>${defs}</defs>
<rect width="${W}" height="${H}" fill="url(#gCeu)"/><rect width="${W}" height="620" fill="url(#gCeuV)"/>
${ceu.join('')}${fundo.join('')}${solo.join('\n')}${vida.join('\n')}${plantas.join('\n')}${superficie.join('\n')}${frente.join('\n')}
</svg>`;
  return svg;
}
