# Registro do Squad Legend AI

Fonte única de quem faz o quê. O roteamento é **por capability**, nunca por nome do agente.

## Agentes e capabilities

| Agente | Capabilities | Como acionar | Autoridade primária |
|---|---|---|---|
| **copywriter** | `copywriting.script`<br>`copywriting.social`<br>`copywriting.meta_ads`<br>`copywriting.landing_page` | `Agent(subagent_type: "copywriter")` · base `~/projetos/copywriter/` | copy, mensagem, promessa verbal, headline, argumento, CTA, narrativa verbal, roteiro |
| **designer-ia** | `design.peca_grafica`<br>`design.direcao_de_arte` | `Skill(designer-ia)` · motor `~/.claude/art-builder/` | direção visual, composição, tipografia, layout, peça gráfica |
| **legend-ai** | `video.edicao`<br>`video.motion` | pipeline `~/video-editor/` (`Skill(editar-video)` no projeto) | execução audiovisual, edição, motion, montagem |
| **lp-builder** | `lp.arquitetura`<br>`lp.implementacao`<br>`lp.qa`<br>`lp.publicacao` | `Skill(lp-ingestao)` · `Skill(lp-design-review)` · `Skill(lp-qa)` · `Skill(lp-publicar)` · motor `~/.claude/lp-builder/` | arquitetura da página, UX, composição, implementação, responsividade, interações |
| **revisor-de-criacao** | `revisao.visual` | `Agent` lendo a BASE que `python3 ~/.claude/art-builder/revisor.py locate` devolve | julgamento de qualidade **visual** da peça |
| **humanizer** | `texto.humanizacao` | `Skill(humanizer)` | remoção de marcas de IA na prosa; sem autoridade sobre fato |

Sem dono nomeado aqui — SEO, blog, e-mail marketing, atendimento, analytics, calendário
editorial, comunidade — vai para o Diretor de Operações, que aloca. **Proibido inventar dono.**

**Gestor de Tráfego não existe.** Campanha, orçamento, conjunto, segmentação e publicação não
têm executor no squad. Não simular, não implementar, não inventar capability. É a etapa seguinte.

## Roteamento por capability

| A demanda pede | Capability | Agente |
|---|---|---|
| roteiro de vídeo, fala, texto na tela, beats | `copywriting.script` | copywriter |
| legenda, copy de post, caption | `copywriting.social` | copywriter |
| primary text, headline de anúncio, description, variações de ângulo | `copywriting.meta_ads` | copywriter |
| copy de LP, hero, promessa, objeções, microcopy | `copywriting.landing_page` | copywriter |
| arte, criativo, feed, story, banner | `design.peca_grafica` | designer-ia |
| editar, legendar, montar, animar vídeo | `video.edicao` | legend-ai |
| construir, implementar, publicar página | `lp.implementacao` | lp-builder |
| julgar a peça pronta | `revisao.visual` | revisor-de-criacao |

## Regra de precedência verbal

Existindo job de copywriting necessário, **Design, Legend AI e LP Builder não reinventam a
estratégia verbal em silêncio**. O fluxo é:

```
COPYWRITER → COPY APROVADA → ESPECIALISTA EXECUTOR
```

Adaptação de formato é permitida e esperada: quebrar linha, condensar, encurtar para caber no
espaço, ajustar ao tempo de vídeo. **Volta ao Copywriter** qualquer mudança de promessa, oferta,
argumento, claim, posicionamento ou CTA estratégico.

## Source of Truth do cliente — uma só, para todos

| Fonte | Papel |
|---|---|
| `~/.claude/art-builder/clients/<slug>/brand.json` | canônica: identidade, tom, institucional, `restrictions` |
| `~/<slug>-lp/` e `~/.claude/lp-builder/previews/<slug>/current/` | LP vigente: oferta, promessa, prova, CTA, destino do clique |
| `~/.claude/lp-builder/clients/<slug>/index.json` | acervo triado — só existe se a ingestão rodou |
| `~/.claude/projects/<projeto>/memory/` | claims verificados e claims sem lastro |

`restrictions` e `tone.avoid` vencem sempre, inclusive contra o site do próprio cliente.
Entregas antigas (`~/projetos/copywriter/entregas/`, `~/.claude/art-builder/jobs/`) são **rastro
de produção, não Source of Truth**. Ninguém cria banco paralelo.

## Revisão

Copy isolada **não** vai ao Revisor de Criação — ele julga resultado visual. O Copywriter faz a
própria revisão textual pelo Master Prompt dele. Quando a copy vira criativo, vídeo ou LP, aí o
resultado final passa pelo QA apropriado: `revisor-de-criacao` para peça e vídeo, `lp-qa` para
Landing Page.
