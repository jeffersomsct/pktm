"""
core/models.py
Modelos de dados centralizados do pktm.

TODOS os dataclasses e enums do dominio poker ficam aqui.
Outros modulos importam deste, nunca o contrario.

Migracao da versao anterior:
  - Player.position (int, era o assento)  -> Player.seat
  - TableInfo.pot / small_pot: str        -> float
  - TableInfo.community_cards: List[tuple] -> List[Card]
  - PlayerPositionInfo (removido)         -> usar Player.pos_preflop
  - Novos: Action, StreetRecord, HandRecord, TableSession, Pot, HeroInfo,
           TournamentInfo, Card
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import time


# ============================================================
# ENUMS
# ============================================================

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


class ActionType(Enum):
    FOLD = "FOLD"
    CHECK = "CHECK"
    CALL = "CALL"
    BET = "BET"
    RAISE = "RAISE"
    ALL_IN = "ALL_IN"
    POST_SB = "POST_SB"
    POST_BB = "POST_BB"
    POST_ANTE = "POST_ANTE"
    SIT_OUT = "SIT_OUT"


class GameType(Enum):
    CASH = "cash"
    MTT = "mtt"
    SNG = "sng"
    SPIN = "spin"


# Ordem de acao preflop (utilitario para HandOrchestrator e strategists)
POSITION_ORDER_PREFLOP: List[Position] = [
    Position.UTG, Position.UTG_PLUS_1, Position.UTG_PLUS_2, Position.MP,
    Position.HJ, Position.CO, Position.BTN, Position.SB, Position.BB,
]

# Ordem de acao pos-flop (SB primeiro, BTN por ultimo)
POSITION_ORDER_POSTFLOP: List[Position] = [
    Position.SB, Position.BB, Position.UTG, Position.UTG_PLUS_1,
    Position.UTG_PLUS_2, Position.MP, Position.HJ, Position.CO, Position.BTN,
]


# ============================================================
# CARTAS
# ============================================================

@dataclass(frozen=True)
class Card:
    """Carta de poker. Imutavel para poder ser usada em sets/dicts."""
    rank: str   # '2'-'9', 'T', 'J', 'Q', 'K', 'A'
    suit: str   # 'S' (Spades), 'H' (Hearts), 'D' (Diamonds), 'C' (Clubs)

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


# ============================================================
# JOGADOR
# ============================================================

@dataclass
class Player:
    name: str
    seat: int                                  # antes chamado 'position' (0-8)
    stack: float
    current_bet: float = 0.0
    pos_preflop: Optional[Position] = None
    is_present: bool = True
    is_active: bool = True                     # na mao atual (nao deu fold)
    is_hero: bool = False
    is_all_in: bool = False
    just_joined: bool = False
    pending_big_blind: bool = False
    sitting_out: bool = False
    disconnected: bool = False
    hole_cards: List[Card] = field(default_factory=list)
    shown_cards: List[Card] = field(default_factory=list)   # showdown
    last_action: Optional[ActionType] = None
    last_action_amount: float = 0.0

    @property
    def is_button(self) -> bool:
        return self.pos_preflop == Position.BTN


# ============================================================
# ACAO
# ============================================================

@dataclass
class Action:
    """Uma acao individual dentro de uma street, em sequencia."""
    order: int                                 # 1, 2, 3... dentro da street
    player_name: str
    seat: int
    type: ActionType
    amount: float = 0.0
    street: Street = Street.PREFLOP
    timestamp: float = field(default_factory=time.time)


# ============================================================
# POTE
# ============================================================

@dataclass
class Pot:
    """Um pote (main ou side). Suporta multi-all-in."""
    amount: float
    eligible_seats: List[int] = field(default_factory=list)
    is_main: bool = True


# ============================================================
# INFO DE HERO (quando hero esta na mao)
# ============================================================

@dataclass
class HeroInfo:
    seat: int
    hole_cards: List[Card] = field(default_factory=list)
    is_turn: bool = False
    available_actions: List[ActionType] = field(default_factory=list)
    min_raise: float = 0.0
    max_raise: float = 0.0
    call_amount: float = 0.0


# ============================================================
# INFO DE TORNEIO (MTT/SNG)
# ============================================================

@dataclass
class TournamentInfo:
    tournament_id: str
    table_number: int
    level: int = 1
    players_remaining: int = 0
    average_stack: float = 0.0
    is_itm: bool = False                       # in the money


# ============================================================
# STREET RECORD (sequencia de acoes em uma rodada)
# ============================================================

@dataclass
class StreetRecord:
    street: Street
    board_before: List[Card] = field(default_factory=list)
    pot_before: float = 0.0
    actions: List[Action] = field(default_factory=list)
    pot_after: float = 0.0


# ============================================================
# HAND RECORD (uma mao inteira)
# ============================================================

@dataclass
class HandRecord:
    hand_id: str                               # do SwC (muda a cada mao)
    table_id: str                              # hash estavel da TableSession
    tournament_id: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    sb_amount: float = 0.0
    bb_amount: float = 0.0
    ante: float = 0.0
    straddle: float = 0.0
    hero_seat: Optional[int] = None
    hero_cards: List[Card] = field(default_factory=list)
    dealer_seat: int = -1
    streets: Dict[Street, StreetRecord] = field(default_factory=dict)
    pots: List[Pot] = field(default_factory=list)
    winners: List[str] = field(default_factory=list)
    stack_deltas: Dict[str, float] = field(default_factory=dict)
    snapshot_paths: List[str] = field(default_factory=list)

    @property
    def current_street(self) -> Street:
        """Street mais avancada registrada."""
        if Street.RIVER in self.streets:
            return Street.RIVER
        if Street.TURN in self.streets:
            return Street.TURN
        if Street.FLOP in self.streets:
            return Street.FLOP
        return Street.PREFLOP


# ============================================================
# TABLE SESSION (identidade persistente da mesa)
# ============================================================

@dataclass
class TableSession:
    table_id: str                              # hash estavel
    room_name: str
    game_type: GameType
    stakes: str                                # ex.: "0.10/0.20" ou "MTT"
    table_name: str                            # ex.: "Table Kraken" ou "T#12345 Table 4"
    max_seats: int = 9
    created_at: float = field(default_factory=time.time)
    last_seen_at: float = field(default_factory=time.time)
    last_hand_id: Optional[str] = None
    last_x: int = 0
    last_y: int = 0
    last_w: int = 0
    last_h: int = 0
    last_player_names: List[str] = field(default_factory=list)
    tournament: Optional[TournamentInfo] = None
    hands: List[HandRecord] = field(default_factory=list)

    @property
    def current_hand(self) -> Optional[HandRecord]:
        return self.hands[-1] if self.hands else None


# ============================================================
# TABLE INFO (estado bruto observado pelo recognizer)
# ============================================================

@dataclass
class TableInfo:
    """
    Saida bruta do TableRecognizer: tudo que foi possivel extrair de uma foto.

    Campos novos (vs versao anterior):
      - sb_amount, bb_amount, ante (float estruturado em vez de inferido)
      - hero: Optional[HeroInfo]
      - pots: List[Pot]  (substitui small_pot para multi-all-in)
      - tournament: Optional[TournamentInfo]
      - snapshot_path: caminho do PNG que originou este TableInfo
    """
    hand: str
    pot: float
    small_pot: float
    dealer_position: int                       # -1 se nao detectado
    community_cards: List[Card] = field(default_factory=list)
    players: List[Player] = field(default_factory=list)
    bb_positions: List[int] = field(default_factory=list)
    sb_amount: float = 0.0
    bb_amount: float = 0.0
    ante: float = 0.0
    hero: Optional[HeroInfo] = None
    pots: List[Pot] = field(default_factory=list)
    tournament: Optional[TournamentInfo] = None
    snapshot_path: Optional[str] = None
