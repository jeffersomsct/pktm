import numpy as np
from pk_agent.dqn.train.slumbot_env import SlumbotEnv

class PokerEnvAdapter:
    """
    Adaptador para o ambiente de poker para uso com Deep CFR.
    Adiciona funcionalidades necessárias para o algoritmo CFR.
    """
    def __init__(self, username=None, password=None):
        self.env = SlumbotEnv(username, password)
        self.current_player_id = 0  # Simplificado: alterna entre 0 e 1
        
    def reset(self):
        """
        Reseta o ambiente e retorna o estado inicial.
        """
        state = self.env.reset()
        self.current_player_id = self.get_position()
        return state
    
    def step(self, action):
        """
        Executa uma ação no ambiente.
        """
        next_state, reward, done, info = self.env.step(action)
        
        self.current_player_id =  self.get_position()
            
        return next_state, reward, done, info
    
    def current_player(self):
        """
        Retorna o ID do jogador atual.
        """
        return self.current_player_id
    
    def legal_actions(self):
        """
        Retorna as ações legais no estado atual.
        """
        # Retorna todas as ações disponíveis
        from pk_agent.common.constants import ACTION_LIST
        return ACTION_LIST
    
    def get_hole_cards(self):
        """
        Retorna as cartas do jogador.
        """
        if self.env.last_response and 'hole_cards' in self.env.last_response:
            return self.env.last_response['hole_cards']
        return []
    
    def get_board_cards(self):
        """
        Retorna as cartas comunitárias.
        """
        if self.env.last_response and 'board' in self.env.last_response:
            return self.env.last_response['board']
        return []
    
    def get_pot_size(self):
        """
        Retorna o tamanho do pote.
        """
        # Simplificado: estima o pote com base nas apostas
        if self.env.last_response and 'action' in self.env.last_response:
            action_str = self.env.last_response['action']
            # Extrai valores de apostas (simplificado)
            bets = [int(b[1:]) for b in action_str.split('/') if b.startswith('b')]
            return sum(bets) * 2  # Simplificado: assume que cada aposta foi paga
        return 0
    
    def get_stack_size(self):
        """
        Retorna o tamanho da pilha do jogador.
        """
        return self.env.stack_size
    
    def get_bet_history(self):
        """
        Retorna o histórico de apostas.
        """
        if self.env.last_response and 'action' in self.env.last_response:
            return self.env.last_response['action'].split('/')[-1]
        return ""
    
    def get_position(self):
        """
        Retorna a posição do jogador.
        """
        if self.env.last_response and 'client_pos' in self.env.last_response:
            return self.env.last_response['client_pos']
        return 0
    
    def get_num_players_in_hand(self):
        """
        Retorna o número de jogadores na mão.
        """
        # Simplificado: sempre 2 jogadores
        return 2
    
    def clone(self):
        """
        Cria uma cópia do ambiente atual.
        """
        # Simplificado: cria um novo ambiente
        # Em uma implementação real, você precisaria copiar o estado completo
        clone = PokerEnvAdapter()
        clone.current_player_id = self.current_player_id
        return clone