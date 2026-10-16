import numpy as np
import random
from collections import deque

class ReservoirBuffer:
    """
    Buffer de memória baseado em amostragem por reservatório para Deep CFR.
    Mantém uma amostra uniforme de experiências quando o buffer está cheio.
    """
    def __init__(self, capacity):
        self.capacity = capacity
        self.buffer = []
        self.position = 0
        self.size = 0
    
    def add(self, experience):
        """
        Adiciona uma experiência ao buffer usando amostragem por reservatório.
        """
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            # Amostragem por reservatório
            idx = random.randint(0, self.position)
            if idx < self.capacity:
                self.buffer[idx] = experience
        
        self.position += 1
        self.size = min(self.position, self.capacity)
    
    def sample(self, batch_size):
        """
        Amostra um batch de experiências do buffer.
        """
        if self.size < batch_size:
            return random.sample(self.buffer, self.size)
        else:
            return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return self.size

class MemoryBuffer:
    """
    Buffer de memória para armazenar experiências de treinamento para Deep CFR.
    Mantém buffers separados para cada jogador.
    """
    def __init__(self, num_players, capacity_per_player):
        self.advantage_memories = [ReservoirBuffer(capacity_per_player) for _ in range(num_players)]
        self.strategy_memory = ReservoirBuffer(capacity_per_player)
    
    def add_advantage_experience(self, player_id, info_state, action, advantage, iteration):
        """
        Adiciona uma experiência de vantagem ao buffer do jogador correspondente.
        """
        self.advantage_memories[player_id].add((info_state, action, advantage, iteration))
    
    def add_strategy_experience(self, info_state, strategy, iteration):
        """
        Adiciona uma experiência de estratégia ao buffer.
        """
        self.strategy_memory.add((info_state, strategy, iteration))
    
    def sample_advantage(self, player_id, batch_size):
        """
        Amostra experiências de vantagem do buffer do jogador.
        """
        return self.advantage_memories[player_id].sample(batch_size)
    
    def sample_strategy(self, batch_size):
        """
        Amostra experiências de estratégia do buffer.
        """
        return self.strategy_memory.sample(batch_size)