# Este é o primeiro passo da implementação, focando no rastreamento básico de uma mão de poker. O código:

# Rastreia o estado completo de uma mão
# Processa ações dos jogadores
# Mantém controle do pot e apostas
# Gerencia as streets e o board
# Valida ações (ex: não pode dar check quando há uma aposta)

# Para integrar com seu sistema de captura existente, você precisaria:

# Chamar start_new_hand() quando detectar uma nova mão
# Usar process_action() quando detectar ações dos jogadores
# Chamar update_board() quando novas cartas aparecerem no board


from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime

class Position(Enum):
    BTN = "BTN"       # Button (dealer)
    SB = "SB"         # Small Blind
    BB = "BB"         # Big Blind
    UTG = "UTG"       # Under The Gun
    MP = "MP"         # Middle Position
    CO = "CO"         # Cutoff
    HJ = "HJ"         # Hijack (just before the cutoff)
    LJ = "LJ"         # Lojack (just before hijack)
    EP = "EP"         # Early Position (can represent UTG+1)
    OTB = "OTB"       # Out of position (any position when you’re not in the last positions)

class Action(Enum):
    FOLD = "FOLD"
    CHECK = "CHECK"
    CALL = "CALL"
    BET = "BET"
    RAISE = "RAISE"
    ALL_IN = "ALL_IN"

class Street(Enum):
    PREFLOP = "PREFLOP"
    FLOP = "FLOP"
    TURN = "TURN"
    RIVER = "RIVER"

@dataclass
class Player:
    name: str
    position: Position
    stack: float
    current_bet: float = 0
    total_invested: float = 0
    is_active: bool = True

@dataclass
class HandState:
    hand_id: str
    timestamp: datetime
    street: Street
    pot: float
    current_bet: float
    players: Dict[str, Player]
    board_cards: List[str]
    action_history: List[dict]

class HandTracker:
    def __init__(self):
        self.current_hand: Optional[HandState] = None
        self.position_order = [
            Position.BTN, Position.SB, Position.BB,
            Position.UTG, Position.MP, Position.CO
        ]
    
    def start_new_hand(self, players_info: Dict[str, dict]) -> HandState:
        """Inicia o rastreamento de uma nova mão"""
        # Gera um ID único para a mão
        hand_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Inicializa os jogadores com suas posições e stacks
        players = {}
        for name, info in players_info.items():
            players[name] = Player(
                name=name,
                position=info['position'],
                stack=info['stack']
            )
        
        # Cria o estado inicial da mão
        self.current_hand = HandState(
            hand_id=hand_id,
            timestamp=datetime.now(),
            street=Street.PREFLOP,
            pot=0.0,
            current_bet=0.0,
            players=players,
            board_cards=[],
            action_history=[]
        )
        
        return self.current_hand
    
    def process_action(self, player_name: str, action_type: Action, amount: float = 0) -> dict:
        """Processa uma ação de um jogador e atualiza o estado da mão"""
        if not self.current_hand or player_name not in self.current_hand.players:
            raise ValueError("Mão não iniciada ou jogador inválido")
        
        player = self.current_hand.players[player_name]
        
        # Calcula quanto o jogador precisa pagar para continuar
        to_call = self.current_hand.current_bet - player.current_bet
        
        # Processa a ação baseado no tipo
        action_result = {
            'player': player_name,
            'action': action_type,
            'amount': amount,
            'street': self.current_hand.street,
            'pot_size': self.current_hand.pot,
            'stack_before': player.stack,
            'timestamp': datetime.now()
        }
        
        if action_type == Action.FOLD:
            player.is_active = False
        
        elif action_type == Action.CHECK:
            if to_call > 0:
                raise ValueError("Não pode dar check quando há uma aposta")
        
        elif action_type == Action.CALL:
            if to_call > 0:
                # Atualiza os valores do jogador
                player.stack -= to_call
                player.current_bet += to_call
                player.total_invested += to_call
                self.current_hand.pot += to_call
        
        elif action_type in [Action.BET, Action.RAISE]:
            if amount < to_call * 2:
                raise ValueError("Raise deve ser pelo menos o dobro da aposta anterior")
            
            # Atualiza os valores do jogador
            total_to_pay = amount
            player.stack -= total_to_pay
            player.current_bet = amount
            player.total_invested += total_to_pay
            self.current_hand.pot += total_to_pay
            self.current_hand.current_bet = amount
        
        elif action_type == Action.ALL_IN:
            amount = player.stack
            player.stack = 0
            player.current_bet += amount
            player.total_invested += amount
            self.current_hand.pot += amount
            if amount > self.current_hand.current_bet:
                self.current_hand.current_bet = amount
        
        # Adiciona a ação ao histórico
        self.current_hand.action_history.append(action_result)
        
        return action_result
    
    def update_board(self, new_cards: List[str]):
        """Atualiza as cartas do board e a street atual"""
        if not self.current_hand:
            raise ValueError("Mão não iniciada")
        
        old_len = len(self.current_hand.board_cards)
        self.current_hand.board_cards.extend(new_cards)
        new_len = len(self.current_hand.board_cards)
        
        # Atualiza a street baseado no número de cartas
        if new_len == 3:
            self.current_hand.street = Street.FLOP
        elif new_len == 4:
            self.current_hand.street = Street.TURN
        elif new_len == 5:
            self.current_hand.street = Street.RIVER
        
        # Reseta as apostas atuais quando muda a street
        if new_len > old_len:
            self.reset_street_bets()
    
    def reset_street_bets(self):
        """Reseta as apostas dos jogadores para a nova street"""
        if self.current_hand:
            self.current_hand.current_bet = 0
            for player in self.current_hand.players.values():
                player.current_bet = 0
    
    def get_active_players(self) -> List[Player]:
        """Retorna a lista de jogadores ainda ativos na mão"""
        if not self.current_hand:
            return []
        return [p for p in self.current_hand.players.values() if p.is_active]
    
    def get_hand_summary(self) -> dict:
        """Retorna um resumo da mão atual"""
        if not self.current_hand:
            return {}
        
        return {
            'hand_id': self.current_hand.hand_id,
            'street': self.current_hand.street.value,
            'pot': self.current_hand.pot,
            'board': self.current_hand.board_cards,
            'players': {
                name: {
                    'position': player.position.value,
                    'stack': player.stack,
                    'invested': player.total_invested,
                    'is_active': player.is_active
                }
                for name, player in self.current_hand.players.items()
            },
            'actions': self.current_hand.action_history
        }

def main():
    # Exemplo de uso
    tracker = HandTracker()
    
    # Informações dos jogadores (exemplo)
    players_info = {
        "Player1": {"position": Position.BTN, "stack": 1000},
        "Player2": {"position": Position.SB, "stack": 1500},
        "Player3": {"position": Position.BB, "stack": 2000}
    }
    
    # Inicia uma nova mão
    tracker.start_new_hand(players_info)
    
    # Processa algumas ações
    tracker.process_action("Player1", Action.RAISE, 30)  # BTN raise
    tracker.process_action("Player2", Action.CALL, 30)   # SB call
    tracker.process_action("Player3", Action.CALL, 30)   # BB call
    
    # Flop
    tracker.update_board(["Ah", "Kh", "2d"])
    
    # Mostra o resumo da mão
    print(tracker.get_hand_summary())

if __name__ == "__main__":
    main()