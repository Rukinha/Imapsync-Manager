"""Tradução e classificação de erros comuns do imapsync / conexão de rede.

O imapsync produz uma saída bastante verbosa e em inglês. Este módulo:
  1. Detecta se uma falha é de conexão/rede (para decidir se vale a pena
     tentar novamente automaticamente).
  2. Gera uma mensagem curta em português para exibir na tabela e no log,
     em vez de o usuário precisar garimpar a causa no meio de centenas
     de linhas de saída técnica.
"""
from __future__ import annotations

import re

# Cada entrada: (regex para casar na saída bruta, mensagem amigável em PT-BR, é_erro_de_conexao)
_PADROES: list[tuple[re.Pattern, str, bool]] = [
    (re.compile(r"connection refused", re.I),
     "Conexão recusada pelo servidor (verifique host/porta).", True),
    (re.compile(r"connection reset by peer", re.I),
     "Conexão foi encerrada pelo servidor no meio da transferência.", True),
    (re.compile(r"(network is unreachable|no route to host)", re.I),
     "Servidor inacessível na rede (verifique conectividade/firewall).", True),
    (re.compile(r"(timed out|timeout)", re.I),
     "Tempo de conexão esgotado (timeout) — servidor não respondeu a tempo.", True),
    (re.compile(r"name or service not known|nodename nor servname|getaddrinfo", re.I),
     "Não foi possível resolver o endereço do servidor (host incorreto ou DNS).", True),
    (re.compile(r"ssl.*(handshake|certificate|verify)", re.I),
     "Falha na conexão segura (SSL/TLS) — certifique-se de que a porta/SSL do perfil está correta.", True),
    (re.compile(r"broken pipe", re.I),
     "Conexão foi interrompida durante a transferência (broken pipe).", True),

    (re.compile(r"(login failed|authentication failed|auth.*fail|invalid credentials)", re.I),
     "Falha de autenticação — usuário ou senha incorretos.", False),
    (re.compile(r"password.*(incorrect|invalid|wrong)", re.I),
     "Senha incorreta.", False),
    (re.compile(r"user unknown|no such user|mailbox does ?n[o']?t exist", re.I),
     "Conta/caixa de e-mail não encontrada no servidor.", False),
    (re.compile(r"permission denied", re.I),
     "Permissão negada pelo servidor para essa operação.", False),
    (re.compile(r"quota exceeded|over quota", re.I),
     "Cota de armazenamento excedida no servidor de destino.", False),
    (re.compile(r"too many (connections|simultaneous)", re.I),
     "Servidor recusou por excesso de conexões simultâneas — reduza o paralelismo.", False),
]


def traduzir_erro(saida_bruta: str) -> tuple[str, bool]:
    """Analisa a saída (stdout/stderr) do imapsync e retorna:
        (mensagem_amigavel_pt_br, é_erro_de_conexao)

    Se nenhum padrão conhecido for encontrado, retorna uma mensagem genérica
    apontando para o log completo, e é_erro_de_conexao=False.
    """
    for padrao, mensagem, conexao in _PADROES:
        if padrao.search(saida_bruta):
            return mensagem, conexao

    return "Falha não identificada automaticamente — consulte o log completo da conta.", False
