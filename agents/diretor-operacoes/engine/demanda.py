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
    if b.get("feedback_anterior"):
        linhas.append("JÁ REPROVADO ANTES " + "\n                   ".join(b["feedback_anterior"]))
    linhas.append(f"TENTATIVA          {b['tentativa']}")
    linhas.append(f"EXECUTION_MODE     {b.get('execution_mode', modelo.EXECUTION_MODE_PADRAO)}"
                  "  — execute sem narrar etapa, handoff ou progresso")
    linhas.append("═" * 62)
    return "\n".join(linhas)


def cmd_job_iniciar(a) -> int:
    d = modelo.carregar(a.demanda)
    j = modelo.achar_job(d, a.job)
    if j["status"] not in ("PENDENTE", "FALHOU"):
        raise modelo.ErroDeEstado(f"{j['id']} está {j['status']}; só se inicia PENDENTE ou FALHOU")
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
    prontos = modelo.elegiveis(d)
    if prontos:
        p("  liberou: " + ", ".join(f"{x['id']} ({x['agente']})" for x in prontos))
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
    linhas.append("═" * 62)
    return "\n".join(linhas)


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
    reg = modelo.carregar_fontes(a.cliente)
    reg["cliente"] = modelo.slug(a.cliente)
    fonte = {
        "id": modelo.proxima_fonte_id(reg), "classe": a.classe, "titulo": a.titulo,
        "resumo": a.resumo or "", "fonte_externa": a.fonte_externa,
        "ref": a.ref or "", "link": a.link or "",
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
                                resumo=f"[{fonte['classe']}] {fonte['titulo'][:120]}")
    p(fonte["id"])
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
