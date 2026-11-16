"""
core/blinds.py
Validacao de blinds pre-flop -- versao funcional (sem classe).

Substitui core/blinds_manager.py (BlindsManager).
Importar:
    from core.blinds import validate_preflop_bets
"""
from typing import List, Optional

from core.models import Player, Position


def validate_preflop_bets(
    players: List[Player],
    bb_amount: float,
    sb_amount: Optional[float] = None,
    tolerance: float = 0.01,
) -> List[int]:
    """
    Identifica seats de Big Blind baseado nas apostas pre-flop observadas.

    Args:
        players: lista de Player com current_bet ja preenchido.
        bb_amount: valor esperado do BB.
        sb_amount: opcional, valor esperado do SB. Default = bb_amount / 2.
        tolerance: margem em unidades (default 0.01) pra evitar erro de float.

    Returns:
        Lista de seats identificados como BB.

    Efeito colateral:
        Marca player.pos_preflop = Position.BB nos jogadores identificados,
        e Position.SB nos small blinds.
    """
    if sb_amount is None:
        sb_amount = bb_amount / 2

    bb_seats: List[int] = []
    for player in players:
        if not player.is_present or player.stack <= 0:
            continue
        bet = player.current_bet
        if abs(bet - bb_amount) <= tolerance:
            bb_seats.append(player.seat)
            player.pos_preflop = Position.BB
        elif abs(bet - sb_amount) <= tolerance:
            player.pos_preflop = Position.SB
    return bb_seats
