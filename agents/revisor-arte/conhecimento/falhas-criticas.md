# Falhas Críticas

Falha crítica é o que **impede a entrega de ser publicada como está** — não é
"problema grave". A régua é: publicar assim causaria erro de comunicação, prejuízo
à marca ou retrabalho inevitável.

Efeito no status, por tipo de entrega:

- **`criativo`** — ver `criterios/criativos.md` §3.1: confirmada → **no máximo 3
  estrelas** (nunca aprovada), com gravidade e quantidade decidindo entre 3, 2 e 1;
  suspeita não confirmada → no máximo 4 estrelas, com a suspeita declarada.
- **Demais tipos** — ver `regras-gerais.md` §1.3: confirmada → **REPROVADO**; suspeita
  com confiança baixa → no máximo **AJUSTES NECESSÁRIOS**, com o que falta para confirmar.

A detecção das falhas é idêntica em todos os tipos. Só o efeito no status muda.

---

## 1. Falhas críticas comuns *(todo tipo de entrega)*

| # | Falha | Como confirmar | Cuidado |
|---|---|---|---|
| C1 | **Erro ortográfico ou gramatical** em texto visível | Ler o texto | Nome próprio, marca, estrangeirismo e jargão **não** são erro. Confirmar antes de acusar |
| C2 | **Informação incorreta** (preço, data, telefone, endereço, URL, condição) | Cruzar com o briefing | Sem briefing que comprove, é dúvida, não erro |
| C3 | **Ausência de informação obrigatória** listada no briefing | Cruzar com o briefing | Só vale o que está **escrito** no briefing |
| C4 | **CTA ausente** quando o briefing o exige | Cruzar com o briefing | Briefing não pede CTA → ausência não é falha |
| C5 | **Texto ilegível** por tamanho, contraste ou sobreposição | Leitura visual | Distinguir "difícil" de "impossível". Difícil é problema de qualidade |
| C6 | **Aplicação incorreta da marca** (logo distorcido, cor errada, versão proibida) | Comparar com material de referência | Sem manual ou referência disponível, não afirmar — declarar limitação |
| C7 | **Descumprimento relevante do briefing** que altera o sentido da entrega | Cruzar com o briefing | "Relevante" = muda a mensagem, o público ou o objetivo |
| C8 | **Entrega incompleta** — falta peça, formato ou variação pedida | Inventário × briefing | Confirmar que não está em outro arquivo antes de apontar |
| C9 | **Arquivo corrompido, ilegível ou vazio** | Abrir / inspecionar | Distinguir de formato não suportado pelo revisor |
| C10 | **Conteúdo trocado** — material de outro cliente, campanha ou versão antiga | Cruzar com o briefing | Alta gravidade; confirmar com cuidado antes de afirmar |

---

## 2. Falhas críticas específicas — Criativos

| # | Falha | Observação |
|---|---|---|
| A1 | Formato/dimensão fora da especificação escrita no briefing | Verificável objetivamente pelas dimensões do arquivo |
| A2 | Elemento essencial cortado (logo, rosto, texto, produto) pela margem ou pelo crop | |
| A3 | Área de segurança violada em formato de story/reels (texto sob a barra de UI) | Só quando o briefing especifica o canal |
| A4 | Resolução insuficiente para o uso declarado (pixelização visível) | Declarar confiança; ampliação e compressão se confundem |
| A5 | Texto sobreposto a outro texto ou a elemento que o torna irrecuperável | |

---

## 3. Falhas críticas específicas — Landing Pages

| # | Falha | Observação |
|---|---|---|
| L1 | CTA sem destino, com destino vazio (`href="#"`, `href=""`) ou apontando para lugar errado | Verificável no código-fonte |
| L2 | Formulário sem `action`, sem campo obrigatório pedido, ou sem envio configurado | Verificável no código-fonte |
| L3 | Proposta de valor ausente na primeira dobra | Verificável em screenshot ou código |
| L4 | Texto placeholder em produção (`lorem ipsum`, `TODO`, `xxx`, `Lorem`) | Busca textual direta |
| L5 | Imagem quebrada — `src` vazio, arquivo ausente na pasta | Verificável no código + inventário |
| L6 | Quebra grave de layout visível em screenshot (sobreposição, corte, estouro) | Só com screenshot; sem ele, declarar não verificável |
| L7 | Ausência de rastreamento/pixel/tag explicitamente exigido no briefing | Busca no código |

**Não é falha crítica nesta fase:** problema de responsividade sem screenshot mobile,
comportamento de hover, animação, velocidade de carregamento. Sem navegador,
**nada disso é verificável** — vai para "Limitações da análise", não para falhas.

---

## 4. Falhas críticas específicas — Vídeos

| # | Falha | Como confirmar |
|---|---|---|
| V1 | Duração fora do especificado no briefing | `ffprobe` — **objetivo** |
| V2 | Resolução ou aspect ratio fora do especificado | `ffprobe` — **objetivo** |
| V3 | Ausência total de faixa de áudio quando o briefing pressupõe áudio | `ffprobe` — **objetivo** |
| V4 | Áudio mudo ou em nível inutilizável (silêncio digital ou pico próximo de 0 dBFS com clipping) | `ffmpeg` — **objetivo** |
| V5 | Frames pretos ou congelados em meio ao vídeo | `blackdetect` — **objetivo** |
| V6 | Erro ortográfico em legenda ou texto em tela | Leitura de frames / arquivo `.srt` |
| V7 | Corte abrupto no fim, cortando fala ou logo | Frames finais + duração |
| V8 | Arquivo que não decodifica ou stream inválido | `ffprobe` retorna erro |
| V9 | CTA final ausente quando o briefing o exige | Frames finais |

**Nunca é falha crítica nesta fase** — porque não é verificável:
qualidade de locução, qualidade artística de trilha, equilíbrio voz/música,
ruído percebido, qualidade de mixagem, ritmo percebido, sincronia labial fina.
Ver `criterios/videos.md` §3.

---

## 5. Como reportar uma falha crítica

Cada falha crítica registra obrigatoriamente:

1. **Código e nome** (ex.: `C1 — Erro ortográfico`)
2. **Localização exata** — arquivo, e onde dentro dele (região da peça, linha do código,
   timecode do vídeo)
3. **Evidência** — o que foi lido, medido ou observado; qual ferramenta produziu o dado
4. **Grau de confiança** — Alta / Média / Baixa
5. **Correção necessária** — o que precisa ser feito para destravar
6. **Base** — o trecho do briefing que sustenta a falha, quando a falha depende do briefing

Falha crítica **sem** localização e evidência não deve ser reportada como falha crítica.
Ela vira observação com incerteza declarada.
