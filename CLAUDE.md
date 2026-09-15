# Squad NK — instruções do repositório

Este repositório é a fonte da verdade do Squad. Todo agente, skill e motor vive aqui.
Se algo funciona numa máquina e não está aqui, está errado.

## Regras

1. **Nada de segredo.** Nenhuma chave, token, cookie, `.env` ou credencial entra no repositório,
   nem em repositório privado. Variável nova vai para `.env.example` só com o nome.
2. **Nada de dado de cliente.** Fotos, briefings, acervos de Drive, peças entregues, previews e
   revisões ficam fora do git. Já estão no `.gitignore`; não force `git add -f`.
3. **Caminho absoluto de máquina é bug.** `/home/ffili/...` e `/mnt/c/...` não podem aparecer em
   código ou skill. Use `Path(__file__).parent`, `$HOME`, ou variável do `.env`.
4. **Quem conhece o roteamento é o REGISTRY.** `agents/diretor-operacoes/REGISTRY.md` define quem
   faz o quê por *capability*. Nenhum agente inventa dono de tarefa.
5. **Prosa passa pelo humanizer.** Qualquer texto entregue a cliente roda `Skill(humanizer)` antes.

## Layout

| Caminho | O que é |
|---|---|
| `agents/diretor-operacoes/` | orquestrador + REGISTRY de capabilities |
| `agents/copywriter/` | agente de copy + 4 skills importadas |
| `agents/design-ia/` | skill `designer-ia` + motor `art-builder` (Python + Chromium) |
| `agents/revisor-arte/` | plugin `revisor-de-criacao` (tem `.claude-plugin/`) |
| `apps/lp-builder/` | 4 skills `lp-*` + motor Python (ingestão, QA, publicação) |
| `apps/legend-ia/` | pipeline de vídeo `process_video.py` (FFmpeg + faster-whisper) |
| `shared/skills/` | skills de terceiros instaladas por script (não versionadas) |
| `scripts/` | `setup.sh` (instala) e `check.sh` (diagnostica) |
| `docs/` | inventário da migração e arquitetura web |

## Depois de clonar

```bash
bash scripts/setup.sh
bash scripts/check.sh
```

`setup.sh` liga o repositório ao Claude Code por symlink e é idempotente: não apaga dado de
cliente já existente na máquina.

## Ao mexer num agente

- Edite o arquivo **no repositório**, nunca a cópia em `~/.claude/` — ela é um symlink para cá.
- Mudou capability? Atualize `REGISTRY.md` no mesmo commit.
- Mudou dependência? Atualize `scripts/check.sh` e a seção *Dependências* do README.
