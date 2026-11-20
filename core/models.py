"""
core/models.py
Modelos de dados do pktm. Outros modulos importam deste, nunca o contrario.

Hoje o fluxo e: o reconhecedor produz um TableInfo por captura e o storage grava essa captura
pelo numero da mao. Street / ActionType / Action ficam como vocabulario para a etapa de deduzir
o que cada jogador fez (ainda nao implementada).
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
# TABLE INFO (estado bruto observado pelo recognizer)
# ============================================================

@dataclass
class TableInfo:
    """
    Saida bruta do TableRecognizer: tudo que foi possivel extrair de UMA captura.

    sb_amount / bb_amount / ante vem do titulo da janela (ver core.blinds.parse_blinds).
    hero fica para quando a captura ler as cartas do heroi; snapshot_path e o PNG da captura.
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
    snapshot_path: Optional[str] = None
