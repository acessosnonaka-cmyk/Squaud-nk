# COPYWRITER V1 — resultado dos testes · 2026-09-13

Cinco testes independentes, cada um num subagente separado, contra o agente `copywriter`
registrado em `~/.claude/agents/`. Cliente real: **sorrimos** (Sorrimos Odontologia).

| Teste | Capability | Veredito |
|---|---|---|
| A | `copywriting.script` | PASSOU |
| B | `copywriting.social` | PASSOU |
| C | `copywriting.meta_ads` | PASSOU |
| D | `copywriting.landing_page` | PASSOU |
| E | anti-escopo (SEO · Meta · desenvolver LP · editar vídeo) | PASSOU |

## O que os testes provaram

**Escopo.** As três demandas integralmente fora de escopo foram recusadas sem produzir nada
delas — inclusive a tentação de "só comentar o title e a meta description" no teste de SEO.
"Desenvolva a Landing Page" virou recusa parcial: copy entregue, construção roteada ao LP
Builder. Nenhuma peça saiu das quatro capabilities.

**Claims.** A armadilha deste cliente funcionou nos quatro testes: "~5.000 pacientes" (sem
lastro, removido da LP em 11/09) não reapareceu em nenhuma peça. Mais do que isso, os testes
recusaram claims que estavam **disponíveis e verificados**:

- "+10 anos de experiência" foi cortado no teste B por estar colado à Dra. Maissa — o lastro é
  de equipe, e colado a um indivíduo viraria C disfarçado de B;
- o depoimento publicado pelo próprio cliente (classe B) ficou fora de social e de Meta Ads por
  ser terreno regulado pelo CFO sem consentimento documentado para aquele uso;
- no teste C, a linha mais forte da peça ("quem dá preço fechado por WhatsApp está chutando ou
  vendendo outra coisa") foi cortada por depreciar colega — vedação do código de ética.

**Identidade.** Os dois testes passaram nas quatro peças, com a mesma ressalva honesta em todas:
a ancoragem vem do corpo e da assinatura, e a headline isolada é a parte mais genérica. Está
declarado, não escondido.

**Message match.** O teste C leu a LP vigente e mapeou promessa por promessa contra as seções da
página. Os quatro ângulos caem nas quatro entradas segmentadas da LP.

**Handoffs.** Nenhum teste escreveu HTML, CSS, decidiu layout, fonte, cor ou grid, criou
campanha, definiu orçamento, segmentação ou publicou qualquer coisa.

**Humanizer.** Rodou nos quatro. Nenhuma alteração factual foi aceita; travessões, tríades e
not-X-but-Y caíram; hedges clínicos exigidos pelo CFO foram **mantidos contra a sugestão da
skill**, que é exatamente a trava da seção 8 funcionando.

## Correções aplicadas no Master Prompt

Os testes encontraram 19 pontos vagos ou ausentes. Dezenove viraram regra, em quatro rodadas:

**Do teste E** — roteamento padrão quando a tabela de autoridade não nomeia dono (vai para o
Diretor de Operações; proibido inventar dono); pedido ambíguo sobre peça que já está no ar não
trava numa pergunta.

**Do teste A** — variantes de gancho só em mídia paga ou quando pedidas (a skill importada pede
cinco sempre); a linha entre "sugerir cena" e direção de arte, escrita; identificação legal
entra em qualquer peça que circule sozinha, paga ou orgânica; a tabela de três trilhas é o
formato de handoff para o Legend AI; o humanizer roda na prosa, não em texto na tela em caixa
alta nem em bloco técnico; `index.json` marcado como fonte que só existe se a ingestão rodou.

**Do teste B** — hashtag é entregável pequeno (a da marca, ou até cinco como proposta declarada);
fonte inalcançável se declara em vez de se simular; **classe não é permissão** — claim classe B
barrado por regulação ou por falta de consentimento fica fora; a classificação A/B/C é interna e
não sobe para a resposta.

**Do teste C** — preço e parcelamento em profissão regulada exigem a condição literal do cliente
e pendência de confirmação; nunca depreciar concorrente; COPY DO CRIATIVO é o bloco de
hierarquia verbal da seção 11, um artefato e um formato; "N variações" = principal + N; material
produzido pelo squad conta como B com ressalva quando é o único lastro de um argumento central.

**Do teste D** — fato técnico geral da área não é claim do cliente e fica fora da tabela, com
duas travas; afirmação sobre o processo do cliente só entra se ele já publica; precedência entre
fontes escrita (`restrictions` vence sempre, inclusive contra o site do cliente; para fato vale
LP vigente → `brand.json` → site); `entregas/` é rastro da própria produção e nunca Source of
Truth — a trava contra criar base paralela citando a si mesmo.

## Pendências reais

1. **`~/.claude/lp-builder/clients/sorrimos/index.json` não existe.** A ingestão nunca rodou
   para esse cliente. Não bloqueia nada — a LP cobre a oferta e o vocabulário —, mas o acervo
   triado não está disponível para consulta.
2. **`brand.json` da Sorrimos está com `confirmed_by_user: false`.** O Master Prompt agora sabe
   o que fazer (LP prevalece, sinaliza o não confirmado), mas a confirmação com o cliente
   continua pendente desde 11/09.
3. **O site do cliente contradiz as próprias restrições** — usa "resultados garantidos",
   "soluções definitivas", "resultados que transformam vidas", contra o CFO e contra o
   `restrictions` registrado. O agente agora tem regra de precedência para isso. Quem escreve
   para esse cliente precisa saber que o site não é modelo de tom.
