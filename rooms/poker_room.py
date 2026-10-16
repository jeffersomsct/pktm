from poker_table_recognizer import TableAnalyzer, TableState, TableInfo, Player
from config.room_config import get_swc_poker_config_v2, get_acr_poker_config, get_bodog_poker_config
from config.room_config import RoomConfig
from typing import List, Optional
import numpy as np

class PokerRoom:
    """
    Classe principal para gerenciar uma sala de poker.
    Centraliza todas as informações da mesa e fornece interface para estratégia.
    
    Nomes de salas suportados:
        - "SwC Poker - usuário jeffpk": SwC Poker
        - "Bodog.com - Poker Lobby": Bodog Poker
        - "Lobby ACR Poker Conectado como jeffersom": ACR Poker
    """
    
    def __init__(self, room_name: str):
        self.room_name = room_name
        self.room_config = self._load_room_config(room_name)
        self.analyzer = TableAnalyzer(self.room_config)
        
        # Estado atual da mesa
        self._current_players: List[Player] = []
        self._bb_positions: List[int] = []
        self._dealer_position: int = -1
        self._current_hand: str = ""
        self._current_pot: str = ""
        self._current_small_pot: str = ""
        self._current_community_cards: List[tuple] = []
    
    def _load_room_config(self, room_name: str) -> RoomConfig:
        """Carrega a configuração apropriada baseada no nome da sala."""
        if "SwC Poker" in room_name:
            return get_swc_poker_config_v2()
        elif "Bodog" in room_name:
            return get_bodog_poker_config()
        elif "ACR Poker" in room_name:
            return get_acr_poker_config()
        else:
            print(f"Aviso: Nome de sala não reconhecido: {room_name}. Usando configuração padrão.")
            return get_swc_poker_config_v2()
    
    def update_table_state(self, snapshot: Optional[np.ndarray] = None) -> TableInfo:
        """
        Atualiza o estado da mesa analisando o snapshot.
        
        Args:
            snapshot: Imagem da mesa (numpy array). Se None, usa imagem de exemplo.
            
        Returns:
            TableInfo com todas as informações atualizadas
        """
        table_info = self.analyzer.analyze_table(snapshot)
        
        # Atualiza o estado interno diretamente do TableInfo
        self._current_players = table_info.players
        self._bb_positions = table_info.bb_positions
        self._dealer_position = table_info.dealer_position
        self._current_hand = table_info.hand
        self._current_pot = table_info.pot
        self._current_small_pot = table_info.small_pot
        self._current_community_cards = table_info.community_cards
        
        return table_info
    
    # Propriedades para acesso fácil às informações da mesa
    @property
    def players(self) -> List[Player]:
        """Lista de jogadores na mesa."""
        return self._current_players
    
    @property
    def active_players(self) -> List[Player]:
        """Lista de jogadores ativos (presentes e com fichas)."""
        return [p for p in self._current_players if p.is_present and p.stack > 0]
    
    @property
    def dealer_position(self) -> int:
        """Posição do dealer."""
        return self._dealer_position
    
    @property
    def bb_positions(self) -> List[int]:
        """Posições dos big blinds."""
        return self._bb_positions
    
    @property
    def pot(self) -> str:
        """Valor do pot principal."""
        return self._current_pot
    
    @property
    def small_pot(self) -> str:
        """Valor do pot secundário."""
        return self._current_small_pot
    
    @property
    def hand_id(self) -> str:
        """ID da mão atual."""
        return self._current_hand
    
    @property
    def community_cards(self) -> List[tuple]:
        """Cartas comunitárias no formato [(rank, suit), ...]."""
        return self._current_community_cards
    
    @property
    def config(self) -> RoomConfig:
        """Configuração da sala."""
        return self.room_config
    
    def get_player_by_position(self, position: int) -> Optional[Player]:
        """Retorna o jogador em uma posição específica."""
        for player in self._current_players:
            if player.position == position:
                return player
        return None
    
    def get_sb_player(self) -> Optional[Player]:
        """Retorna o jogador no small blind."""
        for player in self._current_players:
            if player.pos_preflop and player.pos_preflop.value == 'SB':
                return player
        return None
    
    def get_bb_player(self) -> Optional[Player]:
        """Retorna o jogador no big blind."""
        for player in self._current_players:
            if player.pos_preflop and player.pos_preflop.value == 'BB':
                return player
        return None