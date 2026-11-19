import React from "react";
import {
  AbsoluteFill, Img, OffthreadVideo, interpolate, staticFile, useCurrentFrame, useVideoConfig, Easing,
} from "remotion";
import { Base, Cena, MarcaTexto, Papel, Surge, TEXTO, TITULO, useSeg } from "./comum";

const src = (s: string) => (/^https?:/.test(s) ? s : staticFile(s));

/* ------------------------------------------------------------------ */
/* 1. Texto cinético: palavras entram no tempo da fala, sobre fundo      */
/*    (B-roll escurecido, imagem ou cor). Assinatura do formato.         */
/* ------------------------------------------------------------------ */
export type TextoCineticoProps = Base & {
  palavras: { t: string; em: number }[];
  destaque?: string[];
  fundo?: { tipo: "video" | "imagem" | "cor" | "claro"; src?: string; inicio?: number };
  posicao?: "centro" | "baixo";
};
export const TextoCinetico: React.FC<TextoCineticoProps> = ({ marca, palavras, destaque = [], fundo, posicao = "centro" }) => {
  const f = useCurrentFrame();
  const seg = useSeg();
  const { durationInFrames: d } = useVideoConfig();
  const zoom = interpolate(f, [0, d], [1.0, 1.08]);
  const alvo = new Set(destaque.map((p) => p.toUpperCase()));
  // "claro": papel da marca e texto escuro — aula gravada em cenário claro não mergulha no preto
  // (gate F04 pegou 1,1 s de verde quase preto com uma palavra só, parte 1 de uma aula).
  const claro = fundo?.tipo === "claro";
  const midia = fundo?.tipo === "video" || fundo?.tipo === "imagem";
  return (
    <Cena pushIn={0} fundo={claro ? marca.cores.claro : marca.cores.escuro}>
      {fundo?.tipo === "video" && fundo.src && (
        <AbsoluteFill style={{ transform: `scale(${zoom})` }}>
          <OffthreadVideo src={src(fundo.src)} muted startFrom={seg(fundo.inicio ?? 0)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </AbsoluteFill>
      )}
      {fundo?.tipo === "imagem" && fundo.src && (
        <AbsoluteFill style={{ transform: `scale(${zoom})` }}>
          <Img src={src(fundo.src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </AbsoluteFill>
      )}
      {midia && palavras.length > 0 && <AbsoluteFill style={{ background: "rgba(0,0,0,0.55)" }} />}
      <AbsoluteFill style={{
        justifyContent: posicao === "centro" ? "center" : "flex-end", alignItems: "center",
        padding: posicao === "centro" ? 120 : "0 120px 150px",
      }}>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0 22px", maxWidth: 1500 }}>
          {palavras.map((p, i) => {
            const vis = f >= seg(p.em);
            const k = interpolate(f, [seg(p.em), seg(p.em) + 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            const forte = alvo.has(p.t.toUpperCase().replace(/[^\p{L}\p{N}$%]/gu, ""));
            return (
              <span key={i} style={{
                fontFamily: TITULO, fontSize: 96, lineHeight: 1.08, textTransform: "uppercase",
                color: claro ? (forte ? marca.cores.primaria : marca.cores.tinta) : (forte ? marca.cores.destaque : marca.cores.claro),
                opacity: vis ? k : 0,
                transform: `translateY(${(1 - k) * 18}px)`, filter: `blur(${(1 - k) * 6}px)`,
                textShadow: claro ? "none" : "0 0 30px rgba(255,255,255,0.25), 0 4px 18px rgba(0,0,0,0.6)",
                textDecoration: claro && forte ? `underline ${marca.cores.destaque} 8px` : "none",
                textUnderlineOffset: 14,
              }}>{p.t}</span>
            );
          })}
        </div>
      </AbsoluteFill>
    </Cena>
  );
};

/* ------------------------------------------------------------------ */
/* 2. Manchete: card editorial de notícia com marca-texto sincronizado. */
/*    Título citado literalmente, com veículo e data como crédito.      */
/* ------------------------------------------------------------------ */
export type MancheteProps = Base & {
  veiculo: string; data?: string; titulo: string; linhaFina?: string;
  destaque?: string; destaqueEm?: number; imagem?: string;
};
export const Manchete: React.FC<MancheteProps> = ({ marca, veiculo, data, titulo, linhaFina, destaque, destaqueEm = 0.6, imagem }) => {
  const c = marca.cores;
  let corpo: React.ReactNode = titulo;
  if (destaque && titulo.includes(destaque)) {
    const [a, b] = titulo.split(destaque);
    corpo = <>{a}<MarcaTexto em={destaqueEm} cor={c.destaque}>{destaque}</MarcaTexto>{b}</>;
  }
  return (
    <Cena pushIn={0.07}>
      <Papel cor={c.papel} />
      <AbsoluteFill style={{ padding: "130px 260px", flexDirection: "column", gap: 28 }}>
        <div style={{ fontFamily: TEXTO, fontWeight: 800, fontSize: 26, letterSpacing: 3, color: c.alerta, textTransform: "uppercase" }}>
          {veiculo}{data ? <span style={{ color: "#777", fontWeight: 600 }}>{"  ·  " + data}</span> : null}
        </div>
        <div style={{ fontFamily: TEXTO, fontWeight: 800, fontSize: 68, lineHeight: 1.18, color: c.tinta }}>{corpo}</div>
        {linhaFina && <div style={{ fontFamily: TEXTO, fontSize: 32, color: "#555", lineHeight: 1.4 }}>{linhaFina}</div>}
        {imagem && (
          <Img src={src(imagem)} style={{ marginTop: 10, width: "100%", height: 360, objectFit: "cover", borderRadius: marca.raio }} />
        )}
      </AbsoluteFill>
    </Cena>
  );
};

/* ------------------------------------------------------------------ */
/* 3. Print: captura real de página com push-in e caixas de destaque    */
/*    (coordenadas em px da imagem, vindas do getBoundingClientRect).  */
/* ------------------------------------------------------------------ */
export type PrintProps = Base & {
  imagem: string; largura: number; altura: number;
  destaques?: { x: number; y: number; w: number; h: number; em: number }[];
  foco?: { x: number; y: number };
};
export const Print: React.FC<PrintProps> = ({ marca, imagem, largura, altura, destaques = [], foco }) => {
  const f = useCurrentFrame();
  const seg = useSeg();
  const { width: W, height: H, durationInFrames: d } = useVideoConfig();
  const base = Math.min((W * 0.86) / largura, (H * 0.9) / altura);
  const z = interpolate(f, [0, d], [1, 1.12], { easing: Easing.inOut(Easing.quad) });
  const fx = foco ? (largura / 2 - foco.x) * base * (z - 1) : 0;
  const fy = foco ? (altura / 2 - foco.y) * base * (z - 1) : 0;
  return (
    <Cena pushIn={0}>
      <Papel cor={marca.cores.papel} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div style={{
          position: "relative", width: largura * base, height: altura * base,
          transform: `translate(${fx}px, ${fy}px) scale(${z})`, boxShadow: "0 30px 80px rgba(0,0,0,0.25)", borderRadius: 8, overflow: "hidden",
        }}>
          <Img src={src(imagem)} style={{ width: "100%", height: "100%" }} />
          {destaques.map((r, i) => {
            const p = interpolate(f, [seg(r.em), seg(r.em + 0.5)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            return <div key={i} style={{
              position: "absolute", left: r.x * base, top: r.y * base, width: r.w * base * p, height: r.h * base,
              background: marca.cores.destaque, mixBlendMode: "multiply",
            }} />;
          })}
        </div>
      </AbsoluteFill>
    </Cena>
  );
};

/* ------------------------------------------------------------------ */
/* 4. Número: estados que se dissolvem um no outro (ex.: 150 mil ->      */
/*    1 milhão). Cada estado tem um tempo de entrada.                  */
/* ------------------------------------------------------------------ */
export type NumeroProps = Base & {
  estados: { valor: string; rotulo?: string; em: number; cor?: "destaque" | "alerta" | "primaria" | "tinta" }[];
  fundoImagem?: string; escuro?: boolean;
};
export const Numero: React.FC<NumeroProps> = ({ marca, estados, fundoImagem, escuro }) => {
  const f = useCurrentFrame();
  const seg = useSeg();
  const c = marca.cores;
  return (
    <Cena pushIn={0.05}>
      {escuro ? <AbsoluteFill style={{ background: c.escuro }} /> : <Papel cor={c.papel} />}
      {fundoImagem && <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: 0.85 }}>
        <Img src={src(fundoImagem)} style={{ height: "70%", objectFit: "contain" }} /></AbsoluteFill>}
      {estados.map((e, i) => {
        const ini = seg(e.em);
        const fim = i + 1 < estados.length ? seg(estados[i + 1].em) : Infinity;
        const a = interpolate(f, [ini, ini + 7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const s = fim === Infinity ? 0 : interpolate(f, [fim - 2, fim + 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const v = a * (1 - s);
        if (v <= 0) return null;
        return (
          <AbsoluteFill key={i} style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", opacity: v, filter: `blur(${(1 - v) * 16}px)`, transform: `scale(${0.94 + a * 0.06 + s * 0.08})` }}>
            <div style={{ fontFamily: TITULO, fontSize: 170, color: c[e.cor ?? "alerta"], letterSpacing: -2, textShadow: escuro ? "0 0 40px rgba(0,0,0,.5)" : undefined }}>{e.valor}</div>
            {e.rotulo && <div style={{ fontFamily: TEXTO, fontWeight: 800, fontSize: 40, letterSpacing: 4, textTransform: "uppercase", color: escuro ? c.claro : c.tinta, marginTop: 8 }}>{e.rotulo}</div>}
          </AbsoluteFill>
        );
      })}
    </Cena>
  );
};

/* ------------------------------------------------------------------ */
/* 5. Comparação: dois lados ligados por linha pontilhada que se desenha */
/* ------------------------------------------------------------------ */
export type ComparacaoProps = Base & {
  titulo?: string;
  linhas: { rotulo: string; valor: string; em: number; cor?: "destaque" | "alerta" | "primaria" }[];
};
export const Comparacao: React.FC<ComparacaoProps> = ({ marca, titulo, linhas }) => {
  const f = useCurrentFrame();
  const seg = useSeg();
  const c = marca.cores;
  return (
    <Cena pushIn={0.04}>
      <Papel cor={c.papel} />
      <AbsoluteFill style={{ padding: "150px 240px", flexDirection: "column", justifyContent: "center", gap: 56 }}>
        {titulo && <Surge em={0}><div style={{ fontFamily: TEXTO, fontWeight: 800, fontSize: 34, letterSpacing: 4, color: c.primaria, textTransform: "uppercase" }}>{titulo}</div></Surge>}
        {linhas.map((l, i) => {
          const p = interpolate(f, [seg(l.em), seg(l.em) + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 30, opacity: Math.min(1, p * 3) }}>
              <div style={{ fontFamily: TITULO, fontSize: 60, color: c.tinta, whiteSpace: "nowrap" }}>{l.rotulo}</div>
              <div style={{ flex: 1, height: 4, backgroundImage: `radial-gradient(circle, ${c.tinta} 2px, transparent 2.5px)`, backgroundSize: "16px 4px", clipPath: `inset(0 ${100 - p * 100}% 0 0)` }} />
              <div style={{ fontFamily: TITULO, fontSize: 72, color: c[l.cor ?? "primaria"], opacity: p >= 1 ? 1 : 0, whiteSpace: "nowrap" }}>{l.valor}</div>
            </div>
          );
        })}
      </AbsoluteFill>
    </Cena>
  );
};

/* ------------------------------------------------------------------ */
/* 6. Lista: itens numerados que aparecem no tempo da fala              */
/* ------------------------------------------------------------------ */
export type ListaProps = Base & { titulo?: string; itens: { texto: string; em: number }[]; atual?: number; escuro?: boolean };
export const Lista: React.FC<ListaProps> = ({ marca, titulo, itens, escuro = true }) => {
  const c = marca.cores;
  return (
    <Cena pushIn={0.04} fundo={escuro ? c.primaria : undefined}>
      {!escuro && <Papel cor={c.papel} />}
      <AbsoluteFill style={{ padding: "110px 200px", flexDirection: "column", justifyContent: "center", gap: 40 }}>
        {titulo && <Surge em={0}><div style={{ fontFamily: TITULO, fontSize: 104, lineHeight: 1.05, color: escuro ? c.claro : c.tinta, marginBottom: 30 }}>{titulo}</div></Surge>}
        {itens.map((it, i) => (
          <Surge key={i} em={it.em} de="baixo">
            <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
              <div style={{ fontFamily: TITULO, fontSize: 60, width: 112, height: 112, flexShrink: 0, borderRadius: marca.raio, background: c.destaque, color: c.tinta, display: "flex", alignItems: "center", justifyContent: "center" }}>{i + 1}</div>
              <div style={{ fontFamily: TEXTO, fontWeight: 800, fontSize: 70, lineHeight: 1.1, color: escuro ? c.claro : c.tinta }}>{it.texto}</div>
            </div>
          </Surge>
        ))}
      </AbsoluteFill>
    </Cena>
  );
};

/* ------------------------------------------------------------------ */
/* 7. Gráfico de linha ou barras com fonte dos dados obrigatória        */
/* ------------------------------------------------------------------ */
export type GraficoProps = Base & {
  titulo: string; tipo: "linha" | "barras"; pontos: { x: string; y: number }[];
  unidade?: string; fonte: string; destacarUltimo?: boolean;
};
export const Grafico: React.FC<GraficoProps> = ({ marca, titulo, tipo, pontos, unidade = "", fonte, destacarUltimo = true }) => {
  const f = useCurrentFrame();
  const c = marca.cores;
  const W = 1400, H = 560;
  const max = Math.max(...pontos.map((p) => p.y)) * 1.12;
  const min = tipo === "barras" ? 0 : Math.min(...pontos.map((p) => p.y)) * 0.9;
  const X = (i: number) => (pontos.length === 1 ? W / 2 : (i / (pontos.length - 1)) * W);
  const Y = (v: number) => H - ((v - min) / (max - min)) * H;
  const prog = interpolate(f, [8, 8 + Math.max(20, pontos.length * 5)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const fmt = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 2 }) + unidade;
  const d = pontos.map((p, i) => `${i ? "L" : "M"}${X(i)},${Y(p.y)}`).join(" ");
  const bw = (W / pontos.length) * 0.62;
  return (
    <Cena pushIn={0.03}>
      <Papel cor={c.papel} />
      <AbsoluteFill style={{ padding: "100px 260px", flexDirection: "column" }}>
        <div style={{ fontFamily: TITULO, fontSize: 60, color: c.tinta }}>{titulo}</div>
        <svg width={W} height={H + 80} style={{ marginTop: 50, overflow: "visible" }}>
          {tipo === "linha" ? (
            <>
              <path d={d} fill="none" stroke={c.primaria} strokeWidth={8} strokeLinejoin="round" strokeLinecap="round"
                pathLength={1} strokeDasharray={1} strokeDashoffset={1 - prog} />
              {pontos.map((p, i) => {
                const vis = prog >= i / Math.max(1, pontos.length - 1);
                const ult = destacarUltimo && i === pontos.length - 1;
                return vis ? <g key={i}>
                  <circle cx={X(i)} cy={Y(p.y)} r={ult ? 14 : 8} fill={ult ? c.alerta : c.primaria} />
                  <text x={X(i)} y={Y(p.y) - 26} textAnchor="middle" style={{ fontFamily: TEXTO }} fontWeight={800} fontSize={ult ? 40 : 28} fill={ult ? c.alerta : c.tinta}>{fmt(p.y)}</text>
                </g> : null;
              })}
            </>
          ) : pontos.map((p, i) => {
            const h = (H - Y(p.y)) * prog;
            const ult = destacarUltimo && i === pontos.length - 1;
            const cx = (i + 0.5) * (W / pontos.length);
            return <g key={i}>
              <rect x={cx - bw / 2} y={H - h} width={bw} height={h} rx={6} fill={ult ? c.alerta : c.primaria} />
              {prog > 0.95 && <text x={cx} y={H - h - 18} textAnchor="middle" style={{ fontFamily: TEXTO }} fontWeight={800} fontSize={30} fill={c.tinta}>{fmt(p.y)}</text>}
            </g>;
          })}
          {pontos.map((p, i) => (
            <text key={"x" + i} x={tipo === "barras" ? (i + 0.5) * (W / pontos.length) : X(i)} y={H + 50} textAnchor="middle" style={{ fontFamily: TEXTO }} fontWeight={600} fontSize={26} fill="#555">{p.x}</text>
          ))}
        </svg>
        <div style={{ fontFamily: TEXTO, fontSize: 22, color: "#666", marginTop: "auto" }}>Fonte: {fonte}</div>
      </AbsoluteFill>
    </Cena>
  );
};

/* ------------------------------------------------------------------ */
/* 8. Citação                                                           */
/* ------------------------------------------------------------------ */
export type CitacaoProps = Base & { texto: string; autor: string; fonte?: string; destaque?: string };
export const Citacao: React.FC<CitacaoProps> = ({ marca, texto, autor, fonte, destaque }) => {
  const c = marca.cores;
  let corpo: React.ReactNode = texto;
  if (destaque && texto.includes(destaque)) {
    const [a, b] = texto.split(destaque);
    corpo = <>{a}<span style={{ color: c.destaque }}>{destaque}</span>{b}</>;
  }
  return (
    <Cena pushIn={0.05} fundo={c.escuro}>
      <AbsoluteFill style={{ padding: "0 260px", justifyContent: "center", flexDirection: "column", gap: 40 }}>
        <div style={{ fontFamily: TITULO, fontSize: 200, color: c.destaque, lineHeight: 0.6, height: 80 }}>“</div>
        <div style={{ fontFamily: TEXTO, fontWeight: 800, fontSize: 64, lineHeight: 1.25, color: c.claro }}>{corpo}</div>
        <div style={{ fontFamily: TEXTO, fontWeight: 600, fontSize: 32, color: "#BBB" }}>— {autor}{fonte ? `, ${fonte}` : ""}</div>
      </AbsoluteFill>
    </Cena>
  );
};

/* ------------------------------------------------------------------ */
/* 9. Palavra-chave SOBRE a câmera (fundo transparente): termo em caixa */
/*    alta no terço inferior, pulando junto com a fala.                */
/* ------------------------------------------------------------------ */
export type PalavraChaveProps = Base & { texto: string; lado?: "esquerda" | "direita" | "centro" | "coluna"; cor?: "destaque" | "alerta" | "claro" | "primaria"; rotulo?: string;
  pos?: { x: number; y: number; w: number } };
export const PalavraChave: React.FC<PalavraChaveProps> = ({ marca, texto, lado = "esquerda", cor = "claro", rotulo, pos }) => {
  const f = useCurrentFrame();
  const { durationInFrames: d } = useVideoConfig();
  const a = interpolate(f, [0, 6], [0, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.back(2)) });
  const s = interpolate(f, [d - 5, d], [1, 0], { extrapolateLeft: "clamp" });
  if (lado === "coluna") {
    // Aula com tela compartilhada (cena "Principal + Tela"): faixa livre da coluna direita,
    // entre o título da aula e o logo do cenário — nunca por cima do documento.
    return (
      <AbsoluteFill>
        {/* faixa livre: y 590–800 (abaixo de "Aula 01", acima do logo do cenário em y 820).
            Texto sempre escuro: dourado sobre o bege do cenário não tem contraste (QC 11/10). */}
        {/* pos: área livre de outra cena do OBS (ex.: "Principal + Tablet"); padrão = coluna da "Principal + Tela" */}
        <div style={{ position: "absolute", left: pos?.x ?? 1408, top: pos?.y ?? 590, width: pos?.w ?? 470, opacity: a * s,
          transform: `translateY(${(1 - a) * 24}px)` }}>
          <div style={{ width: 64 * a, height: 6, background: marca.cores[cor === "alerta" ? "alerta" : "destaque"],
            borderRadius: 3, marginBottom: 16 }} />
          {rotulo && <div style={{ fontFamily: TEXTO, fontWeight: 800, fontSize: 22, letterSpacing: 3,
            textTransform: "uppercase", color: cor === "claro" ? marca.cores.claro : marca.cores.tinta, opacity: cor === "claro" ? 0.85 : 0.7, marginBottom: 8,
            textShadow: cor === "claro" ? "0 2px 12px rgba(0,0,0,0.8)" : "none" }}>{rotulo}</div>}
          {/* coluna estreita (cena do tablet, ~285 px): palavra longa em 56 px vazava da tela */}
          <div style={{ fontFamily: TITULO, lineHeight: 1.08, overflowWrap: "break-word",
            fontSize: (pos?.w ?? 470) < 400 ? (texto.length > 16 ? 34 : 40) : (texto.length > 22 ? 44 : 56),
            textTransform: "uppercase", color: marca.cores[cor === "alerta" ? "alerta" : cor === "claro" ? "claro" : "primaria"],
            // cor "claro": coluna sobre slide/foto escura (aula de solo, 13/10: verde-escuro sumia na foto)
            textShadow: cor === "claro" ? "0 2px 14px rgba(0,0,0,0.85)" : "none" }}>{texto}</div>
        </div>
      </AbsoluteFill>
    );
  }
  const just = lado === "centro" ? "center" : lado === "direita" ? "flex-end" : "flex-start";
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: just, padding: "0 140px 130px" }}>
      <div style={{
        fontFamily: TITULO, fontSize: 92, textTransform: "uppercase", color: marca.cores[cor], opacity: a * s,
        transform: `scale(${0.6 + a * 0.4})`, transformOrigin: "bottom left",
        WebkitTextStroke: "2px rgba(0,0,0,0.35)", textShadow: "0 6px 0 rgba(0,0,0,0.45), 0 12px 40px rgba(0,0,0,0.55)",
      }}>{texto}</div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/* 11. Encerramento: card claro com o logo oficial (PNG — nunca recriado */
/*     em texto), tagline e arroba. Fundo claro porque logos com letra   */
/*     escura somem sobre o verde da marca.                             */
/* ------------------------------------------------------------------ */
export type EncerramentoProps = Base & { tagline?: string; chamada?: string; logo?: string | null };
export const Encerramento: React.FC<EncerramentoProps> = ({ marca, tagline, chamada, logo }) => {
  const c = marca.cores;
  return (
    <Cena pushIn={0.03}>
      <Papel cor={c.claro === "#FFFFFF" ? c.papel : c.claro} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 26 }}>
        <Surge em={0.1}>{logo
          ? <Img src={src(logo)} style={{ height: 520, objectFit: "contain" }} />
          : <div style={{ fontFamily: TITULO, fontSize: 130, color: c.tinta, textTransform: "uppercase" }}>{marca.nome}</div>}</Surge>
        {tagline && <Surge em={0.6} de="baixo"><div style={{ fontFamily: TEXTO, fontWeight: 600, fontSize: 40, color: c.tinta }}>{tagline}</div></Surge>}
        {marca.arroba && <Surge em={0.9} de="baixo"><div style={{ fontFamily: TITULO, fontSize: 44, color: c.primaria }}>{marca.arroba}</div></Surge>}
        {chamada && <Surge em={1.3} de="baixo"><div style={{ fontFamily: TEXTO, fontWeight: 800, fontSize: 30, color: "#fff", background: c.primaria, padding: "14px 30px", borderRadius: marca.raio, textTransform: "uppercase", letterSpacing: 2 }}>{chamada}</div></Surge>}
      </AbsoluteFill>
    </Cena>
  );
};

/* ------------------------------------------------------------------ */
/* 10. Legenda de short (vertical, transparente): 3 palavras por vez,  */
/*     palavra falada em destaque.                                      */
/* ------------------------------------------------------------------ */
// fundoClaro: short empilhado (câmera + tela sobre o papel da marca) — título branco sumia no claro (QC 11/10).
// baixo: distância da legenda à base (px); no empilhado ela fica entre a câmera e a tela.
export type LegendaProps = Base & { palavras: { t: string; ini: number; fim: number }[]; titulo?: string; fundoClaro?: boolean; baixo?: number };
export const Legenda: React.FC<LegendaProps> = ({ marca, palavras, titulo, fundoClaro = false, baixo = 560 }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const grupos: { t: string; ini: number; fim: number }[][] = [];
  palavras.forEach((p, i) => {
    const g = grupos[grupos.length - 1];
    const pausa = i > 0 && p.ini - palavras[i - 1].fim > 0.45;
    if (!g || g.length >= 3 || pausa) grupos.push([p]); else g.push(p);
  });
  const atual = grupos.find((g) => t >= g[0].ini && t <= g[g.length - 1].fim + 0.15);
  return (
    <AbsoluteFill>
      {titulo && <div style={{ position: "absolute", top: fundoClaro ? 150 : 230, width: "100%", textAlign: "center", fontFamily: TITULO, fontSize: fundoClaro ? 72 : 78, color: fundoClaro ? marca.cores.primaria : marca.cores.claro, textTransform: "uppercase", lineHeight: 1.05, padding: "0 70px", textShadow: fundoClaro ? "none" : "0 5px 0 rgba(0,0,0,.6)" }}>{titulo}</div>}
      {atual && (
        <div style={{ position: "absolute", bottom: baixo, width: "100%", padding: "0 60px", display: "flex", flexWrap: "wrap", justifyContent: "center", rowGap: 6 }}>
          {atual.map((p, i) => (
            <span key={i} style={{
              fontFamily: TITULO, fontSize: 82, margin: "0 10px", textTransform: "uppercase",
              color: t >= p.ini && t <= p.fim + 0.05 ? marca.cores.destaque : marca.cores.claro,
              WebkitTextStroke: "10px black", paintOrder: "stroke fill",
            }}>{p.t}</span>
          ))}
        </div>
      )}
    </AbsoluteFill>
  );
};
