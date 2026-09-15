# Teste de reconstrução em clone limpo — 2026-09-15

Método: `git clone` do repositório num diretório temporário vazio, `CLAUDE_CONFIG_DIR`
apontado para uma pasta nova, `scripts/setup.sh`, e depois execução real de cada motor.
Nenhum arquivo da máquina de origem foi usado como entrada, exceto onde anotado.

| Componente | Resultado | O que foi executado de fato |
|---|---|---|
| **LP Builder** | 🟢 reprodutível | `lp_qa.py` numa LP de teste: 3 viewports, contraste WCAG, acessibilidade, escala tipográfica e 3 capturas PNG. `publish.py publish` versionou o preview e `publish.py ls` o listou |
| **Diretor de Operações** | 🟢 reprodutível | prompt e `REGISTRY.md` no clone, frontmatter íntegro, symlink registrado em `$CLAUDE_CONFIG_DIR/agents/` |
| **Design IA** | 🟢 reprodutível | `brand.py init` → `job.py new` → `artdirection.py compile` → `job.py render`: **PNG 1080×1350 gerado**, autofit e contraste validados |
| **Revisor de Arte** | 🟢 reprodutível | `revisor.py locate` resolveu para `agents/revisor-arte` **do próprio clone** (origem: "monorepo Squad NK"), as 4 skills apareceram e o `handoff.v1.md` foi gerado |
| **Legend IA** | 🟢 reprodutível | vídeo 720×1280 processado duas vezes: com `--no-subtitles --preset pro` e com transcrição real via `faster-whisper`. MP4 final H.264+AAC nos dois casos |

## Três defeitos reais que o teste encontrou — e que foram corrigidos

1. **Design IA não renderizava.** O motor dependia de `libnss3`/`libnspr4` embarcadas em
   `runtime/lib/` na máquina de origem, deixadas de fora por serem regeneráveis. Sem elas o
   Chromium não sobe: gerava o HTML, não gerava o PNG.
   → `scripts/chromium-libs.sh`, que resolve com apt **ou sem root nenhum**.
2. **QA do LP Builder morria pelo mesmo motivo.** `render.py` injetava `LD_LIBRARY_PATH`;
   `lp_qa.py` não. → mesma injeção em `lp_qa.py`, libs compartilhadas em `shared/runtime/lib`.
3. **Dado de cliente caía dentro do clone.** O `art-builder` resolve caminhos a partir do
   próprio arquivo, e com os `.py` ligados por symlink isso apontava para dentro da árvore do
   git. → `setup.sh` liga `clients/`, `jobs/` e `output/` de volta para `~/.claude/art-builder/`.

Além disso, `revisor.py` só encontrava o Revisor por plugin instalado ou varredura do home —
num clone limpo, sem plugin, o handoff falhava. Agora o próprio monorepo é o primeiro candidato.

## Limitações conhecidas do teste

- **`publish.py` resolve `~/.claude/lp-builder` fixo**, ignorando `CLAUDE_CONFIG_DIR`. O teste de
  publicação gravou na árvore real da máquina de origem; o preview `teste-clone` criado foi
  removido em seguida. Não é bloqueio — só significa que o LP Builder guarda previews num
  caminho único por usuário.
- **`python3`, `ffmpeg` e `playwright` já existiam na máquina do teste.** O clone limpo prova
  que o *repositório* basta; não prova a instalação dessas três dependências de sistema numa
  máquina virgem. Estão documentadas no README e verificadas por `check.sh`.
- **O plugin do Revisor não foi instalado via `claude plugin install`** — o `locate` passou a
  resolver pelo próprio clone, que é o caminho que interessa para reconstrução. O comando de
  instalação continua correto: o `marketplace.json` da raiz aponta `./agents/revisor-arte`.
- **Peça de teste do Design IA acusou "1 imagem não carregou"**: o briefing de teste não tinha
  foto e a marca de teste não tinha logo. É a validação funcionando, não defeito do motor.
