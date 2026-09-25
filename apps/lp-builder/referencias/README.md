# Referências aprovadas de Landing Page

Esta pasta existe para receber **páginas que o gestor já olhou e aprovou** — não
inspiração genérica de Dribbble, não "LP bonita que vi na internet". A régua do
Squad é o que este cliente considera bom, e isso ninguém adivinha.

## O que colocar aqui

| Formato | Para que serve |
|---|---|
| `.png` / `.jpg` | captura da página inteira (desktop e mobile, dois arquivos) — é o que se compara |
| `.html` | a página, quando existir o arquivo. Permite ler decisão de composição, não só ver |
| `.pdf` | quando a referência veio como apresentação ou proposta |

Nome do arquivo diz de quem é e o que é:
`cliente-ou-marca__assunto__desktop.png`. Exemplo:
`gympass__captacao-plano-anual__mobile.png`.

Junto de cada referência, uma linha em [`NOTAS.md`](NOTAS.md) dizendo **por que ela
foi aprovada**: sem isso a referência é só uma imagem, e o próximo que abrir a
pasta vai copiar a coisa errada. "Aprovada" não é "bonita" — é o que o gestor
quer que se repita.

## Como o Squad usa

`engine/suficiencia.py` conta as referências disponíveis e imprime na linha
`REGUA` a cada checagem de piso. Hoje a pasta está vazia e o piso roda pelas oito
perguntas e pelas checagens mecânicas — que barram página com tarja de debug,
página sem imagem e mobile sem direção própria, mas **não** medem distância até um
padrão de qualidade combinado.

Referência não é gabarito: ninguém vai clonar layout. Ela entra como régua de
ambição — o patamar abaixo do qual a página não é entregue.

## O que NÃO entra

Material de cliente (fotografia, acervo, peça entregue) fica fora do git, como
sempre — regra 2 do `CLAUDE.md`. Se a referência é uma LP de cliente do próprio
gestor com fotografia dele dentro, deixe-a fora do repositório e aponte o caminho
local em `NOTAS.md`.
