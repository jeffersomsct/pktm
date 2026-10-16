# agent/dqn_agent.py
import torch
import torch.nn.functional as F
from pk_agent.dqn.agent.model import DuelingDQN
from pk_agent.dqn.agent.replay_buffer import PrioritizedReplayBuffer
import random
import numpy as np

class DQNAgent:
    def __init__(self, state_dim, action_dim, device):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.device = device

        # Usa o modelo Dueling DQN
        self.policy_net = DuelingDQN(state_dim, action_dim).to(device)
        self.target_net = DuelingDQN(state_dim, action_dim).to(device)
        self.optimizer = torch.optim.Adam(self.policy_net.parameters(), lr=1e-4)
        self.update_target()

        self.replay_buffer = PrioritizedReplayBuffer(100_000)
        self.batch_size = 64
        self.gamma = 0.99
        self.epsilon = 1.0
        self.epsilon_min = 0.05
        self.epsilon_decay = 0.999
        self.learn_step = 0
        self.update_freq = 100
        
        # Parâmetros adicionais para melhorar a estabilidade
        self.beta_start = 0.4
        self.beta_frames = 100000
        self.beta = self.beta_start

    def update_target(self):
        self.target_net.load_state_dict(self.policy_net.state_dict())

    def act(self, state):
        # Converte para numpy array primeiro
        state = np.array([state])
        # Depois converte para tensor
        state = torch.from_numpy(state).float().to(self.device)
        
        if random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        
        with torch.no_grad():
            q_values = self.policy_net(state)
        return int(q_values.argmax().item())

    def remember(self, *args, error):
        experience = tuple(args)
        self.replay_buffer.add(experience, error)

    def learn(self):
        if len(self.replay_buffer.buffer) < self.batch_size:
            return
            
        # Atualiza beta para amostragem prioritária
        self.beta = min(1.0, self.beta_start + self.learn_step * (1.0 - self.beta_start) / self.beta_frames)

        states, actions, rewards, next_states, dones, weights, indices = self.replay_buffer.sample(self.batch_size, self.beta)

        states = states.to(self.device)
        next_states = next_states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        dones = dones.to(self.device)
        weights = weights.to(self.device)

        # Double DQN: seleciona ações usando a rede de política
        q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        next_actions = self.policy_net(next_states).argmax(1)
        
        # Mas avalia usando a rede alvo
        next_q_values = self.target_net(next_states).gather(1, next_actions.unsqueeze(1)).squeeze(1)

        # Calcula o valor Q esperado
        expected_q = rewards + (1 - dones) * self.gamma * next_q_values
        
        # Calcula o erro TD ponderado
        loss = (q_values - expected_q.detach()).pow(2) * weights
        
        # Atualiza prioridades no buffer
        prios = (q_values - expected_q.detach()).abs().cpu().detach().numpy()

        # Otimização
        self.optimizer.zero_grad()
        loss.mean().backward()
        
        # Clipping de gradiente para estabilidade
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 10)
        
        self.optimizer.step()

        # Atualiza prioridades no buffer
        self.replay_buffer.update_priorities(indices, prios)

        # Atualiza a rede alvo periodicamente
        if self.learn_step % self.update_freq == 0:
            self.update_target()

        self.learn_step += 1
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        
        return loss.mean().item()
