// Utilidades dos geradores de imagem (carrossel, panorama, stories).
import { createRequire } from 'node:module';
import { readFileSync, existsSync } from 'node:fs';
import { extname, resolve, dirname } from 'node:path';

const require = createRequire(import.meta.url);

/** Abre o Chrome/Edge instalado em modo headless (playwright-core não traz navegador). */
export async function abrirNavegador() {
  const { chromium } = require('playwright-core');
  const exe = process.env.CHROME_PATH;
  if (exe) return chromium.launch({ executablePath: exe, headless: true });
  for (const channel of ['chrome', 'msedge']) {
    try { return await chromium.launch({ channel, headless: true }); } catch { /* tenta o próximo */ }
  }
  throw new Error('Chrome/Edge não encontrado. Defina CHROME_PATH com o caminho do executável.');
}

const MIME = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml' };

/**
 * Imagem embutida em base64.
 * Lição de 18/11: com page.setContent() a página não tem origem de arquivo, e url('file://...') não carrega
 * (o fundo sai em branco, sem erro). Embutir a imagem resolve.
 */
export function dataUri(caminho) {
  const m = MIME[extname(caminho).toLowerCase()];
  if (!m) throw new Error(`formato de imagem não suportado: ${caminho}`);
  return `data:${m};base64,${readFileSync(caminho).toString('base64')}`;
}

/** Lê um JSON de config e resolve caminhos relativos a ele. */
export function lerConfig(arq) {
  if (!arq || !existsSync(arq)) throw new Error(`config não encontrado: ${arq}`);
  const cfg = JSON.parse(readFileSync(arq, 'utf8'));
  const base = dirname(resolve(arq));
  return { cfg, rel: (p) => (p ? resolve(base, p) : p) };
}

/** Escapa texto para HTML. Campos que aceitam marcação usam a chave `html` em vez de `texto`. */
export const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
