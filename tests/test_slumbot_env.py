"""
SlumbotEnv (pk_agent/dqn/train/slumbot_env.py) contra o servidor falso: usa o cliente unico,
codifica o estado, calcula acoes legais e trata erros como antes.

Rodar da raiz do projeto:   python tests/test_slumbot_env.py
"""
import sys

try:
    import gymnasium  # noqa: F401
    import requests   # noqa: F401
except ImportError as error:
    print(f"PULADO: {error.name} nao instalado (pip install -r requirements-train.txt)")
    sys.exit(0)

import numpy as np

import _fake_slumbot
from _common import ROOT  # noqa: F401  (ajusta sys.path)
from pk_agent.common.constants import ALL_IN, BET_2BB, BET_3BB, BET_5BB, BET_10BB, CALL, FOLD
from pk_agent.dqn.train.slumbot_env import SlumbotEnv
from pk_agent.slumbot.client import SlumbotClient

server, url = _fake_slumbot.start()
try:
    # com credenciais, o login acontece no cliente unico
    env = SlumbotEnv(username="jeff", password="ok", client=SlumbotClient(host=url))
    assert env.token == "tok-1" and server.requests[0][0] == "/api/login"

    # last_response ainda nao existe: antes isso levantava AttributeError
    assert env._get_current_action() == ""

    # reset: nova mao; Ah e Kd codificados nas posicoes de 'hole cards' (valor*4 + naipe)
    state = env.reset()
    assert isinstance(state, np.ndarray) and state.shape == (138,)
    assert state[12 * 4 + 0] == 1 and state[11 * 4 + 1] == 1 and state[:52].sum() == 2     # Ah, Kd
    assert state[104 + 0] == 1                                                              # client_pos 0
    assert env.last_response["hole_cards"] == ["Ah", "Kd"] and server.requests[-1][1] == {"token": "tok-1"}

    # acoes legais no inicio da mao: call/check e todos os raises (200 BB de stack)
    assert env.get_legal_actions() == [CALL, BET_2BB, BET_3BB, BET_5BB, BET_10BB, ALL_IN]

    # step: call continua a mao; fold termina com a perda informada pelo servidor
    next_state, reward, done, info = env.step(CALL)
    assert (reward, done) == (0, False) and info["action_description"] == "Call/Check"
    assert server.requests[-1] == ("/api/act", {"token": "tok-1", "incr": "c"})
    next_state, reward, done, info = env.step(FOLD)
    assert (reward, done) == (-100, True) and info["action_description"] == "Fold"

    # raise vira 'b<valor>' (2 BB = 200 fichas)
    env.reset()
    env.step(BET_2BB)
    assert server.requests[-1][1]["incr"] == "b200", server.requests[-1]

    # erro do servidor: comportamento preservado (estado zerado, -1000, mao encerrada)
    server.act_status = 500
    state, reward, done, info = env.step(CALL)
    assert (reward, done) == (-1000, True) and not state.any() and "error" in info
    server.act_status = 200

    # resposta com error_msg encerra a mao sem recompensa
    original = env._convert_action
    env._convert_action = lambda action_idx: "x"
    _, reward, done, info = env.step(CALL)
    assert (reward, done) == (0, True) and info["error_msg"] == "acao invalida"
    env._convert_action = original

    # sem credenciais: joga anonimo e o token vem na primeira mao
    anonymous = SlumbotEnv(client=SlumbotClient(host=url))
    assert anonymous.token is None
    anonymous.reset()
    assert anonymous.token == "tok-anon"
finally:
    server.shutdown()

print("OK: ambiente usa o cliente unico; estado, acoes legais, step e erros.")
