import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { loadFont as fonteTitulo } from "@remotion/google-fonts/ArchivoBlack";
import { loadFont as fonteTexto } from "@remotion/google-fonts/Inter";
import { loadFont as fonteOswald } from "@remotion/google-fonts/Oswald";
import { loadFont as fonteGrotesk } from "@remotion/google-fonts/SpaceGrotesk";

const sub = { subsets: ["latin", "latin-ext"] as any };
/** Famílias disponíveis; a marca escolhe pelo nome (marca.json -> fonte_titulo / fonte_texto). */
export const FONTES: Record<string, string> = {
  "Archivo Black": fonteTitulo("normal", sub).fontFamily,
  "Inter": fonteTexto("normal", { weights: ["400", "600", "800"], ...sub }).fontFamily,
  "Oswald": fonteOswald("normal", { weights: ["700"], ...sub }).fontFamily,
  "Space Grotesk": fonteGrotesk("normal", { weights: ["500", "700"], ...sub }).fontFamily,
};
// Templates usam variáveis CSS; a raiz da composição (Root.tsx) define os valores pela marca.
export const TITULO = "var(--fonte-titulo)";
export const TEXTO = "var(--fonte-texto)";

export type Marca = {
  cores: Record<"primaria" | "destaque" | "alerta" | "papel" | "tinta" | "escuro" | "claro", string>;
  raio: number;
  arroba?: string;
  nome?: string;
  fonte_titulo?: string;
  fonte_texto?: string;
  caixa_alta_titulo?: boolean;
};

export const MARCA_PADRAO: Marca = {
  cores: {
    primaria: "#1F6F4A", destaque: "#F2B33D", alerta: "#E04A3A",
    papel: "#F3F0E8", tinta: "#15171A", escuro: "#0E1512", claro: "#FFFFFF",
  },
  raio: 14,
};

export type Base = { marca: Marca; duracao: number };

/** segundos -> frames */
export const useSeg = () => {
  const { fps } = useVideoConfig();
  return (s: number) => Math.round(s * fps);
};

const suave = Easing.bezier(0.22, 1, 0.36, 1);

/**
 * Entrada e saída por desfoque + escala, e push-in lento durante a cena.
 * É a transição-assinatura do formato: um estado se dissolve no próximo.
 */
export const Cena: React.FC<{ children: React.ReactNode; pushIn?: number; fundo?: string }> = ({
  children, pushIn = 0.05, fundo,
}) => {
  const f = useCurrentFrame();
  const { durationInFrames: d } = useVideoConfig();
  const entra = interpolate(f, [0, 9], [0, 1], { extrapolateRight: "clamp", easing: suave });
  const sai = interpolate(f, [d - 7, d], [0, 1], { extrapolateLeft: "clamp" });
  const blur = (1 - entra) * 18 + sai * 14;
  const escala = 1.035 - entra * 0.035 + interpolate(f, [0, d], [0, pushIn]) + sai * 0.03;
  return (
    <AbsoluteFill style={{ background: fundo }}>
      <AbsoluteFill style={{ transform: `scale(${escala})`, filter: `blur(${blur}px)` }}>
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Fundo de papel com grão e vinheta — textura editorial, não fundo chapado. */
export const Papel: React.FC<{ cor: string }> = ({ cor }) => (
  <AbsoluteFill style={{ background: cor }}>
    <svg width="100%" height="100%" style={{ position: "absolute", opacity: 0.16, mixBlendMode: "multiply" }}>
      <filter id="grao">
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grao)" />
    </svg>
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.18) 100%)" }} />
  </AbsoluteFill>
);

/** Marca-texto que varre da esquerda para a direita a partir de `em` (s). */
export const MarcaTexto: React.FC<{ children: React.ReactNode; em: number; cor: string; dur?: number }> = ({
  children, em, cor, dur = 0.5,
}) => {
  const f = useCurrentFrame();
  const seg = useSeg();
  const p = interpolate(f, [seg(em), seg(em + dur)], [0, 100], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: suave,
  });
  return (
    <span style={{
      backgroundImage: `linear-gradient(${cor}, ${cor})`, backgroundRepeat: "no-repeat",
      backgroundSize: `${p}% 100%`, padding: "0 6px", boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone",
    }}>{children}</span>
  );
};

/** Elemento que surge com pulo (escala + desfoque) no instante `em` (s). */
export const Surge: React.FC<{ em: number; children: React.ReactNode; style?: React.CSSProperties; de?: "baixo" | "escala" }> = ({
  em, children, style, de = "escala",
}) => {
  const f = useCurrentFrame();
  const seg = useSeg();
  const p = interpolate(f, [seg(em), seg(em) + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: suave });
  const t = de === "baixo" ? `translateY(${(1 - p) * 40}px)` : `scale(${0.85 + p * 0.15})`;
  return <div style={{ ...style, opacity: p, transform: t, filter: `blur(${(1 - p) * 10}px)` }}>{children}</div>;
};
