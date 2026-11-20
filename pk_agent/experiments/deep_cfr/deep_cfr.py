"""
ESBOCO CONCEITUAL de Deep CFR. Nao roda contra o Slumbot.

O Deep CFR e um algoritmo de self-play: em cada decisao do jogador que treina ele precisa
calcular o valor de TODAS as acoes, ramificando a mao (clone do estado, volta atras). O Slumbot e um
servidor remoto de uma mao so: nao da para clonar nem voltar atras, entao o clone() do
PokerEnvAdapter cria um ambiente novo e sem estado, e os valores contrafactuais saem sem sentido.
Para treinar CFR de verdade use um simulador local (por exemplo OpenSpiel ou RLCard) e deixe o Slumbot
so para AVALIAR o agente. Ver README.md desta pasta.
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random

from paths import DATA_DIR
from pk_agent.experiments.deep_cfr.models import ValueNetwork, AdvantageNetwork
from pk_agent.experiments.deep_cfr.memory import MemoryBuffer
from pk_agent.experiments.deep_cfr.regret import masked_softmax, regret_matching
from pk_agent.dqn.train.state_representation import PokerStateRepresentation

class DeepCFR:
    """
    Implementação do algoritmo Deep Counterfactual Regret Minimization (Deep CFR).
    """
    def __init__(self, state_dim, action_dim, num_players=2, device="cpu"):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.num_players = num_players
        self.device = device
        
        # Redes de vantagem para cada jogador
        self.advantage_networks = [
            AdvantageNetwork(state_dim, action_dim).to(device) 
            for _ in range(num_players)
        ]
        
        # Rede de estratégia (política de arrepemdimento)
        self.strategy_network = ValueNetwork(state_dim, action_dim).to(device)
        
        # Otimizadores
        self.advantage_optimizers = [
            optim.Adam(network.parameters(), lr=1e-3)
            for network in self.advantage_networks
        ]
        self.strategy_optimizer = optim.Adam(self.strategy_network.parameters(), lr=1e-3)
        
        # Buffer de memória
        self.memory = MemoryBuffer(num_players, capacity_per_player=1_000_000)
        
        # Representação de estado
        self.state_rep = PokerStateRepresentation()
        
        # Parâmetros de treinamento
        self.advantage_batch_size = 128
        self.strategy_batch_size = 128
        self.num_traversals = 1000
        self.num_iterations = 100
        self.cfr_batch_size = 1000
        
    def _compute_advantages(self, player_id, info_state, legal_actions, iteration):
        """
        Calcula os valores de vantagem para um estado de informação.
        """
        # Converte o estado para tensor
        state_tensor = torch.FloatTensor(info_state).unsqueeze(0).to(self.device)
        
        # Obtém os valores de vantagem da rede
        with torch.no_grad():
            advantages = self.advantage_networks[player_id](state_tensor).squeeze(0).cpu().numpy()
        
        # Filtra apenas ações legais
        masked_advantages = np.ones(self.action_dim) * float('-inf')
        masked_advantages[legal_actions] = advantages[legal_actions]
        
        return masked_advantages
    
    def _compute_strategy(self, advantages, legal_actions):
        """Regret-matching sobre as acoes legais (0 nas ilegais, soma 1)."""
        return regret_matching(advantages, legal_actions)

    def _update_advantage_network(self, player_id, iteration):
        """
        Atualiza a rede de vantagem para um jogador.
        """
        if len(self.memory.advantage_memories[player_id]) < self.advantage_batch_size:
            return
        
        # Amostra experiências
        experiences = self.memory.sample_advantage(player_id, self.advantage_batch_size)
        
        # Prepara os dados para treinamento
        info_states = torch.FloatTensor([exp[0] for exp in experiences]).to(self.device)
        actions = torch.LongTensor([exp[1] for exp in experiences]).to(self.device)
        advantages = torch.FloatTensor([exp[2] for exp in experiences]).to(self.device)
        sample_iterations = torch.FloatTensor([exp[3] for exp in experiences]).to(self.device)
        
        # Pesos para dar mais importância a amostras mais recentes
        weights = (sample_iterations / iteration).to(self.device)
        
        # Forward pass
        pred_advantages = self.advantage_networks[player_id](info_states)
        pred_advantages = pred_advantages.gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Calcula a perda ponderada
        loss = torch.mean(weights * (pred_advantages - advantages) ** 2)
        
        # Otimização
        self.advantage_optimizers[player_id].zero_grad()
        loss.backward()
        self.advantage_optimizers[player_id].step()
        
        return loss.item()
    
    def _update_strategy_network(self, iteration):
        """
        Atualiza a rede de estratégia.
        """
        if len(self.memory.strategy_memory) < self.strategy_batch_size:
            return
        
        # Amostra experiências
        experiences = self.memory.sample_strategy(self.strategy_batch_size)
        
        # Prepara os dados para treinamento
        info_states = torch.FloatTensor([exp[0] for exp in experiences]).to(self.device)
        target_strategies = torch.FloatTensor([exp[1] for exp in experiences]).to(self.device)
        sample_iterations = torch.FloatTensor([exp[2] for exp in experiences]).to(self.device)
        
        # Pesos para dar mais importância a amostras mais recentes
        weights = (sample_iterations / iteration).to(self.device)
        
        # Forward pass
        pred_strategies = torch.softmax(self.strategy_network(info_states), dim=1)
        
        # Calcula a perda de entropia cruzada ponderada
        loss = -torch.mean(weights * torch.sum(target_strategies * torch.log(pred_strategies + 1e-8), dim=1))
        
        # Otimização
        self.strategy_optimizer.zero_grad()
        loss.backward()
        self.strategy_optimizer.step()
        
        return loss.item()
    
    def get_action_probabilities(self, info_state, legal_actions):
        """
        Retorna as probabilidades de ação para um estado de informação.
        """
        # Converte o estado para tensor
        state_tensor = torch.FloatTensor(info_state).unsqueeze(0).to(self.device)
        
        # Obtém as probabilidades da rede de estratégia
        with torch.no_grad():
            logits = self.strategy_network(state_tensor).squeeze(0).cpu().numpy()
        
        # Converte para probabilidades (0 nas ilegais, soma 1)
        return masked_softmax(logits, legal_actions)
    
    def select_action(self, info_state, legal_actions):
        """
        Seleciona uma ação com base nas probabilidades da política.
        """
        probabilities = self.get_action_probabilities(info_state, legal_actions)
        action = np.random.choice(len(probabilities), p=probabilities)
        return action
    
    def _traverse_game_tree(self, env, player_id, iteration):
        """
        Realiza uma travessia do jogo para coletar experiências de treinamento.
        """
        # Implementação simplificada - na prática, você precisaria de uma simulação completa do jogo
        # Esta é uma versão conceitual que mostra a ideia geral
        
        # Reseta o ambiente
        state = env.reset()
        done = False
        
        while not done:
            # Determina o jogador atual
            current_player = env.current_player()
            
            # Obtém as ações legais
            legal_actions = env.legal_actions()
            
            # Converte o estado para representação de informação
            info_state = self.state_rep.create_state_vector(
                env.get_hole_cards(), 
                env.get_board_cards(),
                env.get_pot_size(),
                env.get_stack_size(),
                env.get_bet_history(),
                env.get_position(),
                env.get_num_players_in_hand()
            )
            
            # Se for o jogador que estamos treinando
            if current_player == player_id:
                # Calcula vantagens e estratégia
                advantages = self._compute_advantages(player_id, info_state, legal_actions, iteration)
                strategy = self._compute_strategy(advantages, legal_actions)
                
                # Adiciona experiência de estratégia
                self.memory.add_strategy_experience(info_state, strategy, iteration)
                
                # Seleciona ação com base na estratégia
                action = int(np.random.choice(len(strategy), p=strategy))
            else:
                # Para outros jogadores, usa a política atual
                action_probs = self.get_action_probabilities(info_state, legal_actions)
                action = int(np.random.choice(len(action_probs), p=action_probs))
            
            # Executa a ação
            next_state, reward, done, _ = env.step(action)
            
            # Se o jogo terminou, calcula os valores de vantagem
            if done and current_player == player_id:
                for a in legal_actions:
                    # Calcula o valor counterfactual para cada ação
                    cf_value = self._calculate_counterfactual_value(env, player_id, a)
                    
                    # Calcula a vantagem como diferença entre valor counterfactual e valor esperado
                    advantage = cf_value - reward
                    
                    # Adiciona experiência de vantagem
                    self.memory.add_advantage_experience(player_id, info_state, a, advantage, iteration)
            
            state = next_state
    
    def _calculate_counterfactual_value(self, env, player_id, action):
        """
        Calcula o valor counterfactual de uma ação.
        Esta é uma implementação simplificada.
        """
        # Clone o ambiente para simular a ação
        env_copy = env.clone()
        
        # Executa a ação
        _, reward, _, _ = env_copy.step(action)
        
        # Retorna o valor para o jogador
        return reward
    
    def train(self, env):
        """
        Treina o agente Deep CFR.
        """
        for iteration in range(1, self.num_iterations + 1):
            print(f"Iteração {iteration}/{self.num_iterations}")
            
            # Para cada jogador
            for player_id in range(self.num_players):
                print(f"  Treinando jogador {player_id}")
                
                # Realiza travessias do jogo
                for _ in range(self.num_traversals):
                    self._traverse_game_tree(env, player_id, iteration)
                
                # Atualiza a rede de vantagem
                advantage_loss = self._update_advantage_network(player_id, iteration)
                print(f"    Perda de vantagem: {advantage_loss}")
            
            # Atualiza a rede de estratégia
            strategy_loss = self._update_strategy_network(iteration)
            print(f"  Perda de estratégia: {strategy_loss}")
            
            # Salva o modelo periodicamente
            if iteration % 10 == 0:
                self.save_model(str(DATA_DIR / "models" / f"deep_cfr_iter_{iteration}.pt"))
    
    def save_model(self, path):
        """
        Salva o modelo treinado.
        """
        torch.save({
            'advantage_networks': [net.state_dict() for net in self.advantage_networks],
            'strategy_network': self.strategy_network.state_dict(),
            'advantage_optimizers': [opt.state_dict() for opt in self.advantage_optimizers],
            'strategy_optimizer': self.strategy_optimizer.state_dict()
        }, path)
    
    def load_model(self, path):
        """
        Carrega um modelo treinado.
        """
        checkpoint = torch.load(path)
        
        for i, state_dict in enumerate(checkpoint['advantage_networks']):
            self.advantage_networks[i].load_state_dict(state_dict)
        
        self.strategy_network.load_state_dict(checkpoint['strategy_network'])
        
        for i, state_dict in enumerate(checkpoint['advantage_optimizers']):
            self.advantage_optimizers[i].load_state_dict(state_dict)
        
        self.strategy_optimizer.load_state_dict(checkpoint['strategy_optimizer'])