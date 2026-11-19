#!/usr/bin/env node
// Autoteste do gate-post-insta: cada regra tem que ser vista reprovando ("exit 0 não é prova").
// Usa uma config própria do teste, independente do config.json de quem roda.
const { verificar } = require('./gate-post-insta.cjs');
const fs = require('fs');
const path = require('path');
const os = require('os');

const cfg = {
  marca: { nome: 'Marca Teste', escritas_erradas: ['Marka Teste'] },
  telefone_oficial: '(00) 00000-0000',
  termos_vetados: [
    { padrao: '\\bclientevetado\\b', motivo: 'cliente sem autorização' },
    { padrao: '\\b(margem|lucro)\\b', motivo: 'não fala de margem' },
  ],
  pastas_vetadas: ['pasta-vetada'],
  correcoes_legenda: [{ errado: '\\bbic\\b', certo: 'bico' }],
  legenda: { max_caracteres: 2200, max_hashtags: 30, midia_min_bytes: 20000 },
};

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gate-insta-'));
const grande = path.join(dir, 'midia.bin');
fs.writeFileSync(grande, Buffer.alloc(50000));
fs.mkdirSync(path.join(dir, 'pasta-vetada'));
const vetada = path.join(dir, 'pasta-vetada', 'foto.bin');
fs.writeFileSync(vetada, Buffer.alloc(50000));
const pequena = path.join(dir, 'pequena.bin');
fs.writeFileSync(pequena, Buffer.alloc(100));

const base = { midia: grande, legenda: 'Solo vivo.\n\nComente SOLO que eu te mando o teste. #solovivo', palavraManychat: 'SOLO' };
const casos = [
  ['ok', {}, null],
  ['comente no início', { legenda: 'Comente SOLO e receba o teste.\n\nSolo vivo segura água. #solovivo' }, null],
  ['comente com aspas', { legenda: 'Solo vivo. Comente “SOLO” que eu te mando.' }, null],
  ['termo vetado (cliente)', { legenda: 'Obra do clientevetado. Comente SOLO' }, 'termo'],
  ['termo vetado (margem)', { legenda: 'Nossa margem é justa. Comente SOLO' }, 'termo'],
  ['pasta vetada', { midia: vetada }, 'midia'],
  ['bic', { legenda: 'Troque o bic do aspersor. Comente SOLO' }, 'transcricao'],
  ['bico ok', { legenda: 'Troque o bico do aspersor. Comente SOLO' }, null],
  ['marca escrita errada', { legenda: 'Aqui na Marka Teste. Comente SOLO' }, 'marca'],
  ['tel errado', { legenda: 'Chame: (00) 11111-2222', palavraManychat: null }, 'whatsapp'],
  ['tel certo', { legenda: 'Chame: (00) 00000-0000', palavraManychat: null }, null],
  ['palavra diferente', { palavraManychat: 'TESTE' }, 'manychat'],
  ['comente sem automação', { palavraManychat: null }, 'manychat'],
  ['automação sem comente', { legenda: 'Solo vivo. #solovivo' }, 'manychat'],
  ['dois ctas', { legenda: 'Comente SOLO ou chame (00) 00000-0000' }, 'cta-unico'],
  ['comente + link na bio', { legenda: 'Comente SOLO. Link na bio.' }, 'cta-unico'],
  ['sem mídia', { midia: path.join(dir, 'nao-existe.mp4') }, 'midia'],
  ['mídia pequena', { midia: pequena }, 'midia'],
  ['legenda longa', { legenda: 'Comente SOLO ' + 'a'.repeat(2300) }, 'tamanho'],
  ['hashtags demais', { legenda: 'Comente SOLO ' + Array.from({ length: 31 }, (_, i) => `#tag${i}`).join(' ') }, 'tamanho'],
  ['legenda vazia', { legenda: '   ', palavraManychat: null }, 'tamanho'],
];
let falhou = 0;
for (const [nome, mud, esperado] of casos) {
  const regras = verificar({ ...base, ...mud }, cfg).map((x) => x[0]);
  const ok = esperado ? regras.includes(esperado) : regras.length === 0;
  console.log(`${ok ? '✓' : '✗'} ${nome}${ok ? '' : `: esperado ${esperado || 'aprovar'}, veio [${regras}]`}`);
  if (!ok) falhou++;
}
fs.rmSync(dir, { recursive: true, force: true });
console.log(`${casos.length - falhou}/${casos.length} casos`);
process.exit(falhou ? 1 : 0);
