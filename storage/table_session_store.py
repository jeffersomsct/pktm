"""
storage/table_session_store.py
Persistencia de TableSession em SQLite.

Cada TableSession eh identificada por table_id (hash estavel).
Hands dentro de uma sessao sao persistidas junto (JSON dentro da coluna data).
"""
import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

from core.models import (
    TableSession, HandRecord, StreetRecord, Action, Card, Pot,
    TournamentInfo, Street, Position, ActionType, GameType,
)


_lock = threading.Lock()


# ============================================================
# Serializacao (dataclass -> dict)
# ============================================================

def _serialize_card(c: Card) -> dict:
    return {"rank": c.rank, "suit": c.suit}


def _serialize_action(a: Action) -> dict:
    return {
        "order": a.order,
        "player_name": a.player_name,
        "seat": a.seat,
        "type": a.type.value,
        "amount": a.amount,
        "street": a.street.value,
        "timestamp": a.timestamp,
    }


def _serialize_street_record(sr: StreetRecord) -> dict:
    return {
        "street": sr.street.value,
        "board_before": [_serialize_card(c) for c in sr.board_before],
        "pot_before": sr.pot_before,
        "actions": [_serialize_action(a) for a in sr.actions],
        "pot_after": sr.pot_after,
    }


def _serialize_pot(p: Pot) -> dict:
    return {
        "amount": p.amount,
        "eligible_seats": p.eligible_seats,
        "is_main": p.is_main,
    }


def _serialize_hand(hand: HandRecord) -> dict:
    return {
        "hand_id": hand.hand_id,
        "table_id": hand.table_id,
        "tournament_id": hand.tournament_id,
        "started_at": hand.started_at,
        "ended_at": hand.ended_at,
        "sb_amount": hand.sb_amount,
        "bb_amount": hand.bb_amount,
        "ante": hand.ante,
        "straddle": hand.straddle,
        "hero_seat": hand.hero_seat,
        "hero_cards": [_serialize_card(c) for c in hand.hero_cards],
        "dealer_seat": hand.dealer_seat,
        "streets": {s.value: _serialize_street_record(sr)
                    for s, sr in hand.streets.items()},
        "pots": [_serialize_pot(p) for p in hand.pots],
        "winners": hand.winners,
        "stack_deltas": hand.stack_deltas,
        "snapshot_paths": hand.snapshot_paths,
    }


def _serialize_tournament(t: Optional[TournamentInfo]) -> Optional[dict]:
    if t is None:
        return None
    return {
        "tournament_id": t.tournament_id,
        "table_number": t.table_number,
        "level": t.level,
        "players_remaining": t.players_remaining,
        "average_stack": t.average_stack,
        "is_itm": t.is_itm,
    }


def _serialize_session(session: TableSession) -> str:
    data = {
        "table_id": session.table_id,
        "room_name": session.room_name,
        "game_type": session.game_type.value,
        "stakes": session.stakes,
        "table_name": session.table_name,
        "max_seats": session.max_seats,
        "created_at": session.created_at,
        "last_seen_at": session.last_seen_at,
        "last_hand_id": session.last_hand_id,
        "last_x": session.last_x,
        "last_y": session.last_y,
        "last_w": session.last_w,
        "last_h": session.last_h,
        "last_player_names": session.last_player_names,
        "tournament": _serialize_tournament(session.tournament),
        "hands": [_serialize_hand(h) for h in session.hands],
    }
    return json.dumps(data, ensure_ascii=False)


# ============================================================
# Desserializacao (dict -> dataclass)
# ============================================================

def _deserialize_card(d: dict) -> Card:
    return Card(rank=d["rank"], suit=d["suit"])


def _deserialize_action(d: dict) -> Action:
    return Action(
        order=d["order"],
        player_name=d["player_name"],
        seat=d["seat"],
        type=ActionType(d["type"]),
        amount=d["amount"],
        street=Street(d["street"]),
        timestamp=d["timestamp"],
    )


def _deserialize_street_record(d: dict) -> StreetRecord:
    return StreetRecord(
        street=Street(d["street"]),
        board_before=[_deserialize_card(c) for c in d.get("board_before", [])],
        pot_before=d["pot_before"],
        actions=[_deserialize_action(a) for a in d.get("actions", [])],
        pot_after=d["pot_after"],
    )


def _deserialize_pot(d: dict) -> Pot:
    return Pot(
        amount=d["amount"],
        eligible_seats=d.get("eligible_seats", []),
        is_main=d.get("is_main", True),
    )


def _deserialize_hand(d: dict) -> HandRecord:
    streets = {}
    for street_val, sr_data in d.get("streets", {}).items():
        streets[Street(street_val)] = _deserialize_street_record(sr_data)

    return HandRecord(
        hand_id=d["hand_id"],
        table_id=d["table_id"],
        tournament_id=d.get("tournament_id"),
        started_at=d["started_at"],
        ended_at=d.get("ended_at"),
        sb_amount=d.get("sb_amount", 0.0),
        bb_amount=d.get("bb_amount", 0.0),
        ante=d.get("ante", 0.0),
        straddle=d.get("straddle", 0.0),
        hero_seat=d.get("hero_seat"),
        hero_cards=[_deserialize_card(c) for c in d.get("hero_cards", [])],
        dealer_seat=d.get("dealer_seat", -1),
        streets=streets,
        pots=[_deserialize_pot(p) for p in d.get("pots", [])],
        winners=d.get("winners", []),
        stack_deltas=d.get("stack_deltas", {}),
        snapshot_paths=d.get("snapshot_paths", []),
    )


def _deserialize_tournament(d: Optional[dict]) -> Optional[TournamentInfo]:
    if not d:
        return None
    return TournamentInfo(
        tournament_id=d["tournament_id"],
        table_number=d["table_number"],
        level=d.get("level", 1),
        players_remaining=d.get("players_remaining", 0),
        average_stack=d.get("average_stack", 0.0),
        is_itm=d.get("is_itm", False),
    )


def _deserialize_session(payload: str) -> TableSession:
    d = json.loads(payload)
    return TableSession(
        table_id=d["table_id"],
        room_name=d["room_name"],
        game_type=GameType(d["game_type"]),
        stakes=d["stakes"],
        table_name=d["table_name"],
        max_seats=d.get("max_seats", 9),
        created_at=d["created_at"],
        last_seen_at=d["last_seen_at"],
        last_hand_id=d.get("last_hand_id"),
        last_x=d.get("last_x", 0),
        last_y=d.get("last_y", 0),
        last_w=d.get("last_w", 0),
        last_h=d.get("last_h", 0),
        last_player_names=d.get("last_player_names", []),
        tournament=_deserialize_tournament(d.get("tournament")),
        hands=[_deserialize_hand(h) for h in d.get("hands", [])],
    )


# ============================================================
# Store
# ============================================================

class TableSessionStore:
    """Persistencia SQLite de TableSession."""

    def __init__(self, db_path: str = "pktm_sessions.db"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with _lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    table_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    last_seen_at REAL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_last_seen
                ON sessions(last_seen_at)
            """)
            conn.commit()

    def save(self, session: TableSession) -> None:
        """Salva (ou atualiza) uma sessao. Substitui integralmente."""
        payload = _serialize_session(session)
        with _lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (table_id, data, last_seen_at) "
                "VALUES (?, ?, ?)",
                (session.table_id, payload, session.last_seen_at),
            )
            conn.commit()

    def load(self, table_id: str) -> Optional[TableSession]:
        with _lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM sessions WHERE table_id = ?",
                (table_id,),
            ).fetchone()
        if not row:
            return None
        return _deserialize_session(row[0])

    def load_all(self) -> List[TableSession]:
        with _lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT data FROM sessions").fetchall()
        return [_deserialize_session(r[0]) for r in rows]

    def delete(self, table_id: str) -> None:
        with _lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE table_id = ?", (table_id,))
            conn.commit()

    def count(self) -> int:
        with _lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
        return row[0] if row else 0
