# Procedência das skills do COPYWRITER

Auditado e instalado em 2026-09-12. Nada foi instalado em `~/.claude/skills/`: as skills
complementares vivem nesta base e são carregadas por leitura de arquivo. Decisão deliberada —
evita expor as skills ao squad inteiro e mantém o isolamento pedido no briefing.

| Skill | Origem | Commit | Licença | Capability | Status |
|---|---|---|---|---|---|
| `copywriting` | github.com/entpnomad/copywriting | `c3b84cb` (2026-08-12) | MIT © entpnomad | fundação das quatro | instalada |
| `caption-writer` | github.com/social-media-skills/skills · `skills/caption-writer` | `6e30eeb` (2026-07-19) | MIT © Frank Heijdenrijk | `copywriting.social` | instalada |
| `short-form-video-script` | github.com/social-media-skills/skills · `skills/short-form-video-script` | `6e30eeb` (2026-07-19) | MIT © Frank Heijdenrijk | `copywriting.script` | instalada |
| `landing-page-copy` | github.com/rampstackco/claude-skills · `skills/landing-page-copy` | `a67dd34` (2026-08-28) | MIT © RampStack Co. | `copywriting.landing_page` | instalada |
| `humanizer` | já existia no ambiente (`~/.agents/skills/humanizer`, v3.0.0, MIT) | — | MIT | revisão final das quatro | **reutilizada** |

## Auditoria prévia — o que foi procurado antes de instalar

Busca por skill existente relacionada a `copywriting`, `copy`, `caption`, `social`, `script`,
`roteiro`, `landing-page`, `brand-voice`, `humanizer` em `~/.claude/skills/`,
`~/.agents/skills/`, `~/.claude/plugins/`, `~/projetos/` e no plugin `revisor-de-criacao`.

**Encontrado:**

- `humanizer` v3.0.0 — pasta real em `~/.agents/skills/humanizer`, symlink em
  `~/.claude/skills/humanizer`. Funcional, compatível, **reutilizada**. Nenhum segundo
  humanizer foi instalado.
- Nenhuma skill de copywriting, caption, roteiro ou landing-page-copy em disco. As quatro
  instaladas **não duplicam** nada existente.

**Skills de copy que existem na conta claude.ai e NÃO em disco** (`copywriter-nonaka`,
`megazord`, `criacao-copy-*`): não são invocáveis no Claude Code. Não foram instaladas nem
substituídas — são caminhos paralelos que o usuário usa no claude.ai. Se em algum momento
quiser consolidá-las aqui, é decisão dele; comparar antes é obrigatório.

## Referências deliberadamente NÃO instaladas

Cada skill importada pede skills companheiras. Nenhuma é necessária, e instalar qualquer uma
ampliaria o escopo do agente. O mapa de substituição está em `skills/ADAPTACOES.md`.

- `tone-of-voice` (companheira de `copywriting`) → Master Prompt seção 4 + `brand.json` + `humanizer`
- `brand-profile`, `voice-builder` → `brand.json` do cliente + Master Prompt seções 3 e 4
- `hook-writer`, `linkedin-post-writer`, `thread-writer`, `hashtag-strategy`,
  `cross-platform-repurposing` → fora de escopo ou cobertos pela skill principal
- `scheduling-and-queue`, WoopSocial, `reels-script`, `tiktok-script`, `youtube-shorts` →
  publicação e plataforma: fora de escopo
- `analytics-and-reporting` → fora de escopo
- `ai-video`, `veo-3`, `heygen`, `kling`, `captions-and-clipping` → execução de vídeo: Legend AI
- `cro-optimization`, `design-standards`, `content-and-copy`, `email-sequences`,
  `brand-discovery` → fora de escopo ou de outro agente

Os 106 skills de `social-media-skills/skills` **não** foram instalados: o clone usou
`--filter=blob:none --sparse` e só os dois diretórios pedidos foram materializados. Mesmo
método no `rampstackco/claude-skills`. Diretórios `evals/` foram descartados (material de teste
dos autores, sem função aqui).

## Nenhum agente existente foi alterado

Intocados: `designer-ia`, `lp-ingestao`, `lp-design-review`, `lp-qa`, `lp-publicar`,
`humanizer`, `revisor-de-criacao`, `~/.claude/art-builder/*`, `~/.claude/lp-builder/*`,
`~/.claude/settings.json`. O Diretor de Operações e o roteamento global **não** foram mexidos —
a conexão é a etapa seguinte, conforme o briefing.

Arquivos criados, todos novos:

```
~/projetos/copywriter/**                (base do agente)
~/.claude/agents/copywriter.md          (symlink -> agents/copywriter.md, registra o subagente)
```
