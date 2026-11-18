"""Modelo de texto da esteira. LOL_LLM=claude (padrão quando há credencial do Claude) ou gemini.

Claude roda pelo Claude Code headless (`claude -p`), autenticado com CLAUDE_CODE_OAUTH_TOKEN
(gerado uma vez com `claude setup-token`) ou ANTHROPIC_API_KEY. Sem ferramentas: só texto in, JSON out.
"""
import json
import os
import re
import subprocess

MODELO_CLAUDE = os.environ.get("LOL_CLAUDE_MODELO", "claude-opus-5-5")


def provedor():
    escolha = os.environ.get("LOL_LLM")
    if escolha:
        return escolha
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    return "gemini"


def _json_de(texto):
    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip()).strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", texto, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def claude(sistema, usuario, ferramentas="", diretorio=None, timeout=900):
    cmd = ["claude", "-p", "--model", MODELO_CLAUDE, "--output-format", "json", "--system-prompt",
           sistema + "\n\nResponda SOMENTE com um objeto JSON válido, sem texto antes ou depois.",
           "--tools", ferramentas]
    if ferramentas:
        cmd += ["--allowedTools", ferramentas]
    if diretorio:
        cmd += ["--add-dir", str(diretorio)]
    r = subprocess.run(cmd, input=usuario, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"claude -p falhou (código {r.returncode}): {r.stderr[-200:]}")
    saida = json.loads(r.stdout)
    if saida.get("is_error"):
        raise RuntimeError(f"claude -p erro: {str(saida.get('result', ''))[:200]}")
    return _json_de(saida["result"])


def gerar_json(sistema, usuario, temperatura=0.8, modelo=None):
    if provedor() == "claude":
        return claude(sistema, usuario)
    from gemini import gerar_json as g
    return g(sistema, usuario, temperatura=temperatura, modelo=modelo)
