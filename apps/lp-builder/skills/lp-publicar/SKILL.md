---
name: lp-publicar
description: Publica o preview de uma Landing Page pronta e devolve URL estável. Use ao finalizar qualquer LP, antes de entregar o link ao usuário. Versiona, isola por cliente e permite rollback.
---

# Publicar preview de LP

Comando: `lp-publish` (ou `python3 ~/.claude/lp-builder/publish.py`)

```
lp-publish publish <slug> <diretorio>   # valida, versiona, publica, testa HTTP, devolve URL
lp-publish ls [slug]                    # clientes e versões
lp-publish rollback <slug> [--to V]     # volta à versão anterior
lp-publish serve --port 8090            # servidor que atende todos os previews
```

O servidor precisa estar no ar: `nohup python3 ~/.claude/lp-builder/publish.py serve &`

Estrutura: `~/.claude/lp-builder/previews/<slug>/current -> versions/<carimbo>/`
Troca de ponteiro é atômica; a versão anterior fica intacta como backup (8 preservadas).

**URL estável:** republicar o mesmo slug mantém o mesmo endereço.

**VPS:** preencha `remote` em `~/.claude/lp-builder/publish.conf.json` e a publicação passa a
enviar por rsync+ssh sozinha. Sem isso, publica local.

**Nunca** edite `previews/` na mão — use os comandos. Slug é validado (`a-z0-9-`) e todo
caminho é confinado à raiz de previews.
