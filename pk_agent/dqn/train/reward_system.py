# Sistema de recompensas avançado para poker
import numpy as np

class PokerRewardSystem:
    def __init__(self):
        self.previous_pot = 0
        self.previous_stack = 0
        self.action_history = []
        
    def calculate_pot_odds(self, call_amount, pot_size):
        """
        Calcula as pot odds (razão entre o valor a ser pago e o pot total após o pagamento)
        """
        if call_amount == 0:
            return 0
        return pot_size / (pot_size + call_amount)
    
    def calculate_hand_strength(self, hole_cards, board_cards):
        """
        Calcula a força da mão (simplificado)
        Retorna um valor entre 0 e 1
        """
        # Implementação simplificada - em um sistema real, usaria um avaliador de mãos
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
            
        # Limita o valor entre 0 e 1
        return min(max(normalized_strength, 0.0), 1.0)
    
    def evaluate_decision_quality(self, action, hand_strength, pot_odds, position, num_players):
        """
        Avalia a qualidade da decisão com base em princípios estratégicos de poker
        Retorna um valor entre -1 e 1
        """
        # Posição relativa (0 = early, 1 = late)
        position_value = position / max(1, num_players - 1)
        
        # Avalia fold
        if action == 'f':
            # Fold com mão fraca é bom, especialmente em posição inicial
            if hand_strength < 0.3:
                return 0.5 - 0.3 * position_value  # Menos recompensa em posição tardia
            # Fold com mão média depende da posição
            elif hand_strength < 0.6:
                return 0.2 - 0.4 * position_value  # Pode ser ruim em posição tardia
            # Fold com mão forte é geralmente ruim
            else:
                return -0.5 + 0.2 * (1 - position_value)  # Menos penalidade em posição inicial
        
        # Avalia call/check
        elif action in ['c', 'k']:
            # Call com mão fraca é ruim, mas menos ruim com boas pot odds
            if hand_strength < 0.3:
                return -0.3 + 0.5 * pot_odds
            # Call com mão média é neutro a bom dependendo das pot odds
            elif hand_strength < 0.6:
                return 0.0 + 0.4 * pot_odds
            # Call com mão forte é bom
            else:
                return 0.4
        
        # Avalia bet/raise
        elif action in ['b', 'r']:
            # Bet com mão fraca é blefe - recompensa em posição tardia, penaliza em inicial
            if hand_strength < 0.3:
                return -0.4 + 0.8 * position_value
            # Bet com mão média é ok em posição tardia
            elif hand_strength < 0.6:
                return -0.2 + 0.6 * position_value
            # Bet com mão forte é bom
            else:
                return 0.5
        
        return 0.0
    
    def calculate_reward(self, action, reward, pot_size, stack_size, 
                     hole_cards, board_cards, call_amount, is_terminal, position=0, num_players=2):
        """
        Calcula uma recompensa sofisticada considerando múltiplos fatores
        """
        # Inicializa a recompensa final com a recompensa base
        final_reward = reward
        
        # Recompensa base (ganho/perda de fichas)
        base_reward = reward
        
        # Recompensa intermediária baseada na variação do pot e stack
        pot_change = pot_size - self.previous_pot
        stack_change = stack_size - self.previous_stack
        
        # Atualiza valores anteriores
        self.previous_pot = pot_size
        self.previous_stack = stack_size
        
        # Registra a ação no histórico
        self.action_history.append(action)
        
        # Se não for um estado terminal, adiciona recompensas intermediárias
        if not is_terminal:
            # Calcula pot odds
            pot_odds = self.calculate_pot_odds(call_amount, pot_size)
            
            # Calcula força da mão
            hand_strength = self.calculate_hand_strength(hole_cards, board_cards)
            
            # Avalia qualidade da decisão
            decision_quality = self.evaluate_decision_quality(
                action, hand_strength, pot_odds, position, num_players
            )
            
            # Recompensa por decisões estratégicas (peso maior que antes)
            strategic_reward = decision_quality * 0.5
            
            # Recompensa específica para fold - penaliza menos em situações desfavoráveis
            if action == 'f':
                # Se a mão é fraca e/ou pot odds são ruins, reduz a penalidade
                fold_adjustment = 0.0
                if hand_strength < 0.3:
                    fold_adjustment += 0.2
                if pot_odds < 0.2:
                    fold_adjustment += 0.2
                    
                strategic_reward += fold_adjustment
            
            # Recompensa para ações agressivas em posição tardia
            if action in ['b', 'r'] and position / max(1, num_players - 1) > 0.7:
                strategic_reward += 0.1
                
            # Recompensa para check em posição inicial com mão média
            if action == 'k' and position / max(1, num_players - 1) < 0.3 and 0.3 <= hand_strength <= 0.6:
                strategic_reward += 0.1
            
            # Adiciona recompensa intermediária à recompensa base
            final_reward = base_reward + strategic_reward
        else:
            # Em estados terminais, usa a recompensa base mas ajusta com base no histórico de ações
            # Recompensa extra para vitórias com jogo agressivo
            if base_reward > 0 and any(a in ['b', 'r'] for a in self.action_history[-3:]):
                final_reward = base_reward * 1.1
            # Reduz penalidade para folds estratégicos
            elif base_reward < 0 and action == 'f':
                hand_strength = self.calculate_hand_strength(hole_cards, board_cards)
                if hand_strength < 0.4:  # Fold com mão fraca
                    final_reward = base_reward * 0.8  # Reduz a penalidade em 20%
            else:
                final_reward = base_reward
                
        return final_reward
    
    def reset(self):
        """
        Reseta o estado do sistema de recompensas
        """
        self.previous_pot = 0
        self.previous_stack = 0