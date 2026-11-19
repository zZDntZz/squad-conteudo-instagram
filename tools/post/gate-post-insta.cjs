#!/usr/bin/env node
/*
 * Gate de legenda de post do Instagram. Nada é agendado ou publicado sem exit 0.
 *
 * Uso: node gate-post-insta.cjs post.json [--config config.json]
 * post.json: { "midia": "caminho do arquivo", "legenda": "texto", "palavraManychat": "SOLO" | null }
 *
 * As regras de marca (termos vetados, telefone oficial, pastas vetadas, escritas erradas do nome)
 * vêm do config.json. O código não sabe nada da sua marca.
 *
 * Cada regra nasceu de um defeito real:
 *  - termo:       conteúdo vetado pelo dono apareceu na legenda (cliente sem autorização, margem/lucro).
 *  - midia:       foto de pasta vetada entrou no post; arquivo inexistente ou pequeno demais.
 *  - transcricao: legenda saiu com erro de transcrição ("bic" no lugar de "bico").
 *  - marca:       o nome da marca saiu escrito como o Whisper ouviu.
 *  - whatsapp:    número na legenda tem que ser o oficial.
 *  - manychat:    a legenda pede "Comente X" e X tem que ser a palavra da automação (e vice-versa).
 *                 A posição não importa: "Comente X" pode abrir a legenda ou fechar.
 *  - cta-unico:   uma chamada por peça (comente OU WhatsApp OU link na bio).
 *  - tamanho:     limite do Instagram (2.200 caracteres, 30 hashtags) e legenda vazia.
 */
const fs = require('fs');
const path = require('path');

function carregarConfig(arq) {
  const raiz = path.resolve(__dirname, '..', '..');
  const cand = arq ? [arq] : [path.join(raiz, 'config.json'), path.join(raiz, 'config.exemplo.json')];
  for (const c of cand) {
    if (fs.existsSync(c)) {
      if (!arq && c.endsWith('config.exemplo.json')) console.error('aviso: usando config.exemplo.json (crie o seu config.json)');
      return JSON.parse(fs.readFileSync(c, 'utf8'));
    }
  }
  throw new Error(`config não encontrado: ${cand.join(', ')}`);
}

const digitos = (s) => String(s || '').replace(/\D/g, '');

function verificar(post, cfg) {
  const f = [];
  const L = post.legenda || '';
  const lim = cfg.legenda || {};
  for (const t of cfg.termos_vetados || []) {
    if (new RegExp(t.padrao, 'i').test(L)) f.push(['termo', `a legenda bate em "${t.padrao}": ${t.motivo}`]);
  }
  for (const p of cfg.pastas_vetadas || []) {
    if ((post.midia || '').toLowerCase().includes(p.toLowerCase())) f.push(['midia', `a mídia vem de pasta vetada (${p})`]);
  }
  for (const c of cfg.correcoes_legenda || []) {
    if (new RegExp(c.errado, 'i').test(L)) f.push(['transcricao', `"${c.errado}" na legenda (o certo é "${c.certo}")`]);
  }
  for (const e of (cfg.marca || {}).escritas_erradas || []) {
    if (L.toLowerCase().includes(e.toLowerCase())) f.push(['marca', `"${e}" na legenda (é "${cfg.marca.nome}")`]);
  }
  const oficial = digitos(cfg.telefone_oficial);
  const tels = L.match(/\(?\b\d{2}\)?\s?\d{4,5}-?\d{4}\b/g) || [];
  for (const t of tels) if (digitos(t) !== oficial) f.push(['whatsapp', `número ${t} não é o oficial ${cfg.telefone_oficial}`]);
  const comente = L.match(/comente\s+["“'*]*([A-Za-zÀ-ÿ0-9]+)/i);
  const palavra = post.palavraManychat;
  if (comente && !palavra) f.push(['manychat', `a legenda pede "Comente ${comente[1]}" mas não há automação`]);
  if (comente && palavra && comente[1].toLowerCase() !== palavra.toLowerCase())
    f.push(['manychat', `legenda pede "${comente[1]}", automação usa "${palavra}"`]);
  if (!comente && palavra) f.push(['manychat', `automação "${palavra}" mas a legenda não pede o comentário`]);
  const ctas = [!!comente, tels.length > 0, /link na bio/i.test(L)].filter(Boolean).length;
  if (ctas > 1) f.push(['cta-unico', `${ctas} chamadas na mesma legenda; deixe uma só`]);
  const max = lim.max_caracteres || 2200, maxh = lim.max_hashtags || 30;
  if (L.length > max) f.push(['tamanho', `legenda com ${L.length} caracteres (máx. ${max})`]);
  if ((L.match(/#[\wÀ-ÿ]/g) || []).length > maxh) f.push(['tamanho', `mais de ${maxh} hashtags`]);
  if (!L.trim()) f.push(['tamanho', 'legenda vazia']);
  if (!post.midia || !fs.existsSync(post.midia)) f.push(['midia', `arquivo não encontrado: ${post.midia}`]);
  else if (fs.statSync(post.midia).size < (lim.midia_min_bytes || 20000)) f.push(['midia', 'arquivo pequeno demais para ser a mídia final']);
  return f;
}

module.exports = { verificar, carregarConfig };

if (require.main === module) {
  const a = process.argv.slice(2);
  const i = a.indexOf('--config');
  const cfg = carregarConfig(i >= 0 ? a[i + 1] : null);
  const arq = a.find((x, k) => !x.startsWith('--') && a[k - 1] !== '--config');
  if (!arq) { console.error('uso: node gate-post-insta.cjs post.json [--config config.json]'); process.exit(2); }
  const post = JSON.parse(fs.readFileSync(arq, 'utf8'));
  const f = verificar(post, cfg);
  if (f.length) {
    console.error(`GATE REPROVOU — ${f.length} problema(s) em ${arq}:`);
    for (const [r, d] of f) console.error(`  ${r.padEnd(12)} ${d}`);
    process.exit(1);
  }
  console.log('gate aprovado');
}
