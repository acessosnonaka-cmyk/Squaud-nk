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
| **gestor-de-trafego** | `trafego.planejamento`<br>`trafego.criacao`<br>`trafego.otimizacao`<br>`trafego.analise` | `Agent(subagent_type: "gestor-de-trafego")` · skill `gestao-de-trafego` · plugin `gestor-de-trafego@squad-legend-ai` | mídia paga: campanha, público, orçamento, pixel, UTM, otimização |
| **humanizer** | `texto.humanizacao` | `Skill(humanizer)` | remoção de marcas de IA na prosa; sem autoridade sobre fato |

Sem dono nomeado aqui — SEO, blog, e-mail marketing, atendimento, analytics, calendário
editorial, comunidade — vai para o Diretor de Operações, que aloca. **Proibido inventar dono.**

O `subagent_type` de cada um vem do `squad.yaml` e é o mesmo `name` do frontmatter do prompt.
Quem confere se isso continua verdadeiro é o motor, não a memória de ninguém:

```bash
python3 agents/diretor-operacoes/engine/auditoria.py     # roster x disco x REGISTRY x setup.sh
```

## Contrato de cada especialista

Conhecer o nome não basta para delegar. Isto é o que o Diretor precisa saber antes de abrir
um job — e o que ele promete ao especialista no briefing.

### ✍️ Copywriter · `copywriter`

| | |
|---|---|
| **entrega** | roteiro de vídeo, copy de social, Meta Ads e copy de Landing Page |
| **recebe** | objetivo, público, oferta, claims permitidos, canal, formato, restrições do brand kit |
| **devolve** | copy pronta no formato do canal, com a classe factual de cada afirmação. **Roteiro devolve também o PDF** — `engine/roteiro_pdf.py` fecha a entrega, e job de roteiro sem PDF nos artefatos está incompleto |
| **não faz** | SEO, e-mail marketing, tráfego, design, vídeo, desenvolvimento de LP |
| **depende de** | Source of Truth do cliente. Nada mais — é o primeiro da cadeia |
| **revisão** | a dele é textual e própria. Copy isolada **não** vai ao Revisor de Arte |

### 🎨 Designer · `designer`

| | |
|---|---|
| **entrega** | peça gráfica de anúncio e campanha: feed, story, carrossel, banner, criativo |
| **recebe** | copy aprovada, identidade do cliente, formato, acervo selecionado para o job |
| **devolve** | peça renderizada, já submetida ao Revisor |
| **não faz** | copy estratégica, promessa, oferta, claim, CTA de campanha; vídeo; LP; campanha |
| **depende de** | job de copy, quando a peça tem texto estratégico |
| **revisão** | obrigatória, pelo Revisor de Arte. Ele não aprova a própria peça |

### 🧱 LP Builder · `lp-builder`

| | |
|---|---|
| **entrega** | landing page: arquitetura, UX, CRO, implementação, QA e publicação |
| **recebe** | copy aprovada, oferta, destino da conversão, acervo triado, identidade |
| **devolve** | página implementada e o link do preview |
| **não faz** | copy estratégica, arte de anúncio, vídeo, campanha de mídia |
| **depende de** | job de copy quando a página é nova; ingestão do acervo quando há imagem |
| **revisão** | `lp-qa` (skill própria). Publicação passa pela trava de autonomia |

### 🎬 Legend IA · `legend-ia`

| | |
|---|---|
| **entrega** | vídeo transcrito, legendado e com headline e CTA queimados |
| **recebe** | arquivo de vídeo, roteiro ou copy quando houver texto na tela, formato de saída |
| **devolve** | vídeo novo. O original nunca é alterado |
| **não faz** | roteiro estratégico, arte estática, LP, campanha |
| **depende de** | job de copy quando o texto na tela é estratégico |
| **revisão** | Revisor de Arte, quando o vídeo é peça de anúncio |

### 🔎 Revisor de Arte · `revisor-de-criacao`

| | |
|---|---|
| **entrega** | parecer com nota, status e correções objetivas |
| **recebe** | a peça entregue **e** o briefing que a originou — sem briefing não há requisito a cobrar |
| **devolve** | aprovação ou reprovação com correção acionável |
| **não faz** | editar, corrigir, mover ou refazer o que revisa. Nunca |
| **depende de** | um job de produção concluído |
| **revisão** | é ele. Ninguém revisa a própria peça |

### 📈 Gestor de Tráfego · `gestor-de-trafego`

| | |
|---|---|
| **entrega** | planejamento de mídia, estrutura de campanha, diagnóstico de gargalo, otimização, relatório de performance e briefing para o squad |
| **recebe** | objetivo de negócio, oferta, verba, KPIs, acesso ou export da conta, `guardrails.md` do cliente |
| **devolve** | plano, parecer ou relatório com evidência e recomendação — e o que precisa de aprovação, declarado. **Análise de performance volta em duas peças: relatório executivo + dashboard ou infográfico** (`modelos/dashboard-executivo.md`) |
| **não faz** | copy de anúncio (é do Copywriter), peça, vídeo, página; e **não executa na conta** por conta própria |
| **depende de** | leitura real da conta. Sem dado, declara a limitação e devolve `precisa_de_informacao` — não estima métrica |
| **revisão** | própria, pela evidência. Prosa que vai ao cliente passa pelo `humanizer` |

Subir, ativar, pausar, duplicar, publicar ou mexer em orçamento é `REQUER_APROVACAO` no
`policy.yaml`: ele **recomenda**, o Diretor leva ao portão e o gestor humano autoriza. Sem
`guardrails.md` preenchido para a conta, toda alteração financeira passa por aprovação.
Integrar ao motor não muda nada disso.

### Gestor de Tráfego — recomenda sempre, executa só com autorização

O papel saiu do conceito: tem prompt, skill e base de conhecimento em disco. Duas
fronteiras continuam valendo, e são o motivo de ele ser seguro de acionar:

- **Não escreve a copy do anúncio** — isso é `copywriting.meta_ads`, do Copywriter. Ele
  define ângulo, público e critério de sucesso; o Copywriter escreve.
- **Não executa na conta do cliente por conta própria.** `trafego.criacao` e qualquer ação
  sobre orçamento, publicação, ativação ou pausa é classificada `REQUER_APROVACAO` pelo
  `policy.yaml` e só roda com aprovação registrada. Sem acesso autorizado e sem
  `guardrails.md` preenchido para a conta, ele analisa e recomenda — não publica.

**Métrica afirmada sem leitura da conta é invenção.** Sem dado, ele declara a limitação em
vez de estimar. O que existe fora do repositório — as 5 skills da conta claude.ai e o
conector Meta ADS — segue mapeado em
[`docs/gestor-de-trafego.md`](../../docs/gestor-de-trafego.md).

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
| planejar mídia, estrutura de campanha, público, orçamento, KPIs | `trafego.planejamento` | gestor-de-trafego |
| montar campanha, estrutura de conta, UTM, pixel, rascunho de subida | `trafego.criacao` | gestor-de-trafego |
| achar o gargalo, decidir manter, pausar, testar ou escalar | `trafego.otimizacao` | gestor-de-trafego |
| ler resultado, CPL/CPA/CAC/ROAS, relatório de performance | `trafego.analise` | gestor-de-trafego |
| achar o gargalo da aquisição, por que o CPL/CPA subiu | `trafego.diagnostico` | gestor-de-trafego |
| planejar mídia, estrutura de campanha, orçamento, KPIs | `trafego.planejamento` | gestor-de-trafego |
| ler resultado, decidir manter, pausar, testar ou escalar | `trafego.analise` | gestor-de-trafego |
| criar, publicar, pausar, ajustar campanha na plataforma | `trafego.operacao` | gestor-de-trafego |
| relatório de performance para o cliente | `trafego.relatorio` | gestor-de-trafego |

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
| `$SQUAD_DATA_HOME/trafego/clients/<slug>/` | memória de mídia: guardrails, contexto de aquisição e histórico de campanha |
| `$SQUAD_DATA_HOME/diretor/clientes/<slug>.fontes.json` | acervo externo do cliente (Drive): base, apelidos e fontes classificadas. Só `fato`, `asset` e `decisao_vigente` entram no briefing como verdade — histórico e campanha anterior viajam como referência, e só quando anexados ao job |

`restrictions` e `tone.avoid` vencem sempre, inclusive contra o site do próprio cliente.
Quem consulta o Drive é **só o Diretor** — especialista recebe fato pelo briefing e não vai ao
acervo por conta própria. O protocolo está na seção 7 do prompt do Diretor.
Entregas antigas (`~/projetos/copywriter/entregas/`, `~/.claude/art-builder/jobs/`) são **rastro
de produção, não Source of Truth**. Ninguém cria banco paralelo.

## Revisão

Copy isolada **não** vai ao Revisor de Criação — ele julga resultado visual. O Copywriter faz a
própria revisão textual pelo Master Prompt dele. Quando a copy vira criativo, vídeo ou LP, aí o
resultado final passa pelo QA apropriado: `revisor-de-criacao` para peça e vídeo, `lp-qa` para
Landing Page.
