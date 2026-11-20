"""
core/blinds.py
Blinds sem depender de ler apostas na mesa:
  - valores (sb, bb, ante): do titulo da janela;
  - posicoes (BTN/SB/BB): do assento do dealer e da ordem de jogo.
"""
import re
from typing import List, Tuple

from core.models import Player, Position

_NUM = r"\d+(?:\.\d+)?"
_LEVEL = re.compile(rf"Level\s+({_NUM})\s*/\s*({_NUM})(?:\s+ante\s+({_NUM}))?", re.IGNORECASE)
_STAKES = re.compile(rf"({_NUM})\s*/\s*({_NUM})")


def parse_blinds(title) -> Tuple[float, float, float]:
    """
    (sb, bb, ante) lidos do titulo da janela, ou (0, 0, 0) se nao houver.

    Torneio: '... Level 40/80 ante 16;  Next Level 50/100 ante 20' -> (40, 80, 16)  (vale o nivel ATUAL, o 1o)
    Cash:    '... 0.02/0.04 ...'                                   -> (0.02, 0.04, 0)
    """
    text = title or ""
    match = _LEVEL.search(text)
    if match:
        return float(match.group(1)), float(match.group(2)), float(match.group(3) or 0)
    match = _STAKES.search(text)
    if match:
        return float(match.group(1)), float(match.group(2)), 0.0
    return 0.0, 0.0, 0.0


def assign_blinds(players: List[Player], dealer_seat: int, n_seats: int, step: int = -1) -> List[int]:
    """
    Marca BTN / SB / BB em player.pos_preflop (so jogadores presentes) e devolve [seat do BB].

    A ordem de jogo parte do dealer e anda de `step` em `step` assentos, com volta. Com 3+ jogadores:
    SB = primeiro presente depois do dealer, BB = o seguinte, BTN = o dealer (se estiver sentado: o
    botao pode ficar num assento vazio). Heads-up com o dealer sentado: ele e o SB e o outro e o BB.
    Devolve [] se o dealer nao foi detectado ou ha menos de 2 jogadores.
    """
    if dealer_seat < 0:
        return []
    seated = {p.seat: p for p in players if p.is_present}
    if len(seated) < 2:
        return []

    after_dealer = [(dealer_seat + k * step) % n_seats for k in range(1, n_seats + 1)]
    in_play_order = [seat for seat in after_dealer if seat in seated]

    if len(seated) == 2 and dealer_seat in seated:
        sb_seat, bb_seat = dealer_seat, in_play_order[0]
    else:
        sb_seat, bb_seat = in_play_order[0], in_play_order[1]
        if dealer_seat in seated:
            seated[dealer_seat].pos_preflop = Position.BTN
    seated[sb_seat].pos_preflop = Position.SB
    seated[bb_seat].pos_preflop = Position.BB
    return [bb_seat]
