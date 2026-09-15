# Revisor de Criação

Agente de controle de qualidade do **Squad NK**. Revisa entregas do squad antes
da aprovação final — criativos, landing pages e vídeos — comparando **o que foi pedido**
com **o que foi entregue**.

Não cria entregas. Não refaz material. **Nunca edita o que revisa.**

---

## Instalação

Uma vez, em cada máquina:

```bash
claude plugin marketplace add acessosnonaka-cmyk/Squaud-nk
```

```bash
claude plugin install revisor-de-criacao@squad-legend-ai
```

Os **dois** comandos são necessários, nesta ordem: o primeiro registra o catálogo, o
segundo instala o plugin. Numa máquina limpa, o `install` sozinho não encontra nada.

Pronto. O agente passa a existir em qualquer pasta, em qualquer sessão.

Para conferir:

```bash
claude plugin list
```

Para atualizar, quando houver versão nova:

```bash
claude plugin marketplace update squad-legend-ai
```

### Requisitos

| | |
|---|---|
| **Claude Code** | 2.1.251 ou superior, com acesso próprio |
| **Google Drive** | conector conectado à sua conta, com acesso às pastas do time |
| **ffmpeg / ffprobe** | opcional, mas recomendado — sem eles as medições técnicas não são feitas e a revisão avisa |

Instalar o ffmpeg, se faltar:

```bash
sudo apt install ffmpeg
```

---

## Como usar

Em linguagem natural. Duas informações bastam: **o link e o tipo**.

```
Use o Revisor de Criação para revisar https://drive.google.com/drive/folders/... 
É para anúncio.
```

```
Use o Revisor de Criação para revisar https://drive.google.com/drive/folders/...
É para social mídia.
```

Aceita link de **arquivo** ou de **pasta**, e também caminhos locais.

**Não é preciso** enviar briefing, informar cliente, explicar objetivo nem chamar skills
manualmente. Se você não disser o tipo, o Revisor assume social mídia.

### Os dois contextos

| Contexto | O que muda |
|---|---|
| **Anúncio** | acrescenta a camada de mídia paga: leitura rápida em feed, legibilidade mobile, densidade, qualidade percebida |
| **Social mídia** | não cobra características de performance de mídia paga |

Variações aceitas: *anúncio, ads, tráfego, meta ads, mídia paga* · *social, social mídia, orgânico, post*.

---

## O que você recebe

Peça aprovada:

```
imagem-01.jpg

⭐⭐⭐⭐
APROVADO

Ortografia: ✓
Visual: ✓
Técnico: ✓
Anúncio: ✓

Pronta para uso.
```

Peça com problema:

```
imagem-03.png

⭐⭐⭐
AJUSTES NECESSÁRIOS

Problema:
Palavra duplicada na headline — "UMA UMA RECEITA PRONTA!".

Correção:
Trocar por "UMA RECEITA PRONTA!" na segunda linha do título.
```

Pasta com várias peças: primeiro o panorama, depois só as que precisam de ajuste.

Os relatórios completos ficam em `~/revisoes-criativos/<data>-<pasta>/`.

---

## A escala

| | |
|---|---|
| ⭐⭐⭐⭐⭐ | **APROVADO** — excelente |
| ⭐⭐⭐⭐ | **APROVADO** — boa, profissional, publicável |
| ⭐⭐⭐ | **AJUSTES NECESSÁRIOS** — há problema concreto que justifica devolver |
| ⭐⭐ | **REPROVADO** — problemas relevantes ou múltiplos |
| ⭐ | **REPROVADO** — claramente inadequada |

**Regra central:** se não existe motivo concreto para devolver a peça, ela recebe no
mínimo ⭐⭐⭐⭐. Preferência estética não é defeito — o Revisor não devolve peça porque
faria diferente. Erro ortográfico objetivo, por outro lado, nunca é aprovado.

Peça aprovada **não recebe lista de melhorias**.

---

## Segurança

- **Google Drive somente leitura.** O Revisor nunca modifica, move, renomeia, apaga nem
  compartilha nada no Drive.
- **Nada é tornado público.** O acesso é pela sua conta autenticada.
- **Os arquivos revisados nunca são editados.**
- Downloads temporários vão para `~/.cache/revisor-de-criacao/` e são apagados ao fim.

---

## Estrutura

```
agents/revisor-de-criacao.md     o agente: identidade, fluxo e regras invioláveis
skills/                          textual · visual · técnica · anúncios
conhecimento/                    réguas, regras gerais, falhas críticas, formato
ferramentas/                     drive-baixar.sh · inspecionar-video.sh
modelos/template-briefing.md     modelo de briefing, quando houver
```

Adicionar uma categoria de entrega: copiar `conhecimento/criterios/_template-categoria.md`
e acrescentar uma linha em `conhecimento/deteccao-de-tipo.md`. O agente não é tocado.

---

## Limitações conhecidas

- **Landing pages** não são renderizadas (não há navegador): revisão por código-fonte
  e/ou screenshots. Responsividade e interações não são verificáveis.
- **Vídeos**: o Revisor mede o arquivo e lê frames amostrados. Não assiste e não escuta —
  qualidade de locução, trilha, mixagem e ritmo **não** são avaliados.
- **Imagens**: leitura visual é estimativa, não medição. DPI, CMYK e perfil de cor não
  são verificáveis. `.psd`, `.ai` e `.svg` precisam de export.
- Arquivos muito grandes (acima de ~8 MB) podem falhar no download do Drive.
- A avaliação não é determinística: rodadas diferentes podem variar em torno de meia
  estrela. Falhas críticas e status são estáveis.
