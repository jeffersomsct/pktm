# Representação do estado do jogo de poker
import numpy as np

class PokerStateRepresentation:
    def __init__(self):
        self.num_features = 150  # Aumentado para acomodar novas features
        
    def encode_cards(self, cards):
        """
        Codifica as cartas do jogador e da mesa.
        cards: lista de strings no formato "Vs" onde V é o valor e s é o naipe
        """
        # Mapeamento de valores e naipes
        values = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, 
                 '9': 7, 'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}
        suits = {'h': 0, 'd': 1, 's': 2, 'c': 3}
        
        # Inicializa vetor de características para cartas (52 posições)
        card_features = np.zeros(52)
        
        for card in cards:
            if len(card) == 2:
                value, suit = card[0], card[1]
                if value in values and suit in suits:
                    idx = values[value] * 4 + suits[suit]
                    card_features[idx] = 1
                    
        return card_features
    
    def calculate_hand_strength(self, hole_cards, board_cards):
        """
        Calcula a força relativa da mão do jogador.
        Retorna um valor entre 0 e 1, onde 1 é a mão mais forte possível.
        """
        # Implementação simplificada - em um sistema real, usaria um avaliador de mãos completo
        
        # Verifica se temos cartas suficientes para avaliar
        if not hole_cards:
            return 0.0
            
        # Extrai valores das cartas
        values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                 '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        # Calcula valor médio das cartas do jogador (simplificado)
        hole_values = [values.get(card[0], 0) for card in hole_cards if len(card) == 2]
        avg_value = sum(hole_values) / len(hole_values) if hole_values else 0
        
        # Normaliza para [0,1]
        normalized_strength = (avg_value - 2) / 12
        
        # Bônus para pares
        if len(hole_values) == 2 and hole_values[0] == hole_values[1]:
            normalized_strength += 0.2
            
        # Bônus para cartas do mesmo naipe (potencial de flush)
        if len(hole_cards) == 2 and hole_cards[0][1] == hole_cards[1][1]:
            normalized_strength += 0.1
            
        # Bônus para cartas sequenciais (potencial de straight)
        if len(hole_values) == 2 and abs(hole_values[0] - hole_values[1]) == 1:
            normalized_strength += 0.1
            
        # Limita o valor entre 0 e 1
        return min(max(normalized_strength, 0.0), 1.0)
    
    def encode_bet_history(self, bet_history, num_rounds=3):
        """
        Codifica o histórico completo de apostas, não apenas a última street.
        Retorna um vetor de características para o histórico de apostas.
        """
        # Inicializa vetor de características para histórico de apostas
        # 5 tipos de ações (f, c, k, b, r) para 3 rounds anteriores
        bet_features = np.zeros(5 * num_rounds)
        
        # Divide o histórico por streets
        streets = bet_history.split('/') if bet_history else []
        
        # Codifica cada street, começando pelas mais recentes
        for i, street in enumerate(streets[-num_rounds:]):
            if i >= num_rounds:
                break
                
            # Conta ocorrências de cada tipo de ação
            fold_count = street.count('f')
            call_count = street.count('c')
            check_count = street.count('k')
            
            # Conta apostas e raises (simplificado)
            bet_count = sum(1 for c in street if c == 'b')
            raise_count = sum(1 for c in street if c == 'r')
            
            # Normaliza contagens
            bet_features[i*5] = min(fold_count, 1)
            bet_features[i*5 + 1] = min(call_count, 1)
            bet_features[i*5 + 2] = min(check_count, 1)
            bet_features[i*5 + 3] = min(bet_count, 1)
            bet_features[i*5 + 4] = min(raise_count, 1)
            
        return bet_features
    
    def encode_position_features(self, position, num_players):
        """
        Codifica características relacionadas à posição do jogador.
        Considera a posição relativa e importância estratégica.
        """
        # Inicializa vetor de características para posição
        position_features = np.zeros(10)
        
        # One-hot para posição absoluta (6 posições)
        if 0 <= position < 6:
            position_features[position] = 1
            
        # Posição relativa (early, middle, late)
        relative_pos = position / max(1, num_players - 1)
        
        # Early position
        if relative_pos < 0.33:
            position_features[6] = 1
        # Middle position
        elif relative_pos < 0.66:
            position_features[7] = 1
        # Late position
        else:
            position_features[8] = 1
            
        # Dealer/Button indicator
        if position == num_players - 1:
            position_features[9] = 1
            
        return position_features
    
    def create_state_vector(self, hole_cards, board_cards, pot_size, stack_size, 
                           bet_history, position, num_players_in_hand):
        """
        Cria um vetor de estado completo para o agente DQN.
        """
        # Codifica cartas (52 posições)
        hole_card_features = self.encode_cards(hole_cards)
        board_card_features = self.encode_cards(board_cards)
        
        # Calcula e codifica força da mão (1 posição)
        hand_strength = self.calculate_hand_strength(hole_cards, board_cards)
        hand_strength_feature = np.array([hand_strength])
        
        # Normaliza valores numéricos
        norm_pot = pot_size / 10000  # Normaliza para [0,1] assumindo pot máximo de 10000
        norm_stack = stack_size / 10000  # Normaliza para [0,1]
        
        # Codifica posição com features melhoradas (10 posições)
        position_features = self.encode_position_features(position, num_players_in_hand)
            
        # Codifica histórico de apostas completo (15 posições para 3 streets)
        bet_features = self.encode_bet_history(bet_history, num_rounds=3)
                
        # Normaliza número de jogadores
        norm_players = (num_players_in_hand - 1) / 8  # Normaliza para [0,1] assumindo máximo de 9 jogadores
        
        # Concatena todas as características
        state_vector = np.concatenate([
            hole_card_features,        # 52 posições
            board_card_features,       # 52 posições
            hand_strength_feature,     # 1 posição (NOVA)
            [norm_pot],                # 1 posição
            [norm_stack],              # 1 posição
            position_features,         # 10 posições (MELHORADA)
            bet_features,              # 15 posições (MELHORADA)
            [norm_players]             # 1 posição
        ])
        
        # Garante que o vetor tenha o tamanho correto
        assert len(state_vector) == 133, f"Vetor de estado tem tamanho {len(state_vector)}, esperado 133"
        
        return state_vector