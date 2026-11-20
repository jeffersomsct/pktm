"""
Exemplo de como usar o PokerRoom para implementar estratégias.

Este arquivo demonstra como acessar todas as informações da mesa
de forma organizada e limpa através da interface do PokerRoom.
"""

from rooms.poker_room import PokerRoom
from poker_table_recognizer import Player
from typing import List


class PokerStrategy:
    """Classe base para implementação de estratégias de poker."""
    
    def __init__(self, room: PokerRoom):
        self.room = room
    
    def should_fold(self) -> bool:
        """Decide se deve dar fold."""
        # Exemplo: fold se não tiver cartas comunitárias ainda
        if not self.room.community_cards:
            return True
        return False
    
    def should_call(self) -> bool:
        """Decide se deve dar call."""
        # Exemplo: call se tiver pelo menos 3 cartas comunitárias
        return len(self.room.community_cards) >= 3
    
    def should_raise(self) -> bool:
        """Decide se deve dar raise."""
        # Exemplo: raise se tiver 5 cartas comunitárias (river)
        return len(self.room.community_cards) == 5
    
    def get_raise_amount(self) -> float:
        """Calcula o valor do raise."""
        # Exemplo: raise 2x o pot (room.pot ja e float)
        return self.room.pot * 2
    
    def analyze_opponents(self) -> List[Player]:
        """Analisa os oponentes ativos."""
        opponents = []
        for player in self.room.active_players:
            # Filtra apenas oponentes (não é você)
            if player.name != "YourName":  # Substitua pelo seu nome
                opponents.append(player)
        return opponents
    
    def calculate_pot_odds(self) -> float:
        """Calcula as pot odds."""
        # Aqui você adicionaria a lógica para calcular o valor da aposta atual
        # Por enquanto, retorna apenas o valor do pot (room.pot ja e float)
        return self.room.pot
    
    def get_position_advantage(self) -> str:
        """Determina a vantagem posicional."""
        dealer_pos = self.room.dealer_position
        active_count = len(self.room.active_players)
        
        if dealer_pos == -1:
            return "Desconhecida"
        
        # Lógica simplificada de posição
        if active_count <= 3:
            return "Heads-up ou 3-handed"
        elif dealer_pos in [0, 1]:
            return "Early Position"
        elif dealer_pos in [2, 3]:
            return "Middle Position"
        else:
            return "Late Position"


def main():
    """Exemplo de uso da estratégia."""
    
    # Inicializar sala
    room = PokerRoom("SwC Poker - Logged in as jeffpk")
    
    # Atualizar estado da mesa (tudo fica armazenado no room)
    room.update_table_state(snapshot=None)
    
    # Criar estratégia
    strategy = PokerStrategy(room)
    
    # Tomar decisões
    print("="*60)
    print("ANÁLISE DE ESTRATÉGIA")
    print("="*60)
    
    print(f"\nCartas comunitárias: {room.community_cards}")
    print(f"Pot: {room.pot}")
    print(f"Posição do dealer: {room.dealer_position}")
    
    print("\n--- Decisões ---")
    print(f"Should fold? {strategy.should_fold()}")
    print(f"Should call? {strategy.should_call()}")
    print(f"Should raise? {strategy.should_raise()}")
    
    if strategy.should_raise():
        print(f"Raise amount: {strategy.get_raise_amount()}")
    
    print(f"\nVantagem posicional: {strategy.get_position_advantage()}")
    
    print("\n--- Oponentes Ativos ---")
    opponents = strategy.analyze_opponents()
    for opp in opponents:
        print(f"  {opp.name} - Stack: {opp.stack} - Bet: {opp.current_bet}")
    
    print("\n--- Acesso Direto às Propriedades ---")
    print(f"room.hand_id: {room.hand_id}")
    print(f"room.pot: {room.pot}")
    print(f"room.small_pot: {room.small_pot}")
    print(f"room.dealer_position: {room.dealer_position}")
    print(f"room.community_cards: {room.community_cards}")
    print(f"room.active_players: {len(room.active_players)} jogadores")
    
    # Acessar jogadores específicos
    sb = room.get_sb_player()
    bb = room.get_bb_player()
    
    if sb:
        print(f"\nSmall Blind: {sb.name} (Stack: {sb.stack})")
    if bb:
        print(f"Big Blind: {bb.name} (Stack: {bb.stack})")


if __name__ == "__main__":
    main()
