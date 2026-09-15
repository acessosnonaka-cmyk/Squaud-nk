# Squad NK Web — v0.1

Interface de navegador para o Squad. O funcionário faz login, escolhe a ferramenta,
envia o arquivo, acompanha o processamento e baixa o resultado. Sem terminal, sem WSL,
sem Git, sem Claude Code.

**Esta versão é a espinha dorsal.** Um agente está integrado de ponta a ponta — o
Legend IA. Os outros cinco aparecem no dashboard marcados *EM BREVE*, sem nenhuma
integração simulada.

---

## Como subir

### Docker (recomendado — sobe igual em qualquer host)

```bash
git clone git@github.com:acessosnonaka-cmyk/Squaud-nk.git
cd Squaud-nk
cp .env.example .env
python3 -c "import secrets;print(secrets.token_urlsafe(48))"   # cole em SQUAD_WEB_SESSION_SECRET
# preencha também SQUAD_ADMIN_EMAIL e SQUAD_ADMIN_PASSWORD
docker compose up -d
```

Abra `http://127.0.0.1:8000`. O primeiro usuário é criado a partir do `.env` **apenas
enquanto não houver nenhum** — depois disso as duas variáveis são ignoradas.

```bash
docker compose logs -f worker      # acompanhar execução
docker compose down                # parar (os dados ficam no volume)
```

### Sem Docker (desenvolvimento)

```bash
python3 -m venv apps/web/.venv
apps/web/.venv/bin/pip install -r apps/web/requirements.txt
bash scripts/setup.sh                       # prepara o venv do Legend IA
cp .env.example .env                        # preencha o segredo de sessão
bash scripts/web-dev.sh start               # start | stop | restart | status | logs
```

Requer `ffmpeg` e `ffprobe` no PATH.

---

## Arquitetura

```
NAVEGADOR
   │
   ▼
┌─────────┐   enfileira    ┌──────────┐   subprocesso   ┌──────────────────┐
│   web   │ ─────────────► │  SQLite  │ ◄───────────── │      worker      │
│ FastAPI │   status/SSE   │   (WAL)  │    reivindica   │                  │
└─────────┘ ◄───────────── └──────────┘                 └────────┬─────────┘
                                                                 │ chama, sem duplicar
                                                                 ▼
                                                   apps/legend-ia/process_video.py
```

**O web nunca executa motor.** Ele autentica, valida, enfileira e mostra. Job de vídeo
leva minutos e não cabe numa request HTTP: quem executa é o worker.

**A fila é uma tabela**, não um broker. `BEGIN IMMEDIATE` serializa a reivindicação, então
dois workers nunca pegam o mesmo job nem furam o teto de concorrência. Sem Redis, sem Celery.

| Peça | Arquivo |
|---|---|
| Configuração (tudo por ambiente) | `apps/web/squadnk/config.py` |
| Banco, fila e artefatos | `apps/web/squadnk/db.py` |
| Login, scrypt, bootstrap | `apps/web/squadnk/auth.py` |
| Carregador de ferramentas (YAML → formulário e argv) | `apps/web/squadnk/registry.py` |
| Execução de um job | `apps/web/squadnk/runner.py` |
| Loop da fila | `apps/web/squadnk/worker.py` |
| Rotas e telas | `apps/web/squadnk/main.py` |
| Administração pela linha de comando | `apps/web/squadnk/cli.py` |

---

## Adicionar uma ferramenta: escreva um YAML

Nenhum endpoint por motor. O formulário, a validação, a linha de comando e a coleta de
artefatos saem todos da mesma declaração em `apps/web/tools/*.yaml`. Ver
`apps/web/tools/legend.editar.yaml` como referência viva.

Tipos de campo: `file`, `text`, `enum`, `bool`, `number`, `lines` (uma flag repetida por
linha — cobre `action="append"` do argparse).

Para o card aparecer no dashboard, acrescente a entrada em `apps/web/agents.yaml`. Um
agente só é mostrado como **DISPONÍVEL** quando o YAML de ferramenta existe de fato: não
há como marcar disponível algo que não está integrado.

---

## Como o Legend IA foi integrado sem duplicar o motor

`apps/legend-ia/process_video.py` **não foi tocado**. O que existe é uma declaração que
descreve como chamá-lo, e um runner que adapta o mundo ao contrato dele.

O contrato é restritivo de propósito: `resolve_video_path()` recusa qualquer arquivo fora
de `apps/legend-ia/`. Então o runner:

1. grava o upload em `$SQUAD_DATA_HOME/jobs/<job_id>/input/`;
2. copia para `apps/legend-ia/entrada de vídeo/<job_id>-<arquivo>`;
3. executa o motor com o caminho relativo que ele aceita;
4. move `entrega/<job_id>-<arquivo>_final.mp4` para `jobs/<job_id>/out/`;
5. apaga a cópia estagiada.

O carimbo `<job_id>` resolve uma colisão real: o motor grava
`entrega/<stem>_final.mp4`, então dois funcionários enviando `01.mp4` sobrescreveriam o
vídeo um do outro (docs/arquitetura-web.md §9). As duas pastas de trabalho já estão no
`.gitignore` e ficam vazias ao fim de cada job.

---

## Dados

Tudo que é de produção vive em `SQUAD_DATA_HOME`, **fora do repositório**:

```
$SQUAD_DATA_HOME/
  db.sqlite                     usuários, jobs, artefatos
  jobs/<job_id>/
     input/                     o que o funcionário enviou
     out/                       o que o motor produziu
     job.log                    saída completa da execução
```

No Docker é o volume `squad_data`; sem Docker, `~/.squad-nk` por padrão. O `.gitignore`
cobre `*.sqlite`, `/data/`, `data/` e as pastas de trabalho dos motores, para o caso de
alguém apontar `SQUAD_DATA_HOME` para dentro do clone.

---

## Segurança

| Medida | Como |
|---|---|
| Nada aberto sem login | middleware fecha **tudo** por padrão; só `/login` e `/static` passam |
| Senha nunca em texto puro | `scrypt` (n=2¹⁵, sal por usuário), ~110 ms por verificação |
| Login não vaza quais e-mails existem | e-mail inexistente gasta o mesmo tempo de um hash real |
| Sessão não forjável | cookie assinado; **o app recusa subir** sem `SQUAD_WEB_SESSION_SECRET` de 32+ caracteres |
| Credencial fora do Git | só `.env.example`, com nomes de variável e nenhum valor |
| Download sem diretório navegável | servido por **id de artefato** registrado no banco, nunca por caminho vindo do navegador, e só ao dono do job; o caminho resolvido ainda é conferido contra `out/` do próprio job |
| Upload não derruba a máquina | teto de tamanho aplicado durante a gravação, em blocos, sem carregar na memória |
| Formato validado de verdade | extensão **e** `ffprobe` — um `.mp4` pode ser qualquer coisa |
| Sem injeção de shell | o argv vai como lista para `subprocess`; nada é concatenado |
| Não derruba o host | tetos de concorrência por chave (`whisper`, `ffmpeg`, `chromium`) e global |

**O problema do `lp-serve` na 8090 não é reproduzido.** Aquele serviço expõe todos os
previews de todos os clientes sem autenticação, com a raiz listando os slugs. Aqui não
existe diretório servido: cada arquivo sai por uma rota autenticada que só entrega o que
está registrado no banco para aquele usuário.

Fora de escopo nesta versão, e por isso registrado: não há rate limit no login, nem CSRF
token, nem cadastro pela interface. São aceitáveis num MVP interno atrás de rede
confiável; deixam de ser quando a aplicação ganhar URL pública.

---

## Operação

| Ação | Comando |
|---|---|
| Criar usuário | `python -m squadnk.cli adduser pessoa@empresa.com` |
| Ver estado | `python -m squadnk.cli status` |
| Gerar segredo de sessão | `python -m squadnk.cli secret` |
| Logs | `docker compose logs -f worker` ou `bash scripts/web-dev.sh logs` |

No Docker: `docker compose exec web python -m squadnk.cli adduser pessoa@empresa.com`.

### Quando algo falha

O job vira `failed` e a página mostra a última linha útil do motor, com o log completo
logo abaixo. Se o worker for reiniciado no meio de uma execução, o job que ficava preso
em `running` é marcado como falha na subida seguinte — sem isso, um restart deixaria um
job fantasma ocupando slot de concorrência para sempre.

---

## O que ainda não funciona

- Apenas o **Legend IA** está integrado. Os outros cinco cards são informativos.
- Cada usuário vê **só os próprios jobs**. Não há visão de equipe nem papéis.
- Sem cancelamento de job pela interface, sem reprocessar com um clique, sem limpeza
  automática de jobs antigos.
- Sem HTTPS, sem domínio, sem exposição pública — roda em `127.0.0.1`.
- **Nenhum agente de LLM roda aqui.** Isso é a Etapa 2, e não está implementado.
