"""
Loop de treino do DQN (pk_agent/dqn/train/train_loop.py) com ambiente e agente FALSOS: o loop nao
toca em torch, entao da para testar sem ele. A equivalencia com o loop antigo foi verificada a parte
(3678 chamadas identicas a act/remember/learn em 600 episodios).

Rodar da raiz do projeto:   python tests/test_train_loop.py
"""
import sys
import tempfile
from pathlib import Path

try:
    import matplotlib  # noqa: F401
except ImportError as error:
    print(f"PULADO: {error.name} nao instalado (pip install -r requirements-train.txt)")
    sys.exit(0)

import numpy as np

from _common import ROOT  # noqa: F401  (ajusta sys.path)
from pk_agent.dqn.train.reward_system import PokerRewardSystem
from pk_agent.dqn.train.state_representation import PokerStateRepresentation
from pk_agent.dqn.train.train_loop import Metrics, fit, run_episode


class FakeEnv:
    stack_size = 20000

    def __init__(self):
        self.last_response = None

    def reset(self):
        self.hist = ""
        self.last_response = {"hole_cards": ["Ah", "Kd"], "board": [], "action": "", "client_pos": 1}

    def step(self, action):
        self.hist += {0: "f", 1: "b300", 2: "c"}.get(action, "c")
        done = len(self.hist) >= 5 or action == 0                    # duas acoes terminam a mao
        self.last_response = {**self.last_response, "action": self.hist}
        return np.zeros(138), (100 if done else 0), done, self.last_response


class FakeAgent:
    epsilon = 0.5
    gamma = 0.99

    def __init__(self):
        self.acts = self.learns = 0
        self.remembered = []

    def act(self, state):
        self.acts += 1
        return 1                                                      # sempre 'b300'... depois 'c' pelo FakeEnv

    def remember(self, *args, error=None):
        self.remembered.append((args[1], args[4], error))

    def learn(self):
        self.learns += 1
        return 0.25 if self.learns % 2 == 0 else None


class RecordingReward(PokerRewardSystem):
    def __init__(self):
        super().__init__()
        self.calls = []

    def calculate_reward(self, *args):
        self.calls.append(args)
        return super().calculate_reward(*args)


def td_error(agent, state, action_idx, reward, next_state, done):
    return 0.125


# ---- um episodio: estimativa do pot e do call a partir da string de acao ----
agent, reward_system = FakeAgent(), RecordingReward()
episode_reward, losses = run_episode(FakeEnv(), agent, PokerStateRepresentation(), reward_system, td_error)
assert agent.acts == len(agent.remembered) == 2 and agent.learns == 2
assert [r[2] for r in agent.remembered] == [0.125, 0.125]                     # o erro TD injetado vai para o replay
assert agent.remembered[-1][1] is True and agent.remembered[0][1] is False    # 'done' so no ultimo passo
# apos 'b300': pot estimado = 300 * 2 = 600 e call_amount = 300 (args do calculate_reward: acao, raw, pot, stack, ..., call, done)
first = reward_system.calls[0]
assert first[0] == "c" and first[2] == 600 and first[3] == 20000 and first[6] == 300 and first[7] is False
assert losses == [0.25]

# ---- fit completo: agenda de logs, checkpoints, graficos e arquivos ----
checkpoints, logs = [], []
with tempfile.TemporaryDirectory(prefix="treino_\u00e7_") as tmp:
    before_pyplot = "matplotlib.pyplot" in sys.modules
    metrics = fit(FakeEnv(), FakeAgent(), PokerStateRepresentation(), PokerRewardSystem(), episodes=501,
                  save_path=Path(tmp) / "models", td_error=td_error,
                  checkpoint=lambda agent, path, episode: checkpoints.append((Path(path).name, episode)), log=logs.append)
    assert ("matplotlib.pyplot" in sys.modules) == before_pyplot, "o treino nao pode abrir pyplot/janela (antes: plt.show())"

    # checkpoints a cada 100 episodios + o final (com o indice do ultimo episodio)
    assert checkpoints == [(f"dqn_poker_ep{e}.pt", e) for e in (0, 100, 200, 300, 400, 500)] + [("dqn_poker_final.pt", 500)]

    # log a cada 10 episodios e a mensagem final
    assert len([l for l in logs if l.startswith("Episódio")]) == 51 and logs[0].startswith("Episódio 0, ")
    assert logs[-1].startswith("\nTreinamento concluído! Recompensa total acumulada: ")

    # graficos e dados: PNG validos e .npz que abre sem pickle
    models = Path(tmp) / "models"
    for name in ("training_results.png", "training_progress_episode_500.png"):
        assert (models / name).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", name
    data = np.load(models / "training_data_episode_500.npz", allow_pickle=False)
    assert set(data.files) == {"loss", "reward", "avg_reward", "epsilon"}
    assert all(len(data[key]) == 501 for key in data.files)          # episodios 0..500: o 500 ja foi registrado

# ---- Metrics: media movel dos ultimos 100 e NaN quando nao houve aprendizado ----
m = Metrics()
for i in range(150):
    m.record(float(i), [] if i % 2 else [1.0, 3.0], 0.1)
assert m.avg_rewards[0] == 0.0 and m.avg_rewards[99] == np.mean(range(100)) and m.avg_rewards[149] == np.mean(range(50, 150))
assert m.total_reward == sum(range(150))
assert m.losses[0] == 2.0 and np.isnan(m.losses[1]) and len(m.losses) == 150      # alinhado ao episodio

print("OK: loop de treino com agente falso (agenda, pot/call, metricas, graficos sem janela, .npz).")
