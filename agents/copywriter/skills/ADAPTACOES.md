# Adaptações — como as skills importadas se submetem ao Master Prompt

Leia este arquivo antes de seguir instrução de qualquer skill desta pasta. As três skills
importadas de repositórios públicos pressupõem um ecossistema que não é o nosso. Abaixo, a
tradução de cada pressuposto. **Onde houver divergência, o Master Prompt vence.**

## Regra geral

As skills contribuem com **método de escrita**. Elas não ampliam escopo, não adicionam
capability e não mandam em fluxo. Capability que uma skill sugere e não está em
`capabilities.json` é ignorada, sem comentário ao usuário.

## `copywriting` (entpnomad)

| A skill diz | Aqui |
|---|---|
| "Pairs with / hand off to `tone-of-voice`" | **não instalada.** Identidade verbal vem da seção 4 do Master Prompt (Brand Voice) + `brand.json` (`tone.voice`, `tone.prefer`, `tone.avoid`); o polimento final é a skill global `humanizer` |
| Cobre LinkedIn post, newsletter, sales page, tagline, positioning line | só entra nas quatro capabilities. Newsletter e LinkedIn thought-leadership não são nossos |
| "Short-form post structure" com bold unicode e arrow bullets | padrão de LinkedIn. Em social BR, use só se a marca já escreve assim |

O que aproveitamos: o teste de três perguntas (visualizável / falsificável / não assinável pelo
concorrente), o teste de 2 segundos, concreto sobre abstrato, fato em vez de adjetivo,
posicionamento (o que você substitui / o que só você faz), conflito como motor, reescrever até
simplificar, cortar palavra que não trabalha.

## `caption-writer` (social-media-skills)

| A skill diz | Aqui |
|---|---|
| "Step 0 — load `brand-profile.md` and `voice.md` (required)" | essas skills **não estão instaladas**. Substituem: `brand.json` do cliente + seção 3 e 4 do Master Prompt. O passo continua obrigatório; muda a fonte |
| "run `brand-profile` / `voice-builder` first" | não existe aqui. Se falta identidade verbal, leia material real da marca (LP, peças veiculadas, site, Instagram) |
| "Related skills: hook-writer, linkedin-post-writer, thread-writer, hashtag-strategy, cross-platform-repurposing, scheduling-and-queue" | nenhuma instalada, nenhuma necessária. `scheduling-and-queue` e WoopSocial são **publicação**: fora de escopo |
| "Deliver 2-3 caption options, recommend one" | **só quando o usuário pedir variações.** O padrão do squad é uma peça por pedido. Pedidas variações, valem as regras da seção 10 (ângulo diferente, não paráfrase) |
| Plataformas: X, Threads, Bluesky, Pinterest, YouTube | o canal vem da demanda. Não ofereça plataforma que ninguém pediu |

O que aproveitamos: primeira linha como jogo inteiro, corte do "…mais" por plataforma, legenda
que complementa em vez de descrever, objetivo antes de estrutura, um CTA só, mecânica de
hashtag e link por plataforma, formatos de legenda.

## `short-form-video-script` (social-media-skills)

| A skill diz | Aqui |
|---|---|
| "Read brand-profile + voice-builder first" | igual ao `caption-writer`: `brand.json` + Master Prompt |
| "Pulls the 'what' from the content-angle skills; uses hook-writer" | não instaladas. O ângulo vem da Source of Truth e do objetivo da demanda |
| "WoopSocial publishes the finished file" | **não existe aqui e não é nosso.** Publicação está fora de escopo |
| "Feeds reels-script / tiktok-script / youtube-shorts" | não instaladas. A especialização por plataforma entra como ajuste de duração e ritmo dentro do próprio roteiro |
| "Measure with analytics-and-reporting, 3s hold / AVD / replays" | analytics é fora de escopo. Não prometa medição, não cite benchmark como resultado esperado |
| Estatísticas com ano e fonte (OpusClip, Zebracat, Socialinsider) | são **referência de método**, não claim de cliente. Nunca migram para dentro da copy. Regra da seção 5 |
| "design-and-templates (on-screen text style)" | estilo visual do texto na tela é do Design. Você escreve o texto, não o estilo |

O que aproveitamos: WATCH (ganhar os 3 primeiros segundos, arco com loops abertos, versão muda
primeiro, pagar a promessa do gancho, fechar o loop e aterrar o CTA), formato de três trilhas
(visual + texto na tela + fala), variantes de gancho, beats, payoff, ritmo audiovisual, e a
trava de honestidade do gancho (sem bait-and-switch, sem número inventado).

Limite que a própria skill declara e que coincide com o nosso: **o agente escreve o roteiro; o
humano grava e edita.** No squad, quem executa vídeo, motion e edição é o Legend AI.

## `landing-page-copy` (rampstackco)

| A skill diz | Aqui |
|---|---|
| "The framework: 7 sections" | **não é template obrigatório.** O LP Builder trabalha com páginas compactas: poucas seções, alta densidade. Se quatro resolvem, quatro |
| "Use `cro-optimization` / `brand-voice` / `brand-discovery` / `content-and-copy` / `email-sequences` / `design-standards`" | nenhuma instalada. CRO técnico, e-mail e design são fora de escopo; identidade verbal é o Master Prompt + `brand.json` |
| "Step 9 — post-import checklist: URLs resolvem, preview mobile, SEO basics" | o entregável é copy, não página. A checagem de URL, mobile e SEO **não é sua**: vai como observação para o LP Builder, e SEO fica fora |
| "Social proof early: customer logos, 'over 10,000 teams'" | só com lastro. Número de cliente sem confirmação é claim classe C: não entra |
| "Case study 1: customer, outcome, numbers" | sem caso real documentado, declare a lacuna. Não construa depoimento |
| Vocabulário SaaS (free trial, no credit card, demo, signup) | traduza para a realidade do cliente. Clínica converte por WhatsApp e avaliação, não por trial |

O que aproveitamos: anatomia do hero (headline = promessa, subheadline = mecanismo, CTA = ação),
padrões de hero fortes e fracos, features traduzidas em resultado, biblioteca de objeções
(preço, tempo, confiança, risco, comparação, implementação), padrões de CTA fortes e fracos,
padrões de falha, e a regra de que dado indisponível se declara em vez de se estimar.
