#!/usr/bin/env python3
"""CLI operacional do Diretor de Operações.

O Diretor continua sendo agente: ele interpreta, planeja, decide o grafo e
delega. Este CLI cuida do que não pode depender de memória de conversa —
persistência, estados, contratos, log e recuperação.

    demanda.py nova --cliente X --titulo T --descricao D
    demanda.py planejar DEM-... --plano "..."
    demanda.py job add DEM-... --agente designer --objetivo "..." --depende JOB-001
    demanda.py briefing DEM-... JOB-002
    demanda.py job concluir DEM-... JOB-002 --status concluido --resumo "..."
    demanda.py requisito add DEM-... --texto "5 criativos" --dono designer
    demanda.py gate DEM-...
    demanda.py retomar DEM-...
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

if __package__ in (None, ""):                      # permite rodar por caminho direto
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from engine import modelo, policy, roster    # type: ignore
else:
    from . import modelo, policy, roster


# --------------------------------------------------------------- saída

def p(texto: str = "") -> None:
    print(texto)


def cab(titulo: str) -> None:
    p(f"\n{titulo}\n" + "─" * min(len(titulo), 62))


# --------------------------------------------------------------- demanda

def cmd_nova(a) -> int:
    did = modelo.novo_id()
    d = {
        "id": did, "cliente": modelo.slug(a.cliente), "titulo": a.titulo,
        "descricao": a.descricao, "objetivo": a.objetivo or "",
        "contexto": a.contexto or "", "prioridade": a.prioridade,
        "status": "RECEBIDA", "plano": "", "agentes": [], "jobs": [],
        "resultados": [], "pendencias": [], "aprovacoes": [], "feedback": [],
        "requisitos": [], "alteracoes": [],
        "criada_em": modelo.agora(), "atualizada_em": modelo.agora(),
    }
    modelo.salvar(d)
    modelo.registrar_evento(did, "DEMANDA_CRIADA", resumo=f"{a.titulo} · cliente {d['cliente']}")
    p(did)
    return 0


def cmd_listar(a) -> int:
    ds = modelo.listar()
    if a.status:
        ds = [d for d in ds if d["status"] == a.status.upper()]
    if not ds:
        p("  nenhuma demanda"); return 0
    cab(f"DEMANDAS ({len(ds)})")
    for d in ds:
        pend = sum(1 for x in d.get("aprovacoes", []) if x["status"] == "PENDENTE")
        jobs = d.get("jobs", [])
        feitos = sum(1 for j in jobs if j["status"] == "CONCLUIDO")
        p(f"  {d['id']}  {d['status']:<21} {d['cliente']:<18} "
          f"jobs {feitos}/{len(jobs)}"
          f"{'  ⚠ ' + str(pend) + ' aprovação(ões) pendente(s)' if pend else ''}")
        p(f"              {d['titulo'][:70]}")
    return 0


def cmd_ver(a) -> int:
    d = modelo.carregar(a.demanda)
    cab(f"{d['id']} · {d['titulo']}")
    p(f"  cliente     {d['cliente']}")
    p(f"  status      {d['status']}")
    p(f"  prioridade  {d.get('prioridade','normal')}")
    p(f"  criada em   {d['criada_em']}")
    if d.get("objetivo"): p(f"  objetivo    {d['objetivo']}")
    if d.get("contexto"): p(f"  contexto    {d['contexto'][:200]}")
    if d.get("plano"):    p(f"  plano       {d['plano'][:300]}")
    if d.get("bloqueio"): p(f"  BLOQUEIO    {d['bloqueio']}")
    if d.get("jobs"):
        cab("JOBS")
        for j in d["jobs"]:
            dep = f" ← {', '.join(j['dependencias'])}" if j.get("dependencias") else ""
            tent = f" [{j['tentativas']}/{j.get('max_tentativas', modelo.MAX_TENTATIVAS)}]" if j.get("tentativas") else ""
            p(f"  {j['id']}  {j['status']:<21} {j['agente']:<20}{tent}{dep}")
            p(f"           {j['objetivo'][:66]}")
    pend = [x for x in d.get("aprovacoes", []) if x["status"] == "PENDENTE"]
    if pend:
        cab("APROVAÇÕES PENDENTES")
        for x in pend:
            p(f"  {x['id']}  {x['acao']}")
            p(f"          motivo: {x['motivo']}")
    if d.get("feedback"):
        cab("FEEDBACK")
        for f in d["feedback"]:
            p(f"  [{f['classe']}] {f['texto'][:70]}")
    return 0


def cmd_planejar(a) -> int:
    d = modelo.carregar(a.demanda)
    if a.plano:
        d["plano"] = a.plano
    modelo.transitar(d, "PLANEJADA", motivo=a.plano or "")
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], "PLANO_CRIADO", resumo=(a.plano or "")[:200])
    p(f"  {d['id']} -> PLANEJADA")
    return 0


def _mudar_status(a, novo: str, motivo_campo: str | None = None) -> int:
    d = modelo.carregar(a.demanda)
    motivo = getattr(a, "motivo", "") or ""
    if motivo_campo:
        d[motivo_campo] = motivo
    if novo == "CONCLUIDA":
        # CONCLUIDA não é um rótulo que se aplica: é o que sobra quando nada
        # trava. Recalculado aqui, e não só em cmd_concluir, para que nenhum
        # caminho futuro consiga chegar a este estado por fora do gate.
        trava = avaliar_gate(d)
        if trava:
            p(formatar_gate(d, trava))
            raise modelo.ErroDeEstado(
                f"{d['id']} não pode ir para CONCLUIDA: {len(trava)} condição(ões) aberta(s). "
                "O estado final decorre do gate, não o contrário.")
    modelo.transitar(d, novo, motivo=motivo)
    if novo == "CONCLUIDA":
        d["concluida_em"] = modelo.agora()
    modelo.salvar(d)
    p(f"  {d['id']} -> {novo}")
    return 0


# --------------------------------------------------------------- jobs

def cmd_job_add(a) -> int:
    d = modelo.carregar(a.demanda)
    if d["status"] == "RECEBIDA":
        raise modelo.ErroDeEstado(
            "planeje a demanda antes de criar jobs: demanda.py planejar <ID> --plano \"...\"")
    acionaveis = modelo.agentes_acionaveis()
    if a.agente not in acionaveis:
        no_roster = roster.por_id(a.agente) or roster.por_subagent_type(a.agente)
        if no_roster and no_roster.get("agente") == "conceito":
            raise modelo.ErroDeEstado(
                f"'{a.agente}' está no roster como CONCEITO: papel definido, implementação "
                "ausente. Não existe executor para receber este job. Declare a lacuna ao "
                "gestor humano em vez de abrir job que ninguém roda — docs/gestor-de-trafego.md.")
        raise modelo.ErroDeEstado(
            f"agente '{a.agente}' não é acionável. Acionáveis hoje: {', '.join(acionaveis)}")
    jid = modelo.proximo_job_id(d)
    deps = a.depende or []
    modelo.validar_dependencias(d, deps, jid)
    job = {
        "id": jid, "demanda_id": d["id"], "agente": a.agente, "objetivo": a.objetivo,
        "entrada": a.entrada or "", "saida_esperada": a.saida or "",
        "criterios": a.criterio or [], "restricoes": a.restricao or [],
        "dependencias": deps, "fontes": _validar_fontes(d["cliente"], a.fonte or []),
        "status": "PENDENTE", "tentativas": 0,
        "max_tentativas": modelo.MAX_TENTATIVAS, "resultado": None, "erro": None,
        "criado_em": modelo.agora(),
    }
    erros = modelo.validar(job, "job")
    if erros:
        raise modelo.ErroDeEstado("job inválido: " + "; ".join(erros))
    d.setdefault("jobs", []).append(job)
    if a.agente not in d.get("agentes", []):
        d.setdefault("agentes", []).append(a.agente)
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], "JOB_CRIADO", agente=a.agente, job=jid,
                            resumo=a.objetivo[:160])
    p(jid)
    return 0


def cmd_job_elegiveis(a) -> int:
    d = modelo.carregar(a.demanda)
    prontos = modelo.elegiveis(d)
    if prontos:
        cab("PRONTOS PARA DELEGAR AGORA")
        for j in prontos:
            p(f"  {j['id']}  {j['agente']:<20} {j['objetivo'][:56]}")
    else:
        p("  nenhum job elegível agora")
    travados = modelo.bloqueados_por_dependencia(d)
    if travados:
        cab("AGUARDANDO DEPENDÊNCIA")
        for j, faltam in travados:
            p(f"  {j['id']}  {j['agente']:<20} espera {', '.join(faltam)}")
    return 0


def cmd_briefing(a) -> int:
    """Gera o contrato DIRETOR -> ESPECIALISTA e o grava no disco."""
    d = modelo.carregar(a.demanda)
    j = modelo.achar_job(d, a.job)
    por_id = {x["id"]: x for x in d.get("jobs", [])}

    faltam = [x for x in (j.get("dependencias") or [])
              if por_id.get(x, {}).get("status") != "CONCLUIDO"]
    if faltam and not a.forcar:
        raise modelo.ErroDeEstado(
            f"{j['id']} depende de {', '.join(faltam)}, que ainda não concluíram. "
            "Use --forcar só se souber o que está fazendo.")

    arquivos, entrada_deps = [], []
    for dep in (j.get("dependencias") or []):
        r = (por_id.get(dep) or {}).get("resultado") or {}
        arquivos += r.get("artefatos") or []
        if r.get("resumo"):
            entrada_deps.append(f"[{dep} · {por_id[dep]['agente']}] {r['resumo']}")

    mem = dir_memoria_cliente(d["cliente"])
    feedback_job = [f for f in d.get("feedback", []) if f.get("job") == j["id"]]
    ctx = modelo.contexto_cliente(d["cliente"], j.get("fontes") or [])

    briefing = {
        "demanda": d["id"], "job": j["id"], "cliente": d["cliente"],
        "agente": j["agente"], "objetivo": d.get("objetivo") or d["titulo"],
        "contexto": d.get("contexto", ""), "tarefa": j["objetivo"],
        "entrada_disponivel": "\n".join([j.get("entrada", "")] + entrada_deps).strip(),
        "restricoes": j.get("restricoes") or [],
        "resultado_esperado": j.get("saida_esperada") or "",
        "arquivos": arquivos, "dependencias": j.get("dependencias") or [],
        "criterios_conclusao": j.get("criterios") or [],
        "memoria_cliente": mem, "feedback_anterior": [f["texto"] for f in feedback_job],
        "requisitos": [f"{r['id']} {r['texto']}" for r in d.get("requisitos", [])
                       if r.get("job") == j["id"]
                       or (not r.get("job") and r.get("dono") == j["agente"])],
        "base_externa": ctx["base_externa"],
        "fontes_canonicas": ctx["fontes_canonicas"],
        "referencias_nao_canonicas": ctx["referencias_nao_canonicas"],
        "nao_estabelecido": ctx.get("nao_estabelecido") or [],
        "tentativa": j.get("tentativas", 0) + 1, "gerado_em": modelo.agora(),
        "execution_mode": modelo.EXECUTION_MODE_PADRAO,
    }
    erros = modelo.validar(briefing, "briefing")
    if erros:
        raise modelo.ErroDeEstado("briefing inválido: " + "; ".join(erros))

    destino = modelo.dir_demanda(d["id"]) / "handoffs" / f"{j['id']}.briefing.json"
    modelo.gravar_json(destino, briefing)
    modelo.registrar_evento(d["id"], "HANDOFF_REALIZADO", agente=j["agente"], job=j["id"],
                            resumo=f"briefing gerado (tentativa {briefing['tentativa']})")
    if a.json:
        p(json.dumps(briefing, ensure_ascii=False, indent=2))
    else:
        p(formatar_briefing(briefing))
        p(f"  (gravado em {destino})")
    return 0


def formatar_briefing(b: dict) -> str:
    linhas = [
        f"\n═══ BRIEFING · {b['demanda']} · {b['job']} · para {b['agente'].upper()} ═══",
        f"CLIENTE            {b['cliente']}",
        f"OBJETIVO DA DEMANDA {b['objetivo']}",
    ]
    if b.get("contexto"):
        linhas.append(f"CONTEXTO           {b['contexto']}")
    linhas.append(f"TAREFA             {b['tarefa']}")
    if b.get("entrada_disponivel"):
        linhas.append(f"ENTRADA            {b['entrada_disponivel']}")
    if b.get("arquivos"):
        linhas.append("ARQUIVOS           " + "\n                   ".join(b["arquivos"]))
    if b.get("restricoes"):
        linhas.append("RESTRIÇÕES         " + "\n                   ".join(b["restricoes"]))
    linhas.append(f"RESULTADO ESPERADO {b['resultado_esperado']}")
    if b.get("criterios_conclusao"):
        linhas.append("CRITÉRIOS          " + "\n                   ".join(b["criterios_conclusao"]))
    if b.get("requisitos"):
        linhas.append("REQUISITOS DO PEDIDO " + "\n                     ".join(b["requisitos"]))
    if b.get("memoria_cliente"):
        linhas.append(f"MEMÓRIA DO CLIENTE {b['memoria_cliente'][:400]}")
    if b.get("base_externa"):
        linhas.append(f"ACERVO DO CLIENTE  {b['base_externa']}")
    if b.get("fontes_canonicas"):
        linhas.append("SOURCE OF TRUTH    " + "\n                   ".join(b["fontes_canonicas"]))
    if b.get("referencias_nao_canonicas"):
        linhas.append("REFERÊNCIA (NÃO É VERDADE ATUAL — o pedido original e a instrução "
                      "atual prevalecem)\n                   "
                      + "\n                   ".join(b["referencias_nao_canonicas"]))
    if b.get("nao_estabelecido"):
        linhas.append("NÃO ESTABELECIDO   (ninguém verificou, ou não deu para acessar. "
                      "NÃO é ausência e NÃO é fato.\n"
                      "                   Precisando disto para produzir, peça a verificação "
                      "em vez de assumir)\n                   "
                      + "\n                   ".join(b["nao_estabelecido"]))
    if b.get("feedback_anterior"):
        linhas.append("JÁ REPROVADO ANTES " + "\n                   ".join(b["feedback_anterior"]))
    linhas.append(f"TENTATIVA          {b['tentativa']}")
    linhas.append(f"EXECUTION_MODE     {b.get('execution_mode', modelo.EXECUTION_MODE_PADRAO)}"
                  "  — execute sem narrar etapa, handoff ou progresso")
    linhas.append("═" * 62)
    return "\n".join(linhas)


def _barrar_por_dependencia(d: dict, j: dict, verbo: str) -> None:
    """Dependência é trava, não sugestão.

    O grafo existe para que o job dependente receba os artefatos do anterior.
    Deixar `iniciar` e `concluir` passarem com dependência aberta faz o briefing
    sair sem esses artefatos — que é exatamente o que a aresta existia para
    impedir. A checagem mora aqui, em cada comando, e não na listagem de
    elegíveis: ninguém é obrigado a ter consultado a listagem antes.
    """
    abertas = modelo.dependencias_abertas(d, j)
    if not abertas:
        return
    linhas = "\n".join(f"    {dep}  {estado}" for dep, estado in abertas)
    raise modelo.ErroDeEstado(
        f"{j['id']} ({j['agente']}) não pode {verbo}: dependência aberta.\n"
        f"  job solicitado: {j['id']} — {(j.get('objetivo') or '')[:70]}\n"
        f"  dependências abertas ({len(abertas)}):\n{linhas}\n"
        "  Conclua a dependência primeiro, ou remova a aresta conscientemente.")


def cmd_job_iniciar(a) -> int:
    d = modelo.carregar(a.demanda)
    j = modelo.achar_job(d, a.job)
    if j["status"] not in ("PENDENTE", "FALHOU"):
        raise modelo.ErroDeEstado(f"{j['id']} está {j['status']}; só se inicia PENDENTE ou FALHOU")
    _barrar_por_dependencia(d, j, "iniciar")
    j["tentativas"] = j.get("tentativas", 0) + 1
    if j["tentativas"] > j.get("max_tentativas", modelo.MAX_TENTATIVAS):
        j["status"] = "BLOQUEADO"
        j["erro"] = f"teto de {j.get('max_tentativas')} tentativas atingido"
        modelo.salvar(d)
        modelo.registrar_evento(d["id"], "JOB_BLOQUEADO", agente=j["agente"], job=j["id"],
                                resumo=j["erro"])
        p(f"  {j['id']} BLOQUEADO — {j['erro']}.")
        p("  O Diretor precisa corrigir o briefing ou escalar ao gestor humano.")
        return 2
    j["status"] = "EM_EXECUCAO"
    j["iniciado_em"] = modelo.agora()
    if d["status"] in ("PLANEJADA", "EM_REVISAO", "AGUARDANDO_APROVACAO"):
        modelo.transitar(d, "EM_EXECUCAO")
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], "JOB_INICIADO", agente=j["agente"], job=j["id"],
                            resumo=f"tentativa {j['tentativas']}")
    p(f"  {j['id']} EM_EXECUCAO (tentativa {j['tentativas']})")
    return 0


def cmd_job_concluir(a) -> int:
    d = modelo.carregar(a.demanda)
    j = modelo.achar_job(d, a.job)
    if j["status"] == "CONCLUIDO":
        p(f"  {j['id']} já está CONCLUIDO — nada refeito.")
        return 0
    _barrar_por_dependencia(d, j, "concluir")

    antes = {x["id"] for x in modelo.elegiveis(d)}
    retorno = modelo.ler_json(pathlib.Path(a.retorno)) if a.retorno else {
        "status": a.status, "resumo": a.resumo or "",
        "artefatos": a.artefato or [], "decisoes": a.decisao or [],
        "observacoes": a.observacao or "", "proximo_passo": a.proximo or "",
        "pendencia": a.pendencia or "",
    }
    retorno.setdefault("agente", j["agente"])
    retorno.setdefault("em", modelo.agora())
    erros = modelo.validar(retorno, "retorno")
    if retorno.get("status") != "concluido" and not retorno.get("pendencia"):
        erros.append("status diferente de 'concluido' exige o campo 'pendencia'")
    if erros:
        raise modelo.ErroDeEstado("retorno inválido: " + "; ".join(erros))

    modelo.gravar_json(modelo.dir_demanda(d["id"]) / "handoffs" / f"{j['id']}.retorno.json", retorno)
    j["resultado"] = retorno

    mapa = {"concluido": "CONCLUIDO", "falhou": "FALHOU", "bloqueado": "BLOQUEADO",
            "precisa_de_informacao": "BLOQUEADO", "precisa_de_aprovacao": "AGUARDANDO_APROVACAO"}
    j["status"] = mapa[retorno["status"]]
    j["concluido_em"] = modelo.agora()
    if j["status"] != "CONCLUIDO":
        j["erro"] = retorno.get("pendencia", "")
        d.setdefault("pendencias", []).append(
            {"job": j["id"], "agente": j["agente"], "texto": retorno.get("pendencia", ""),
             "em": modelo.agora()})
    else:
        d.setdefault("resultados", []).append(
            {"job": j["id"], "agente": j["agente"], "resumo": retorno["resumo"],
             "artefatos": retorno.get("artefatos", []), "em": modelo.agora()})

    evento = {"CONCLUIDO": "JOB_CONCLUIDO", "FALHOU": "JOB_FALHOU",
              "BLOQUEADO": "JOB_BLOQUEADO", "AGUARDANDO_APROVACAO": "APROVACAO_SOLICITADA"}[j["status"]]
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], evento, agente=j["agente"], job=j["id"],
                            resumo=retorno.get("resumo") or retorno.get("pendencia", ""))
    p(f"  {j['id']} -> {j['status']}")
    # "liberou" é o delta, não a foto: job que já estava elegível antes não foi
    # liberado por este. Dizer que foi induz o runtime a achar que respeitou a
    # ordem quando não respeitou.
    depois = {x["id"] for x in modelo.elegiveis(d)}
    liberados = [x for x in modelo.elegiveis(d)
                 if x["id"] in (depois - antes) and j["id"] in (x.get("dependencias") or [])]
    if liberados:
        p("  liberou: " + ", ".join(f"{x['id']} ({x['agente']})" for x in liberados))
    return 0


def cmd_job_falhar(a) -> int:
    d = modelo.carregar(a.demanda)
    j = modelo.achar_job(d, a.job)
    j["status"] = "FALHOU"
    j["erro"] = a.erro
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], "JOB_FALHOU", agente=j["agente"], job=j["id"], resumo=a.erro)
    restam = j.get("max_tentativas", modelo.MAX_TENTATIVAS) - j.get("tentativas", 0)
    p(f"  {j['id']} -> FALHOU · {a.erro}")
    p(f"  tentativas restantes: {max(restam, 0)}")
    return 0


def cmd_job_reprocessar(a) -> int:
    d = modelo.carregar(a.demanda)
    j = modelo.achar_job(d, a.job)
    if j["status"] not in ("FALHOU", "CONCLUIDO", "BLOQUEADO"):
        raise modelo.ErroDeEstado(f"{j['id']} está {j['status']}; reprocesse FALHOU, CONCLUIDO ou BLOQUEADO")
    if j.get("tentativas", 0) >= j.get("max_tentativas", modelo.MAX_TENTATIVAS):
        raise modelo.ErroDeEstado(
            f"{j['id']} já usou {j['tentativas']} de {j.get('max_tentativas')} tentativas. "
            "Corrija o briefing e aumente o teto conscientemente, ou escale ao gestor humano.")
    j["status"] = "PENDENTE"
    j["erro"] = None
    if a.corrigir:
        j["objetivo"] = j["objetivo"] + f"\n[correção pedida] {a.corrigir}"
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], "JOB_REPROCESSADO", agente=j["agente"], job=j["id"],
                            resumo=a.corrigir or "novo ciclo")
    p(f"  {j['id']} -> PENDENTE (ciclo {j.get('tentativas',0)+1})")
    return 0


# ------------------------------------- trava de entrada e de saída: requisitos

DONOS_FORA_DO_SQUAD = ("diretor", "gestor-humano")


def _validar_dono(nome: str) -> dict | None:
    """Todo requisito tem dono. Devolve o agente do roster, ou None se o dono é
    o próprio Diretor ou o gestor humano — os dois únicos donos que não são
    especialistas."""
    if nome in DONOS_FORA_DO_SQUAD:
        return None
    agente = roster.por_subagent_type(nome) or roster.por_id(nome)
    if agente is None:
        raise modelo.ErroDeEstado(
            f"dono '{nome}' não existe. Use um especialista acionável "
            f"({', '.join(modelo.agentes_acionaveis())}) ou {', '.join(DONOS_FORA_DO_SQUAD)}.")
    return agente


def cmd_requisito_add(a) -> int:
    """Um item do REQUEST_CHECKLIST: o que o gestor pediu, com dono."""
    d = modelo.carregar(a.demanda)
    agente = _validar_dono(a.dono)
    if a.job:
        modelo.achar_job(d, a.job)
    req = {"id": modelo.proximo_requisito_id(d), "texto": a.texto, "dono": a.dono,
           "job": a.job, "estado": "PENDENTE", "evidencia": "", "motivo": "",
           "em": modelo.agora()}
    d.setdefault("requisitos", []).append(req)
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], "REQUISITO_REGISTRADO", job=a.job,
                            resumo=f"{req['id']} ({a.dono}): {a.texto[:120]}")
    p(req["id"])
    if agente is not None and agente.get("agente") == "conceito":
        p(f"  ⚠ {a.dono} não tem executor: este requisito só fecha como BLOQUEADO.")
    return 0


def cmd_requisito_estado(a) -> int:
    d = modelo.carregar(a.demanda)
    r = modelo.achar_requisito(d, a.requisito)
    estado = a.estado.upper()
    if estado not in modelo.ESTADOS_REQUISITO:
        raise modelo.ErroDeEstado(f"estado inválido. Use: {', '.join(modelo.ESTADOS_REQUISITO)}")
    if estado == "CUMPRIDO" and not a.evidencia:
        raise modelo.ErroDeEstado(
            "CUMPRIDO exige --evidencia: o job, o arquivo ou o link que prova a entrega. "
            "Sem evidência é 'provavelmente cumprido', que não existe.")
    if estado in ("BLOQUEADO", "NAO_APLICAVEL", "CANCELADO") and not a.motivo:
        raise modelo.ErroDeEstado(f"{estado} exige --motivo.")
    agente = _validar_dono(r["dono"])
    if estado == "CUMPRIDO" and agente is not None and agente.get("agente") == "conceito":
        raise modelo.ErroDeEstado(
            f"{r['id']} é de '{r['dono']}', que não tem executor no Squad. Ninguém executou "
            "isso: marque BLOQUEADO com o motivo e devolva a decisão ao gestor humano.")
    r["estado"] = estado
    r["evidencia"] = a.evidencia or r.get("evidencia", "")
    r["motivo"] = a.motivo or r.get("motivo", "")
    r["decidido_em"] = modelo.agora()
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], "REQUISITO_ATUALIZADO", job=r.get("job"),
                            resumo=f"{r['id']} -> {estado}")
    p(f"  {r['id']} -> {estado}")
    return 0


def cmd_requisito_listar(a) -> int:
    d = modelo.carregar(a.demanda)
    reqs = d.get("requisitos", [])
    if not reqs:
        p("  REQUEST_CHECKLIST vazio"); return 0
    cab(f"REQUEST_CHECKLIST · {d['id']} ({len(reqs)})")
    for r in reqs:
        job = f" [{r['job']}]" if r.get("job") else ""
        p(f"  {r['id']}  {r['estado']:<14} {r['dono']:<18}{job} {r['texto'][:52]}")
        prova = r.get("evidencia") or r.get("motivo")
        if prova:
            p(f"           {prova[:70]}")
    return 0


def cmd_alteracao(a) -> int:
    """Mudança do gestor durante a execução. Entra ao lado do original, nunca por cima."""
    d = modelo.carregar(a.demanda)
    for req in (a.afeta or []):
        modelo.achar_requisito(d, req)
    alt = {"id": modelo.proxima_alteracao_id(d), "texto": a.texto,
           "afeta": a.afeta or [], "em": modelo.agora()}
    d.setdefault("alteracoes", []).append(alt)
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], "DEMANDA_ALTERADA", resumo=f"{alt['id']}: {a.texto[:140]}")
    p(alt["id"])
    p("  o pedido original continua valendo no que não foi alterado.")
    return 0


# ------------------------------------- FINAL_REQUEST_GATE

def avaliar_gate(d: dict) -> list:
    """O que impede fechar a demanda. Lista vazia é a única autorização para entregar."""
    trava = []
    reqs = d.get("requisitos", [])
    if not reqs:
        trava.append("REQUEST_CHECKLIST vazio: nenhum requisito foi extraído do pedido "
                     "original. Sem checklist não há o que conferir.")
    pendentes = [r for r in reqs if r["estado"] == "PENDENTE"]
    for r in pendentes:
        trava.append(f"{r['id']} ainda PENDENTE ({r['dono']}): {r['texto'][:70]}")
    sem_prova = [r for r in reqs if r["estado"] == "CUMPRIDO" and not r.get("evidencia")]
    for r in sem_prova:
        trava.append(f"{r['id']} está CUMPRIDO sem evidência: {r['texto'][:70]}")
    abertos = [j for j in d.get("jobs", []) if j["status"] != "CONCLUIDO"]
    for j in abertos:
        trava.append(f"{j['id']} ({j['agente']}) está {j['status']}, não CONCLUIDO")
    for x in d.get("aprovacoes", []):
        if x["status"] == "PENDENTE":
            trava.append(f"{x['id']} espera aprovação humana: {x['acao'][:60]}")
    for c in d.get("consultas", []):
        if c["status"] == "PENDENTE":
            trava.append(f"{c['id']} ({c['agente']}) pediu dado de {c['fonte']} e não recebeu: "
                         f"{c['pergunta'][:60]}")
    trava += _revisoes_faltando(d)
    trava += _piso_lp_faltando(d)
    return trava


# Extensões que caracterizam peça pronta para o olho de alguém. A regra olha o
# artefato, não o nome do agente: transcrição em .json do Legend é insumo e não
# precisa de parecer; o .mp4 finalizado precisa. Job de copy e de tráfego não
# produz nada desta lista e segue sem Revisor, como sempre foi.
EXT_PECA = (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov")

# Página é peça. Ficou de fora até a LP da Academia Mergulho sair com tarja de
# debug sobre o H1 e sem uma única fotografia: o QA da LP mede engenharia e
# passou tudo verde, o gate conferia conformidade com a Source of Truth e a SoT
# estava errada, e ninguém nunca olhou a página. Desde então .html exige parecer
# de Revisor igual a um .png — e, diferente do .png, exige também o piso de
# suficiência e a captura assinada (ver _piso_lp_faltando).
EXT_PAGINA = (".html", ".htm")
AGENTE_REVISOR = "revisor-de-criacao"


def _revisoes_faltando(d: dict) -> list:
    """Peça visual concluída sem parecer de Revisor vinculado a ela.

    Parecer que existe mas não está preso ao job que produziu a peça não conta:
    o gate precisa saber qual parecer olhou qual peça.
    """
    jobs = d.get("jobs", [])
    revisores = [j for j in jobs if j["agente"] == AGENTE_REVISOR]
    trava = []
    for j in jobs:
        if j["agente"] == AGENTE_REVISOR or j["status"] != "CONCLUIDO":
            continue
        arte = [a for a in ((j.get("resultado") or {}).get("artefatos") or [])
                if str(a).lower().endswith(EXT_PECA + EXT_PAGINA)]
        if not arte:
            continue
        ligados = [r for r in revisores if j["id"] in (r.get("dependencias") or [])]
        if not ligados:
            trava.append(f"{j['id']} ({j['agente']}) entregou peça ({len(arte)} arquivo(s)) "
                         f"e nenhum job de {AGENTE_REVISOR} depende dele: revisão obrigatória ausente")
        elif not any(r["status"] == "CONCLUIDO" for r in ligados):
            estados = ", ".join(f"{r['id']} {r['status']}" for r in ligados)
            trava.append(f"{j['id']} ({j['agente']}) entregou peça e a revisão não terminou: {estados}")
    return trava


ENGINE_LP = pathlib.Path(__file__).resolve().parents[3] / "apps" / "lp-builder" / "engine"


def _motores_lp():
    """(suficiencia, render) do LP Builder, ou (None, None) se o runtime não está aqui.

    O Diretor não implementa o piso da LP — ele o cobra. O piso mora no agente
    que constrói a página, e o gate só se recusa a fechar sem ele.
    """
    try:
        import importlib.util as iu
        mods = []
        for nome in ("suficiencia", "render"):
            spec = iu.spec_from_file_location(f"lp_{nome}", ENGINE_LP / f"{nome}.py")
            if spec is None or spec.loader is None:
                return None, None
            m = iu.module_from_spec(spec)
            spec.loader.exec_module(m)
            mods.append(m)
        return mods[0], mods[1]
    except Exception:
        return None, None


def _piso_lp_faltando(d: dict) -> list:
    """Página concluída sem piso de suficiência ou sem captura assinada.

    Três coisas que o lp_qa.py nunca mediu e que o gestor pagou:
      1. a página existe no disco onde o job disse que existe;
      2. ela passa o piso de suficiência (marca de debug, imagem, mobile próprio,
         e as oito perguntas respondidas de forma que dê para discordar);
      3. existe captura desktop + mobile da VERSÃO ATUAL do arquivo, e o parecer
         do Revisor cita essa captura.

    Nada aqui é opinião sobre a página — é a prova de que alguém olhou a página
    certa. O julgamento continua sendo do Revisor.
    """
    jobs = d.get("jobs", [])
    revisores = [j for j in jobs if j["agente"] == AGENTE_REVISOR]
    trava = []
    for j in jobs:
        if j["agente"] == AGENTE_REVISOR or j["status"] != "CONCLUIDO":
            continue
        arts = [str(x) for x in ((j.get("resultado") or {}).get("artefatos") or [])]
        paginas = [a for a in arts if a.lower().endswith(EXT_PAGINA)]
        if not paginas:
            continue

        piso, render = _motores_lp()
        if piso is None:
            trava.append(f"{j['id']} entregou página e o piso da LP não pôde ser verificado: "
                         f"{ENGINE_LP} ausente. Runtime que falta é BLOQUEADO declarado, "
                         "não passagem livre — rode bash scripts/setup.sh")
            continue

        for pag in paginas:
            alvo = pathlib.Path(pag).expanduser()
            if not alvo.is_file():
                trava.append(f"{j['id']} declarou a página {pag} e ela não está no disco: "
                             "artefato que só existe no retorno não existe")
                continue

            respostas = [a for a in arts if a.lower().endswith("suficiencia.json")]
            if not respostas:
                trava.append(f"{j['id']} entregou {alvo.name} sem suficiencia.json: as oito "
                             "perguntas do piso da LP não foram respondidas "
                             "(suficiencia.py schema)")
            else:
                falhas, _ = piso.checar_mecanico(alvo.read_text(encoding="utf-8", errors="replace"))
                try:
                    falhas += piso.checar_respostas(
                        modelo.ler_json(pathlib.Path(respostas[0]).expanduser()))
                except Exception as e:
                    falhas.append(f"suficiencia.json ilegível: {str(e)[:80]}")
                for f in falhas[:6]:
                    trava.append(f"{j['id']} piso da LP · {f[:150]}")

            mans = [a for a in arts if a.lower().endswith("render.json")]
            if not mans:
                trava.append(f"{j['id']} entregou {alvo.name} sem render.json: sem captura "
                             "desktop e mobile ninguém pode ter visto a página "
                             "(render.py --pagina)")
                continue
            for pb in render.verificar(pathlib.Path(mans[0]).expanduser()):
                trava.append(f"{j['id']} captura · {pb[:150]}")

            vistos = [r for r in revisores if j["id"] in (r.get("dependencias") or [])
                      and r["status"] == "CONCLUIDO"]
            for r in vistos:
                ra = [str(x).lower() for x in ((r.get("resultado") or {}).get("artefatos") or [])]
                rt = ((r.get("resultado") or {}).get("resumo") or "").lower() + " " + " ".join(ra)
                if not any(k in rt for k in ("render.json", "desktop.png", "mobile.png",
                                             "desktop", "mobile")):
                    trava.append(f"{r['id']} deu parecer sobre {alvo.name} sem citar a captura "
                                 "desktop ou mobile: parecer que não nomeia o que abriu é "
                                 "parecer sobre o HTML")
    return trava


def formatar_gate(d: dict, trava: list) -> str:
    reqs = d.get("requisitos", [])
    por_estado = {e: [r for r in reqs if r["estado"] == e] for e in modelo.ESTADOS_REQUISITO}
    linhas = [f"\n═══ FINAL_REQUEST_GATE · {d['id']} ═══",
              "PEDIDO ORIGINAL (imutável)",
              "  " + (d.get("descricao") or "").strip().replace("\n", "\n  ")]
    if d.get("alteracoes"):
        linhas.append("ALTERAÇÕES POSTERIORES")
        for alt in d["alteracoes"]:
            alvo = f" (afeta {', '.join(alt['afeta'])})" if alt.get("afeta") else ""
            linhas.append(f"  {alt['id']} [{alt['em'][:10]}]{alvo} {alt['texto']}")
    linhas.append("CHECKLIST  " + "  ".join(
        f"{e.lower()} {len(por_estado[e])}" for e in modelo.ESTADOS_REQUISITO))
    for r in reqs:
        marca = {"CUMPRIDO": "✓", "PENDENTE": "·", "BLOQUEADO": "⏸",
                 "NAO_APLICAVEL": "—", "CANCELADO": "✗"}[r["estado"]]
        prova = r.get("evidencia") or r.get("motivo") or ""
        linhas.append(f"  {marca} {r['id']} {r['dono']:<18} {r['texto'][:44]}"
                      + (f"  · {prova[:40]}" if prova else ""))
    if trava:
        linhas.append("NÃO FECHA — o que falta:")
        linhas += [f"  ✗ {x}" for x in trava]
        linhas.append("Reabra o job certo, corrija e rode o gate de novo.")
    else:
        linhas.append("LIBERADO: todo requisito tem estado, todo job terminou, "
                      "nenhuma aprovação pendente.")
    sem_dado = [c for c in d.get("consultas", []) if c["status"] == "SEM_DADO"]
    if sem_dado:
        # Não trava — mas o Diretor não entrega sem saber sobre o que NÃO se sabe.
        linhas.append("LACUNA DECLARADA — dado que o Squad pediu e não existe:")
        for c in sem_dado:
            linhas.append(f"  ○ {c['id']} [{c['fonte']}] {c['pergunta'][:52]}"
                          f"  · {(c.get('observacao') or '')[:60]}")
        linhas.append("  Isto entra na entrega como lacuna, não sai calado.")
    linhas.append("═" * 62)
    return "\n".join(linhas)


# ------------------------------------------- consulta: o especialista pergunta

# A plataforma não dá conector MCP a subagente. Provado na autópsia: o Gestor de
# Tráfego fez zero chamadas ao Meta em todas as execuções, porque a declaração
# dele é `Read, Grep, Glob, Bash, Write, Edit, WebSearch, WebFetch, Skill`.
# Resultado: ele analisava o que o runtime tivesse colado, e o teto analítico
# dele era o teto da minha extração.
#
# Isto inverte a direção. O especialista escreve QUAL corte precisa e POR QUE,
# o runtime executa o conector como I/O e devolve o dado bruto. Quem escolhe a
# análise continua sendo o especialista; quem tem a tomada continua sendo o
# runtime. Nenhum dos dois faz o trabalho do outro.
FONTES_CONSULTA = ["meta_ads", "google_ads", "tiktok_ads", "ga4", "drive", "crm", "outra"]


def cmd_consulta_abrir(a) -> int:
    d = modelo.carregar(a.demanda)
    j = modelo.achar_job(d, a.job)
    if a.fonte not in FONTES_CONSULTA:
        raise modelo.ErroDeEstado(f"fonte inválida. Use: {', '.join(FONTES_CONSULTA)}")
    if len((a.pergunta or "").strip()) < 25:
        raise modelo.ErroDeEstado(
            "a consulta precisa dizer O QUE se quer descobrir, não só qual tabela puxar.\n"
            "  'quero ver os anúncios' não é pergunta; 'a queda de CTR está concentrada em\n"
            "  algum anúncio ou é geral' é. Mínimo de 25 caracteres.")
    if not (a.corte or "").strip():
        raise modelo.ErroDeEstado(
            "--corte é obrigatório: diga o recorte técnico que responde a pergunta "
            "(nível, campos, período, quebra, filtro). É isto que o runtime executa.")

    consultas = d.setdefault("consultas", [])
    c = {
        "id": f"CONSULTA-{len(consultas) + 1:03d}",
        "job": j["id"], "agente": j["agente"], "fonte": a.fonte,
        "pergunta": a.pergunta.strip(), "corte": a.corte.strip(),
        "hipotese": (a.hipotese or "").strip(),
        "status": "PENDENTE", "aberta_em": modelo.agora(),
        "resposta_em": None, "arquivo": None, "observacao": None,
    }
    consultas.append(c)
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], "CONSULTA_ABERTA", agente=j["agente"], job=j["id"],
                            resumo=f"{c['id']} [{a.fonte}] {c['pergunta'][:100]}")
    p(f"  {c['id']} aberta em {a.fonte} — o runtime executa e devolve o dado bruto.")
    p("  Não conclua o job em cima de palpite enquanto ela estiver PENDENTE.")
    return 0


def cmd_consulta_pendentes(a) -> int:
    demandas = [modelo.carregar(a.demanda)] if a.demanda else modelo.listar()
    achou = False
    for d in demandas:
        for c in d.get("consultas", []):
            if c["status"] != "PENDENTE":
                continue
            achou = True
            p(f"\n  {d['id']} · {c['id']} · {c['fonte']}  (pedida por {c['agente']}, {c['job']})")
            p(f"     pergunta: {c['pergunta']}")
            p(f"     corte:    {c['corte']}")
            if c.get("hipotese"):
                p(f"     hipótese: {c['hipotese']}")
    if not achou:
        p("  nenhuma consulta pendente")
    return 0


def cmd_consulta_responder(a) -> int:
    d = modelo.carregar(a.demanda)
    for c in d.get("consultas", []):
        if c["id"] != a.consulta:
            continue
        if c["status"] != "PENDENTE":
            raise modelo.ErroDeEstado(f"{c['id']} já está {c['status']}")
        # SEM_DADO é o caminho honesto quando a fonte não tem conector — GA4,
        # TikTok, CRM e WhatsApp não têm, e isso não vai mudar por esforço. Mas
        # ausência também se prova: sem dizer o que se tentou, "não deu" é
        # indistinguível de "não tentei", e é assim que lacuna vira hipótese
        # silenciosa. Mesma doutrina do --busca da fonte de cliente.
        if a.sem_dado:
            just = (a.observacao or "").strip()
            if len(just) < 40:
                raise modelo.ErroDeEstado(
                    "--sem-dado exige --observacao dizendo O QUE FOI TENTADO e por que não "
                    "há dado: conector inexistente, conta sem permissão, período fora do "
                    "retido, evento não instrumentado.\n"
                    "  Sem isso, 'não deu' é indistinguível de 'não tentei' — e o "
                    "especialista não tem como saber se a lacuna é da fonte ou do runtime.\n"
                    "  Mínimo de 40 caracteres.")
            c["status"] = "SEM_DADO"
            c["arquivo"] = str(pathlib.Path(a.arquivo).expanduser().resolve()) if a.arquivo else None
            c["observacao"] = just
            c["resposta_em"] = modelo.agora()
            modelo.salvar(d)
            modelo.registrar_evento(d["id"], "CONSULTA_RESPONDIDA", job=c["job"],
                                    resumo=f"{c['id']} -> SEM_DADO ({just[:60]})")
            p(f"  {c['id']} -> SEM_DADO · {just[:90]}")
            p(f"  Redispare {c['agente']} no {c['job']}: a lacuna viaja DECLARADA, "
              "não vira hipótese.")
            return 0

        if not a.arquivo:
            raise modelo.ErroDeEstado(
                "--arquivo é obrigatório: o dado bruto tem de chegar em arquivo.\n"
                "  Sem dado nenhum? Use --sem-dado --observacao \"<o que foi tentado>\".")
        arq = pathlib.Path(a.arquivo).expanduser()
        if not arq.is_file():
            raise modelo.ErroDeEstado(
                f"o dado bruto precisa existir em disco: {arq} não existe.\n"
                "  Resposta que fica só na conversa não chega ao especialista.")
        c["status"] = "RESPONDIDA"
        c["arquivo"] = str(arq.resolve())
        c["observacao"] = a.observacao or ""
        c["resposta_em"] = modelo.agora()
        modelo.salvar(d)
        modelo.registrar_evento(d["id"], "CONSULTA_RESPONDIDA", job=c["job"],
                                resumo=f"{c['id']} -> RESPONDIDA ({arq.name})")
        p(f"  {c['id']} -> RESPONDIDA · {arq}")
        p(f"  Redispare {c['agente']} no {c['job']} com este arquivo no briefing.")
        return 0
    raise modelo.ErroDeEstado(f"consulta '{a.consulta}' não existe em {d['id']}")


def cmd_consulta_listar(a) -> int:
    d = modelo.carregar(a.demanda)
    cs = d.get("consultas", [])
    if not cs:
        p("  nenhuma consulta nesta demanda")
        return 0
    for c in cs:
        p(f"  {c['id']} {c['status']:<11} {c['fonte']:<11} {c['job']} ({c['agente']})")
        p(f"     {c['pergunta'][:96]}")
        if c.get("arquivo"):
            p(f"     dado: {c['arquivo']}")
    return 0


def cmd_gate(a) -> int:
    d = modelo.carregar(a.demanda)
    trava = avaliar_gate(d)
    p(formatar_gate(d, trava))
    return 2 if trava else 0


def cmd_concluir(a) -> int:
    """Fechar passa pelo gate. Revisão aprovada não substitui conferir o pedido."""
    d = modelo.carregar(a.demanda)
    trava = avaliar_gate(d)
    if trava:
        p(formatar_gate(d, trava))
        return 2
    return _mudar_status(a, "CONCLUIDA", None)


# ------------------------------------------- ponto canônico de saída do Squad

def condicoes_de_entrega(d: dict) -> list:
    """Tudo que precisa ser verdade antes de a demanda sair para o gestor.

    O gate diz que a demanda PODE fechar. Isto diz que ela JÁ fechou, pelas mãos
    do Diretor, e que o fechamento continua de pé agora — não em algum momento
    do passado. Recalculado a cada chamada de propósito: estado gravado ontem
    não prova nada sobre o arquivo de hoje.
    """
    falta = []
    if d["status"] != "CONCLUIDA":
        falta.append(f"demanda está {d['status']}, não CONCLUIDA — o Diretor ainda não liberou")
    if not d.get("concluida_em"):
        falta.append("demanda sem 'concluida_em': não há registro de quando o gate liberou")
    falta += [f"gate reabriu: {x}" for x in avaliar_gate(d)]
    return falta


def cmd_entregar(a) -> int:
    """A saída. Nada do Squad chega ao gestor sem passar por aqui.

    Existe porque a entrega era o único passo sem mecanismo: a sessão escrevia o
    texto e pronto. Reproduzido em sessão nova — demanda PLANEJADA, concluida_em
    nulo, legenda entregue assim mesmo. Prompt já tinha sido tentado; agora a
    liberação tem comando, tem verificação e tem registro.
    """
    d = modelo.carregar(a.demanda)
    falta = condicoes_de_entrega(d)
    if falta:
        p(f"\n═══ ENTREGA BARRADA · {d['id']} ═══")
        p("PEDIDO ORIGINAL (imutável)")
        p("  " + (d.get("descricao") or "").strip().replace("\n", "\n  "))
        p(f"NÃO ENTREGA — {len(falta)} condição(ões) aberta(s):")
        for x in falta:
            p(f"  ✗ {x}")
        p("Nada foi liberado. Feche pelo Diretor (`demanda.py concluir`) antes de entregar.")
        p("═" * 62)
        return 2

    artefatos = []
    for j in d.get("jobs", []):
        for art in ((j.get("resultado") or {}).get("artefatos") or []):
            artefatos.append((j["id"], j["agente"], art))

    d["entregue_em"] = modelo.agora()
    d.setdefault("entregas", []).append(
        {"em": d["entregue_em"], "artefatos": [x[2] for x in artefatos]})
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], "DEMANDA_ENTREGUE",
                            resumo=f"{len(artefatos)} artefato(s) liberado(s)")

    p(f"\n═══ ENTREGA LIBERADA · {d['id']} ═══")
    p(f"  fechada pelo Diretor em {d['concluida_em']}")
    p(f"  liberada para entrega em {d['entregue_em']}")
    p(f"  requisitos: {len(d.get('requisitos', []))} · jobs: {len(d.get('jobs', []))}")
    if artefatos:
        p("  artefatos:")
        for jid, ag, art in artefatos:
            p(f"    {jid} ({ag})  {art}")
    else:
        p("  artefatos: nenhum registrado (entrega textual)")
    p("═" * 62)
    return 0


# --------------------------------------------------------------- aprovações

def cmd_aprovacao_solicitar(a) -> int:
    d = modelo.carregar(a.demanda)
    v = policy.classificar(a.acao)
    if v["classe"] == "AUTONOMO":
        p(f"  '{a.acao}' é AUTONOMO pela política — não precisa de aprovação.")
        return 0
    if v["classe"] == "PROIBIDO":
        modelo.registrar_evento(d["id"], "ACAO_PROIBIDA_BLOQUEADA", resumo=a.acao)
        p(f"  '{a.acao}' é PROIBIDO (regra {v['regra']}). Não se aprova.")
        return 3
    ap = policy.solicitar(d, a.acao, v, job=a.job)
    if "AGUARDANDO_APROVACAO" in modelo.TRANSICOES.get(d["status"], set()):
        modelo.transitar(d, "AGUARDANDO_APROVACAO", motivo=ap["id"])
    modelo.salvar(d)
    p(policy.painel_aprovacao(ap).replace("<DEMANDA>", d["id"]))
    return 2


def cmd_aprovacao_listar(a) -> int:
    achou = False
    for d in modelo.listar():
        pend = [x for x in d.get("aprovacoes", [])
                if x["status"] == "PENDENTE" or not a.pendentes]
        for x in pend:
            achou = True
            p(f"  {d['id']} {x['id']}  {x['status']:<10} {x['acao'][:52]}")
            if x["status"] == "PENDENTE":
                p(f"                  motivo: {x['motivo']}")
    if not achou:
        p("  nenhuma aprovação pendente")
    return 0


def cmd_aprovacao_decidir(a, conceder: bool) -> int:
    d = modelo.carregar(a.demanda)
    for x in d.get("aprovacoes", []):
        if x["id"] == a.aprovacao:
            if x["status"] != "PENDENTE":
                raise modelo.ErroDeEstado(f"{x['id']} já está {x['status']}")
            x["status"] = "CONCEDIDA" if conceder else "NEGADA"
            x["decidida_em"] = modelo.agora()
            x["decidida_por"] = a.por or "gestor humano"
            x["observacao"] = getattr(a, "motivo", None)
            modelo.salvar(d)
            modelo.registrar_evento(d["id"], "APROVACAO_CONCEDIDA" if conceder else "APROVACAO_NEGADA",
                                    job=x.get("job"), resumo=f"{x['id']} por {x['decidida_por']}")
            p(f"  {x['id']} -> {x['status']} por {x['decidida_por']}")
            if not conceder:
                p("  a ação continua barrada.")
            return 0
    raise modelo.ErroDeEstado(f"aprovação '{a.aprovacao}' não existe em {d['id']}")


# --------------------------------------------------------------- memória

def dir_memoria_cliente(cliente: str) -> str:
    caminho = modelo.dir_clientes() / f"{cliente}.md"
    return caminho.read_text(encoding="utf-8") if caminho.is_file() else ""


def cmd_cliente_ver(a) -> int:
    texto = dir_memoria_cliente(modelo.slug(a.cliente))
    p(texto or f"  sem memória para o cliente '{modelo.slug(a.cliente)}'")
    return 0


def cmd_cliente_anotar(a) -> int:
    caminho = modelo.dir_clientes() / f"{modelo.slug(a.cliente)}.md"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if not caminho.exists():
        caminho.write_text(f"# Memória do cliente · {modelo.slug(a.cliente)}\n\n"
                           "Contexto estável. O que vale para toda demanda deste cliente.\n",
                           encoding="utf-8")
    with caminho.open("a", encoding="utf-8") as fh:
        fh.write(f"\n- [{modelo.agora()[:10]}] **{a.secao}**: {a.texto}\n")
    p(f"  anotado em {caminho}")
    return 0


# ------------------------------------- contexto externo do cliente (Drive)
#
# Quem fala com o Drive é o Diretor, pelo conector MCP — motor não tem conector e
# não vai ganhar um. O que mora aqui é a decisão: qual cliente é este, o que do
# que foi encontrado vale como verdade e o que é apenas referência. Assim existe
# uma implementação só, no orquestrador, e não sete nos especialistas.

def _validar_fontes(cliente: str, ids: list) -> list:
    if not ids:
        return []
    reg = modelo.carregar_fontes(cliente)
    for i in ids:
        modelo.achar_fonte(reg, i)          # levanta se a fonte não existe
    return ids


def cmd_cliente_resolver(a) -> int:
    """Do nome falado para o cliente registrado. Três saídas, e só três.

    Duas pastas possíveis é dúvida material: o Diretor pergunta, não escolhe.
    Confundir cliente é o erro que não se conserta depois da entrega.
    """
    achados = modelo.resolver_cliente(a.cliente)
    if len(achados) == 1:
        p(f"RESOLVIDO {achados[0]['cliente']}")
        return 0
    if not achados:
        p(f"SEM BASE  {modelo.slug(a.cliente)}")
        p("  nenhum cliente registrado com este nome. Localize a pasta no acervo e "
          "registre com 'cliente base definir', ou siga sem base externa.")
        return 0
    p("DÚVIDA MATERIAL")
    for reg in achados:
        base = reg.get("base") or {}
        p(f"  {reg['cliente']:<24} {base.get('pasta_nome', '(sem pasta registrada)')}")
    p("  dois clientes possíveis para o mesmo nome. Pergunte ao gestor qual é, antes "
      "de consultar qualquer arquivo.")
    return 2


def cmd_cliente_base_definir(a) -> int:
    reg = modelo.carregar_fontes(a.cliente)
    reg["cliente"] = modelo.slug(a.cliente)
    reg["base"] = {"fonte": a.fonte_externa, "pasta_id": a.pasta_id,
                   "pasta_nome": a.pasta_nome or "", "definida_em": modelo.agora()}
    for apelido in (a.alias or []):
        if apelido not in reg.setdefault("aliases", []):
            reg["aliases"].append(apelido)
    modelo.salvar_fontes(a.cliente, reg)
    p(f"  base de {reg['cliente']}: {a.fonte_externa}:{a.pasta_id}")
    return 0


def cmd_cliente_base_ver(a) -> int:
    reg = modelo.carregar_fontes(a.cliente)
    base = reg.get("base")
    if not base:
        p(f"  {reg['cliente']}: sem base externa registrada")
        return 0
    p(f"  {reg['cliente']}")
    p(f"  base      {base.get('fonte')}:{base.get('pasta_id')}  {base.get('pasta_nome', '')}")
    if reg.get("aliases"):
        p(f"  também conhecido por: {', '.join(reg['aliases'])}")
    return 0


def cmd_cliente_fonte_add(a) -> int:
    if a.classe not in modelo.CLASSES_FONTE:
        raise modelo.ErroDeEstado(f"classe inválida. Use: {', '.join(modelo.CLASSES_FONTE)}")
    estado = (getattr(a, "estado", None) or "ENCONTRADO").upper()
    if estado not in modelo.ESTADOS_EVIDENCIA:
        raise modelo.ErroDeEstado(
            f"estado de evidência inválido. Use: {', '.join(modelo.ESTADOS_EVIDENCIA)}")
    busca = (getattr(a, "busca", None) or "").strip()

    # A trava. Afirmar que algo não existe é afirmação material: muda o que o
    # especialista pode fazer. Ela só entra no registro com a busca descrita.
    texto = f"{a.titulo} {a.resumo or ''}"
    if modelo.afirma_ausencia(texto):
        if estado == "ENCONTRADO":
            raise modelo.ErroDeEstado(
                "esta fonte afirma que algo NÃO existe, e está marcada ENCONTRADO.\n"
                "  Ausência não é achado. Use --estado NAO_ENCONTRADO_APOS_BUSCA (com --busca),\n"
                "  ou NAO_VERIFICADO se ninguém procurou, ou INDISPONIVEL se não dá para olhar.")
        if estado == "NAO_ENCONTRADO_APOS_BUSCA" and len(busca) < 40:
            raise modelo.ErroDeEstado(
                "NAO_ENCONTRADO_APOS_BUSCA exige --busca dizendo o que foi feito: onde se\n"
                "  procurou, com que termo ou filtro, quantos resultados vieram e o que\n"
                "  foi aberto. Mínimo de 40 caracteres, e 'procurei' não conta.\n"
                "  Sem isso, o estado correto é NAO_VERIFICADO — que não vira fato.")

    reg = modelo.carregar_fontes(a.cliente)
    reg["cliente"] = modelo.slug(a.cliente)
    fonte = {
        "id": modelo.proxima_fonte_id(reg), "classe": a.classe, "titulo": a.titulo,
        "resumo": a.resumo or "", "fonte_externa": a.fonte_externa,
        "ref": a.ref or "", "link": a.link or "",
        "estado_evidencia": estado, "busca": busca,
        "verificado_em": a.verificado_em or modelo.agora()[:10],
        "demanda": a.demanda or "", "registrado_em": modelo.agora(),
    }
    erros = modelo.validar(fonte, "fonte")
    if erros:
        raise modelo.ErroDeEstado("fonte inválida: " + "; ".join(erros))
    reg.setdefault("fontes", []).append(fonte)
    modelo.salvar_fontes(a.cliente, reg)
    if a.demanda:
        modelo.registrar_evento(a.demanda, "FONTE_REGISTRADA",
                                resumo=f"[{fonte['classe']}·{estado}] {fonte['titulo'][:110]}")
    p(fonte["id"])
    if estado not in modelo.EVIDENCIA_UTILIZAVEL:
        p(f"  {estado}: não entra no briefing como Source of Truth. "
          "O especialista vai receber isto como informação não estabelecida.")
    return 0


def cmd_cliente_fonte_listar(a) -> int:
    reg = modelo.carregar_fontes(a.cliente)
    if not reg.get("fontes"):
        p(f"  {reg['cliente']}: nenhuma fonte registrada")
        return 0
    cab(f"FONTES · {reg['cliente']}")
    for f in reg["fontes"]:
        efetiva = modelo.classe_efetiva(f)
        marca = "·" if efetiva in modelo.FONTES_CANONICAS else " "
        envelheceu = f"  (registrada como {f['classe']})" if efetiva != f["classe"] else ""
        p(f"  {marca} {f['id']}  {modelo.rotular_fonte(f)}{envelheceu}")
    return 0


def cmd_cliente_contexto(a) -> int:
    """O que iria para um briefing deste cliente agora — canônico e referência."""
    ctx = modelo.contexto_cliente(a.cliente, a.fonte or [])
    cab(f"CONTEXTO · {modelo.slug(a.cliente)}")
    p(f"  ACERVO             {ctx['base_externa'] or '(sem base externa)'}")
    p("  SOURCE OF TRUTH")
    for linha in ctx["fontes_canonicas"] or ["    (nada vigente registrado)"]:
        p(f"    {linha}")
    if ctx["referencias_nao_canonicas"]:
        p("  REFERÊNCIA — não é verdade atual")
        for linha in ctx["referencias_nao_canonicas"]:
            p(f"    {linha}")
    return 0


def cmd_feedback(a) -> int:
    """Registra feedback do gestor, classificado — não vira regra eterna por descuido."""
    d = modelo.carregar(a.demanda)
    if a.classe not in modelo.CLASSES_FEEDBACK:
        raise modelo.ErroDeEstado(f"classe inválida. Use: {', '.join(modelo.CLASSES_FEEDBACK)}")
    item = {"texto": a.texto, "classe": a.classe, "job": a.job, "agente": a.agente,
            "motivo": a.motivo or "", "em": modelo.agora(), "confirmado": False}
    if a.classe == "regra_global" and not a.confirmado:
        p("\n  ⚠ 'regra_global' vira regra permanente para TODOS os clientes.")
        p("  Registrado como PROPOSTA, não aplicado. Para confirmar:")
        p(f"     demanda.py feedback {d['id']} --texto \"{a.texto[:40]}...\" "
          f"--classe regra_global --confirmado")
        item["classe"] = "regra_global_proposta"
    else:
        item["confirmado"] = True
    d.setdefault("feedback", []).append(item)
    modelo.salvar(d)
    modelo.registrar_evento(d["id"], "FEEDBACK_REGISTRADO", agente=a.agente, job=a.job,
                            resumo=f"[{item['classe']}] {a.texto[:120]}")
    if a.classe == "preferencia_do_cliente" and item["confirmado"]:
        caminho = modelo.dir_clientes() / f"{d['cliente']}.md"
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with caminho.open("a", encoding="utf-8") as fh:
            fh.write(f"\n- [{modelo.agora()[:10]}] **preferência** ({d['id']}): {a.texto}\n")
        p(f"  também anotado na memória do cliente: {caminho}")
    p(f"  feedback registrado como '{item['classe']}'")
    return 0


# --------------------------------------------------------------- histórico e retomada

def cmd_historico(a) -> int:
    evs = modelo.eventos(a.demanda)
    if not evs:
        p("  sem eventos"); return 0
    cab(f"HISTÓRICO · {a.demanda} ({len(evs)} eventos)")
    for e in evs:
        job = f" {e['job']}" if e.get("job") else ""
        p(f"  {e['em'][:19].replace('T',' ')}  {e['evento']:<28}{job:<9} {e.get('resumo','')[:52]}")
    return 0


def cmd_retomar(a) -> int:
    """O relatório que permite continuar sem depender de histórico de conversa."""
    d = modelo.carregar(a.demanda)
    cab(f"RETOMADA · {d['id']} · {d['titulo']}")
    p(f"  cliente {d['cliente']} · status {d['status']} · aberta em {d['criada_em'][:10]}")
    if d.get("objetivo"): p(f"  objetivo: {d['objetivo']}")
    if d.get("plano"):    p(f"  plano:    {d['plano'][:240]}")

    jobs = d.get("jobs", [])
    por = lambda s: [j for j in jobs if j["status"] == s]
    cab("O QUE JÁ TERMINOU")
    for j in por("CONCLUIDO"):
        r = j.get("resultado") or {}
        p(f"  ✓ {j['id']} {j['agente']:<20} {r.get('resumo','')[:56]}")
        for art in (r.get("artefatos") or []):
            p(f"      artefato: {art}")
    if not por("CONCLUIDO"): p("  (nenhum)")

    cab("O QUE FALHOU OU TRAVOU")
    for j in por("FALHOU") + por("BLOQUEADO"):
        p(f"  ✗ {j['id']} {j['agente']:<20} {j['status']} · {(j.get('erro') or '')[:52]}")
        p(f"      tentativas {j.get('tentativas',0)}/{j.get('max_tentativas', modelo.MAX_TENTATIVAS)}")
    if not (por("FALHOU") + por("BLOQUEADO")): p("  (nenhum)")

    reqs = d.get("requisitos", [])
    if reqs or d.get("alteracoes"):
        cab("REQUEST_CHECKLIST")
        for r in reqs:
            p(f"  {r['id']} {r['estado']:<14} {r['dono']:<18} {r['texto'][:48]}")
        for alt in d.get("alteracoes", []):
            p(f"  {alt['id']} ALTERAÇÃO      {alt['texto'][:66]}")

    cab("AGUARDANDO APROVAÇÃO HUMANA")
    pend = [x for x in d.get("aprovacoes", []) if x["status"] == "PENDENTE"]
    for x in pend:
        p(f"  ⏸ {x['id']} {x['acao']}")
        p(f"      {x['motivo']}")
    if not pend: p("  (nenhuma)")

    cab("PRÓXIMO PASSO ELEGÍVEL")
    prontos = modelo.elegiveis(d)
    if prontos:
        for j in prontos:
            p(f"  → {j['id']} {j['agente']:<20} {j['objetivo'][:52]}")
        p(f"\n  Comece por:  demanda.py briefing {d['id']} {prontos[0]['id']}")
    else:
        travados = modelo.bloqueados_por_dependencia(d)
        if travados:
            for j, faltam in travados:
                p(f"  ⏳ {j['id']} espera {', '.join(faltam)}")
        elif pend:
            p("  Nada avança até uma aprovação ser decidida.")
        elif d["status"] not in ("CONCLUIDA", "CANCELADA"):
            p("  Todos os jobs terminaram. Feche a demanda:")
            p(f"     demanda.py concluir {d['id']}")
        else:
            p("  (demanda encerrada)")
    return 0


# --------------------------------------------------------------- argumentos

def main(argv=None) -> int:
    p_ = argparse.ArgumentParser(prog="demanda", description="Sistema de demandas do Diretor de Operações")
    sub = p_.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("nova", help="abre uma demanda")
    n.add_argument("--cliente", required=True); n.add_argument("--titulo", required=True)
    n.add_argument("--descricao", "--pedido", dest="descricao", required=True,
                   help="ORIGINAL_REQUEST: o pedido do gestor, palavra por palavra. Imutável.")
    n.add_argument("--objetivo")
    n.add_argument("--contexto")
    n.add_argument("--prioridade", default="normal", choices=["baixa", "normal", "alta", "urgente"])
    n.set_defaults(fn=cmd_nova)

    l = sub.add_parser("listar", help="lista demandas"); l.add_argument("--status")
    l.set_defaults(fn=cmd_listar)

    v = sub.add_parser("ver", help="mostra uma demanda"); v.add_argument("demanda")
    v.set_defaults(fn=cmd_ver)

    pl = sub.add_parser("planejar", help="RECEBIDA -> PLANEJADA")
    pl.add_argument("demanda"); pl.add_argument("--plano", required=True)
    pl.set_defaults(fn=cmd_planejar)

    cc = sub.add_parser("concluir", help="fecha a demanda — passa pelo FINAL_REQUEST_GATE")
    cc.add_argument("demanda"); cc.add_argument("--motivo", default="")
    cc.set_defaults(fn=cmd_concluir)

    en = sub.add_parser("entregar", help="ponto canônico de saída — libera a entrega ao gestor")
    en.add_argument("demanda")
    en.set_defaults(fn=cmd_entregar)

    co = sub.add_parser("consulta", help="o especialista pede dado; o runtime executa o conector")
    cos = co.add_subparsers(dest="sub", required=True)
    co1 = cos.add_parser("abrir", help="especialista pede um corte de dado")
    co1.add_argument("demanda"); co1.add_argument("job")
    co1.add_argument("--fonte", required=True, help=", ".join(FONTES_CONSULTA))
    co1.add_argument("--pergunta", required=True, help="o que se quer descobrir, não a tabela")
    co1.add_argument("--corte", required=True, help="nível, campos, período, quebra, filtro")
    co1.add_argument("--hipotese", help="o que este corte confirma ou derruba")
    co1.set_defaults(fn=cmd_consulta_abrir)
    co2 = cos.add_parser("pendentes", help="o que o runtime tem de executar")
    co2.add_argument("demanda", nargs="?"); co2.set_defaults(fn=cmd_consulta_pendentes)
    co3 = cos.add_parser("responder", help="devolve o dado bruto ao especialista")
    co3.add_argument("demanda"); co3.add_argument("consulta")
    co3.add_argument("--arquivo", help="o dado bruto em disco (obrigatório sem --sem-dado)")
    co3.add_argument("--observacao", help="com --sem-dado: o que foi tentado, mín. 40 caracteres")
    co3.add_argument("--sem-dado", dest="sem_dado", action="store_true",
                     help="não há o dado: fonte sem conector, sem permissão, sem instrumentação")
    co3.set_defaults(fn=cmd_consulta_responder)
    co4 = cos.add_parser("listar"); co4.add_argument("demanda")
    co4.set_defaults(fn=cmd_consulta_listar)

    for nome, estado, campo in [("bloquear", "BLOQUEADA", "bloqueio"),
                                ("cancelar", "CANCELADA", None), ("revisar", "EM_REVISAO", None)]:
        s = sub.add_parser(nome, help=f"demanda -> {estado}")
        s.add_argument("demanda"); s.add_argument("--motivo", default="")
        s.set_defaults(fn=lambda a, e=estado, c=campo: _mudar_status(a, e, c))

    j = sub.add_parser("job", help="jobs da demanda")
    js = j.add_subparsers(dest="sub", required=True)

    ja = js.add_parser("add", help="cria um job")
    ja.add_argument("demanda"); ja.add_argument("--agente", required=True)
    ja.add_argument("--objetivo", required=True); ja.add_argument("--entrada")
    ja.add_argument("--saida"); ja.add_argument("--depende", action="append")
    ja.add_argument("--criterio", action="append"); ja.add_argument("--restricao", action="append")
    ja.add_argument("--fonte", action="append",
                    help="anexa uma fonte do cliente a este job. Só assim histórico e "
                         "campanha anterior chegam ao especialista")
    ja.set_defaults(fn=cmd_job_add)

    je = js.add_parser("elegiveis", help="o que pode rodar agora"); je.add_argument("demanda")
    je.set_defaults(fn=cmd_job_elegiveis)

    ji = js.add_parser("iniciar", help="marca EM_EXECUCAO e conta a tentativa")
    ji.add_argument("demanda"); ji.add_argument("job"); ji.set_defaults(fn=cmd_job_iniciar)

    jc = js.add_parser("concluir", help="registra o retorno do especialista")
    jc.add_argument("demanda"); jc.add_argument("job")
    jc.add_argument("--retorno", help="arquivo JSON no formato retorno.schema.json")
    jc.add_argument("--status", default="concluido",
                    choices=["concluido", "bloqueado", "precisa_de_informacao",
                             "precisa_de_aprovacao", "falhou"])
    jc.add_argument("--resumo"); jc.add_argument("--artefato", action="append")
    jc.add_argument("--decisao", action="append"); jc.add_argument("--observacao")
    jc.add_argument("--proximo"); jc.add_argument("--pendencia")
    jc.set_defaults(fn=cmd_job_concluir)

    jf = js.add_parser("falhar", help="marca falha")
    jf.add_argument("demanda"); jf.add_argument("job"); jf.add_argument("--erro", required=True)
    jf.set_defaults(fn=cmd_job_falhar)

    jr = js.add_parser("reprocessar", help="novo ciclo, respeitando o teto")
    jr.add_argument("demanda"); jr.add_argument("job"); jr.add_argument("--corrigir")
    jr.set_defaults(fn=cmd_job_reprocessar)

    b = sub.add_parser("briefing", help="contrato DIRETOR -> ESPECIALISTA")
    b.add_argument("demanda"); b.add_argument("job")
    b.add_argument("--json", action="store_true"); b.add_argument("--forcar", action="store_true")
    b.set_defaults(fn=cmd_briefing)

    rq = sub.add_parser("requisito", help="REQUEST_CHECKLIST: o que o gestor pediu, com dono")
    rqs = rq.add_subparsers(dest="sub", required=True)
    r1 = rqs.add_parser("add", help="registra um requisito extraído do pedido original")
    r1.add_argument("demanda"); r1.add_argument("--texto", required=True)
    r1.add_argument("--dono", required=True,
                    help="especialista acionável, 'diretor' ou 'gestor-humano'")
    r1.add_argument("--job"); r1.set_defaults(fn=cmd_requisito_add)
    r2 = rqs.add_parser("estado", help="cumprido / bloqueado / nao_aplicavel / cancelado")
    r2.add_argument("demanda"); r2.add_argument("requisito")
    r2.add_argument("--estado", required=True,
                    choices=[e.lower() for e in modelo.ESTADOS_REQUISITO])
    r2.add_argument("--evidencia", help="job, arquivo ou link que prova — exigido em cumprido")
    r2.add_argument("--motivo"); r2.set_defaults(fn=cmd_requisito_estado)
    r3 = rqs.add_parser("listar"); r3.add_argument("demanda")
    r3.set_defaults(fn=cmd_requisito_listar)

    al = sub.add_parser("alteracao", help="mudança do gestor, ao lado do pedido original")
    al.add_argument("demanda"); al.add_argument("--texto", required=True)
    al.add_argument("--afeta", action="append", help="REQ-00N afetado; pode repetir")
    al.set_defaults(fn=cmd_alteracao)

    g = sub.add_parser("gate", help="FINAL_REQUEST_GATE: confere o pedido contra o resultado")
    g.add_argument("demanda"); g.set_defaults(fn=cmd_gate)

    ap = sub.add_parser("aprovacao", help="fluxo de aprovação humana")
    aps = ap.add_subparsers(dest="sub", required=True)
    a1 = aps.add_parser("solicitar"); a1.add_argument("demanda")
    a1.add_argument("--acao", required=True); a1.add_argument("--job")
    a1.set_defaults(fn=cmd_aprovacao_solicitar)
    a2 = aps.add_parser("listar"); a2.add_argument("--pendentes", action="store_true", default=True)
    a2.set_defaults(fn=cmd_aprovacao_listar)
    a3 = aps.add_parser("conceder"); a3.add_argument("demanda"); a3.add_argument("aprovacao")
    a3.add_argument("--por", required=True); a3.set_defaults(fn=lambda a: cmd_aprovacao_decidir(a, True))
    a4 = aps.add_parser("negar"); a4.add_argument("demanda"); a4.add_argument("aprovacao")
    a4.add_argument("--por", required=True); a4.add_argument("--motivo")
    a4.set_defaults(fn=lambda a: cmd_aprovacao_decidir(a, False))

    f = sub.add_parser("feedback", help="registra feedback classificado")
    f.add_argument("demanda"); f.add_argument("--texto", required=True)
    f.add_argument("--classe", required=True, choices=modelo.CLASSES_FEEDBACK)
    f.add_argument("--job"); f.add_argument("--agente"); f.add_argument("--motivo")
    f.add_argument("--confirmado", action="store_true")
    f.set_defaults(fn=cmd_feedback)

    c = sub.add_parser("cliente", help="memória de cliente")
    cs = c.add_subparsers(dest="sub", required=True)
    c1 = cs.add_parser("ver"); c1.add_argument("cliente"); c1.set_defaults(fn=cmd_cliente_ver)
    c2 = cs.add_parser("anotar"); c2.add_argument("cliente")
    c2.add_argument("--secao", required=True); c2.add_argument("--texto", required=True)
    c2.set_defaults(fn=cmd_cliente_anotar)

    c3 = cs.add_parser("resolver", help="nome falado -> cliente registrado")
    c3.add_argument("cliente"); c3.set_defaults(fn=cmd_cliente_resolver)

    cb = cs.add_parser("base", help="acervo externo do cliente")
    cbs = cb.add_subparsers(dest="sub2", required=True)
    cb1 = cbs.add_parser("definir"); cb1.add_argument("cliente")
    cb1.add_argument("--fonte-externa", dest="fonte_externa", default="drive")
    cb1.add_argument("--pasta-id", dest="pasta_id", required=True)
    cb1.add_argument("--pasta-nome", dest="pasta_nome")
    cb1.add_argument("--alias", action="append",
                     help="variação de nome pela qual este cliente também é chamado")
    cb1.set_defaults(fn=cmd_cliente_base_definir)
    cb2 = cbs.add_parser("ver"); cb2.add_argument("cliente")
    cb2.set_defaults(fn=cmd_cliente_base_ver)

    cf = cs.add_parser("fonte", help="o que foi encontrado no acervo, classificado")
    cfs = cf.add_subparsers(dest="sub2", required=True)
    cf1 = cfs.add_parser("add"); cf1.add_argument("cliente")
    cf1.add_argument("--classe", required=True,
                     help=", ".join(modelo.CLASSES_FONTE))
    cf1.add_argument("--titulo", required=True); cf1.add_argument("--resumo")
    cf1.add_argument("--fonte-externa", dest="fonte_externa", default="drive")
    cf1.add_argument("--ref", help="fileId na origem — o rastro de volta ao original")
    cf1.add_argument("--link"); cf1.add_argument("--verificado-em", dest="verificado_em")
    cf1.add_argument("--estado", default="ENCONTRADO",
                     help="evidência: " + ", ".join(modelo.ESTADOS_EVIDENCIA))
    cf1.add_argument("--busca",
                     help="o que foi feito para procurar: onde, com que termo, quantos "
                          "resultados, o que foi aberto. Obrigatório para afirmar ausência")
    cf1.add_argument("--demanda"); cf1.set_defaults(fn=cmd_cliente_fonte_add)
    cf2 = cfs.add_parser("listar"); cf2.add_argument("cliente")
    cf2.set_defaults(fn=cmd_cliente_fonte_listar)

    c4 = cs.add_parser("contexto", help="o que iria para o briefing deste cliente")
    c4.add_argument("cliente")
    c4.add_argument("--fonte", action="append", help="anexa uma fonte não canônica")
    c4.set_defaults(fn=cmd_cliente_contexto)

    h = sub.add_parser("historico", help="event log da demanda"); h.add_argument("demanda")
    h.set_defaults(fn=cmd_historico)

    r = sub.add_parser("retomar", help="onde a demanda parou e qual o próximo passo")
    r.add_argument("demanda"); r.set_defaults(fn=cmd_retomar)

    a = p_.parse_args(argv)
    try:
        return a.fn(a)
    except modelo.ErroDeEstado as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"erro: arquivo não encontrado: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
