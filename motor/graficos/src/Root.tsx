import React from "react";
import { AbsoluteFill, CalculateMetadataFunction, Composition } from "remotion";
import { FONTES, MARCA_PADRAO, Base } from "./comum";
import {
  Citacao, Comparacao, Encerramento, Grafico, Lista, Manchete, Numero, PalavraChave, Print, TextoCinetico, Legenda,
} from "./templates";

// Duração vem da prop `duracao` (s); formato vem de `vertical`.
const meta: CalculateMetadataFunction<Base & { vertical?: boolean }> = ({ props }) => ({
  durationInFrames: Math.max(1, Math.round((props.duracao ?? 4) * 30)),
  width: props.vertical ? 1080 : 1920,
  height: props.vertical ? 1920 : 1080,
});

/** Aplica as fontes da marca (variáveis CSS lidas pelos templates). */
const comMarca = (Comp: React.FC<any>): React.FC<any> => (props) => {
  const m = props.marca ?? MARCA_PADRAO;
  const titulo = FONTES[m.fonte_titulo ?? "Archivo Black"] ?? FONTES["Archivo Black"];
  const texto = FONTES[m.fonte_texto ?? "Inter"] ?? FONTES["Inter"];
  return (
    <AbsoluteFill style={{ ["--fonte-titulo" as any]: titulo, ["--fonte-texto" as any]: texto }}>
      <Comp {...props} />
    </AbsoluteFill>
  );
};

const b = { marca: MARCA_PADRAO, duracao: 5 };

const C = <P,>(id: string, comp: React.FC<P>, padrao: P) => (
  <Composition id={id} component={comMarca(comp as React.FC<any>)} fps={30} width={1920} height={1080}
    durationInFrames={150} defaultProps={padrao as any} calculateMetadata={meta as any} />
);

export const Root: React.FC = () => (
  <>
    {C("TextoCinetico", TextoCinetico, { ...b, palavras: [{ t: "ninguém", em: 0.3 }, { t: "te", em: 0.6 }, { t: "conta", em: 0.8 }, { t: "isso", em: 1.1 }], destaque: ["isso"] })}
    {C("Manchete", Manchete, { ...b, veiculo: "Veículo", data: "10/10/2026", titulo: "Título com o trecho que importa no meio", destaque: "trecho que importa" })}
    {C("Print", Print, { ...b, imagem: "print.png", largura: 1280, altura: 800, destaques: [] })}
    {C("Numero", Numero, { ...b, estados: [{ valor: "150 mil", rotulo: "euros na Europa", em: 0.2 }, { valor: "1 milhão", rotulo: "reais no Brasil", em: 2.4, cor: "primaria" }] })}
    {C("Comparacao", Comparacao, { ...b, titulo: "Capital mínimo exigido", linhas: [{ rotulo: "Europa", valor: "1 mi", em: 0.4 }, { rotulo: "Brasil", valor: "37 mi", em: 1.6, cor: "alerta" }] })}
    {C("Lista", Lista, { ...b, titulo: "3 exigências", itens: [{ texto: "Capital mínimo", em: 0.5 }, { texto: "Governança", em: 1.3 }, { texto: "Segregação", em: 2.1 }] })}
    {C("Grafico", Grafico, { ...b, titulo: "Série", tipo: "linha", pontos: [{ x: "2022", y: 10 }, { x: "2023", y: 13 }, { x: "2024", y: 12 }, { x: "2025", y: 15 }], fonte: "fonte" })}
    {C("Citacao", Citacao, { ...b, texto: "Uma frase curta com destaque.", autor: "Autor", destaque: "destaque" })}
    {C("PalavraChave", PalavraChave, { ...b, duracao: 2, texto: "Taxa", cor: "destaque" })}
    {C("Encerramento", Encerramento, { ...b, tagline: "Tagline da marca", chamada: "Inscreva-se" })}
    {C("Legenda", Legenda, { ...b, vertical: true, palavras: [{ t: "legenda", ini: 0.1, fim: 0.5 }, { t: "de", ini: 0.5, fim: 0.6 }, { t: "short", ini: 0.6, fim: 1.1 }] } as any)}
  </>
);
