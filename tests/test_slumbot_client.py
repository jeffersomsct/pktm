"""
Cliente do Slumbot (pk_agent/slumbot/client.py) contra um servidor falso local.

Mede o que a troca de requests.post por requests.Session prometia: reaproveitar a conexao. E checa o
timeout (antes, uma conexao travada pendurava o treino para sempre) e o tratamento de erros.

Rodar da raiz do projeto:   python tests/test_slumbot_client.py
"""
import sys
import time

try:
    import requests
except ImportError as error:
    print(f"PULADO: {error.name} nao instalado (pip install -r requirements-train.txt)")
    sys.exit(0)

import _fake_slumbot
from _common import ROOT  # noqa: F401  (ajusta sys.path)
from pk_agent.slumbot.client import SlumbotClient, SlumbotError, credentials_from_env

server, url = _fake_slumbot.start()
try:
    # login
    client = SlumbotClient(host=url)
    assert client.login("jeff", "ok") == "tok-1" and client.token == "tok-1"
    assert server.requests[-1] == ("/api/login", {"username": "jeff", "password": "ok"})
    for password, expected in (("bad", "403"), ("bad", "credenciais invalidas"), ("nojson", "JSON"), ("outra", "token")):
        try:
            SlumbotClient(host=url).login("jeff", password)
        except SlumbotError as error:
            assert expected in str(error), (password, str(error))      # a mensagem do servidor chega ao usuario
        else:
            raise AssertionError(f"login com senha {password!r} deveria falhar")

    # mao e acoes: o token vai junto
    hand = client.new_hand()
    assert hand["hole_cards"] == ["Ah", "Kd"] and server.requests[-1] == ("/api/new_hand", {"token": "tok-1"})
    assert client.act("c")["action"] == "c" and server.requests[-1] == ("/api/act", {"token": "tok-1", "incr": "c"})
    assert client.act("f")["winnings"] == -100
    anonymous = SlumbotClient(host=url)                 # sem login: o servidor entrega um token na primeira mao
    anonymous.new_hand()
    assert anonymous.token == "tok-anon" and server.requests[-1] == ("/api/new_hand", {})

    # reaproveitamento de conexao: Session usa 1 conexao para N chamadas; requests.post solto abre N
    before = server.connections
    reusing = SlumbotClient(host=url)
    for _ in range(6):
        reusing.new_hand()
    assert server.connections - before == 1, f"Session deveria reaproveitar a conexao: {server.connections - before}"
    before = server.connections
    for _ in range(6):
        requests.post(f"{url}/api/new_hand", json={})
    assert server.connections - before == 6

    # timeout: servidor lento -> erro rapido em vez de pendurar
    server.delay = 1.5
    slow = SlumbotClient(host=url, timeout=0.3)
    started = time.perf_counter()
    try:
        slow.act("c")
    except requests.Timeout:
        pass
    else:
        raise AssertionError("deveria dar timeout")
    assert time.perf_counter() - started < 1.2, "o timeout nao cortou a espera"
    server.delay = 0

    # erro HTTP do servidor: levanta HTTPError (o ambiente trata)
    server.act_status = 500
    try:
        client.act("c")
    except requests.HTTPError:
        pass
    else:
        raise AssertionError("HTTP 500 deveria levantar HTTPError")
    server.act_status = 200
finally:
    server.shutdown()

# credenciais vem do ambiente, nunca do codigo
import os  # noqa: E402
saved = {k: os.environ.pop(k, None) for k in ("SLUMBOT_USERNAME", "SLUMBOT_PASSWORD")}
try:
    assert credentials_from_env() == (None, None)
    os.environ["SLUMBOT_USERNAME"] = "u"
    assert credentials_from_env() == (None, None)               # so usuario: incompleto
    os.environ["SLUMBOT_PASSWORD"] = "p"
    assert credentials_from_env() == ("u", "p")
finally:
    for key, value in saved.items():
        os.environ.pop(key, None)
        if value is not None:
            os.environ[key] = value

print("OK: login, token, 1 conexao para 6 chamadas (contra 6 sem Session), timeout, erro HTTP, credenciais do ambiente.")
