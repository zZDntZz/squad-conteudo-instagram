# Captação — o que quem grava faz no dia

O pós-produção melhora muito, mas não inventa luz nem resolução. Estes itens valem mais que qualquer filtro.

## OBS
- Grave MP4 (ou MKV remuxado) 1920×1080 30 fps; NVENC se tiver placa NVIDIA.
- **Melhor**: tela base 2560×1440 (ou 4K se a câmera entregar) — o punch-in de 18–25% não perde nitidez.
- Um arquivo por vídeo. Pausar a gravação é ok; o editor junta.

## Fala
- Errou? **Diga "corta"**, respire 1 s e repita a frase inteira. O editor apaga a tentativa errada.
- Pode também só repetir a frase do começo, depois de uma pausa: fica a última tentativa.
- Pausas entre ideias são bem-vindas (o editor corta). Não precisa decorar nem acelerar.
- Nomes próprios difíceis: passe no `--glossario` ao criar o projeto ("Selic, Coinext, Haddad").

## Luz (o "look" de cinema caseiro)
- **Luz principal** a ~45° de um lado, um pouco acima dos olhos, difusa (softbox ou janela com cortina).
- **Fundo mais escuro que o rosto**: apague a luz do teto. Uma ou duas luminárias quentes no fundo (abajur,
  fita LED âmbar) dão profundidade.
- Nada de luz dura de frente nem janela atrás de você.
- Balanço de branco fixo na câmera (não automático), senão a cor oscila entre cortes.

## Enquadramento
- Olhos no terço superior, um palmo de ar acima da cabeça, centro do quadro.
- Distância de ~1,5 m do fundo (desfoque natural). Se a câmera permitir, abertura grande (f/1.8–2.8).

## Áudio
- Microfone a um palmo da boca, ligeiramente de lado. Ambiente com pano (cortina, cama, tapete).
- Ar-condicionado, ventilador e geladeira desligados.
- Pico da fala entre −12 e −6 dB no mixer do OBS.

## Cenário virtual
- Caminho robusto: plugin de remoção de fundo no próprio OBS (você vê o resultado ao vivo) ou tela verde.
- Troca de fundo na pós-produção **ainda não existe** (fase 2: recorte por IA local). Hoje o motor só
  aceita, em `projeto.json → "cenario"`, um vídeo já recortado com a mesma duração da gravação.
  Quando existir: cabelo e mão rápida denunciam o recorte, então o fundo vai desfocado.
