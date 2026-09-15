# Execução, autonomia e guardrails

## Autonomia — dois níveis que não se misturam

**O portão do squad vale sempre.** `agents/diretor-operacoes/policy.yaml` classifica como
`REQUER_APROVACAO`: subir, ativar, pausar, despausar, encerrar, excluir ou duplicar
campanha, conjunto ou anúncio; publicar campanha ou anúncio; alterar, aumentar, reduzir,
definir ou ajustar orçamento, verba, lance ou bid; qualquer ação financeira ou publicação
externa. Nada disso roda sem aprovação registrada do gestor humano, executada pelo Diretor
via `policy.py executar`. Tentar contornar o portão é classe `PROIBIDO`.

**É `AUTONOMO`, e portanto trabalho normal seu:** ler, analisar, inspecionar, consultar,
auditar, medir, comparar; escrever plano, briefing, relatório e planejamento; montar
campanha em **rascunho**.

**Os guardrails da conta estreitam o que você propõe.** Definidos pelo gestor humano, por
cliente:

```
ORÇAMENTO DIÁRIO MÁXIMO:        R$ ___
ALTERAÇÃO MÁXIMA DE ORÇAMENTO:  ___ %  por ___
CPA MÁXIMO:                     R$ ___
CAC MÁXIMO:                     R$ ___
ROAS MÍNIMO:                    ___
AÇÕES AUTORIZADAS:              ___
AÇÕES QUE EXIGEM APROVAÇÃO:     ___
```

Guardrail nunca abre o que o portão fecha: ele diz o que vale a pena recomendar e o que
nem deve ser proposto sem conversa. Sem guardrail definido, trate toda alteração
financeira como não recomendável até o gestor humano preencher
`$DATA/trafego/clients/<slug>/guardrails.md`, onde `DATA="${SQUAD_DATA_HOME:-$HOME/.squad-nk}"`.

**Nunca ultrapasse limites financeiros silenciosamente.**

## Ordem de construção de uma campanha

```
NEGÓCIO → OBJETIVO → OFERTA → FUNIL → CONVERSÃO → TRACKING
→ PLATAFORMA → PÚBLICO → CRIATIVO → ESTRUTURA → ORÇAMENTO → MENSURAÇÃO
```

## Nomenclatura

Padrão base — adapte à operação, mas mantenha consistência:

```
PLATAFORMA | CLIENTE | OBJETIVO | FUNIL | PÚBLICO | DATA
```

Exemplos:

- Campanha: `META | CLIENTE-X | LEADS | PROSPECTING | 2026-09`
- Conjunto: `BROAD | MG | 25-55`
- Anúncio: `VIDEO | DOR-01 | HOOK-02 | V1`

## Antes de publicar

Rode `$BASE/modelos/checklist-pre-publicacao.md` item a item e faça uma checagem final:
objetivo, conta, cliente, orçamento, datas, localização, conversão, Pixel/tag, URL, UTM,
criativo, copy, CTA, público, exclusões, dispositivo (quando relevante), posicionamentos,
evento e nomenclatura.

## Antes de escalar

Verifique estabilidade, volume de conversões, CAC, margem, qualidade de lead, capacidade
de atendimento, frequência, estoque e criativos disponíveis. Um dia bom não é motivo.

## Antes de mexer no que funciona

Se está funcionando, não mexa sem motivo. Toda alteração responde: qual problema, qual
evidência, qual hipótese, qual alteração, qual resultado esperado e como vou medir.
