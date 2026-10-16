from enum import Enum
from typing import List, Dict
from dataclasses import dataclass

class Street(Enum):
    PREFLOP = "Pre-Flop"
    FLOP = "Flop"
    TURN = "Turn"
    RIVER = "River"

class Position(Enum):
    UTG = "UTG"
    UTG_PLUS_1 = "UTG+1"
    UTG_PLUS_2 = "UTG+2"
    MP = "MP"
    HJ = "HJ"
    CO = "CO"
    BTN = "BTN"
    SB = "SB"
    BB = "BB"

@dataclass
class PlayerPositionInfo:
    player_name: str
    position_name: Position
    is_button: bool = False

class PokerHandState:
    def __init__(self, hand_id: str, num_players: int, dealer_position: int):
        self.hand_id = hand_id
        self.num_players = num_players
        self.dealer_position = dealer_position
        self.community_cards = []
        self.current_street = Street.PREFLOP
        self.pot = 0.0
        self.player_positions: Dict[str, PlayerPositionInfo] = {}

    def update_community_cards(self, cards):
        """Atualiza as cartas comunitárias e determina a rodada."""
        self.community_cards = cards
        if not cards:
            self.current_street = Street.PREFLOP
        elif len(cards) == 3:
            self.current_street = Street.FLOP
        elif len(cards) == 4:
            self.current_street = Street.TURN
        elif len(cards) == 5:
            self.current_street = Street.RIVER

    def calculate_positions(self, players):
        """
        Calcula as posições de todos os jogadores na mesa.
        Usa as posições já identificadas (BB, SB, BTN) e calcula as demais.
        """
        num_players = len(players)
        
        # Encontrar índices de BB, SB e BTN
        bb_index = None
        sb_index = None
        btn_index = None
        
        for player in players:
            if player.pos_preflop == Position.BB:
                bb_index = player.position
            elif player.pos_preflop == Position.SB:
                sb_index = player.position
            elif player.pos_preflop == Position.BTN:
                btn_index = player.position
        
        # Se não encontrou, usar o dealer_position como referência
        if btn_index is None:
            btn_index = self.dealer_position
        
        # Mapear posições em ordem: UTG -> ... -> BTN -> SB -> BB
        # Esta é a ordem das posições começando de UTG até BB
        position_order = [
            Position.UTG,
            Position.UTG_PLUS_1,
            Position.UTG_PLUS_2,
            Position.MP,
            Position.HJ,
            Position.CO,
            Position.BTN,
            Position.SB,
            Position.BB,
        ]
        
        # Remover posições conforme o número de jogadores
        if num_players < 9:
            position_order = position_order[-(num_players):]
        
        self.player_positions = {}
        
        # O índice do BTN na ordem é len - 2 (antes de SB e BB)
        btn_position_index = position_order.index(Position.BTN)
        
        # Calcular o índice inicial (onde UTG começa)
        start_index = (btn_index - btn_position_index) % num_players
        
        for i, position in enumerate(position_order):
            player_index = (start_index + i) % num_players
            player = players[player_index]
            
            is_button = (position == Position.BTN)
            
            self.player_positions[player.name] = PlayerPositionInfo(
                player_name=player.name,
                position_name=position,
                is_button=is_button
            )
            player.pos_preflop = position