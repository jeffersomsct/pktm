"""
main.py
Captura as mesas abertas e guarda UMA captura por numero de mao em data/ (ver storage/capture_store.py).

Sem hash nem identificacao de mesa: a chave e o numero da mao. Quem decide QUANDO capturar (por
exemplo, so quando o heroi estiver com as cartas) e o chamador; aqui cada execucao captura uma vez.

LIVE = False roda sobre a imagem de exemplo, sem mesa ao vivo (qualquer sistema operacional).
"""
from core.imageio import read_image
from paths import DATA_DIR
from core.printer import print_players_table, print_table_status
from rooms.poker_room import PokerRoom
from storage.capture_store import EXISTS, NO_HAND, SAVED, CaptureStore


# ============================================================
# Configuracao
# ============================================================

PKR_ROOM_NAME = "SwC Poker - Logged in as jeffpk"
LIVE = False                                      # True = captura ao vivo (Windows)

# Titulo da janela da imagem de exemplo (de onde saem as blinds no modo exemplo).
SAMPLE_TITLE = "Hourly Freeroll - NLH [10 Chips]  -  Level 20/40 ante 8;  Next Level 25/50 ante 10"


# ============================================================
# Fluxo principal
# ============================================================

def main():
    store = CaptureStore(DATA_DIR)

    # ---- Captura ----
    if LIVE:
        from core.window_handler import detect_windows   # so Windows (pywin32)
        tables = detect_windows(PKR_ROOM_NAME)
        if not tables:
            print("Nenhuma mesa encontrada.")
            return
    else:
        sample = read_image(PokerRoom(PKR_ROOM_NAME).config.sample_image_path)
        tables = [{"title": SAMPLE_TITLE, "image": sample}]

    for table in tables:
        title, image = table["title"], table["image"]

        # ---- Le a mesa ----
        room = PokerRoom(PKR_ROOM_NAME)
        room.update_table_state(image, title=title)

        # ---- Exibe ----
        print_table_status(room)
        print_players_table(room)
        print(f"Blinds (do titulo): SB={room.sb_amount} BB={room.bb_amount} Ante={room.ante}")

        # ---- Guarda (uma captura por mao) ----
        status, path = store.save(room.table_info, title, image)
        if status == SAVED:
            print(f"[SALVA] mao {room.hand_id} -> {path}")
        elif status == EXISTS:
            print(f"[JA EXISTIA] mao {room.hand_id}: a primeira captura foi mantida")
        elif status == NO_HAND:
            print(f"[SEM NUMERO DE MAO] o OCR nao leu a mao; imagem guardada em {path}")

    print(f"\nTotal de maos capturadas: {store.count()}")


if __name__ == "__main__":
    main()
