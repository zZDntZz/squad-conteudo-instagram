// Renderiza os grafismos de um projeto a partir de trabalho/plano_render.json.
// Uso: node render.mjs <pasta_do_projeto>
// Empacota uma vez (publicDir = assets do projeto) e renderiza cada beat;
// beats "cheio" saem em H.264, beats "sobre" em ProRes 4444 com alfa.
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const projeto = path.resolve(process.argv[2]);
const plano = JSON.parse(fs.readFileSync(path.join(projeto, "trabalho", "plano_render.json"), "utf-8"));
const saida = path.join(projeto, "graficos");
fs.mkdirSync(saida, { recursive: true });

const serveUrl = await bundle({
  entryPoint: path.join(aqui, "src", "index.ts"),
  publicDir: path.join(projeto, "assets"),
});

// Código dos templates entra na chave do cache: mudou o template, rerenderiza.
const versao = createHash("sha1");
for (const f of fs.readdirSync(path.join(aqui, "src")).sort()) versao.update(fs.readFileSync(path.join(aqui, "src", f)));
const vsrc = versao.digest("hex");

let feitos = 0, pulados = 0;
for (const b of plano.itens) {
  const hash = createHash("sha1").update(vsrc + JSON.stringify({ ...b, saida: undefined })).digest("hex").slice(0, 10);
  const ext = b.alfa ? "mov" : "mp4";
  const arq = path.join(saida, `${b.id}_${hash}.${ext}`);
  b.saida = arq;
  if (fs.existsSync(arq) && fs.statSync(arq).size > 0) { pulados++; continue; }
  const comp = await selectComposition({ serveUrl, id: b.template, inputProps: b.props });
  await renderMedia({
    composition: comp, serveUrl, inputProps: b.props, outputLocation: arq + ".parcial." + ext,
    codec: b.alfa ? "prores" : "h264",
    ...(b.alfa ? { proResProfile: "4444", pixelFormat: "yuva444p10le", imageFormat: "png" } : { crf: 16 }),
    muted: true, concurrency: 4, logLevel: "error",
  });
  fs.renameSync(arq + ".parcial." + ext, arq);
  feitos++;
  console.log(`  ${b.id} ${b.template} (${b.props.duracao.toFixed(1)}s)`);
}
fs.writeFileSync(path.join(projeto, "trabalho", "plano_render.json"), JSON.stringify(plano, null, 1));
// o bundle copia assets/ para o Temp a cada execução e o Remotion não apaga:
// 265 sobras somaram 68 GB e encheram o C: (17/10)
fs.rmSync(serveUrl, { recursive: true, force: true });
console.log(`grafismos: ${feitos} renderizados, ${pulados} do cache`);
