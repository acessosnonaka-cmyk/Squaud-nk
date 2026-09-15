# Régua — Vídeos

**Tipo:** `video`
**Usa nota:** sim
**Escala e faixas de status:** definidas em `regras-gerais.md` §1 — **não redefinir aqui**

Aplica-se a vídeos e edições: reels, stories, VTs, anúncios, institucionais, cortes.

> **Separação obrigatória desta régua:** o revisor **não assiste** ao vídeo e **não
> escuta** o áudio. Ele mede o arquivo com `ffprobe`/`ffmpeg` e lê **frames extraídos
> por amostragem**. §2 é medição. §3 é o que **não existe** aqui.

---

## 1. Pesos

| # | Critério | Peso | Condicional |
|---|---|---|---|
| 1 | Aderência ao briefing | 18 | sim¹ |
| 2 | Conformidade técnica verificável | 16 | não |
| 3 | Estrutura narrativa | 12 | não |
| 4 | Legendas e textos em tela | 12 | sim² |
| 5 | Identidade visual | 10 | sim³ |
| 6 | Enquadramento e composição | 10 | não |
| 7 | CTA | 8 | sim⁴ |
| 8 | Edição e cortes | 7 | sim⁵ |
| 9 | Acabamento técnico | 7 | não |
| | **Total** | **100** | |

¹ Excluído se não houver briefing (`regras-gerais.md` §4.2).
² Excluído se o vídeo não tiver legenda nem texto em tela e o briefing não os exigir.
³ Excluído se não houver material de referência da marca.
⁴ Excluído se o briefing não pedir CTA.
⁵ Excluído quando a amostragem de frames não sustentar conclusão (ver §2.8).

Exclusão sempre acompanhada de renormalização (`regras-gerais.md` §4.1) e registro
em "Limitações da análise".

---

## 2. MÉTRICAS TÉCNICAS VERIFICÁVEIS

Obtidas por `ferramentas/inspecionar-video.sh`. São **fatos medidos** — Classe 1,
confiança **Alta**. Rodar o script **antes** de qualquer afirmação técnica.

| Métrica | Fonte | Confiança |
|---|---|---|
| Duração | `ffprobe` | Alta |
| Resolução (largura × altura) | `ffprobe` | Alta |
| Aspect ratio | `ffprobe` | Alta |
| FPS | `ffprobe` | Alta |
| Codec de vídeo e de áudio | `ffprobe` | Alta |
| Bitrate (total, vídeo, áudio) | `ffprobe` | Alta |
| Presença de faixa de áudio | `ffprobe` | Alta |
| Sample rate e nº de canais | `ffprobe` | Alta |
| Pico (true peak) e loudness integrado (LUFS) | `ffmpeg ebur128` | Alta |
| Frames pretos (timecode e duração) | `ffmpeg blackdetect` | Alta |
| Contagem estimada de cortes | `ffmpeg` scene detection | **Média** |
| Tamanho e integridade do arquivo | `ffprobe` / sistema | Alta |

### 2.1 Aderência ao briefing — 18
Roteiro seguido. Mensagem principal presente. Textos e elementos obrigatórios.
Canal/formato conforme pedido. Restrições respeitadas.

### 2.2 Conformidade técnica verificável — 16
Cruzar as métricas medidas contra o que o briefing especifica: duração, resolução,
aspect ratio, FPS, formato. **Puramente objetivo.**
Divergência do especificado é falha crítica V1/V2, não apenas nota baixa.
*Sem especificação no briefing: avaliar apenas coerência técnica interna (arquivo
íntegro, faixa de áudio presente, sem erro de decodificação).*

### 2.3 Estrutura narrativa — 12
Pelos frames + roteiro/briefing: há abertura, desenvolvimento e fecho? Os beats pedidos
aparecem? O vídeo começa com gancho, quando o briefing pede? Termina resolvido, ou o
corte final trunca algo (falha crítica V7)?
*Confiança Média — leitura por amostragem.*

### 2.4 Legendas e textos em tela — 12
**Ortografia e gramática** (Classe 1, confiança Alta quando há `.srt`/`.vtt`; Média
quando lido de frame). Fidelidade ao texto do briefing. Legibilidade: corpo, contraste,
posição, área de segurança do canal. Presença quando o briefing exige legenda.
*Se houver `.srt`/`.vtt`: ler o arquivo — é a evidência mais confiável do vídeo inteiro.*

### 2.5 Identidade visual — 10
Logo presente na versão e proporção corretas. Paleta e tipografia da marca. Assinatura
final. Aplicação correta em cada frame amostrado.
*Sem referência da marca, não afirmar erro — excluir o critério.*

### 2.6 Enquadramento e composição — 10
Nos frames: enquadramento adequado, elementos essenciais não cortados, área de segurança
do canal respeitada, composição estável.
*Confiança Média — amostragem.*

### 2.7 CTA — 8
Presente quando exigido. Legível. Tempo em tela suficiente (verificável: quantos frames
consecutivos o contêm). Coerente com o CTA do briefing.
*Ausência quando obrigatório é falha crítica V9.*

### 2.8 Edição e cortes *(condicional)* — 7
Apenas o que a evidência sustenta: número estimado de cortes (scene detection), cortes
em frame preto, duplicação de cena, salto visível entre frames adjacentes amostrados.
**Se a amostragem não sustentar conclusão, excluir o critério** — não improvisar.
*Confiança Média, nunca Alta.*

### 2.9 Acabamento técnico — 7
Frames pretos ou congelados no meio (falha crítica V5). Artefatos de compressão visíveis
nos frames. Bitrate incompatível com a resolução. Arquivo íntegro e decodificável.
Nível de áudio dentro de faixa utilizável — **existência e nível, não qualidade**.

---

## 3. AVALIAÇÃO PERCEPTIVA NÃO VERIFICÁVEL NESTA FASE

**Peso zero. Nunca pontuado. Nunca reportado como problema ou falha crítica.**
Vai integralmente para "Limitações da análise".

- qualidade da locução (dicção, interpretação, respiração, entonação);
- qualidade artística da música/trilha;
- equilíbrio subjetivo entre voz e trilha;
- ruído percebido, chiado, eco, ambiência;
- qualidade artística da mixagem e da masterização;
- **ritmo real do vídeo**, quando depender de assistir continuamente;
- **sincronização perceptiva** (labial, legenda×fala, corte×batida) sem evidência
  suficiente;
- transições e efeitos em movimento;
- color grading percebido em movimento;
- impacto emocional e "força" do vídeo.

### 3.1 Regra inviolável

> **Nunca afirmar que o áudio ou o ritmo estão bons com base em métricas técnicas.**

- "Faixa de áudio presente, −16 LUFS, pico −1,2 dBTP" ✅ é fato medido.
- "O áudio está bom" / "a mixagem está equilibrada" / "o ritmo está adequado" ❌ é
  conclusão que estas ferramentas **não** sustentam — proibido em qualquer status.

O mesmo vale no sentido negativo: não afirmar que o áudio está ruim porque um número
saiu fora de uma faixa de referência. O que se reporta é a **medida** e o **desvio da
especificação**, quando o briefing especifica.

### 3.2 Como reportar

No relatório, bloco "Limitações da análise":

```
Áudio: verificada apenas a existência e o nível (presença de faixa, sample rate,
canais, loudness integrado, true peak). Locução, trilha, mixagem, ruído e equilíbrio
voz/música NÃO foram avaliados — exigem audição.

Ritmo e sincronização: não avaliados. A análise visual é feita por amostragem de N
frames, não por reprodução contínua. Um problema entre dois frames amostrados não
seria detectado.
```

---

## 4. Notas de calibração

- Vídeo tecnicamente conforme, sem erro de texto e com estrutura coerente **deve** ficar
  na faixa de aprovação, mesmo com áudio e ritmo não avaliados.
- Confiança global de vídeo dificilmente é Alta: as métricas são Alta, a leitura visual
  é Média. Reportar **Média** salvo quando a decisão se apoiar só em métricas objetivas.
- Amostragem padrão do script: 12 frames + 3 do fecho. Registrar o número usado no
  relatório — é o que define o alcance da revisão visual.
