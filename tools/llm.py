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


ESCRITOR_REGISTRO = []  # o que aconteceu com o roteirista em cada rodada (vai para o relatório)
MODELO_AGY = os.environ.get("LOL_AGY_MODELO", "gemini-4-carbon-medium")


def agy(sistema, usuario, timeout=int(os.environ.get("LOL_AGY_TIMEOUT", "360"))):
    """Antigravity CLI headless (login do Ultra em cache, sem chave). Roda numa pasta vazia e sem ferramentas aprovadas:
    só texto in, JSON out. Saída em JSON: {"status": "SUCCESS", "response": "..."}."""
    import tempfile
    prompt = (sistema + "\n\nResponda SOMENTE com um objeto JSON válido, sem texto antes ou depois.\n\n" + usuario)
    with tempfile.TemporaryDirectory() as vazio:
        r = subprocess.run(["agy", "-p", prompt, "--output-format", "json", "--model", MODELO_AGY,
                            "--disable-slash-commands", "--print-timeout", f"{timeout - 30}s"],
                           capture_output=True, text=True, timeout=timeout, cwd=vazio)
    if r.returncode != 0:
        raise RuntimeError(f"agy falhou (código {r.returncode}): {r.stderr[-200:]}")
    saida = json.loads(r.stdout.strip().splitlines()[-1])
    if saida.get("status") != "SUCCESS" or not saida.get("response", "").strip():
        # o agy -p pode negar algo em silêncio e devolver vazio: isso é falha, não sucesso
        raise RuntimeError(f"agy sem resposta útil (status {saida.get('status')})")
    ESCRITOR_REGISTRO.append(f"agy {MODELO_AGY} respondeu em {saida.get('duration_seconds', 0):.0f}s")
    return _json_de(saida["response"])


def gerar_json(sistema, usuario, temperatura=0.8, modelo=None, papel="fiscal"):
    """papel='escritor' usa LOL_LLM_ESCRITOR (padrão agy: gera); 'fiscal' usa LOL_LLM (padrão claude: confere)."""
    quem = os.environ.get("LOL_LLM_ESCRITOR", "agy") if papel == "escritor" else provedor()
    if quem == "agy":
        try:
            return agy(sistema, usuario)
        except Exception as e:  # agy lento ou sem resposta: a rodada é escrita pelo Claude e isso fica registrado
            ESCRITOR_REGISTRO.append(f"agy falhou ({str(e)[:80]}); rodada escrita pelo Claude")
            return claude(sistema, usuario)
    if quem == "claude":
        return claude(sistema, usuario)
    from gemini import gerar_json as g
    return g(sistema, usuario, temperatura=temperatura, modelo=modelo)
