"""
rooms/poker_room.py
Interface principal para uma mesa de poker.

Nao duplica campos de TableInfo: guarda apenas _last_table_info e expoe via properties.
get_player_by_position() fica por compat; o nome preferido e get_player_by_seat().
"""
from typing import List, Optional
import numpy as np

from core.models import (
    TableInfo, Player, Position, HeroInfo, Card,
)
from config.room_config import RoomConfig, get_swc_poker_config_v3
from poker_table_recognizer import TableAnalyzer

# Salas suportadas: trecho do nome da janela -> funcao que monta a config.
SUPPORTED_ROOMS = {
    "SwC Poker": get_swc_poker_config_v3,
}


class PokerRoom:
    """
    Wrapper de TableAnalyzer + RoomConfig.

    Nao mantem estado duplicado -- apenas repassa o ultimo TableInfo observado.
    """

    def __init__(self, room_name: str):
        self.room_name = room_name
        self.config = self._load_room_config(room_name)
        self.analyzer = TableAnalyzer(self.config)
        self._last_table_info: Optional[TableInfo] = None

    def _load_room_config(self, room_name: str) -> RoomConfig:
        for key, make_config in SUPPORTED_ROOMS.items():
            if key in room_name:
                return make_config()
        raise ValueError(
            f"Sala nao suportada: {room_name!r}. Suportadas: {', '.join(SUPPORTED_ROOMS)}. "
            "(Antes caia em silencio na config da SwC e lia lixo.)"
        )

    def update_table_state(self, snapshot: Optional[np.ndarray] = None,
                           title: Optional[str] = None) -> TableInfo:
        """
        Atualiza o estado da mesa analisando um snapshot.

        Args:
            snapshot: imagem BGR. Se None, usa sample image da config.
            title: titulo da janela (as blinds saem dele: 'Level 40/80 ante 16').

        Returns:
            TableInfo com tudo extraido desta captura.
        """
        self._last_table_info = self.analyzer.analyze_table(snapshot, title=title)
        return self._last_table_info

    # ---- Acesso ao estado bruto ----

    @property
    def table_info(self) -> Optional[TableInfo]:
        """Ultimo TableInfo observado."""
        return self._last_table_info

    @property
    def players(self) -> List[Player]:
        return self._last_table_info.players if self._last_table_info else []

    @property
    def active_players(self) -> List[Player]:
        """Jogadores ativos: presentes, na mao (is_active), com fichas."""
        if not self._last_table_info:
            return []
        return [
            p for p in self._last_table_info.players
            if p.is_present and p.is_active and p.stack > 0
        ]

    @property
    def dealer_position(self) -> int:
        return self._last_table_info.dealer_position if self._last_table_info else -1

    @property
    def bb_positions(self) -> List[int]:
        return self._last_table_info.bb_positions if self._last_table_info else []

    @property
    def pot(self) -> float:
        return self._last_table_info.pot if self._last_table_info else 0.0

    @property
    def small_pot(self) -> float:
        return self._last_table_info.small_pot if self._last_table_info else 0.0

    @property
    def hand_id(self) -> str:
        return self._last_table_info.hand if self._last_table_info else ""

    @property
    def community_cards(self) -> List[Card]:
        return self._last_table_info.community_cards if self._last_table_info else []

    @property
    def hero(self) -> Optional[HeroInfo]:
        return self._last_table_info.hero if self._last_table_info else None

    @property
    def sb_amount(self) -> float:
        return self._last_table_info.sb_amount if self._last_table_info else 0.0

    @property
    def bb_amount(self) -> float:
        return self._last_table_info.bb_amount if self._last_table_info else 0.0

    @property
    def ante(self) -> float:
        return self._last_table_info.ante if self._last_table_info else 0.0

    # ---- Helpers ----

    def get_player_by_seat(self, seat: int) -> Optional[Player]:
        for p in self.players:
            if p.seat == seat:
                return p
        return None

    # Compatibilidade com nome antigo
    def get_player_by_position(self, position: int) -> Optional[Player]:
        return self.get_player_by_seat(position)

    def get_sb_player(self) -> Optional[Player]:
        for p in self.players:
            if p.pos_preflop == Position.SB:
                return p
        return None

    def get_bb_player(self) -> Optional[Player]:
        for p in self.players:
            if p.pos_preflop == Position.BB:
                return p
        return None

    def get_hero_player(self) -> Optional[Player]:
        for p in self.players:
            if p.is_hero:
                return p
        return None
