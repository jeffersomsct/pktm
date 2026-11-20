"""
pk_agent/dqn/train/train_loop.py
Treino do DQN contra o Slumbot.

    train()   monta o ambiente e o agente reais (precisa de torch) e chama fit();
    fit()     e o loop em si. So chama metodos do agente e do ambiente (nada de tensores aqui),
              entao roda com agente e ambiente falsos (ver tests/test_train_loop.py);
    initial_td_error() / save_checkpoint()  sao as unicas partes que tocam no torch.

Execucao (da raiz do projeto):  python -m pk_agent.dqn.main
"""
import re
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Callable, List

import numpy as np

from paths import DATA_DIR
from pk_agent.slumbot.client import credentials_from_env

STATE_DIM = 133                         # tamanho do vetor de PokerStateRepresentation.create_state_vector
ACTION_DIM = 3                          # fold, call/check, bet/raise
ACTION_LETTERS = {0: "f", 1: "c", 2: "b"}
NUM_PLAYERS = 2                         # heads-up
_BET = re.compile(r"b(\d+)")


# ============================================================
# Metricas
# ============================================================

@dataclass
class Metrics:
    """Uma serie por episodio (antes eram duas listas paralelas para a mesma coisa)."""
    rewards: List[float] = field(default_factory=list)
    avg_rewards: List[float] = field(default_factory=list)     # media movel dos ultimos 100
    losses: List[float] = field(default_factory=list)          # perda media do episodio; NaN se nao houve aprendizado
    epsilons: List[float] = field(default_factory=list)
    total_reward: float = 0.0

    def record(self, episode_reward: float, episode_losses: List[float], epsilon: float) -> float:
        """Registra um episodio e devolve a media movel."""
        self.rewards.append(episode_reward)
        self.total_reward += episode_reward
        average = float(np.mean(self.rewards[-100:]))
        self.avg_rewards.append(average)
        self.losses.append(float(np.mean(episode_losses)) if episode_losses else float("nan"))
        self.epsilons.append(epsilon)
        return average


def plot_progress(metrics: Metrics, path) -> None:
    """Grava o grafico de progresso. Nao abre janela (antes um plt.show() prendia o treino no fim)."""
    from matplotlib.figure import Figure         # API orientada a objeto: sem pyplot, sem backend grafico

    figure = Figure(figsize=(15, 10))
    axes = figure.subplots(2, 2)
    panels = [
        (axes[0][0], metrics.losses, "Perda média por episódio", "Perda"),
        (axes[0][1], metrics.rewards, "Recompensa por episódio", "Recompensa"),
        (axes[1][0], metrics.avg_rewards, "Recompensa média (100 episódios)", "Recompensa média"),
        (axes[1][1], metrics.epsilons, "Valor de epsilon", "Epsilon"),
    ]
    for axis, values, title, ylabel in panels:
        axis.plot(values)
        axis.set_title(title)
        axis.set_xlabel("Episódio")
        axis.set_ylabel(ylabel)
    figure.tight_layout()
    figure.savefig(str(path))


def save_metrics(metrics: Metrics, path) -> None:
    """Dados brutos em .npz (antes: np.save de um dict, que e pickle e exige allow_pickle para ler)."""
    np.savez(str(path), loss=metrics.losses, reward=metrics.rewards,
             avg_reward=metrics.avg_rewards, epsilon=metrics.epsilons)


# ============================================================
# Partes que dependem de torch
# ============================================================

def initial_td_error(agent, state, action_idx, reward, next_state, done, device) -> float:
    """Erro TD da transicao, usado como prioridade inicial no replay priorizado."""
    import torch
    with torch.no_grad():
        state_tensor = torch.from_numpy(np.array([state])).float().to(device)
        next_state_tensor = torch.from_numpy(np.array([next_state])).float().to(device)

        current_q = agent.policy_net(state_tensor)[0][action_idx].item()
        next_q = agent.target_net(next_state_tensor)[0].max().item()

        expected_q = reward + (1 - done) * agent.gamma * next_q
        return abs(current_q - expected_q)


def save_checkpoint(agent, path, episode: int) -> None:
    import torch
    torch.save({
        "policy_net": agent.policy_net.state_dict(),
        "target_net": agent.target_net.state_dict(),
        "optimizer": agent.optimizer.state_dict(),
        "episode": episode,
        "epsilon": agent.epsilon,
    }, str(path))


# ============================================================
# O loop
# ============================================================

def _state_vector(state_rep, env, pot_size):
    response = env.last_response
    return state_rep.create_state_vector(
        response.get("hole_cards", []), response.get("board", []), pot_size, env.stack_size,
        response.get("action", ""), response.get("client_pos", 0), NUM_PLAYERS,
    )


def run_episode(env, agent, state_rep, reward_system, td_error: Callable):
    """Joga uma mao. Devolve (recompensa do episodio, perdas do aprendizado)."""
    env.reset()
    reward_system.reset()
    state = _state_vector(state_rep, env, pot_size=0)
    episode_reward, episode_losses, done = 0, [], False

    while not done:
        action_idx = agent.act(state)
        _, reward_raw, done, _ = env.step(action_idx)

        response = env.last_response
        bet_amounts = [int(value) for value in _BET.findall(response.get("action", ""))]
        pot_size = sum(bet_amounts) * 2                    # estimativa: ambos os jogadores apostaram
        call_amount = bet_amounts[-1] if bet_amounts else 0
        next_state = _state_vector(state_rep, env, pot_size)

        reward = reward_system.calculate_reward(
            ACTION_LETTERS[action_idx], reward_raw, pot_size, env.stack_size,
            response.get("hole_cards", []), response.get("board", []), call_amount, done,
            response.get("client_pos", 0), NUM_PLAYERS,
        )

        agent.remember(state, action_idx, reward, next_state, done,
                       error=td_error(agent, state, action_idx, reward, next_state, done))
        loss = agent.learn()
        if loss is not None:
            episode_losses.append(loss)

        state = next_state
        episode_reward += reward

    return episode_reward, episode_losses


def fit(env, agent, state_rep, reward_system, episodes: int, save_path, td_error: Callable,
        checkpoint: Callable = save_checkpoint, log: Callable = print) -> Metrics:
    save_path = Path(save_path)
    save_path.mkdir(parents=True, exist_ok=True)
    metrics = Metrics()

    for episode in range(episodes):
        episode_reward, episode_losses = run_episode(env, agent, state_rep, reward_system, td_error)
        average = metrics.record(episode_reward, episode_losses, agent.epsilon)

        if episode % 10 == 0:
            mean_loss = np.mean(episode_losses) if episode_losses else 0
            log(f"Episódio {episode}, Recompensa: {episode_reward:.2f}, Média: {average:.2f}, "
                f"Total: {metrics.total_reward:.2f}, ε: {agent.epsilon:.2f}, Loss: {mean_loss:.4f}")
        if episode % 100 == 0:
            checkpoint(agent, save_path / f"dqn_poker_ep{episode}.pt", episode)
        if episode % 500 == 0 and episode > 0:
            plot_progress(metrics, save_path / f"training_progress_episode_{episode}.png")
            save_metrics(metrics, save_path / f"training_data_episode_{episode}.npz")

    checkpoint(agent, save_path / "dqn_poker_final.pt", episodes - 1)
    plot_progress(metrics, save_path / "training_results.png")
    log(f"\nTreinamento concluído! Recompensa total acumulada: {metrics.total_reward:.2f}")
    return metrics


def train(episodes=10000, save_path=DATA_DIR / "models", username=None, password=None):
    """Monta o ambiente e o agente reais e treina. Credenciais: argumentos ou SLUMBOT_USERNAME/PASSWORD."""
    import torch
    from pk_agent.dqn.agent.dqn_agent import DQNAgent
    from pk_agent.dqn.train.reward_system import PokerRewardSystem
    from pk_agent.dqn.train.slumbot_env import SlumbotEnv
    from pk_agent.dqn.train.state_representation import PokerStateRepresentation

    if username is None and password is None:
        username, password = credentials_from_env()
    env = SlumbotEnv(username=username, password=password)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Usando dispositivo: {device}")
    agent = DQNAgent(STATE_DIM, ACTION_DIM, device)

    fit(env, agent, PokerStateRepresentation(), PokerRewardSystem(), episodes, save_path,
        td_error=partial(initial_td_error, device=device))
    return agent
