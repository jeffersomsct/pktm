"""
main.py
Exemplo de uso da estrutura refatorada.

Demonstra:
  - Deteccao multi-mesa (detect_windows)
  - Identificacao de TableSession por table_id (com match fuzzy)
  - Persistencia via TableSessionStore (SQLite)
  - HandOrchestrator montando HandRecord com sequencia de acoes
  - Snapshots organizados por table_id/hand_id/tag

Para rodar em modo "foto de exemplo" (sem mesa ao vivo), deixe LIVE = False.
"""
import hashlib
import re

from PIL import Image
import cv2

from rooms.poker_room import PokerRoom
from core.window_handler import detect_windows
from core.printer import print_players_table, print_table_status, print_hand_summary
from core.match_table import ObservedTable, find_matching_session
from core.models import GameType, TableSession, TournamentInfo
from storage.table_session_store import TableSessionStore
from action.hand_orchestrator import HandOrchestrator
from images.snapshot_saver import SnapshotSaver


# ============================================================
# Configuracao
# ============================================================

PKR_ROOM_NAME = "SwC Poker - Logged in as jeffpk"
LIVE = False                                      # True = captura ao vivo
DB_PATH = "pktm_sessions.db"
SNAPSHOT_DIR = "imgs"


# ============================================================
# Helpers de parsing
# ============================================================

def parse_swc_title(title: str) -> dict:
    """
    Faz parse do titulo da janela do SwC.
    Retorna dict com stakes, table_name, tournament_id, table_number.
    """
    info = {
        "stakes": "",
        "table_name": title,
        "tournament_id": None,
        "table_number": None,
    }
    # MTT: "T#12345 - Table 4" ou "T#12345 Table 4"
    m = re.search(r"T#(\d+).*Table\s*(\d+)", title, re.IGNORECASE)
    if m:
        info["tournament_id"] = m.group(1)
        info["table_number"] = int(m.group(2))
        info["table_name"] = f"T#{m.group(1)} Table {m.group(2)}"
        info["stakes"] = "MTT"
        return info
    # Cash: "0.10/0.20 Table Kraken"
    m = re.search(r"(\d+\.?\d*)\s*/\s*(\d+\.?\d*)", title)
    if m:
        info["stakes"] = f"{m.group(1)}/{m.group(2)}"
        rest = re.sub(r"\d+\.?\d*\s*/\s*\d+\.?\d*", "", title).strip()
        info["table_name"] = rest or title
    return info


def make_table_id(
    room_name: str,
    game_type: GameType,
    stakes: str,
    table_name: str,
    tournament_id: str = None,
    table_number: int = None,
) -> str:
    """Hash estavel do table_id (16 chars hex)."""
    parts = [room_name, game_type.value, stakes, table_name]
    if tournament_id and table_number is not None:
        parts.extend([tournament_id, str(table_number)])
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


# ============================================================
# Fluxo principal
# ============================================================

def main():
    store = TableSessionStore(DB_PATH)
    saver = SnapshotSaver(SNAPSHOT_DIR)
    sessions = store.load_all()

    # ---- Captura ----
    if LIVE:
        tables = detect_windows(PKR_ROOM_NAME)
        if not tables:
            print("Nenhuma mesa encontrada.")
            return
    else:
        # Modo exemplo: uma mesa "fantasma" usando sample image da config
        tables = [{
            "hwnd": 0,
            "title": PKR_ROOM_NAME,
            "x": 100, "y": 100, "w": 0, "h": 0,
            "image": None,
        }]

    for tbl in tables:
        title = tbl["title"]
        parsed = parse_swc_title(title)

        game_type = GameType.MTT if parsed["tournament_id"] else GameType.CASH
        table_id = make_table_id(
            PKR_ROOM_NAME, game_type, parsed["stakes"],
            parsed["table_name"],
            parsed["tournament_id"], parsed["table_number"],
        )

        # ---- Match com sessao existente ----
        observed = ObservedTable(
            room_name=PKR_ROOM_NAME,
            game_type=game_type,
            stakes=parsed["stakes"],
            table_name=parsed["table_name"],
            title=title,
            x=tbl["x"], y=tbl["y"],
            w=tbl["w"], h=tbl["h"],
            tournament_id=parsed["tournament_id"],
            table_number=parsed["table_number"],
        )

        session = find_matching_session(sessions, observed, threshold=60.0)
        if session is None:
            # Mesa nova -- cria TableSession
            tournament = None
            if parsed["tournament_id"]:
                tournament = TournamentInfo(
                    tournament_id=parsed["tournament_id"],
                    table_number=parsed["table_number"],
                )
            session = TableSession(
                table_id=table_id,
                room_name=PKR_ROOM_NAME,
                game_type=game_type,
                stakes=parsed["stakes"],
                table_name=parsed["table_name"],
                last_x=tbl["x"], last_y=tbl["y"],
                last_w=tbl["w"], last_h=tbl["h"],
                tournament=tournament,
            )
            sessions.append(session)
            print(f"[NOVA SESSAO] table_id={table_id} ({game_type.value})")
        else:
            print(f"[SESSAO EXISTENTE] table_id={session.table_id}")

        # Atualiza posicao observada (mesmo em sessao existente)
        session.last_x = tbl["x"]
        session.last_y = tbl["y"]
        session.last_w = tbl["w"]
        session.last_h = tbl["h"]

        # ---- Processa a mesa ----
        room = PokerRoom(PKR_ROOM_NAME)
        room.update_table_state(tbl["image"])

        if room.table_info is None:
            print(f"Falha ao analisar mesa: {title}")
            continue

        # ---- Salva snapshot (com table_id/hand_id) ----
        if tbl["image"] is not None:
            rgb = cv2.cvtColor(tbl["image"], cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            path = saver.save(
                pil_img,
                table_id=session.table_id,
                hand_id=room.hand_id,
                tag="raw",
                title=title,
            )
            room.table_info.snapshot_path = path

        # ---- Fingerprint de jogadores (para match futuro) ----
        observed.player_names = [
            p.name for p in room.players if p.is_present
        ]
        session.last_player_names = observed.player_names

        # ---- Orquestra mao ----
        orch = HandOrchestrator(session)
        hand = orch.process(room.table_info, tag="raw")

        # ---- Exibe ----
        print_table_status(room)
        print_players_table(room)
        print_hand_summary(hand)

        # ---- Persiste ----
        store.save(session)

    print(f"\nTotal de sessoes persistidas: {store.count()}")


if __name__ == "__main__":
    main()
