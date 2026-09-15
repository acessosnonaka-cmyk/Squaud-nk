---
name: lp-ingestao
description: Triagem progressiva de materiais do Google Drive para Landing Pages. Use SEMPRE que um cliente enviar um Drive, documento com links de pastas, ou acervo grande de fotos para uma LP — antes de qualquer curadoria manual. Evita analisar milhares de arquivos.
---

# Ingestão de materiais para LP

Ferramenta: `~/.claude/lp-builder/drive_ingest.py`
Cache por cliente: `~/.claude/lp-builder/clients/<slug>/` (isolado; nunca reutilize entre clientes).

**Nunca** enumere, baixe ou revise o acervo inteiro. Siga as cinco etapas.

## 1 · Mapear (sem baixar arquivos)
```
python3 ~/.claude/lp-builder/drive_ingest.py map --client <slug> --doc <url_do_doc>
python3 ~/.claude/lp-builder/drive_ingest.py map --client <slug> --folder <id> <id> ...
```
Uma requisição por pasta, em paralelo. Compara um **fingerprint** (ids + nomes ordenados) com o
cache: pasta inalterada não é reescrita; só a que mudou é atualizada. O TTL de 7 dias sobra apenas
como fallback quando o endpoint falha. `--refresh` força tudo.

Limitação: o endpoint público não expõe data de modificação nem tamanho por arquivo. Um arquivo
**substituído no lugar**, mantendo id e nome, não é detectado — nesse caso use `--refresh`.

## 2 · Priorizar
```
... rank --client <slug> --alta "cozinha,armario,painel" --media "casa,projeto" --ruido "cadeira,sofa,mesa"
```
Derive as palavras do **briefing**, não do acervo. `--ruido` afasta o que não serve à campanha.
Pastas com mais de 400 imagens perdem ponto: costumam ser despejo bruto.

## 3 · Triagem visual barata
```
... triage --client <slug> --tier ALTA --budget 40
```
Baixa só thumbnails (w400) das pastas priorizadas, amostradas, e gera **um** contact sheet.
Revise esse sheet único — não um por pasta.

## 4 · Filtro visual + curadoria
```
... screen --client <slug>
```
Roda sobre os thumbs já baixados (custo de rede zero). Rejeita automaticamente o que é
**mensurável**: sem conteúdo, desfoque forte, sub/superexposição, sem contraste, quase-duplicatas.

O filtro **não** detecta obra inacabada, entulho, fios aparentes nem enquadramento infeliz —
isso é semântico. Por isso **abra o contact sheet e olhe** antes de escolher; não pique por
índice de memória. `fetch` bloqueia os rejeitados e avisa se `screen` não tiver rodado.

## 5 · Alta resolução só da shortlist
```
... fetch --client <slug> --from-sheet --pick 3 7 12 18 22
```
Alvo normal: 8 a 15 finais. Menos, se a LP pedir menos.

## Escalada
Se ALTA não bastar, `--tier ALTA,MEDIA`. Só então BAIXA. Nunca comece pelo universo completo.
Se os nomes forem inúteis, amplie o budget progressivamente — não pergunte ao usuário qual pasta usar.
