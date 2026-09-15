# Calibração

As faixas de status e os pesos das réguas são **iniciais e não calibrados**. Foram
definidos por julgamento, não por evidência. Esta pasta é onde a evidência entra.

## O que depositar

Peças **reais**, já julgadas pela empresa, com o veredicto humano registrado.
Quanto mais próximo da fronteira (quase aprovado / quase reprovado), mais útil —
são os casos limítrofes que revelam se as faixas estão no lugar.

```
calibracao/
├── aprovadas/
│   └── <caso>/
│       ├── briefing.md
│       ├── <arquivos da entrega>
│       └── veredicto.md
└── reprovadas/
    └── <caso>/
        └── ...
```

### `veredicto.md`

```markdown
# Veredicto humano

- Status real: APROVADO | AJUSTES NECESSÁRIOS | REPROVADO
- Tipo: criativo | landing-page | video
- Data: AAAA-MM-DD
- Quem julgou:

## Por que
<O que motivou a decisão. O motivo importa mais que a nota: é ele que mostra
qual critério pesa de verdade nesta empresa.>

## O que foi decisivo
<O fator que sozinho determinou o resultado.>

## O que foi tolerado
<O que estava imperfeito e ainda assim não impediu a aprovação. Este campo é o mais
valioso do arquivo: é o que impede o revisor de ficar rigoroso demais.>
```

## Como a calibração será feita

1. Rodar o Revisor sobre cada caso, **sem** acesso ao `veredicto.md`.
2. Comparar o status previsto com o real.
3. Analisar as divergências:
   - **Reprovou o que a empresa aprovou** → régua rigorosa demais: baixar a faixa,
     reduzir peso do critério que puxou a nota, ou reclassificar observações de
     Classe 3 para 4.
   - **Aprovou o que a empresa reprovou** → falta critério ou falta falha crítica:
     ver o que o `veredicto.md` considerou decisivo e que a régua não olha.
4. Ajustar:
   - **faixas** → apenas `conhecimento/regras-gerais.md` §1 (BLOCO CALIBRÁVEL);
   - **pesos** → apenas a régua da categoria afetada;
   - **falhas críticas** → `conhecimento/falhas-criticas.md`.
5. Rodar de novo sobre todos os casos e verificar que os acertos anteriores continuam
   acertando.

## Enquanto não houver material aqui

A nota é **indicador, não veredicto**. O resumo executivo e as falhas críticas são
mais confiáveis do que o número — eles apontam fatos; a nota depende de pesos que
ainda não foram validados contra a régua real da empresa.
