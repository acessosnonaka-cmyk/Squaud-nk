#!/usr/bin/env python3
"""Testes da política de autonomia — o portão e o hook leem o mesmo policy.yaml.

Rode a partir da raiz do repositório:

    python3 -m unittest discover -s agents/diretor-operacoes/tests -v

Só stdlib: nenhuma dependência nova para rodar o que protege a trava.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import unittest

DIRETOR = pathlib.Path(__file__).resolve().parent.parent
RAIZ = DIRETOR.parent.parent
sys.path.insert(0, str(DIRETOR))

from engine import policy  # noqa: E402


class PadroesSaoMinusculos(unittest.TestCase):
    """A regra que o bug do `-X POST` violou.

    `policy.normalizar()` passa o texto para minúsculas antes de casar. Padrão com
    letra maiúscula, portanto, nunca casa — vira trava que parece existir e não
    existe. Este teste é a guarda para que não volte.
    """

    def test_nenhum_padrao_tem_letra_maiuscula(self):
        pol = policy.carregar()
        ofensores = []
        for classe, bloco in (pol.get("classes") or {}).items():
            for regra in bloco.get("regras") or []:
                for padrao in regra.get("padroes") or []:
                    if re.search(r"[A-Z]", padrao):
                        ofensores.append(f"{classe}/{regra['id']}: {padrao}")
        self.assertEqual(ofensores, [], "padrão com maiúscula nunca casa: " + "; ".join(ofensores))

    def test_normalizar_realmente_minusculiza(self):
        self.assertEqual(policy.normalizar("Curl -X POST"), "curl -x post")


class CurlComMetodo(unittest.TestCase):
    """Regressão do bug: `curl -X POST` passava pelo hook sem ser classificado."""

    def _classe(self, comando):
        v = policy.classificar_shell(comando)
        return None if v is None else (v["classe"], v["regra"])

    def test_curl_post_exige_aprovacao(self):
        self.assertEqual(
            self._classe("curl -X POST https://graph.facebook.com/v21.0/act_1/campaigns -d status=ACTIVE"),
            ("REQUER_APROVACAO", "publicacao-externa"),
        )

    def test_curl_put_e_delete_tambem(self):
        for metodo in ("PUT", "DELETE"):
            with self.subTest(metodo=metodo):
                self.assertEqual(
                    self._classe(f"curl -X {metodo} https://exemplo.com/recurso"),
                    ("REQUER_APROVACAO", "publicacao-externa"),
                )

    def test_minusculo_e_misto_tambem(self):
        for comando in ("curl -x post https://exemplo.com/x", "CURL -X Post https://exemplo.com/x"):
            with self.subTest(comando=comando):
                self.assertEqual(
                    self._classe(comando), ("REQUER_APROVACAO", "publicacao-externa")
                )

    def test_upload_file_continua_pegando(self):
        self.assertEqual(
            self._classe("curl --upload-file arquivo.zip https://exemplo.com/"),
            ("REQUER_APROVACAO", "publicacao-externa"),
        )

    def test_curl_de_leitura_nao_e_barrado(self):
        """Sem método de escrita não há efeito externo: GET continua livre."""
        self.assertIsNone(self._classe("curl https://exemplo.com/status.json"))

    def test_proxy_nao_e_falso_positivo(self):
        """`-x` é também a flag de proxy do curl; só casa com post/put/delete."""
        self.assertIsNone(self._classe("curl -x http://proxy:3128 https://exemplo.com/"))


class ChmodRecursivo(unittest.TestCase):
    """O outro padrão que a normalização matava, na mesma classe de bug."""

    def test_chmod_777_na_raiz_e_proibido(self):
        v = policy.classificar_shell("chmod -R 777 /")
        self.assertIsNotNone(v, "chmod -R 777 / precisa casar")
        self.assertEqual(v["classe"], "PROIBIDO")


class NaoRegrediuORestante(unittest.TestCase):
    """O que já funcionava antes da correção continua igual."""

    def test_shell_perigoso_conhecido(self):
        casos = {
            "rsync -a dist/ deploy@servidor:/var/www": ("REQUER_APROVACAO", "publicacao-externa"),
            "npm publish": ("REQUER_APROVACAO", "publicacao-externa"),
            "git push --force origin main": ("PROIBIDO", "destrutivo-nao-autorizado"),
            "git reset --hard": ("PROIBIDO", "destrutivo-nao-autorizado"),
        }
        for comando, esperado in casos.items():
            with self.subTest(comando=comando):
                v = policy.classificar_shell(comando)
                self.assertIsNotNone(v, comando)
                self.assertEqual((v["classe"], v["regra"]), esperado)

    def test_comando_inocuo_passa(self):
        for comando in ("ls -la", "git status", "python3 -m unittest", "cat .env.example"):
            with self.subTest(comando=comando):
                self.assertIsNone(policy.classificar_shell(comando))

    def test_acao_descrita_desconhecida_cai_em_aprovacao(self):
        """Fail-closed do portão: o que a política não reconhece não é liberado."""
        self.assertEqual(policy.classificar("fazer algo que ninguem previu")["classe"], "REQUER_APROVACAO")

    def test_acao_descrita_conhecida(self):
        casos = {
            "subir a campanha de leads no Meta Ads": "REQUER_APROVACAO",
            "alterar o orcamento diario da campanha": "REQUER_APROVACAO",
            "montar plano de midia em rascunho": "AUTONOMO",
            "desabilitar a aprovacao do portao": "PROIBIDO",
        }
        for acao, esperado in casos.items():
            with self.subTest(acao=acao):
                self.assertEqual(policy.classificar(acao)["classe"], esperado)


class HookPreToolUse(unittest.TestCase):
    """O hook é a superfície onde o bug aparecia: comando cru pelo Bash."""

    HOOK = RAIZ / "scripts" / "hook-pretooluse.py"

    def _decidir(self, comando):
        entrada = json.dumps({"tool_name": "Bash", "tool_input": {"command": comando}})
        r = subprocess.run(
            [sys.executable, str(self.HOOK)],
            input=entrada, capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin", "SQUAD_NK_HOME": str(RAIZ), "HOME": str(pathlib.Path.home())},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("política indisponível", r.stderr, "o hook não conseguiu ler policy.yaml")
        if not r.stdout.strip():
            return None
        return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]

    def test_curl_post_e_negado(self):
        self.assertEqual(self._decidir("curl -X POST https://exemplo.com/api -d x=1"), "deny")

    def test_comando_inocuo_passa(self):
        self.assertIsNone(self._decidir("git status"))

    def test_o_proprio_portao_passa(self):
        self.assertIsNone(
            self._decidir("python3 agents/diretor-operacoes/engine/policy.py executar --acao x -- echo y")
        )


if __name__ == "__main__":
    unittest.main()
