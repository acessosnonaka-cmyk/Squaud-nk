# Registro do Squad NK

Quem faz o quê. O roteamento é **por capability**, nunca por nome do agente.

> **Roster oficial e legível por máquina: [`squad.yaml`](../../squad.yaml) na raiz.**
> Ele é a fonte única — documentação, Diretor e dashboard da web leem de lá. Este
> arquivo é a régua de roteamento em prosa; agente novo ou status alterado muda no
> `squad.yaml` primeiro.

**Estrutura: 1 orquestrador + 6 especialistas = 7 agentes.** Cada um tem prompt próprio.
Skill, motor e conector são **ferramentas** de um agente, nunca o agente inteiro.

## Agentes e capabilities

| Agente | Capabilities | Como acionar | Autoridade primária |
|---|---|---|---|
| **copywriter** | `copywriting.script`<br>`copywriting.social`<br>`copywriting.meta_ads`<br>`copywriting.landing_page` | `Agent(subagent_type: "copywriter")` · base `~/projetos/copywriter/` | copy, mensagem, promessa verbal, headline, argumento, CTA, narrativa verbal, roteiro |
| **designer** | `design.peca_grafica`<br>`design.direcao_de_arte` | `Agent(subagent_type: "designer")` · skill `designer-ia` · motor `agents/design-ia/engine/` | direção visual, composição, tipografia, layout, peça gráfica |
| **legend-ia** | `video.edicao`<br>`video.motion` | `Agent(subagent_type: "legend-ia")` · skill `editar-video` · motor `apps/legend-ia/` | execução audiovisual, edição, motion, montagem |
| **lp-builder** | `lp.arquitetura`<br>`lp.implementacao`<br>`lp.qa`<br>`lp.publicacao` | `Agent(subagent_type: "lp-builder")` · skills `lp-*` · motor `apps/lp-builder/engine/` | arquitetura da página, UX, composição, implementação, responsividade, interações |
| **revisor-de-criacao** | `revisao.visual`<br>`revisao.textual`<br>`revisao.tecnica` | `Agent(subagent_type: "revisor-de-criacao")` · skills `revisao-*` · motor `agents/revisor-arte/ferramentas/` | julgamento de qualidade da peça: nota, status e correções |
| **gestor-de-trafego** | `trafego.planejamento`<br>`trafego.criacao`<br>`trafego.otimizacao`<br>`trafego.analise` | **ainda não acionável** — ver abaixo | mídia paga: campanha, público, orçamento, pixel, UTM, otimização |
| **humanizer** | `texto.humanizacao` | `Skill(humanizer)` | remoção de marcas de IA na prosa; sem autoridade sobre fato |

Sem dono nomeado aqui — SEO, blog, e-mail marketing, atendimento, analytics, calendário
editorial, comunidade — vai para o Diretor de Operações, que aloca. **Proibido inventar dono.**

### Gestor de Tráfego — conceito definido, implementação ausente

O papel **existe no roster** e as capabilities estão reservadas. O executor **não existe**:
não há prompt, skill em disco nem motor. Enquanto for assim:

- **não simular** planejamento, criação, acompanhamento ou otimização de campanha;
- **não** dizer que a campanha foi subida, pausada ou otimizada;
- declarar a lacuna ao usuário e devolver a decisão a ele.

O que existe hoje fora do repositório está documentado em
[`docs/gestor-de-trafego.md`](../../docs/gestor-de-trafego.md), com o que falta para
transformá-lo no sétimo agente de fato.

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
