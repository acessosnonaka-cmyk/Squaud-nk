---
name: revisao-textual-criativos
description: Esta skill deve ser usada sempre que for necessário revisar, conferir ou analisar os textos visíveis de uma peça gráfica, criativo, post, banner, anúncio, story ou arte estática — ortografia, acentuação, palavras duplicadas, letras faltando, digitação, nomes próprios, maiúsculas, datas, números, preços, percentuais, telefones, endereços, textos cortados e inconsistências internas. Produz evidências textuais para o Revisor de Criação; não atribui nota nem decide status.
---

# Revisão Textual de Criativos

**Área de alta prioridade.** Erro de texto é o defeito mais caro de uma peça: é
inequívoco, qualquer pessoa vê, e mancha a percepção de cuidado da marca.

Esta skill **produz evidências**. Ela **não** atribui estrelas, **não** define status e
**não** decide se a peça é aprovada — isso é do Revisor de Criação.

## Procedimento

1. **Transcrever integralmente** todo texto visível: logo, tagline, headline, subtítulo,
   corpo, selos, rodapé, legendas, CTA, letras miúdas.
2. **Conferir palavra por palavra** contra a transcrição.
3. Ampliar o trecho (`ffmpeg` crop) **apenas** quando houver suspeita concreta — é o que
   separa constatar um erro de achar que se viu um.
4. Reportar cada achado com: **o quê · onde · evidência · confiança · ação recomendada**.

## O que procurar

| Categoria | Exemplos |
|---|---|
| Ortografia | grafia incorreta, letra trocada |
| Acentuação | acento ausente, indevido ou trocado |
| **Palavra duplicada** | `UMA UMA`, `de de`, `para para` |
| Letra/palavra ausente | `recuperaão`, frase sem preposição |
| Digitação | espaço duplo, espaço antes de pontuação, aspas trocadas |
| Nomes próprios | grafia de pessoa, marca, cidade, produto |
| Maiúsculas/minúsculas | caixa inconsistente sem intenção visível |
| Datas · Números · Preços · % | formato, coerência interna |
| Telefones · Endereços | quantidade de dígitos, formato, DDD |
| Texto cortado | frase truncada pela margem ou por outro elemento |
| Inconsistência interna | mesmo dado com dois valores na mesma peça |

## Regra dos dados verificáveis

Data, número, preço, percentual, telefone, endereço e nome **só podem ser chamados de
errados quando existir referência que permita verificar** (briefing, manual, peça
anterior, outro trecho da própria peça).

Sem referência, é possível — e desejável — apontar:

- **inconsistência interna** — "o topo diz 15/03 e o rodapé diz 16/03";
- **formato suspeito** — "telefone com 8 dígitos após o DDD";
- **possível problema** — "data sem ano; confirmar se é intencional".

**Nunca inventar qual seria o valor correto.** "O telefone parece incompleto" é válido;
"o telefone correto é 99999-9999" é proibido.

## Erro objetivo × escolha estilística

Esta distinção é o coração da skill. Errar aqui produz devolução injusta.

**É erro objetivo** — inequívoco, sem leitura alternativa:

- `UMA UMA RECEITA PRONTA` → palavra duplicada.
- `recuperaão` → letra faltando.
- `voce` em peça que acentua todo o resto → acentuação ausente.

**NÃO é erro** — construção publicitária legítima:

- Ausência de ponto final em headline, título ou CTA.
- Quebra de linha sem vírgula em segmentos paralelos:

  ```
  Mais confiança
  mais autonomia
  ```

  A quebra faz o trabalho da pontuação. **Não tratar como erro de pontuação.**
- Frase nominal, sem verbo.
- Caixa alta integral por ênfase.
- Estrangeirismo, neologismo, nome de marca, jargão do setor.
- Minúscula inicial deliberada, quando consistente na peça.

**Na dúvida razoável entre erro e escolha estilística: não é erro bloqueante.**
Registrar no máximo como observação opcional, e apenas se for realmente útil.

## Saída esperada

Uma lista de achados. Para cada um:

- **Classificação**: erro objetivo · inconsistência interna · formato suspeito ·
  observação opcional
- **Trecho exato** e onde está na peça
- **Evidência**: leitura direta ou recorte ampliado
- **Confiança**: Alta / Média / Baixa
- **Ação recomendada**

Se nada for encontrado, dizer isso de forma direta: *"Todos os textos conferidos, sem
erro identificado"*, listando o que foi transcrito. Confirmação explícita tem valor —
é o que permite aprovar com segurança.
