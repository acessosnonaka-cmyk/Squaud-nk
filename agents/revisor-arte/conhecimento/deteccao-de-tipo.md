# Detecção de Tipo de Entrega

Roteador do sistema. Resolve **qual régua aplicar** e é o único arquivo que
precisa mudar quando uma categoria nova entra.

---

## 1. Registro de tipos

| Tipo | Régua | Sinais de identificação |
|---|---|---|
| `criativo` | `criterios/criativos.md` | `.png` `.jpg` `.jpeg` `.webp` `.gif` `.pdf` (peça única/carrossel), `.psd` `.ai` `.indd` (só metadados) |
| `landing-page` | `criterios/landing-pages.md` | `.html` `.htm` `.jsx` `.tsx` `.vue` `.astro`, pasta com `index.html`, screenshots de página completa com múltiplas dobras, URL no briefing |
| `video` | `criterios/videos.md` | `.mp4` `.mov` `.webm` `.avi` `.mkv` `.m4v`, acompanhados ou não de `.srt` `.vtt` |

> **Para adicionar uma categoria:** copiar `criterios/_template-categoria.md`,
> preencher, e acrescentar **uma linha** a esta tabela. Nada mais no projeto muda —
> nem o arquivo do agente, nem as outras réguas.

---

## 2. Cascata de identificação

O **primeiro sinal que resolver, vence**.

### Nível 1 — Declaração explícita *(decisivo)*

Campo `tipo` no briefing, com valor do registro acima.

```
Tipo de entrega: video
```

Sobrepõe todos os outros níveis, inclusive as extensões. Se o briefing declara `video`
e a pasta só tem `.png`, isso não é conflito de tipo — é **entrega incompleta**, e vira
falha crítica de completude.

### Nível 2 — Extensão dos arquivos *(força alta)*

Casar as extensões presentes contra a coluna "Sinais" do registro.

### Nível 3 — Conteúdo do material *(força média)*

Quando a extensão é ambígua:

- `.html` com `<form>`, `<section>` repetidas, hero + dobras → `landing-page`
- `.html` que é apenas um template de e-mail (tabelas aninhadas, largura fixa ~600px) → **não** é landing-page; sem régua no registro atual
- `.pdf` de uma página, formato de post/anúncio → `criativo`
- `.pdf` multipágina que reproduz uma página web rolável → `landing-page`
- imagem muito alta e estreita (proporção acima de ~1:3), com várias seções → screenshot de `landing-page`, não `criativo`

### Nível 4 — Nome de pasta ou arquivo *(força fraca — só desempata)*

`lp-`, `landing`, `captura` → `landing-page`
`feed`, `story`, `carrossel`, `banner`, `anuncio` → `criativo`
`reels`, `vt`, `video`, `edit`, `corte` → `video`

**Nunca usar o nível 4 sozinho** para decidir. Ele só desempata quando os níveis 2 e 3
apontam para mais de um tipo com força equivalente.

---

## 3. Regras de contorno

### 3.1 Pasta mista *(caso normal, não exceção)*

Uma pasta com `.mp4`, `.png` e `.html` contém **três entregas**, não uma ambígua.

- Agrupar os arquivos por tipo.
- Revisar cada grupo com sua própria régua e gerar um relatório individual para cada.
- Gerar um consolidado da pasta.
- Arquivos de apoio (briefing, fontes, logos, `.srt`, assets soltos) **não são entregas**:
  são insumos. Não geram relatório próprio; alimentam a revisão das entregas.
- **Ser insumo não faz de um arquivo um briefing.** Um documento só é tratado como
  briefing quando houver evidência suficiente — nome explícito, conteúdo inequivocamente
  estruturado como o pedido daquela entrega, ou indicação direta do usuário. `README.md`,
  documentação técnica e notas de projeto **não** são briefing por padrão. Na dúvida, não
  é briefing: declarar a ausência é sempre preferível a extrair requisitos de um documento
  que não era um pedido.

### 3.2 Variações da mesma peça

Mesma arte em formatos diferentes (`feed-1080x1080.png`, `story-1080x1920.png`) são
**uma entrega com múltiplos formatos**, não entregas separadas. Um relatório, com a
verificação de formatos e a consistência entre variações incluídas nele.

### 3.3 Ambiguidade real

Quando a cascata inteira não resolve — perguntar ao usuário. Apresentar:

- o inventário do que foi encontrado;
- os tipos candidatos e o sinal que aponta para cada um;
- a pergunta objetiva.

**Nunca escolher em silêncio** e nunca "revisar pelos dois" para não ter que perguntar.

### 3.4 Sem tipo reconhecido

Material fora do registro (apresentação, planilha, documento, e-mail, áudio isolado):

- aplicar **apenas** o núcleo comum de `regras-gerais.md`;
- **não atribuir nota** — não existe régua, logo não existem pesos;
- status limitado a **AJUSTES NECESSÁRIOS** ou **REPROVADO** (nunca APROVADO por
  ausência de critério);
- declarar em destaque que não há régua especializada para esse tipo;
- sugerir a criação da categoria, se o tipo for recorrente.

### 3.5 Formatos não legíveis

`.psd`, `.ai`, `.indd`, `.fig`, `.svg` não são lidos visualmente. Se forem o **único**
material da entrega: reportar como impedimento de revisão, pedir export em `.png`/`.jpg`
e **não** emitir nota. Se acompanharem um export legível, revisar o export e registrar
o arquivo-fonte apenas no inventário.
