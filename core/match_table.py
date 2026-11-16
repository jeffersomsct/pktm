"""
core/match_table.py
Matching fuzzy de TableSession: dada uma observacao atual,
encontra a sessao armazenada que melhor casa.

Use quando o bot volta pra uma mesa e precisa saber se eh a mesma
sessao persistida anteriormente.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from core.models import TableSession, GameType


@dataclass
class ObservedTable:
    """Sinalizacao observada ao vivo, pra casar com TableSession armazenada."""
    room_name: str
    game_type: GameType
    stakes: str
    table_name: str
    title: str                                  # titulo bruto da janela
    x: int
    y: int
    w: int = 0
    h: int = 0
    player_names: List[str] = field(default_factory=list)
    hand_id: Optional[str] = None
    tournament_id: Optional[str] = None
    table_number: Optional[int] = None


def score_match(stored: TableSession, observed: ObservedTable) -> float:
    """
    Score de similaridade entre uma sessao armazenada e a observacao atual.

    Pesos (max ~150):
      - stakes + table_name iguais:           50
      - posicao fuzzy (tolerancia 80px):      30
      - overlap de jogadores:                 40
      - bonus MTT (tournament_id + table#):  +30
    """
    score = 0.0

    # 1. Stakes + table_name -- peso alto
    if stored.stakes == observed.stakes and stored.table_name == observed.table_name:
        score += 50
    elif stored.stakes == observed.stakes:
        score += 20

    # 2. Posicao (fuzzy, tolerancia 80px) -- peso medio
    dx = abs(stored.last_x - observed.x)
    dy = abs(stored.last_y - observed.y)
    if dx <= 80 and dy <= 80:
        score += 30 * (1 - (dx + dy) / 160)

    # 3. Player fingerprint (overlap de nomes) -- peso alto
    if observed.player_names:
        stored_set = set(stored.last_player_names)
        observed_set = set(observed.player_names)
        common = stored_set & observed_set
        total = stored_set | observed_set
        if total:
            score += 40 * len(common) / len(total)

    # Bonus MTT: tournament_id + table_number iguais
    if (observed.tournament_id and stored.tournament
            and stored.tournament.tournament_id == observed.tournament_id
            and stored.tournament.table_number == observed.table_number):
        score += 30

    return score


def find_matching_session(
    sessions: List[TableSession],
    observed: ObservedTable,
    threshold: float = 60.0,
) -> Optional[TableSession]:
    """
    Encontra a sessao armazenada que melhor casa com a observacao.

    Args:
        sessions: todas as sessoes conhecidas.
        observed: o que foi detectado agora.
        threshold: score minimo pra considerar mesma sessao (default 60).

    Returns:
        A TableSession casada, ou None se nenhuma passou do threshold.
    """
    if not sessions:
        return None

    scored = [(s, score_match(s, observed)) for s in sessions]
    scored.sort(key=lambda t: t[1], reverse=True)
    best_session, best_score = scored[0]

    if best_score >= threshold:
        return best_session
    return None
